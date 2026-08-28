#!/usr/bin/env python3
"""Refresh the local Goldhand plugin through the personal marketplace."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PLUGIN_NAME = "goldhand-clinic-blog"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
CREATOR_SCRIPTS = (
    Path.home() / ".codex" / "skills" / ".system" / "plugin-creator" / "scripts"
)
DIRECT_SKILL_PATH = Path.home() / ".codex" / "skills" / PLUGIN_NAME
SOURCE_SKILL_PATH = PLUGIN_ROOT / "skills" / PLUGIN_NAME
PLUGIN_MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
SKILL_ENTRYPOINT_PATH = SOURCE_SKILL_PATH / "SKILL.md"
AUTOMATION_VERSION_PATH = SOURCE_SKILL_PATH / "assets" / "automation-version.json"
PUBLISHER_CONFIG_PATH = (
    Path.home() / ".codex" / "state" / PLUGIN_NAME / "publisher.json"
)
MANIFEST_RELATIVE_PATH = Path(".codex-plugin/plugin.json")
SKILL_RELATIVE_PATH = Path(f"skills/{PLUGIN_NAME}/SKILL.md")
AUTOMATION_VERSION_RELATIVE_PATH = Path(
    f"skills/{PLUGIN_NAME}/assets/automation-version.json"
)
DISPLAY_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SKILL_VERSION_LINE_RE = re.compile(
    r"(?m)^- 현재 자동화 버전: `(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))`$"
)
DYNAMIC_VERSION_STATE_KEYS = {
    "automationVersion",
    "sourceFingerprint",
    "packageVersion",
    "updatedAt",
    "packageUpdatedAt",
}


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON 객체가 아닙니다: {path}")
    return data


def write_json_object(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_display_version(value: str) -> tuple[int, int]:
    match = DISPLAY_VERSION_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"자동화 버전은 major.minor 형식이어야 합니다: {value}")
    return int(match.group(1)), int(match.group(2))


def next_minor_version(value: str) -> str:
    major, minor = parse_display_version(value)
    return f"{major}.{minor + 1}"


def package_base_version(value: str) -> str:
    major, minor = parse_display_version(value)
    return f"{major}.{minor}.0"


def normalized_fingerprint_bytes(relative: Path, path: Path) -> bytes:
    if relative == MANIFEST_RELATIVE_PATH:
        manifest = load_json_object(path)
        manifest.pop("version", None)
        return json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    if relative == AUTOMATION_VERSION_RELATIVE_PATH:
        state = load_json_object(path)
        for key in DYNAMIC_VERSION_STATE_KEYS:
            state.pop(key, None)
        return json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    payload = path.read_bytes()
    if relative == SKILL_RELATIVE_PATH:
        text = payload.decode("utf-8")
        # Keep the managed source fingerprint identical across Git checkouts.
        # Windows tests create CRLF files, while the canonical macOS source uses LF.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        matches = list(SKILL_VERSION_LINE_RE.finditer(text))
        if len(matches) != 1:
            raise ValueError("SKILL.md의 관리 대상 자동화 버전 줄은 정확히 하나여야 합니다.")
        text = SKILL_VERSION_LINE_RE.sub(
            "- 현재 자동화 버전: `__MANAGED_AUTOMATION_VERSION__`",
            text,
        )
        return text.encode("utf-8")
    return payload


def source_fingerprint(plugin_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        plugin_root.rglob("*"),
        key=lambda item: item.relative_to(plugin_root).as_posix(),
    ):
        relative = path.relative_to(plugin_root)
        if (
            "__pycache__" in relative.parts
            or path.suffix == ".pyc"
            or path.name == ".DS_Store"
        ):
            continue
        encoded = relative.as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(
                b"L\0" + encoded + b"\0" + path.readlink().as_posix().encode("utf-8")
            )
        elif path.is_file():
            digest.update(
                b"F\0"
                + encoded
                + b"\0"
                + normalized_fingerprint_bytes(relative, path)
            )
    return digest.hexdigest()


def managed_skill_version(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8")
    matches = list(SKILL_VERSION_LINE_RE.finditer(text))
    if len(matches) != 1:
        raise ValueError("SKILL.md의 관리 대상 자동화 버전 줄은 정확히 하나여야 합니다.")
    return matches[0].group("version")


def set_managed_skill_version(skill_path: Path, version: str) -> None:
    parse_display_version(version)
    text = skill_path.read_text(encoding="utf-8")
    matches = list(SKILL_VERSION_LINE_RE.finditer(text))
    if len(matches) != 1:
        raise ValueError("SKILL.md의 관리 대상 자동화 버전 줄은 정확히 하나여야 합니다.")
    updated = SKILL_VERSION_LINE_RE.sub(
        f"- 현재 자동화 버전: `{version}`",
        text,
    )
    if updated != text:
        skill_path.write_text(updated, encoding="utf-8")


def sync_automation_version(
    plugin_root: Path = PLUGIN_ROOT,
    *,
    now: str | None = None,
) -> dict:
    state_path = plugin_root / AUTOMATION_VERSION_RELATIVE_PATH
    manifest_path = plugin_root / MANIFEST_RELATIVE_PATH
    skill_path = plugin_root / SKILL_RELATIVE_PATH
    state = load_json_object(state_path)
    if state.get("schemaVersion") != 1:
        raise ValueError("지원하지 않는 자동화 버전 상태 형식입니다.")
    previous_version = str(state.get("automationVersion", "")).strip()
    parse_display_version(previous_version)
    if managed_skill_version(skill_path) != previous_version:
        raise ValueError("SKILL.md와 자동화 버전 상태 파일의 버전이 일치하지 않습니다.")

    fingerprint = source_fingerprint(plugin_root)
    previous_fingerprint = str(state.get("sourceFingerprint", "")).strip()
    initialized = not previous_fingerprint
    content_changed = bool(previous_fingerprint and previous_fingerprint != fingerprint)
    current_version = (
        next_minor_version(previous_version) if content_changed else previous_version
    )

    manifest = load_json_object(manifest_path)
    existing_package_version = str(manifest.get("version", "")).strip()
    suffix = ""
    if "+" in existing_package_version:
        suffix = "+" + existing_package_version.split("+", 1)[1]
    target_package_version = package_base_version(current_version) + suffix
    manifest_changed = existing_package_version != target_package_version

    set_managed_skill_version(skill_path, current_version)
    manifest["version"] = target_package_version
    if manifest_changed:
        write_json_object(manifest_path, manifest)

    state["automationVersion"] = current_version
    state["sourceFingerprint"] = fingerprint
    if initialized or content_changed:
        state["updatedAt"] = now or utc_now()
    if initialized or content_changed or manifest_changed:
        state["packageVersion"] = ""
        state.pop("packageUpdatedAt", None)
    write_json_object(state_path, state)

    package_version = str(state.get("packageVersion", "")).strip()
    needs_cachebuster = (
        initialized
        or content_changed
        or manifest_changed
        or not package_version
        or package_version != target_package_version
    )
    return {
        "previousVersion": previous_version,
        "currentVersion": current_version,
        "initialized": initialized,
        "contentChanged": content_changed,
        "needsCachebuster": needs_cachebuster,
    }


def mark_package_version(
    plugin_root: Path = PLUGIN_ROOT,
    *,
    now: str | None = None,
) -> str:
    state_path = plugin_root / AUTOMATION_VERSION_RELATIVE_PATH
    manifest_path = plugin_root / MANIFEST_RELATIVE_PATH
    state = load_json_object(state_path)
    manifest = load_json_object(manifest_path)
    automation_version = str(state.get("automationVersion", "")).strip()
    package_version = str(manifest.get("version", "")).strip()
    expected_prefix = package_base_version(automation_version) + "+codex."
    if not package_version.startswith(expected_prefix):
        raise ValueError(
            "플러그인 패키지 버전이 현재 자동화 버전과 일치하지 않습니다: "
            f"{package_version}"
        )
    state["packageVersion"] = package_version
    state["packageUpdatedAt"] = now or utc_now()
    write_json_object(state_path, state)
    return package_version


def cleanup_generated_bytecode() -> None:
    """Keep interpreter caches out of the shareable plugin package."""
    for cache_dir in PLUGIN_ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
    for bytecode in PLUGIN_ROOT.rglob("*.pyc"):
        if bytecode.is_file():
            bytecode.unlink()


def remove_duplicate_direct_skill() -> bool:
    """Keep discovery plugin-only so the same skill is not shown twice."""
    if not DIRECT_SKILL_PATH.is_symlink() and not DIRECT_SKILL_PATH.exists():
        return False
    if not DIRECT_SKILL_PATH.is_symlink():
        raise ValueError(
            f"직접 스킬 경로가 심볼릭 링크가 아니어서 자동 제거하지 않습니다: {DIRECT_SKILL_PATH}"
        )
    resolved = DIRECT_SKILL_PATH.resolve(strict=False)
    expected = SOURCE_SKILL_PATH.resolve(strict=False)
    if resolved != expected:
        raise ValueError(f"직접 스킬 링크 대상 불일치: {resolved}")
    DIRECT_SKILL_PATH.unlink()
    return True


def marketplace_name() -> str:
    data = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("개인 마켓플레이스 이름을 찾을 수 없습니다.")
    entries = data.get("plugins", [])
    expected = (Path.home() / "plugins" / PLUGIN_NAME).resolve()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or entry.get("name") != PLUGIN_NAME:
            continue
        source = entry.get("source", {})
        if not isinstance(source, dict) or source.get("source") != "local":
            raise ValueError("마켓플레이스의 금손 플러그인이 로컬 소스를 가리키지 않습니다.")
        relative = str(source.get("path", ""))
        if not relative.startswith("./"):
            raise ValueError(f"지원하지 않는 마켓플레이스 상대경로: {relative}")
        resolved = (Path.home() / relative.removeprefix("./")).resolve()
        if resolved != expected or resolved != PLUGIN_ROOT.resolve():
            raise ValueError(f"마켓플레이스 소스 불일치: {resolved}")
        return name
    raise ValueError("개인 마켓플레이스에 금손 플러그인 항목이 없습니다.")


def publish_public_update_if_enabled() -> bool:
    """Publish only on the owner's machine with an explicit local opt-in file."""
    if os.environ.get("GOLDHAND_SKIP_AUTO_PUBLISH") == "1":
        print("소유자 공개 자동 배포를 이번 실행에서만 건너뛰었습니다.")
        return False
    if not PUBLISHER_CONFIG_PATH.is_file():
        return False
    data = json.loads(PUBLISHER_CONFIG_PATH.read_text(encoding="utf-8"))
    if data.get("autoPublish") is not True:
        return False
    distribution_root = Path(str(data.get("distributionRoot", ""))).expanduser().resolve()
    publisher = distribution_root / "scripts" / "publish_update.py"
    if not publisher.is_file():
        raise ValueError(f"공개 자동 배포 스크립트를 찾을 수 없습니다: {publisher}")
    run(
        sys.executable,
        str(publisher),
        "--plugin-root",
        str(PLUGIN_ROOT),
        "--distribution-root",
        str(distribution_root),
    )
    return True


def main() -> int:
    cachebuster = CREATOR_SCRIPTS / "update_plugin_cachebuster.py"
    validator = CREATOR_SCRIPTS / "validate_plugin.py"
    if not cachebuster.is_file() or not validator.is_file():
        return fail("Codex plugin-creator 도구를 찾을 수 없습니다.")
    if not MARKETPLACE_PATH.is_file():
        return fail(f"개인 마켓플레이스를 찾을 수 없습니다: {MARKETPLACE_PATH}")
    try:
        name = marketplace_name()
        removed_duplicate = remove_duplicate_direct_skill()
        cleanup_generated_bytecode()
        run(sys.executable, str(validator), str(PLUGIN_ROOT))
        version_result = sync_automation_version()
        run(sys.executable, str(validator), str(PLUGIN_ROOT))
        if version_result["needsCachebuster"]:
            run(sys.executable, str(cachebuster), str(PLUGIN_ROOT))
            mark_package_version()
        run("codex", "plugin", "add", f"{PLUGIN_NAME}@{name}")
        published = publish_public_update_if_enabled()
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return fail(f"플러그인 새로고침 실패: {exc}")
    if removed_duplicate:
        print("중복 노출을 만들던 직접 사용자 스킬 링크를 제거했습니다.")
    if version_result["initialized"]:
        print(f"자동화 버전 기준을 v{version_result['currentVersion']}으로 설정했습니다.")
    elif version_result["contentChanged"]:
        print(
            "자동화 버전을 "
            f"v{version_result['previousVersion']}에서 "
            f"v{version_result['currentVersion']}으로 올렸습니다."
        )
    else:
        print(f"자동화 버전은 v{version_result['currentVersion']}으로 유지했습니다.")
    print("금손한의원 플러그인을 하나의 개인 플러그인으로 새로고침했습니다. 새 Codex 작업에서 확인하세요.")
    if published:
        print("GitHub 공개 릴리스와 사용자 자동 업데이트 배포까지 완료했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
