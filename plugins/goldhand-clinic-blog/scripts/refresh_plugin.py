#!/usr/bin/env python3
"""Refresh the local Goldhand plugin through the personal marketplace."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_NAME = "goldhand-clinic-blog"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
CREATOR_SCRIPTS = (
    Path.home() / ".codex" / "skills" / ".system" / "plugin-creator" / "scripts"
)
DIRECT_SKILL_PATH = Path.home() / ".codex" / "skills" / PLUGIN_NAME
SOURCE_SKILL_PATH = PLUGIN_ROOT / "skills" / PLUGIN_NAME


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def run(*args: str) -> None:
    subprocess.run(args, check=True)


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
        run(sys.executable, str(cachebuster), str(PLUGIN_ROOT))
        run("codex", "plugin", "add", f"{PLUGIN_NAME}@{name}")
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return fail(f"플러그인 새로고침 실패: {exc}")
    if removed_duplicate:
        print("중복 노출을 만들던 직접 사용자 스킬 링크를 제거했습니다.")
    print("금손한의원 플러그인을 하나의 개인 플러그인으로 새로고침했습니다. 새 Codex 작업에서 확인하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
