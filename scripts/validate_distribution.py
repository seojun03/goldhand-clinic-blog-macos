#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "goldhand-clinic-blog"
PLUGIN_ROOT = ROOT / "plugins" / PLUGIN_NAME
MARKETPLACE_NAME = "goldhand-clinic-macos"
REPOSITORY = "seojun03/goldhand-clinic-blog-macos"
PUBLIC_VERSION_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\+codex\.\d{14}$"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    required = [
        ROOT / "INSTALL-MAC.command",
        ROOT / "SETUP-IMAGES-MAC.command",
        ROOT / "install-from-download-macos.sh",
        ROOT / "requirements-macos.txt",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / "scripts" / "update-macos.sh",
        ROOT / "scripts" / "validate_distribution.py",
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / "skills" / PLUGIN_NAME / "SKILL.md",
        PLUGIN_ROOT / "skills" / PLUGIN_NAME / "scripts" / "setup_image_host.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    require(not missing, "missing required macOS files: " + ", ".join(missing))

    forbidden = []
    for path in ROOT.rglob("*"):
        if path.name in {".DS_Store", "__pycache__"} or path.suffix in {".pyc", ".pyo"}:
            forbidden.append(str(path.relative_to(ROOT)))
    require(not forbidden, "forbidden cache files: " + ", ".join(forbidden))

    root_names = {path.name for path in ROOT.iterdir()}
    require("INSTALL-WINDOWS.cmd" not in root_names, "Windows installer must never appear in the macOS distribution")
    require("SETUP-IMAGES-WINDOWS.cmd" not in root_names, "Windows image setup must never appear in the macOS distribution")
    require("install-from-download-windows.ps1" not in root_names, "Windows PowerShell installer must never appear in the macOS distribution")
    require("requirements-windows.txt" not in root_names, "Windows requirements must never appear in the macOS distribution root")

    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    require(marketplace.get("name") == MARKETPLACE_NAME, "macOS marketplace name is not isolated")
    require(len(marketplace.get("plugins", [])) == 1, "macOS marketplace must contain exactly one plugin")
    entry = marketplace["plugins"][0]
    require(entry.get("name") == PLUGIN_NAME, "macOS marketplace plugin name mismatch")
    require(entry.get("source", {}).get("path") == f"./plugins/{PLUGIN_NAME}", "macOS marketplace plugin path mismatch")

    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    require(
        PUBLIC_VERSION_RE.fullmatch(version) is not None,
        "plugin version is not release-addressable",
    )

    bootstrap = (ROOT / "INSTALL-MAC.command").read_text(encoding="utf-8")
    installer = (ROOT / "install-from-download-macos.sh").read_text(encoding="utf-8")
    updater = (ROOT / "scripts" / "update-macos.sh").read_text(encoding="utf-8")
    image_launcher = (ROOT / "SETUP-IMAGES-MAC.command").read_text(encoding="utf-8")
    setup_python = (PLUGIN_ROOT / "skills" / PLUGIN_NAME / "scripts" / "setup_image_host.py").read_text(encoding="utf-8")

    require(REPOSITORY in bootstrap and REPOSITORY in updater, "macOS public repository is not fixed")
    require("goldhand-clinic-blog-macos.zip" in bootstrap and "goldhand-clinic-blog-macos.zip" in updater, "macOS release archive is not fixed")
    require("Darwin" in bootstrap and "Darwin" in installer, "macOS operating-system gate is missing")
    require("GoldhandBlogMac" in installer and "goldhand-clinic-macos" in installer, "macOS install folder or marketplace isolation is missing")
    require("GoldhandBlog" + "Mac" in installer, "macOS managed folder is missing")
    require("goldhand-clinic-windows" not in installer and "goldhand-clinic-blog-windows" not in installer, "Windows distribution identifiers leaked into the macOS installer")
    require("INSTALL-WINDOWS" not in bootstrap and "INSTALL-WINDOWS" not in updater, "Windows installer names leaked into macOS executable files")
    require("setup_image_host.py" in image_launcher, "macOS image retry launcher is incomplete")
    require("state/goldhand-clinic-blog" in installer, "persistent macOS state location is missing")
    require("nodejs.org/dist/index.tab" in installer, "private Node.js fallback is missing")
    require("astral.sh/uv/install.sh" in installer, "private Python fallback is missing")
    require("https://chatgpt.com/codex/install.sh" in installer, "official Codex fallback is missing")
    require("npm" in installer and "install --global vercel" in installer, "managed Vercel CLI installation is missing")
    require("GOLDHANDBLOG_SKIP_IMAGE_HOST_SETUP" in installer and "GOLDHANDBLOG_SKIP_IMAGE_HOST_SETUP=1" in updater, "background updates could trigger browser login")
    require("LaunchAgents" in installer and "StartInterval" in installer and "21600" in installer, "six-hour macOS updater registration is missing")
    require("GOLDHANDBLOG_MAC_UPDATE_ARCHIVE" in updater, "local updater regression route is missing")
    require(
        'vercel_command(["login", "--no-color", "--non-interactive"])'
        in setup_python
        and "run_prefilled_device_login(project_dir)" in setup_python
        and "prefilled_vercel_device_url" in setup_python,
        "browser-approved Vercel login is missing",
    )
    require('run_vercel(["project", "add"' in setup_python and 'run_vercel(["link"' in setup_python, "automatic Vercel project setup is missing")
    require("--token" not in installer and "VERCEL_TOKEN=" not in installer, "macOS installer must not bundle a Vercel credential")
    require("--token" not in setup_python.lower() and "vercel_token=" not in setup_python.lower(), "image setup must not bundle a Vercel credential")

    for script in [ROOT / "INSTALL-MAC.command", ROOT / "SETUP-IMAGES-MAC.command", ROOT / "install-from-download-macos.sh", ROOT / "scripts" / "update-macos.sh"]:
        require(os.access(script, os.X_OK), f"macOS executable bit is missing: {script.relative_to(ROOT)}")
        parsed = subprocess.run(["/bin/bash", "-n", str(script)], text=True, capture_output=True, check=False)
        require(parsed.returncode == 0, f"shell parse failed for {script.relative_to(ROOT)}: {parsed.stderr.strip()}")

    print(f"macOS distribution validation passed: {PLUGIN_NAME} {version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"macOS distribution validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
