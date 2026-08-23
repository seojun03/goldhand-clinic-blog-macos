#!/usr/bin/env python3
"""Recommend one reviewed director-or-credential photo for the article ending.

This selector is deliberately separate from recommend_media.py. Its result never
counts toward the required clinical director-patient photo layout. It excludes
the immediately previous completed article's closing trust ID and file hash,
while allowing older trust photos to rotate back in.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "media-library.json"
ALLOWED_SCENES = {
    "director-agreement-pose",
    "director-community-pose",
    "credential-detail",
}


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--recent-id", action="append", default=[])
    parser.add_argument("--recent-hash", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path, *, required: bool = False) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 최상위는 객체여야 합니다: {path}")
    return value


def immediately_previous_trust_media(state: dict[str, Any]) -> tuple[set[str], set[str]]:
    entries = state.get("entries", [])
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
        return set(), set()
    entry = entries[0]
    ids = {str(value).strip() for value in entry.get("trustMediaIds", []) if str(value).strip()}
    hashes = {str(value).strip() for value in entry.get("trustMediaHashes", []) if str(value).strip()}
    return ids, hashes


def bundled_file(asset: dict[str, Any]) -> Path | None:
    raw = str(asset.get("bundledPath", "")).strip()
    if not raw:
        return None
    candidate = (SKILL_DIR / raw).resolve()
    try:
        candidate.relative_to(SKILL_DIR.resolve())
    except ValueError:
        return None
    return candidate


def is_closing_trust_candidate(asset: dict[str, Any]) -> bool:
    path = bundled_file(asset)
    return (
        asset.get("closingTrustEligible") is True
        and asset.get("closingTrustReviewed") is True
        and asset.get("closingTrustRequiresReview") is False
        and str(asset.get("closingTrustSceneType", "")) in ALLOWED_SCENES
        and (
            asset.get("closingTrustDirectorVisible") is True
            or asset.get("closingTrustDocumentVisible") is True
        )
        and isinstance(asset.get("closingTrustPlacementTerms"), list)
        and bool([term for term in asset.get("closingTrustPlacementTerms", []) if str(term).strip()])
        and bool(str(asset.get("closingTrustApprovedAlt", "")).strip())
        and bool(str(asset.get("closingTrustContextText", "")).strip())
        and str(asset.get("url", "")).startswith("https://")
        and bool(str(asset.get("id", "")).strip())
        and bool(str(asset.get("sha256", "")).strip())
        and path is not None
        and path.is_file()
    )


def public_item(asset: dict[str, Any]) -> dict[str, Any]:
    asset_id = str(asset.get("id", ""))
    url = str(asset.get("url", ""))
    digest = str(asset.get("sha256", ""))
    local_path = bundled_file(asset)
    return {
        "id": asset_id,
        "sha256": digest,
        "origin": "goldhand-bundled-official-library",
        "sourcePostUrl": asset.get("sourcePostUrl", ""),
        "sourceTitle": asset.get("sourceTitle", ""),
        "sourceDate": asset.get("sourceDate", ""),
        "url": url,
        "bundledPath": asset.get("bundledPath", ""),
        "bundledFile": str(local_path) if local_path else "",
        "sceneType": asset.get("closingTrustSceneType", ""),
        "directorVisible": bool(asset.get("closingTrustDirectorVisible")),
        "documentVisible": bool(asset.get("closingTrustDocumentVisible")),
        "priority": int(asset.get("closingTrustPriority", 0) or 0),
        "approvedAlt": asset.get("closingTrustApprovedAlt", ""),
        "visibleContextAllowed": False,
        "visibleCaptionAllowed": False,
        "htmlAttributes": {
            "data-trust-photo": "true",
            "data-media-origin": "goldhand-bundled-official-library",
            "data-goldhand-media": asset_id,
            "data-media-sha256": digest,
            "data-reference-source-url": url,
            "src": url,
            "referrerpolicy": "no-referrer",
            "alt": str(asset.get("closingTrustApprovedAlt", "")),
        },
        "figureAttributes": {
            "data-trust-photo": "true",
            "data-trust-photo-slot": "closing-credential-trust",
            "data-image-placement": "closing-credential-trust",
        },
    }


def recommend(
    library: dict[str, Any], *, recent_ids: set[str], recent_hashes: set[str] | None = None,
) -> dict[str, Any]:
    recent_hashes = recent_hashes or set()
    eligible = [
        asset
        for asset in library.get("assets", [])
        if isinstance(asset, dict) and is_closing_trust_candidate(asset)
    ]
    blocked = [
        asset for asset in eligible
        if str(asset.get("id", "")) in recent_ids
        or str(asset.get("sha256", "")) in recent_hashes
    ]
    fresh = [asset for asset in eligible if asset not in blocked]
    fresh.sort(
        key=lambda asset: (
            int(asset.get("closingTrustPriority", 0) or 0),
            -int(asset.get("postOrder", 9999) or 9999),
            -int(asset.get("imageOrder", 9999) or 9999),
            str(asset.get("id", "")),
        ),
        reverse=True,
    )
    selected = [public_item(fresh[0])] if fresh else []
    return {
        "status": "complete" if selected else "decision-required",
        "requested": 1,
        "selectedCount": len(selected),
        "eligibleCount": len(eligible),
        "freshEligibleCount": len(fresh),
        "blockedImmediatelyPreviousCount": len(blocked),
        "missingToRequested": 0 if selected else 1,
        "decisionRequired": not selected,
        "immediatelyPreviousReuseLimit": 0,
        "policy": "마무리 신뢰 사진은 진료 사진과 별도로 1장 사용하며, 공식 블로그에서 시각 검수된 원장·협약·수료증·기부·봉사 사진만 선택하고 바로 직전 완료 글의 ID·해시는 제외한다. 사진 앞뒤에는 소개·맥락·장면 설명·출처·캡션을 출력하지 않는다.",
        "selected": selected,
    }


def main() -> int:
    args = parse_args()
    try:
        library = load_json(args.library, required=True)
        state = load_json(args.state)
        state_ids, state_hashes = immediately_previous_trust_media(state)
        result = recommend(
            library,
            recent_ids=state_ids | set(args.recent_id),
            recent_hashes=state_hashes | set(args.recent_hash),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"마무리 신뢰 사진 추천 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']} ({result['selectedCount']}/1)")
        for item in result["selected"]:
            print(f"{item['id']}\t{item['sceneType']}\t{item['bundledFile']}")
        if result["missingToRequested"]:
            print(
                "마무리 신뢰 사진 부족: "
                f"직전 글과 겹치지 않는 승인 사진 {result['freshEligibleCount']}장, "
                f"직전 글 때문에 제외된 사진 {result['blockedImmediatelyPreviousCount']}장입니다."
            )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
