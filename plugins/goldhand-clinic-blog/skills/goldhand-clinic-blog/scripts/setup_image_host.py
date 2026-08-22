#!/usr/bin/env python3
"""Set up the one-time Vercel image host used by Goldhand Naver HTML."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CONFIG_ENV = "GOLDHAND_IMAGE_HOST_CONFIG"
PROJECT_DIR_ENV = "GOLDHAND_IMAGE_HOST_PROJECT_DIR"
PROJECT_NAME_ENV = "GOLDHAND_IMAGE_HOST_PROJECT_NAME"
DEFAULT_PROJECT_NAME = "goldhand-blog-images"


class SetupError(ValueError):
    pass


def codex_home_dir() -> Path:
    override = os.environ.get("CODEX_HOME", "").strip()
    return Path(override).expanduser().resolve() if override else Path.home() / ".codex"


def default_config_path() -> Path:
    return Path(
        os.environ.get(
            CONFIG_ENV,
            str(codex_home_dir() / "state" / "goldhand-clinic-blog" / "image-host.json"),
        )
    ).expanduser()


def default_project_dir() -> Path:
    return Path(
        os.environ.get(
            PROJECT_DIR_ENV,
            str(codex_home_dir() / "state" / "goldhand-clinic-blog" / "image-host-project"),
        )
    ).expanduser()


def default_project_name() -> str:
    raw = os.environ.get(PROJECT_NAME_ENV, DEFAULT_PROJECT_NAME).strip().lower()
    normalized = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
    return normalized or DEFAULT_PROJECT_NAME


def resolve_vercel_cli(platform_name: str | None = None) -> str:
    windows = (platform_name or os.name) == "nt"
    candidates = ("vercel.cmd", "vercel.exe", "vercel") if windows else ("vercel",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    if windows:
        explicit_roots = [
            os.environ.get("NPM_CONFIG_PREFIX", ""),
            str(Path(os.environ["APPDATA"]) / "npm") if os.environ.get("APPDATA") else "",
            str(Path(os.environ["LOCALAPPDATA"]) / "npm") if os.environ.get("LOCALAPPDATA") else "",
        ]
        for root in explicit_roots:
            if not root:
                continue
            for candidate in ("vercel.cmd", "vercel.exe"):
                path = Path(root) / candidate
                if path.is_file():
                    return str(path)
    else:
        explicit_paths = [
            codex_home_dir() / "state" / "goldhand-clinic-blog" / "bin" / "vercel",
            Path.home() / ".local" / "bin" / "vercel",
            Path("/opt/homebrew/bin/vercel"),
            Path("/usr/local/bin/vercel"),
        ]
        for path in explicit_paths:
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    expected = "vercel.cmd 또는 vercel.exe" if windows else "vercel"
    raise SetupError(f"Vercel CLI를 찾을 수 없습니다: {expected}")


def vercel_command(arguments: list[str], platform_name: str | None = None) -> list[str]:
    resolved = resolve_vercel_cli(platform_name)
    windows = (platform_name or os.name) == "nt"
    if windows and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", resolved, *arguments]
    return [resolved, *arguments]


def run_vercel(
    arguments: list[str],
    cwd: Path,
    *,
    interactive: bool = False,
    platform_name: str | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "text": True,
        "check": False,
    }
    if not interactive:
        kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.PIPE})
    return subprocess.run(vercel_command(arguments, platform_name), **kwargs)


def command_detail(result: subprocess.CompletedProcess[str]) -> str:
    return ((result.stderr or "") + "\n" + (result.stdout or "")).strip()[-800:]


def ensure_authenticated(project_dir: Path) -> None:
    status = run_vercel(["whoami", "--format", "json"], project_dir)
    if status.returncode == 0:
        return
    print("\n처음 한 번만 Vercel 로그인이 필요합니다.")
    print("브라우저가 열리면 본인 계정으로 로그인하고 연결을 승인해 주세요.\n")
    login = run_vercel(["login"], project_dir, interactive=True)
    if login.returncode != 0:
        raise SetupError("Vercel 로그인이 완료되지 않았습니다. 이 설정 파일을 다시 실행해 주세요.")
    status = run_vercel(["whoami", "--format", "json"], project_dir)
    if status.returncode != 0:
        raise SetupError("Vercel 로그인 상태를 확인할 수 없습니다.")


def write_host_template(project_dir: Path) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "media").mkdir(parents=True, exist_ok=True)
    (project_dir / "index.html").write_text(
        "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\"><title>Goldhand Blog Images</title>"
        "<body>Goldhand Blog Images</body></html>\n",
        encoding="utf-8",
    )
    (project_dir / "vercel.json").write_text(
        json.dumps(
            {
                "$schema": "https://openapi.vercel.sh/vercel.json",
                "cleanUrls": True,
                "headers": [
                    {
                        "source": "/media/(.*)",
                        "headers": [
                            {
                                "key": "Cache-Control",
                                "value": "public, max-age=31536000, immutable",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / ".gitignore").write_text(".vercel\n", encoding="ascii")


def linked_project(project_dir: Path) -> dict[str, Any] | None:
    link_path = project_dir / ".vercel" / "project.json"
    if not link_path.is_file():
        return None
    try:
        payload = json.loads(link_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if payload.get("projectId") and payload.get("projectName") else None


def ensure_project_link(project_dir: Path, project_name: str) -> dict[str, Any]:
    existing = linked_project(project_dir)
    if existing:
        return existing

    inspected = run_vercel(["project", "inspect", project_name, "--yes"], project_dir)
    if inspected.returncode != 0:
        created = run_vercel(["project", "add", project_name], project_dir)
        if created.returncode != 0:
            inspected_again = run_vercel(["project", "inspect", project_name, "--yes"], project_dir)
            if inspected_again.returncode != 0:
                raise SetupError(f"Vercel 이미지 프로젝트를 만들 수 없습니다: {command_detail(created)}")

    linked = run_vercel(["link", "--yes", "--project", project_name], project_dir)
    if linked.returncode != 0:
        raise SetupError(f"Vercel 이미지 프로젝트를 연결할 수 없습니다: {command_detail(linked)}")
    payload = linked_project(project_dir)
    if not payload:
        raise SetupError("Vercel 연결 정보(.vercel/project.json)가 만들어지지 않았습니다.")
    return payload


def parse_json_output(raw: str) -> Any:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise SetupError("Vercel의 JSON 응답을 읽을 수 없습니다.")


def find_deployment_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("url", "deploymentUrl"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            found = find_deployment_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_deployment_url(value)
            if found:
                return found
    return None


def https_url(value: str) -> str:
    return value if value.startswith("https://") else f"https://{value.lstrip('/')}"


def deploy_and_resolve_public_url(project_dir: Path) -> str:
    deployed = run_vercel(["deploy", "--prod", "--yes", "--format", "json"], project_dir)
    if deployed.returncode != 0:
        raise SetupError(f"이미지 프로젝트를 Vercel에 게시할 수 없습니다: {command_detail(deployed)}")
    deployment_url = find_deployment_url(parse_json_output(deployed.stdout or ""))
    if not deployment_url:
        raise SetupError("Vercel 배포 주소를 찾을 수 없습니다.")

    inspected = run_vercel(["inspect", deployment_url, "--format", "json"], project_dir)
    if inspected.returncode != 0:
        raise SetupError(f"Vercel 배포 주소를 확인할 수 없습니다: {command_detail(inspected)}")
    payload = parse_json_output(inspected.stdout or "")
    aliases = payload.get("aliases", []) if isinstance(payload, dict) else []
    stable_aliases = [https_url(str(alias).strip()) for alias in aliases if str(alias).strip()]
    if not stable_aliases:
        raise SetupError("새 이미지를 계속 올릴 수 있는 Vercel 고정 주소를 찾을 수 없습니다.")
    return min(stable_aliases, key=lambda value: (len(value), value))


def verify_public_base_url(public_base_url: str) -> None:
    request = urllib.request.Request(public_base_url, headers={"User-Agent": "goldhand-image-setup/1.0"})
    last_error: Exception | None = None
    for delay in (0, 1, 2, 4, 6):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status == 200:
                    return
                last_error = SetupError(f"HTTP {response.status}")
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
    raise SetupError(f"Vercel 공개 주소가 아직 열리지 않습니다: {public_base_url} ({last_error})")


def read_valid_config(config_path: Path, project_dir: Path) -> dict[str, Any] | None:
    if not config_path.is_file() or not linked_project(project_dir):
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if Path(str(payload.get("projectDir", ""))).expanduser() != project_dir:
        return None
    public_base_url = str(payload.get("publicBaseUrl", ""))
    return payload if public_base_url.startswith("https://") else None


def write_config(config_path: Path, payload: dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = config_path.with_name(config_path.name + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, config_path)


def setup_image_host(config_path: Path, project_dir: Path, project_name: str, *, force: bool = False) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    project_dir = project_dir.expanduser().resolve()
    write_host_template(project_dir)
    ensure_authenticated(project_dir)

    existing = None if force else read_valid_config(config_path, project_dir)
    if existing:
        verify_public_base_url(str(existing["publicBaseUrl"]))
        return existing

    link = ensure_project_link(project_dir, project_name)
    public_base_url = deploy_and_resolve_public_url(project_dir)
    verify_public_base_url(public_base_url)
    payload = {
        "projectDir": str(project_dir),
        "publicBaseUrl": public_base_url,
        "projectName": str(link["projectName"]),
    }
    write_config(config_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--project-dir", type=Path, default=default_project_dir())
    parser.add_argument("--project-name", default=default_project_name())
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = setup_image_host(args.config, args.project_dir, args.project_name, force=args.force)
    except (OSError, UnicodeError, SetupError) as exc:
        print(f"\n[이미지 자동 연결 실패] {exc}", file=sys.stderr)
        print("브라우저 로그인을 마친 뒤 같은 설정 파일을 다시 실행해 주세요.", file=sys.stderr)
        return 1
    print("\n이미지 자동 연결이 완료되었습니다.")
    print(f"공개 이미지 주소: {payload['publicBaseUrl']}")
    print("앞으로 GPT 이미지는 글 HTML에 자동으로 들어갑니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
