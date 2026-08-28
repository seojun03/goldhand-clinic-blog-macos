#!/usr/bin/env python3
"""Set up the one-time Vercel image host used by Goldhand Naver HTML."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Callable


CONFIG_ENV = "GOLDHAND_IMAGE_HOST_CONFIG"
PROJECT_DIR_ENV = "GOLDHAND_IMAGE_HOST_PROJECT_DIR"
PROJECT_NAME_ENV = "GOLDHAND_IMAGE_HOST_PROJECT_NAME"
VERCEL_CLI_ENV = "GOLDHAND_VERCEL_CLI"
DEFAULT_PROJECT_NAME = "goldhand-blog-images"
LOGIN_ATTEMPTS = 2
LOGIN_URL_WAIT_SECONDS = 45
LOGIN_ATTEMPT_TIMEOUT_SECONDS = 630
MINIMUM_VERCEL_CLI_VERSION = (50, 44, 0)
SEMVER_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")
HTTPS_URL_RE = re.compile(r"https://[^\s\x07\x1b]+")
DEVICE_VALUE_RE = re.compile(r"^[A-Za-z0-9._~-]+$")
LOGIN_SUCCESS = "success"
LOGIN_RETRYABLE = "retryable"
LOGIN_FAILED = "failed"
_VERCEL_CLI_OVERRIDE: str | None = None


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
    if _VERCEL_CLI_OVERRIDE:
        return _VERCEL_CLI_OVERRIDE
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


def command_for_vercel_executable(
    resolved: str,
    arguments: list[str],
    platform_name: str | None = None,
) -> list[str]:
    windows = (platform_name or os.name) == "nt"
    if windows and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", resolved, *arguments]
    return [resolved, *arguments]


def vercel_command(arguments: list[str], platform_name: str | None = None) -> list[str]:
    return command_for_vercel_executable(resolve_vercel_cli(platform_name), arguments, platform_name)


def vercel_cli_candidates(platform_name: str | None = None) -> list[str]:
    windows = (platform_name or os.name) == "nt"
    names = ("vercel.cmd", "vercel.exe", "vercel") if windows else ("vercel",)
    candidates: list[str] = []
    explicit = os.environ.get(VERCEL_CLI_ENV, "").strip()
    if explicit:
        candidates.append(explicit)
    if _VERCEL_CLI_OVERRIDE:
        candidates.append(_VERCEL_CLI_OVERRIDE)
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            candidates.append(resolved)
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        for name in names:
            path = Path(directory) / name
            if path.is_file():
                candidates.append(str(path))
    if windows:
        for root in (
            os.environ.get("NPM_CONFIG_PREFIX", ""),
            str(Path(os.environ["APPDATA"]) / "npm") if os.environ.get("APPDATA") else "",
            str(Path(os.environ["LOCALAPPDATA"]) / "npm") if os.environ.get("LOCALAPPDATA") else "",
        ):
            if root:
                for name in ("vercel.cmd", "vercel.exe"):
                    path = Path(root) / name
                    if path.is_file():
                        candidates.append(str(path))
    else:
        for path in (
            codex_home_dir() / "state" / "goldhand-clinic-blog" / "bin" / "vercel",
            Path.home() / ".local" / "bin" / "vercel",
            Path("/opt/homebrew/bin/vercel"),
            Path("/usr/local/bin/vercel"),
        ):
            if path.is_file() and os.access(path, os.X_OK):
                candidates.append(str(path))
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


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


def parse_vercel_cli_version(output: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.search(output)
    return tuple(int(part) for part in match.groups()) if match else None


def ensure_supported_vercel_cli(project_dir: Path) -> None:
    global _VERCEL_CLI_OVERRIDE
    for candidate in vercel_cli_candidates():
        try:
            result = subprocess.run(
                command_for_vercel_executable(candidate, ["--version"]),
                cwd=project_dir,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        version = parse_vercel_cli_version((result.stdout or "") + "\n" + (result.stderr or ""))
        if result.returncode == 0 and version is not None and version >= MINIMUM_VERCEL_CLI_VERSION:
            _VERCEL_CLI_OVERRIDE = candidate
            return
    minimum = ".".join(str(part) for part in MINIMUM_VERCEL_CLI_VERSION)
    raise SetupError(f"Vercel CLI {minimum} 이상이 필요합니다. Windows 설치 파일을 다시 실행해 주세요.")


def prefilled_vercel_device_url(output: str) -> str | None:
    """Return only Vercel's complete approval URL from a CLI ``Visit`` line."""

    if "Visit " not in output:
        return None
    for match in HTTPS_URL_RE.finditer(output):
        candidate = match.group(0).rstrip("'\"),.;]}")
        try:
            parsed = urllib.parse.urlsplit(candidate)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
            base_valid = (
                parsed.scheme == "https"
                and parsed.hostname == "vercel.com"
                and parsed.port in (None, 443)
                and parsed.username is None
                and parsed.password is None
                and not parsed.fragment
            )
            query_form = (
                parsed.path == "/oauth/device"
                and set(query) == {"user_code"}
                and len(query["user_code"]) == 1
                and bool(DEVICE_VALUE_RE.fullmatch(query["user_code"][0]))
            ) or (
                parsed.path == "/device"
                and set(query) == {"code"}
                and len(query["code"]) == 1
                and bool(DEVICE_VALUE_RE.fullmatch(query["code"][0]))
            )
            path_match = re.fullmatch(r"/oauth/device/([A-Za-z0-9._~-]+)", parsed.path)
            path_form = (
                path_match is not None
                and set(query) == {"v"}
                and len(query["v"]) == 1
                and bool(DEVICE_VALUE_RE.fullmatch(query["v"][0]))
            )
            valid = base_valid and (query_form or path_form)
        except (TypeError, ValueError):
            valid = False
        if valid:
            return candidate
    return None


def stop_login_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def run_prefilled_device_login(
    project_dir: Path,
    *,
    browser_opener: Callable[..., bool] | None = None,
) -> str:
    """Run one bounded Vercel login and open only its code-prefilled URL."""

    environment = os.environ.copy()
    environment.update(
        {
            # Vercel skips its own opener in CI. We open the exact validated URL
            # ourselves so a ChatGPT task cannot lose the one-time code.
            "CI": "1",
            "NO_COLOR": "1",
            "TERM": "dumb",
            "FORCE_HYPERLINK": "0",
        }
    )
    popen_kwargs: dict[str, Any] = {
        "cwd": project_dir,
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(
        vercel_command(["login", "--no-color", "--non-interactive"]),
        **popen_kwargs,
    )
    url_ready = threading.Event()
    discovered: dict[str, str] = {}
    retryable_failure = threading.Event()

    def consume_output() -> None:
        assert process.stdout is not None
        try:
            for line in iter(process.stdout.readline, ""):
                lowered = line.lower()
                if "timed out waiting for authentication" in lowered or "expired_token" in lowered:
                    retryable_failure.set()
                url = prefilled_vercel_device_url(line)
                if url and "url" not in discovered:
                    discovered["url"] = url
                    url_ready.set()
        except (OSError, ValueError):
            pass

    reader = threading.Thread(target=consume_output, name="goldhand-vercel-login-output", daemon=True)
    reader.start()

    try:
        deadline = time.monotonic() + LOGIN_URL_WAIT_SECONDS
        while not url_ready.is_set() and process.poll() is None and time.monotonic() < deadline:
            url_ready.wait(timeout=0.2)

        verification_url = discovered.pop("url", None)
        if not verification_url:
            return LOGIN_FAILED

        opener = browser_opener or webbrowser.open
        try:
            opened = bool(opener(verification_url, new=1, autoraise=True))
        except (OSError, webbrowser.Error):
            opened = False
        verification_url = ""
        if not opened:
            return LOGIN_FAILED

        try:
            return_code = process.wait(timeout=LOGIN_ATTEMPT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return LOGIN_RETRYABLE
        if return_code == 0:
            return LOGIN_SUCCESS
        reader.join(timeout=1)
        return LOGIN_RETRYABLE if retryable_failure.is_set() else LOGIN_FAILED
    finally:
        if process.poll() is None:
            stop_login_process(process)
        reader.join(timeout=2)
        if process.stdout is not None:
            process.stdout.close()


def ensure_authenticated(project_dir: Path) -> None:
    status = run_vercel(["whoami", "--format", "json"], project_dir)
    if status.returncode == 0:
        return
    print("\n처음 한 번만 Vercel 로그인이 필요합니다.")
    print("코드가 자동 적용된 브라우저 창에서 본인 계정으로 로그인하고 Allow만 눌러 주세요.")
    print("코드를 직접 찾거나 입력할 필요는 없습니다.\n")
    for attempt in range(LOGIN_ATTEMPTS):
        if attempt:
            print("이전 승인 요청이 만료되어 새 승인 창을 한 번만 더 엽니다.\n")
        login_result = run_prefilled_device_login(project_dir)
        status = run_vercel(["whoami", "--format", "json"], project_dir)
        if status.returncode == 0:
            return
        if login_result != LOGIN_RETRYABLE:
            break
    raise SetupError("Vercel 승인 요청이 완료되지 않았습니다. 빈 코드 입력 화면은 닫고 다시 시도해 주세요.")


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
    ensure_supported_vercel_cli(project_dir)
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
        print("빈 코드 입력 화면은 닫고 Goldhand Image Setup을 다시 실행해 주세요.", file=sys.stderr)
        return 1
    print("\n이미지 자동 연결이 완료되었습니다.")
    print(f"공개 이미지 주소: {payload['publicBaseUrl']}")
    print("앞으로 GPT 이미지는 글 HTML에 자동으로 들어갑니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
