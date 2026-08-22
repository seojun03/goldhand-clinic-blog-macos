#!/usr/bin/env python3
"""Download every indexed Goldhand official-blog image into the plugin.

The public Naver URL remains in the registry for rich-copy output. The bundled
binary is the portable source of truth for selection, duplicate detection, and
package integrity checks on every user's installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "media-library.json"
DEFAULT_ASSET_DIR = SKILL_DIR / "assets" / "official-media"
SEOUL = ZoneInfo("Asia/Seoul")
MIME_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detected_mime(data: bytes, header: str = "") -> str:
    normalized = header.split(";", 1)[0].strip().lower()
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if normalized in MIME_SUFFIX:
        return normalized
    raise ValueError(f"지원하지 않는 이미지 형식입니다: {normalized or 'unknown'}")


def bundled_path(asset: dict[str, Any]) -> Path | None:
    raw = str(asset.get("bundledPath", "")).strip()
    if not raw:
        return None
    candidate = (SKILL_DIR / raw).resolve()
    try:
        candidate.relative_to(SKILL_DIR.resolve())
    except ValueError as exc:
        raise ValueError(f"플러그인 밖의 번들 경로입니다: {raw}") from exc
    return candidate


def existing_metadata(asset: dict[str, Any]) -> dict[str, Any] | None:
    path = bundled_path(asset)
    digest = str(asset.get("sha256", "")).strip()
    if not path or not path.is_file() or not digest:
        return None
    if file_sha256(path) != digest:
        return None
    mime = str(asset.get("mimeType", "")).strip() or mimetypes.guess_type(path.name)[0] or ""
    if mime not in MIME_SUFFIX:
        return None
    return {
        "bundledPath": str(path.relative_to(SKILL_DIR)),
        "sha256": digest,
        "mimeType": mime,
        "sizeBytes": path.stat().st_size,
    }


def download_asset(asset: dict[str, Any], asset_dir: Path) -> tuple[str, dict[str, Any]]:
    asset_id = str(asset.get("id", "")).strip()
    url = str(asset.get("url", "")).strip()
    if not asset_id or not url.startswith("https://"):
        raise ValueError(f"이미지 ID 또는 HTTPS URL이 잘못됐습니다: {asset_id or 'missing-id'}")
    cached = existing_metadata(asset)
    if cached:
        return asset_id, cached
    headers = {
        "User-Agent": "Mozilla/5.0 GoldhandPluginMediaSync/1.0",
        "Referer": str(asset.get("sourcePostUrl", "https://blog.naver.com/goldhand7582_")),
    }
    last_error = ""
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=45)
            response.raise_for_status()
            data = response.content
            if len(data) < 32:
                raise ValueError("이미지 응답이 너무 짧습니다.")
            mime = detected_mime(data, response.headers.get("Content-Type", ""))
            suffix = MIME_SUFFIX[mime]
            target = asset_dir / f"{asset_id}{suffix}"
            for old in asset_dir.glob(f"{asset_id}.*"):
                if old != target and old.is_file():
                    old.unlink()
            partial = target.with_suffix(target.suffix + ".part")
            partial.write_bytes(data)
            os.replace(partial, target)
            digest = hashlib.sha256(data).hexdigest()
            return asset_id, {
                "bundledPath": str(target.relative_to(SKILL_DIR)),
                "sha256": digest,
                "mimeType": mime,
                "sizeBytes": len(data),
            }
        except (OSError, requests.RequestException, ValueError) as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))
    raise ValueError(f"{asset_id} 다운로드 실패: {last_error}")


def validate_library(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        return ["assets가 배열이 아닙니다."]
    for asset in assets:
        if not isinstance(asset, dict):
            errors.append("객체가 아닌 이미지 항목이 있습니다.")
            continue
        asset_id = str(asset.get("id", "missing-id"))
        try:
            metadata = existing_metadata(asset)
        except (OSError, ValueError) as exc:
            errors.append(f"{asset_id}: {exc}")
            continue
        if metadata is None:
            errors.append(f"{asset_id}: 번들 파일 또는 해시가 없거나 일치하지 않습니다.")
        if asset.get("closingTrustEligible") is True:
            required = (
                "closingTrustSceneType",
                "closingTrustPlacementTerms",
                "closingTrustApprovedAlt",
                "closingTrustContextText",
            )
            missing = [field for field in required if not asset.get(field)]
            if asset.get("closingTrustReviewed") is not True or asset.get("closingTrustRequiresReview") is not False:
                missing.append("closingTrustReviewStatus")
            if not (asset.get("closingTrustDirectorVisible") is True or asset.get("closingTrustDocumentVisible") is True):
                missing.append("closingTrustVisibleSubject")
            if missing:
                errors.append(f"{asset_id}: 마무리 신뢰 사진 메타데이터 누락: {', '.join(missing)}")
    expected_closing_trust = sum(
        1 for asset in assets if isinstance(asset, dict) and asset.get("closingTrustEligible") is True
    )
    if int(payload.get("closingTrustCount", 0) or 0) != expected_closing_trust:
        errors.append("closingTrustCount가 실제 승인 자산 수와 다릅니다.")
    return errors


def sync(library_path: Path, asset_dir: Path, workers: int) -> dict[str, Any]:
    payload = json.loads(library_path.read_text(encoding="utf-8"))
    assets = payload.get("assets", []) if isinstance(payload, dict) else []
    if not isinstance(assets, list) or not assets:
        raise ValueError("미디어 레지스트리에 이미지가 없습니다.")
    asset_dir.mkdir(parents=True, exist_ok=True)
    metadata_by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 10))) as pool:
        futures = {
            pool.submit(download_asset, asset, asset_dir): str(asset.get("id", "missing-id"))
            for asset in assets if isinstance(asset, dict)
        }
        for future in as_completed(futures):
            try:
                asset_id, metadata = future.result()
                metadata_by_id[asset_id] = metadata
            except (OSError, ValueError, requests.RequestException) as exc:
                errors.append(str(exc))
    if errors:
        raise ValueError("; ".join(errors))
    for asset in assets:
        if isinstance(asset, dict):
            asset.update(metadata_by_id[str(asset.get("id", ""))])
    payload["schemaVersion"] = max(2, int(payload.get("schemaVersion", 1) or 1))
    payload["bundledAt"] = datetime.now(SEOUL).isoformat(timespec="seconds")
    payload["bundledAssetCount"] = len(metadata_by_id)
    payload["bundledBytes"] = sum(int(item["sizeBytes"]) for item in metadata_by_id.values())
    payload["policy"] = (
        "All indexed official-blog image binaries are bundled in the plugin; "
        "only visually approved director-patient safeAuto assets may be selected as clinical photos, "
        "and separately reviewed director-or-credential assets may be selected as one closing trust photo"
    )
    library_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation_errors = validate_library(payload)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    return payload


def main() -> int:
    args = parse_args()
    try:
        library_path = args.library.expanduser().resolve()
        asset_dir = args.asset_dir.expanduser().resolve()
        if args.verify_only:
            payload = json.loads(library_path.read_text(encoding="utf-8"))
        else:
            payload = sync(library_path, asset_dir, args.workers)
        errors = validate_library(payload)
        if errors:
            raise ValueError("; ".join(errors))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"공식 사진 번들 동기화 실패: {exc}", file=sys.stderr)
        return 1
    summary = {
        "assetCount": len(payload.get("assets", [])),
        "bundledAssetCount": int(payload.get("bundledAssetCount", 0) or 0),
        "bundledBytes": int(payload.get("bundledBytes", 0) or 0),
        "safeAutoCount": int(payload.get("safeAutoCount", 0) or 0),
        "closingTrustCount": int(payload.get("closingTrustCount", 0) or 0),
        "status": "verified" if args.verify_only else "synced",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
