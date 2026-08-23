#!/usr/bin/env python3
"""Build a one-click Naver copy page for a styled Goldhand Clinic article."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


OUTPUT_DIR_ENV = "GOLDHAND_OUTPUT_DIR"
IMAGE_HOST_CONFIG_ENV = "GOLDHAND_IMAGE_HOST_CONFIG"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MEDIA_LIBRARY = SKILL_DIR / "assets" / "media-library.json"
PERSON_SCENE_PREFIX = "director-patient-"
ALLOWED_CLOSING_TRUST_SCENES = {
    "director-agreement-pose",
    "director-community-pose",
    "credential-detail",
}
LOGO_DESCRIPTOR = re.compile(r"(?:로고|logo)", re.I)


def codex_home_dir() -> Path:
    override = os.environ.get("CODEX_HOME", "").strip()
    return Path(override).expanduser().resolve() if override else Path.home() / ".codex"


def default_image_host_config() -> Path:
    return codex_home_dir() / "state" / "goldhand-clinic-blog" / "image-host.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--article-html", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def slugify(title: str) -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣]+", "_", title, flags=re.UNICODE).strip("_")
    return value[:90] or "원고"


def windows_desktop_dir() -> Path:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(str(value))).expanduser()
    except (ImportError, OSError):
        pass
    for variable in ("OneDrive", "USERPROFILE"):
        root = os.environ.get(variable, "").strip()
        if root:
            return Path(root).expanduser() / "Desktop"
    return Path.home() / "Desktop"


def default_output_dir(platform_name: str | None = None) -> Path:
    override = os.environ.get(OUTPUT_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    desktop = windows_desktop_dir() if (platform_name or os.name) == "nt" else Path.home() / "Desktop"
    return desktop / "금손한의원 블로그"


def paste_shortcut(platform_name: str | None = None) -> str:
    return "Ctrl+V" if (platform_name or os.name) == "nt" else "⌘V"


def output_path(title: str, requested: Path | None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    base = default_output_dir() / f"금손한의원_{slugify(title)}.html"
    candidate = base
    index = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.stem}_{index}{base.suffix}")
        index += 1
    return candidate


def article_fragment(raw: str) -> str:
    matches = re.findall(r"<article\b[^>]*>.*?</article>", raw, flags=re.I | re.S)
    if len(matches) != 1:
        raise ValueError("--article-html에는 완전히 꾸민 <article> 하나만 있어야 합니다.")
    return matches[0].strip()


def strip_visible_image_captions(article: str) -> str:
    """Remove legacy visible captions before preview and rich copy output."""

    return re.sub(r"\s*<figcaption\b[^>]*>.*?</figcaption>\s*", "", article, flags=re.I | re.S)


def strip_visible_trust_photo_context(article: str) -> str:
    """Remove legacy trust-photo lead-in prose from preview and rich copy output."""

    cleaned = re.sub(
        r"\s*<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]credential-trust-context['\"])[^>]*>.*?</(?P=tag)>\s*",
        "",
        article,
        flags=re.I | re.S,
    )
    return re.sub(
        r"\s*<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>(?=\s*<figure\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"]))",
        "",
        cleaned,
        flags=re.I | re.S,
    )


def validate_credential_placement(article: str) -> None:
    """Fail closed when the fixed clinic credential table is not before the body."""

    validator_path = Path(__file__).with_name("validate_article.py")
    spec = importlib.util.spec_from_file_location("goldhand_builder_article_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ValueError("금손한의원 소개 표 위치 검증기를 불러올 수 없습니다.")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    issues = validator.credential_placement_issues(article)
    if issues:
        codes = ", ".join(str(issue.get("code", "credential-placement")) for issue in issues)
        raise ValueError(f"금손한의원 소개 표 위치가 올바르지 않습니다: {codes}")


def image_host_config() -> tuple[Path, str]:
    config_path = Path(os.environ.get(IMAGE_HOST_CONFIG_ENV, str(default_image_host_config()))).expanduser()
    if not config_path.is_file():
        raise ValueError(
            "GPT 생성 이미지를 네이버에 붙여넣으려면 금손 전용 HTTPS 이미지 호스트 설정이 필요합니다: "
            f"{config_path}"
        )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"금손 이미지 호스트 설정을 읽을 수 없습니다: {config_path}") from exc
    project_dir = Path(str(config.get("projectDir", ""))).expanduser()
    public_base_url = str(config.get("publicBaseUrl", "")).strip().rstrip("/")
    if not project_dir.is_absolute() or not project_dir.is_dir():
        raise ValueError(f"금손 이미지 호스트 프로젝트 폴더가 없습니다: {project_dir}")
    if not (project_dir / ".vercel" / "project.json").is_file():
        raise ValueError(f"금손 이미지 호스트가 Vercel 프로젝트에 연결되지 않았습니다: {project_dir}")
    if not public_base_url.startswith("https://"):
        raise ValueError("금손 이미지 호스트 주소는 HTTPS여야 합니다.")
    return project_dir, public_base_url


def local_image_paths(article: str) -> list[Path]:
    paths: list[Path] = []
    for raw_path in re.findall(r"\bdata-local-image\s*=\s*(['\"])(.*?)\1", article, flags=re.I | re.S):
        path = Path(html.unescape(raw_path[1])).expanduser()
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"사용자 이미지 파일을 찾을 수 없습니다: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not mime.startswith("image/"):
            raise ValueError(f"이미지 MIME 형식이 아닙니다: {path}")
        if path not in paths:
            paths.append(path)
    return paths


def verify_published_image(url: str) -> None:
    request = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "goldhand-blog-builder/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if response.status not in (200, 206) or not content_type.startswith("image/"):
                raise ValueError(f"게시 이미지 응답이 올바르지 않습니다: {url} ({response.status}, {content_type})")
    except (OSError, urllib.error.URLError) as exc:
        raise ValueError(f"게시 이미지 주소를 확인할 수 없습니다: {url}") from exc


def resolve_vercel_cli(platform_name: str | None = None) -> str:
    """Resolve the npm CLI shim on both Windows and POSIX systems."""

    candidates = ("vercel.cmd", "vercel.exe", "vercel") if (platform_name or os.name) == "nt" else ("vercel",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    if (platform_name or os.name) == "nt":
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
    expected = "vercel.cmd 또는 vercel.exe" if (platform_name or os.name) == "nt" else "vercel"
    raise ValueError(f"금손 이미지 게시용 Vercel CLI를 찾을 수 없습니다: {expected}")


def vercel_deploy_command(platform_name: str | None = None) -> list[str]:
    resolved = resolve_vercel_cli(platform_name)
    if (platform_name or os.name) == "nt" and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", resolved, "--prod", "--yes"]
    return [resolved, "--prod", "--yes"]


def deploy_image_host(project_dir: Path, platform_name: str | None = None) -> None:
    try:
        subprocess.run(
            vercel_deploy_command(platform_name),
            cwd=project_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ValueError(f"금손 이미지 HTTPS 게시에 실패했습니다: {detail.strip()[:400]}") from exc


def publish_local_images(
    article: str,
    project_dir: Path,
    public_base_url: str,
    *,
    deploy: bool = True,
    verify: bool = True,
) -> dict[Path, str]:
    local_paths = local_image_paths(article)
    if not local_paths:
        return {}
    media_dir = project_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    published: dict[Path, str] = {}
    changed = False
    for path in local_paths:
        suffix = path.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            raise ValueError(f"네이버 복사용 HTTPS 게시를 지원하지 않는 이미지 확장자입니다: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        filename = f"{digest}{suffix}"
        target = media_dir / filename
        if not target.is_file() or target.stat().st_size != path.stat().st_size:
            shutil.copy2(path, target)
            changed = True
        published[path] = f"{public_base_url}/media/{filename}"
    if deploy and changed:
        deploy_image_host(project_dir)
    if verify:
        verification_failed = False
        try:
            for url in published.values():
                verify_published_image(url)
        except ValueError:
            verification_failed = True
        if verification_failed and deploy and not changed:
            deploy_image_host(project_dir)
            for url in published.values():
                verify_published_image(url)
        elif verification_failed:
            raise ValueError("게시 이미지 주소 검증에 실패했습니다.")
    return published


def rewrite_img_tags(article: str, published_local_images: dict[Path, str] | None = None) -> str:
    """Restore HTTPS image URLs for the same rich-copy route used by Cheongnyeon."""

    published_local_images = published_local_images or {}

    def rewrite(match: re.Match[str]) -> str:
        tag = match.group(0)
        official = re.search(r"\bdata-reference-source-url\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
        local = re.search(r"\bdata-local-image\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
        if official and local:
            raise ValueError("한 이미지에 공식 원본 URL과 로컬 파일을 함께 지정할 수 없습니다.")
        if official:
            source_url = html.unescape(official.group(2)).strip()
            if not source_url.startswith("https://"):
                raise ValueError("공식 이미지는 HTTPS 원본 URL이어야 합니다.")
            tag = set_attribute(tag, "src", source_url)
            tag = set_attribute(tag, "referrerpolicy", "no-referrer")
            return tag
        if local:
            path = Path(html.unescape(local.group(2))).expanduser()
            source_url = published_local_images.get(path)
            if not source_url or not source_url.startswith("https://"):
                raise ValueError(f"로컬 이미지의 HTTPS 게시 주소가 없습니다: {path}")
            tag = set_attribute(tag, "src", source_url)
            tag = set_attribute(tag, "data-reference-source-url", source_url)
            tag = set_attribute(tag, "referrerpolicy", "no-referrer")
            tag = re.sub(r"\s+data-local-image\s*=\s*(['\"]).*?\1", "", tag, count=1, flags=re.I | re.S)
            return tag
        return tag

    return re.sub(r"<img\b[^>]*>", rewrite, article, flags=re.I | re.S)


def set_attribute(tag: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    if re.search(rf"\b{re.escape(name)}\s*=", tag, flags=re.I):
        return re.sub(
            rf"\b{re.escape(name)}\s*=\s*(['\"]).*?\1",
            f'{name}="{escaped}"',
            tag,
            count=1,
            flags=re.I | re.S,
        )
    return re.sub(r"\s*/?>$", lambda ending: f' {name}="{escaped}"{ending.group(0)}', tag)


def attribute_value(tag: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1", tag, flags=re.I | re.S)
    return html.unescape(match.group(2)).strip() if match else ""


def load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"고정 설정을 읽을 수 없습니다: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"고정 설정의 최상위 값은 객체여야 합니다: {path}")
    return value


def media_by_id(library: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for raw in library.get("assets", []) if isinstance(library.get("assets"), list) else []:
        if isinstance(raw, dict) and str(raw.get("id", "")).strip():
            result[str(raw["id"])] = raw
    return result


def is_approved_director_patient_photo(asset: dict[str, object]) -> bool:
    descriptor = " ".join(
        str(asset.get(field, ""))
        for field in ("filename", "caption", "sceneType")
    )
    return (
        asset.get("safeAuto") is True
        and asset.get("requiresReview") is False
        and asset.get("personInteraction") is True
        and asset.get("directorVisible") is True
        and str(asset.get("sceneType", "")).startswith(PERSON_SCENE_PREFIX)
        and not LOGO_DESCRIPTOR.search(descriptor)
        and str(asset.get("url", "")).startswith("https://")
        and bool(str(asset.get("sha256", "")).strip())
    )


def is_approved_closing_trust_photo(asset: dict[str, object]) -> bool:
    return (
        asset.get("closingTrustEligible") is True
        and asset.get("closingTrustReviewed") is True
        and asset.get("closingTrustRequiresReview") is False
        and str(asset.get("closingTrustSceneType", "")) in ALLOWED_CLOSING_TRUST_SCENES
        and (
            asset.get("closingTrustDirectorVisible") is True
            or asset.get("closingTrustDocumentVisible") is True
        )
        and bool(str(asset.get("closingTrustApprovedAlt", "")).strip())
        and bool(str(asset.get("closingTrustContextText", "")).strip())
        and str(asset.get("url", "")).startswith("https://")
        and bool(str(asset.get("sha256", "")).strip())
    )


def validate_person_media_policy(
    article: str,
    library: dict[str, object] | None = None,
) -> None:
    """Block logos, objects, buildings, products, and spaces from article photo slots."""

    indexed = media_by_id(library or load_json_object(DEFAULT_MEDIA_LIBRARY))
    failures: list[str] = []
    for index, tag in enumerate(re.findall(r"<img\b[^>]*>", article, flags=re.I | re.S), start=1):
        if attribute_value(tag, "data-real-photo") == "true" and attribute_value(tag, "data-trust-photo") == "true":
            failures.append(f"{index}번 사진은 실제 진료 사진과 마무리 신뢰 사진을 동시에 표시할 수 없습니다.")
    for index, tag in enumerate(
        re.findall(
            r"<img\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>",
            article,
            flags=re.I | re.S,
        ),
        start=1,
    ):
        asset_id = attribute_value(tag, "data-goldhand-media")
        asset = indexed.get(asset_id)
        if asset is None:
            failures.append(f"{index}번 실제 사진의 내장 ID가 없습니다: {asset_id or 'missing-id'}")
            continue
        if not is_approved_director_patient_photo(asset):
            failures.append(f"{asset_id}는 원장 치료·진찰·상담 사진이 아니므로 사용할 수 없습니다.")
            continue
        if attribute_value(tag, "data-media-sha256") != str(asset.get("sha256", "")):
            failures.append(f"{asset_id}의 파일 해시가 내장 라이브러리와 다릅니다.")
        if attribute_value(tag, "data-reference-source-url") != str(asset.get("url", "")):
            failures.append(f"{asset_id}의 공식 원본 URL이 내장 라이브러리와 다릅니다.")
    for index, tag in enumerate(
        re.findall(
            r"<img\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"])[^>]*>",
            article,
            flags=re.I | re.S,
        ),
        start=1,
    ):
        asset_id = attribute_value(tag, "data-goldhand-media")
        asset = indexed.get(asset_id)
        if asset is None:
            failures.append(f"{index}번 마무리 신뢰 사진의 내장 ID가 없습니다: {asset_id or 'missing-id'}")
            continue
        if not is_approved_closing_trust_photo(asset):
            failures.append(f"{asset_id}는 검수된 협약·수료·기부·봉사 신뢰 사진이 아니므로 사용할 수 없습니다.")
            continue
        if attribute_value(tag, "data-media-sha256") != str(asset.get("sha256", "")):
            failures.append(f"{asset_id}의 파일 해시가 내장 라이브러리와 다릅니다.")
        if attribute_value(tag, "data-reference-source-url") != str(asset.get("url", "")):
            failures.append(f"{asset_id}의 공식 원본 URL이 내장 라이브러리와 다릅니다.")
    if failures:
        raise ValueError("실제 사진 정책 위반: " + " ".join(failures))


def strip_legacy_closing_links(article: str) -> str:
    opening = re.compile(
        r"<section\b(?=[^>]*\bdata-goldhand-closing-links\s*=\s*['\"]true['\"])[^>]*>",
        flags=re.I | re.S,
    )
    starts = list(opening.finditer(article))
    if len(starts) > 1:
        raise ValueError("이전 글말미 링크·지도 블록이 중복됐습니다.")
    cleaned = article
    if starts:
        depth = 0
        end = None
        for tag in re.finditer(r"<section\b[^>]*>|</section\s*>", article[starts[0].start():], flags=re.I | re.S):
            if tag.group(0).lower().startswith("<section"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    end = starts[0].start() + tag.end()
                    break
        if end is None:
            raise ValueError("이전 글말미 링크·지도 블록의 닫는 태그가 없습니다.")
        cleaned = article[:starts[0].start()] + article[end:]
    if not re.search(r"</article>\s*$", cleaned, flags=re.I):
        raise ValueError("article 닫는 태그가 없습니다.")
    return cleaned


def build_page(
    title: str,
    article: str,
    platform_name: str | None = None,
) -> str:
    article = strip_visible_trust_photo_context(article)
    validate_person_media_policy(article)
    article = strip_legacy_closing_links(article)
    escaped_title = html.escape(title, quote=True)
    escaped_shortcut = html.escape(paste_shortcut(platform_name), quote=True)
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{escaped_title} · 금손한의원 네이버용 HTML</title>
  <style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:124px 16px 52px; background:#F4F4F4; color:#222222; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif; }}
    .copy-toolbar {{ position:fixed; z-index:20; top:0; left:0; right:0; display:flex; align-items:center; justify-content:center; gap:18px; padding:15px 20px; background:rgba(255,255,255,.97); border-bottom:1px solid #E5E5E5; box-shadow:0 7px 22px rgba(0,0,0,.08); backdrop-filter:blur(10px); }}
    .copy-toolbar__text {{ min-width:0; }}
    .copy-toolbar__title {{ margin:0; color:#111111; font-size:15px; line-height:1.45; font-weight:800; }}
    .copy-toolbar__help {{ margin:3px 0 0; color:#666666; font-size:12px; line-height:1.45; }}
    .copy-button {{ flex:0 0 auto; min-width:190px; padding:14px 20px; border:1px solid #111827; border-radius:8px; background:#1F2937; color:#fff; font-size:15px; font-weight:800; cursor:pointer; }}
    .copy-button:hover {{ background:#111827; }}
    .copy-button:focus-visible {{ outline:3px solid #60A5FA; outline-offset:3px; }}
    .copy-button[data-state="done"] {{ background:#2563EB; }}
    .copy-button[data-state="error"] {{ background:#9E3636; border-color:#9E3636; }}
    #copy-status {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}
    #naver-copy-root {{ width:100%; max-width:580px; margin:0 auto; box-shadow:0 12px 34px rgba(0,0,0,.08); }}
    @media (max-width:640px) {{
      body {{ padding:142px 0 0; background:#fff; }}
      .copy-toolbar {{ align-items:stretch; gap:9px; padding:11px 12px; flex-direction:column; }}
      .copy-toolbar__text {{ text-align:center; }}
      .copy-toolbar__help {{ font-size:11px; }}
      .copy-button {{ width:100%; min-width:0; padding:12px 16px; }}
      #naver-copy-root {{ max-width:100%; box-shadow:none; }}
    }}
  </style>
</head>
<body>
  <header class="copy-toolbar">
    <div class="copy-toolbar__text">
      <p class="copy-toolbar__title">금손한의원 네이버 블로그 원고</p>
      <p class="copy-toolbar__help">네이버 본문에서 굵게·밑줄·취소선이 켜져 있으면 먼저 끄기 → 버튼 클릭 → {escaped_shortcut}</p>
    </div>
    <button class="copy-button" id="copy-for-naver" type="button">네이버용 HTML 복사</button>
    <span id="copy-status" role="status" aria-live="polite"></span>
  </header>
  <main id="naver-copy-root">{article}</main>
  <script>
    (() => {{
      const button = document.getElementById('copy-for-naver');
      const root = document.getElementById('naver-copy-root');
      const status = document.getElementById('copy-status');
      function setState(state, message) {{
        button.dataset.state = state; button.textContent = message; status.textContent = message;
        window.setTimeout(() => {{ button.dataset.state = ''; button.textContent = '네이버용 HTML 복사'; }}, 2600);
      }}
      function stripInternalMetadata(copyRoot) {{
        [copyRoot, ...copyRoot.querySelectorAll('*')].forEach((element) => {{
          [...element.attributes].forEach((attribute) => {{
            const name = attribute.name.toLowerCase();
            if (name.startsWith('data-goldhand-') || name.startsWith('data-reference-') ||
                name.startsWith('data-editorial-') ||
                name === 'data-question-source' || name === 'data-mobile-group' ||
                name === 'data-naver-native-component' || name.startsWith('data-native-table-')) {{
              element.removeAttribute(attribute.name);
            }}
          }});
        }});
      }}
      function prepareNaverCopyRoot() {{
        const sourceArticle = root.querySelector('article');
        if (!sourceArticle) throw new Error('article-missing');
        const copyRoot = sourceArticle.cloneNode(true);
        copyRoot.querySelectorAll('figcaption').forEach((caption) => caption.remove());
        copyRoot.removeAttribute('id'); copyRoot.removeAttribute('class'); copyRoot.removeAttribute('style');
        copyRoot.querySelectorAll('img[data-reference-source-url]').forEach((image) => {{
          image.setAttribute('src', image.getAttribute('data-reference-source-url'));
          image.setAttribute('referrerpolicy', 'no-referrer');
          image.removeAttribute('data-reference-source-url');
        }});
        copyRoot.querySelectorAll('p[data-preview-gap="true"]').forEach((spacer) => {{
          spacer.removeAttribute('aria-hidden'); spacer.removeAttribute('data-preview-gap');
          spacer.setAttribute('data-naver-gap', 'true');
          spacer.setAttribute('style', 'margin:0;text-align:center;font-size:15px;line-height:1.8;color:transparent;');
          spacer.textContent = '\\u2060';
        }});
        stripInternalMetadata(copyRoot);
        copyRoot.querySelectorAll('*').forEach((element) => {{
          element.removeAttribute('aria-hidden');
          element.style.removeProperty('text-decoration'); element.style.removeProperty('text-decoration-line');
        }});
        return copyRoot;
      }}
      function nextSeId() {{ return `SE-${{crypto.randomUUID()}}`; }}
      function escapeHtml(value) {{
        const node=document.createElement('span'); node.textContent=String(value ?? ''); return node.innerHTML;
      }}
      function sourceInlineLines(source, base={{}}) {{
        const lines=[[]];
        const append=(text,state) => {{ if (text) lines[lines.length-1].push({{text,...state}}); }};
        const walk=(node,state) => {{
          if (node.nodeType===Node.TEXT_NODE) {{ append(node.nodeValue || '',state); return; }}
          if (node.nodeType!==Node.ELEMENT_NODE) return;
          const element=node;
          if (element.tagName==='BR') {{ lines.push([]); return; }}
          const style=element.style || {{}};
          const next={{...state}};
          if (element.matches('b,strong') || /^(?:600|700|800|900|bold)$/i.test(style.fontWeight || '')) next.bold=true;
          if (element.matches('u') || element.hasAttribute('data-reference-underline-role')) next.underline=true;
          if (element.matches('i,em')) next.italic=true;
          if (element.matches('mark,[data-goldhand-emphasis="highlight"]') || style.backgroundColor) {{
            next.highlight=true; next.background=style.backgroundColor || '#FFF2A8';
          }}
          if (element.matches('[data-goldhand-emphasis="red"]') || style.color) next.color=style.color || next.color;
          [...element.childNodes].forEach((child)=>walk(child,next));
        }};
        [...source.childNodes].forEach((child)=>walk(child,base));
        return lines;
      }}
      function nativeRun(run,fontSize,defaultColor) {{
        const runId=nextSeId(); const classes=['se-ff-nanumgothic',`se-fs${{fontSize}}`];
        if (run.highlight) classes.push('se-highlight'); classes.push('__se-node');
        const styles=[`color: ${{run.color || defaultColor}};`];
        if (run.highlight) styles.push(`background-color: ${{run.background || '#FFF2A8'}};`);
        let content=escapeHtml(run.text);
        if (run.bold) content=`<b>${{content}}</b>`;
        if (run.underline) content=`<u>${{content}}</u>`;
        if (run.italic) content=`<i>${{content}}</i>`;
        if (run.highlight) content=`<mark>${{content}}</mark>`;
        return `<span id="${{runId}}" class="${{classes.join(' ')}}" style="${{styles.join(' ')}}">${{content}}</span>`;
      }}
      function nativeParagraphs(source,options={{}}) {{
        const sourceSize=parseInt(source.style?.fontSize || '',10);
        const fontSize=options.fontSize || sourceSize || (source.matches('h2,h3,h4,h5,h6') ? 19 : 16);
        const lineHeight=options.lineHeight || source.style?.lineHeight || (fontSize>=19 ? '1.8' : '1.9');
        const defaultColor=options.color || source.style?.color || (fontSize>=19 ? 'rgb(0, 0, 0)' : 'rgb(77, 77, 77)');
        const base={{bold:Boolean(options.bold || source.matches('h2,h3,h4,h5,h6'))}};
        if (source.hasAttribute('data-naver-gap')) {{ base.bold=false; }}
        return sourceInlineLines(source,base).map((runs)=>{{
          const paragraphId=nextSeId();
          const normalized=runs.length ? runs : [{{text:'\u2060'}}];
          return `<p id="${{paragraphId}}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height: ${{lineHeight}};">${{normalized.map((run)=>nativeRun(run,fontSize,defaultColor)).join('')}}</p>`;
        }}).join('');
      }}
      function nativeTextComponent(source,options={{}}) {{
        const compId=nextSeId(); const moduleId=nextSeId();
        return `<div class="se-component se-text se-l-default" id="${{compId}}" data-compid="${{compId}}" data-a11y-title="본문"><div class="se-component-content"><div class="se-drop-indicator" data-unitid="" data-compid="${{compId}}" data-direction="top"><div class="se-section se-section-text se-l-default"><div id="${{moduleId}}" class="se-module se-module-text __se-unit">${{nativeParagraphs(source,options)}}</div></div></div></div></div>`;
      }}
      function nativeQuotationComponent(source) {{
        const compId=nextSeId(), quoteModule=nextSeId(), quoteParagraph=nextSeId(), quoteRun=nextSeId();
        const citeModule=nextSeId(), citeParagraph=nextSeId(), citeRun=nextSeId();
        const text=escapeHtml(source.textContent.trim());
        return `<div class="se-component se-quotation se-l-default" id="${{compId}}" data-compid="${{compId}}" data-a11y-title="인용구"><button class="se-component-edge-button se-component-edge-button-top __edge-area" type="button" tab-index="-1" data-compid="${{compId}}" data-direction="top"></button><div class="se-component-content"><div class="__se-toolbar-slot __se-cursor-unrelated" style="display:none;"></div><div class="se-drop-indicator" data-unitid="" data-compid="${{compId}}" data-direction="top"><div class="se-section se-section-quotation se-l-default se-section-align-center __se-unit"><div class="se-quotation-container"><div id="${{quoteModule}}" class="se-module se-module-text __se-unit se-quote"><p id="${{quoteParagraph}}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height:1.8;"><span id="${{quoteRun}}" class="se-ff-nanummyeongjo se-fs19 __se-node" style="color:rgb(0, 0, 0);"><i>${{text}}</i></span></p></div><div id="${{citeModule}}" class="se-module se-module-text __se-unit se-is-empty se-cite"><p id="${{citeParagraph}}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height:1.5;"><span id="${{citeRun}}" class="se-ff-nanumgothic se-fs13 __se-node" style="color:rgb(119, 119, 119);"></span><span class="se-placeholder __se_placeholder se-ff-nanumgothic se-fs13">출처 입력</span></p></div></div></div></div></div></div>`;
      }}
      function nativeDividerComponent() {{
        const compId=nextSeId();
        return `<div class="se-component se-horizontalLine se-l-line1" id="${{compId}}" data-compid="${{compId}}" data-a11y-title="구분선"><button class="se-component-edge-button se-component-edge-button-top __edge-area" type="button" tab-index="-1" data-compid="${{compId}}" data-direction="top"></button><div class="se-component-content"><div class="se-drop-indicator" data-unitid="" data-compid="${{compId}}" data-direction="top"><div draggable="true" class="se-section se-section-horizontalLine se-l-line1 se-section-align-center"><div class="se-module se-module-horizontalLine __se-unit"><span class="se-hr-invisible"></span><hr class="se-hr"><div class="__se-toolbar-slot __se-cursor-unrelated" style="display:none;"></div></div></div></div></div></div>`;
      }}
      function nativeImageComponent(source) {{
        const image=source.matches('img') ? source : source.querySelector('img'); if (!image) return '';
        const compId=nextSeId(), captionId=nextSeId(), paragraphId=nextSeId(), runId=nextSeId();
        const src=escapeHtml(image.currentSrc || image.src), alt=escapeHtml(image.alt || '');
        return `<div class="se-component se-image se-l-default" id="${{compId}}" data-compid="${{compId}}" data-a11y-title="사진"><button class="se-component-edge-button se-component-edge-button-top __edge-area" type="button" tab-index="-1" data-compid="${{compId}}" data-direction="top"></button><div class="se-component-content se-component-content-fit"><div class="se-drop-indicator" data-unitid="" data-compid="${{compId}}" data-direction="top"><div class="se-section se-section-image se-l-default se-section-align-center"><div id="${{compId}}" class="se-module se-module-image __se-unit"><div class="se-drop-indicator" data-unitid="${{compId}}" data-compid="" data-direction="top">${{String.fromCharCode(60)}}img src="${{src}}" alt="${{alt}}" class="se-image-resource" width="580" referrerpolicy="no-referrer"></div><button type="button" class="se-image-delete-button"><span class="se-blind">사진 삭제</span></button><div class="__se-toolbar-slot __se-cursor-unrelated" style="display:none;"></div></div><div id="${{captionId}}" class="se-module se-module-text __se-unit se-is-empty se-caption"><p id="${{paragraphId}}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height:1.5;"><span id="${{runId}}" class="se-ff-nanumgothic se-fs13 __se-node" style="color:rgb(85, 85, 85);"></span><span class="se-placeholder __se_placeholder se-ff-nanumgothic se-fs13">사진 설명을 입력하세요.</span></p><div class="__se-toolbar-slot __se-cursor-unrelated" style="display:none;"></div></div></div></div></div></div>`;
      }}
      function nativeTableComponent(source) {{
        const compId=nextSeId(); const rows=[...source.querySelectorAll('tr')];
        const rowsHtml=rows.map((row)=>{{
          const rowId=nextSeId(); const cells=[...row.children].filter((cell)=>cell.matches('td,th'));
          return `<tr class="se-tr" id="${{rowId}}">${{cells.map((cell)=>{{
            const cellId=nextSeId(), moduleId=nextSeId();
            const width=cell.style.width || `${{100/Math.max(cells.length,1)}}%`;
            const height=cell.style.height || (source.getAttribute('data-native-table-purpose')==='clinic-info' ? '64px' : '40px');
            const background=cell.style.backgroundColor ? ` background-color:${{cell.style.backgroundColor}};` : '';
            const cellStyle=`width:${{width}}; height:${{height}};${{background}} border:1px solid rgb(214, 214, 214);`;
            return `<td id="${{cellId}}" colspan="${{cell.colSpan || 1}}" rowspan="${{cell.rowSpan || 1}}" class="__se-unit se-cell" style="${{cellStyle}}"><div id="${{moduleId}}" class="se-module se-module-text">${{nativeParagraphs(cell,{{fontSize:15,lineHeight:'1.6',color:cell.style.color || 'rgb(77, 77, 77)',bold:/^(?:600|700|800|900|bold)$/i.test(cell.style.fontWeight || '')}})}}</div></td>`;
          }}).join('')}}</tr>`;
        }}).join('');
        return `<div class="se-component se-table se-l-default" id="${{compId}}" data-compid="${{compId}}" data-a11y-title="표"><button class="se-component-edge-button se-component-edge-button-top __edge-area" type="button" tab-index="-1" data-compid="${{compId}}" data-direction="top"></button><div class="se-component-content"><div class="se-drop-indicator" data-unitid="" data-compid="${{compId}}" data-direction="top"><div class="se-section se-section-table se-l-default se-section-align-center" style="width:100%;"><div class="__se-toolbar-slot __se-cursor-unrelated" style="display:none;"></div><div class="se-table-container"><table class="se-table-content" style="border-width:medium;border-style:none;border-color:currentcolor;border-collapse:collapse;"><tbody>${{rowsHtml}}</tbody></table></div></div></div></div></div>`;
      }}
      function nativeComponentsFromNode(node) {{
        if (node.nodeType!==Node.ELEMENT_NODE) return '';
        const element=node;
        if (element.matches('script.__se_module_data')) return element.outerHTML;
        if (element.matches('.se-component.se-oglink,.se-component.se-placesMap')) return element.outerHTML;
        if (element.matches('blockquote')) return nativeQuotationComponent(element);
        if (element.matches('p,h2,h3,h4,h5,h6')) return nativeTextComponent(element);
        if (element.matches('hr')) return nativeDividerComponent();
        if (element.matches('table')) return nativeTableComponent(element);
        if (element.matches('figure,img')) return nativeImageComponent(element);
        if (element.matches('script,style,button')) return '';
        return [...element.childNodes].map(nativeComponentsFromNode).join('');
      }}
      function prepareNativeNaverHtml(copyRoot) {{ return [...copyRoot.childNodes].map(nativeComponentsFromNode).join(''); }}
      function copyRenderedSelection(copyRoot) {{
        copyRoot.style.position='fixed'; copyRoot.style.left='-100000px'; copyRoot.style.top='0'; copyRoot.style.width='580px';
        document.body.appendChild(copyRoot); const selection=window.getSelection(); const range=document.createRange();
        range.selectNodeContents(copyRoot); selection.removeAllRanges(); selection.addRange(range);
        const copied=document.execCommand('copy'); selection.removeAllRanges(); copyRoot.remove(); return copied;
      }}
      button.addEventListener('click', async () => {{
        const prepared = prepareNaverCopyRoot();
        const nativeHtml = prepareNativeNaverHtml(prepared);
        const inputBuffer = document.createElement('span');
        inputBuffer.setAttribute('data-input-buffer', `INPUT_BUFFER_DATA;${{encodeURIComponent(navigator.userAgent)}};blog.naver.com`);
        const htmlValue = `<meta charset="utf-8">${{inputBuffer.outerHTML}}${{nativeHtml}}`;
        const plainValue = prepared.innerText.replaceAll('\\u00a0','').replaceAll('\\u2060','').replace(/\\n{{3,}}/g,'\\n\\n').trim();
        if (window.location.protocol === 'file:') {{
          if (copyRenderedSelection(prepared)) setState('done','복사 완료 · 굵게·밑줄·취소선 확인 후 {escaped_shortcut}');
          else setState('error','복사 실패 · 클립보드가 바뀌지 않았습니다');
          return;
        }}
        try {{
          if (navigator.clipboard?.write && window.ClipboardItem) {{
            await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([htmlValue],{{type:'text/html'}}),'text/plain':new Blob([plainValue],{{type:'text/plain'}})}})]);
          }} else if (!copyRenderedSelection(prepared)) throw new Error('rich-copy-unavailable');
          setState('done','복사 완료 · 굵게·밑줄·취소선 확인 후 {escaped_shortcut}');
        }} catch (error) {{
          try {{ if (!copyRenderedSelection(prepareNaverCopyRoot())) throw error; setState('done','복사 완료 · 굵게·밑줄·취소선 확인 후 {escaped_shortcut}'); }}
          catch {{ setState('error','복사 차단됨 · 브라우저 권한 확인'); }}
        }}
      }});
      window.__goldhandCopyPreview = () => {{
        const prepared=prepareNaverCopyRoot();
        const nativeHtml=prepareNativeNaverHtml(prepared); const template=document.createElement('template'); template.innerHTML=nativeHtml;
        return {{html:nativeHtml, plain:prepared.innerText, gaps:prepared.querySelectorAll('[data-naver-gap="true"]').length, images:template.content.querySelectorAll('.se-image').length, relatedLinks:template.content.querySelectorAll('.se-oglink[data-linktype="oglink"]').length, maps:template.content.querySelectorAll('.se-placesMap').length, nativeModules:template.content.querySelectorAll('script.__se_module_data[data-module-v2]').length, nativeComponents:template.content.querySelectorAll('.se-component').length, inputBuffer:true, requiresNativeFinisher:false}};
      }};
    }})();
  </script>
</body>
</html>
'''


def main() -> int:
    args = parse_args()
    try:
        article = strip_visible_image_captions(article_fragment(args.article_html.read_text(encoding="utf-8")))
        validate_credential_placement(article)
        published_local_images: dict[Path, str] = {}
        if "data-local-image=" in article:
            project_dir, public_base_url = image_host_config()
            published_local_images = publish_local_images(article, project_dir, public_base_url)
        article = rewrite_img_tags(article, published_local_images)
        target = output_path(args.title, args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_page(args.title, article), encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"HTML 저장 실패: {exc}", file=sys.stderr)
        return 1
    print(target.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
