#!/usr/bin/env python3
"""Recommend 6-12 safe director-patient Goldhand photos for one article.

Only visually approved photos of the director treating, examining, consulting,
or explaining to a patient are eligible. Logos, buildings, medicine, equipment,
products, and empty clinic-space photos are never article-photo fallbacks.
Photos used in the newest three articles may be reused only when needed to
reach the hard minimum of six.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "media-library.json"
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣+·._-]{1,}")
STOPWORDS = {
    "광주", "금손한의원", "한의원", "병원", "클리닉", "관련", "대한", "위한", "하는", "있는",
    "없는", "방법", "이유", "기준", "정보", "블로그", "작성", "원고", "환자", "박준희", "원장",
}
TYPE_TAGS = {"정보전달형": set()}
MIN_REAL_PHOTOS = 6
MAX_REAL_PHOTOS = 12
FORBIDDEN_DESCRIPTOR = re.compile(r"(?:로고|logo|건물\s*외관|건물\s*외부|환제|제품\s*포장|장비|원내\s*공간)", re.I)


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--type", required=True, dest="article_type", choices=sorted(TYPE_TAGS))
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--recent-id", action="append", default=[])
    parser.add_argument("--recent-hash", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def tokens(value: str) -> set[str]:
    result: set[str] = set()
    for token in TOKEN_RE.findall(value.lower()):
        cleaned = token.strip("._-")
        if len(cleaned) >= 2 and cleaned not in STOPWORDS:
            result.add(cleaned)
    return result


def load_json(path: Path, *, required: bool = False) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 최상위는 객체여야 합니다: {path}")
    return value


def recent_media(state: dict[str, Any]) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    hashes: set[str] = set()
    entries = state.get("entries", [])
    for entry in entries[:3] if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        ids.update(str(value).strip() for value in entry.get("realMediaIds", []) if str(value).strip())
        hashes.update(str(value).strip() for value in entry.get("realMediaHashes", []) if str(value).strip())
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


def bundled_assets(official: dict[str, Any]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for raw in official.get("assets", []):
        if isinstance(raw, dict):
            item = dict(raw)
            item["origin"] = "goldhand-bundled-official-library"
            assets.append(item)
    return assets


def is_safe_candidate(asset: dict[str, Any]) -> bool:
    if asset.get("safeAuto") is not True or asset.get("requiresReview") is True:
        return False
    descriptor = " ".join(
        str(asset.get(field, ""))
        for field in ("filename", "caption", "sceneType")
    )
    path = bundled_file(asset)
    return (
        str(asset.get("origin", "")) == "goldhand-bundled-official-library"
        and str(asset.get("url", "")).startswith("https://")
        and bool(str(asset.get("id", "")).strip())
        and bool(str(asset.get("sha256", "")).strip())
        and person_interaction(asset)
        and bool(asset.get("directorVisible"))
        and FORBIDDEN_DESCRIPTOR.search(descriptor) is None
        and path is not None
        and path.is_file()
    )


def trust_eligible(asset: dict[str, Any]) -> bool:
    return person_interaction(asset) and bool(asset.get("directorVisible"))


def person_interaction(asset: dict[str, Any]) -> bool:
    return bool(asset.get("personInteraction")) and str(asset.get("sceneType", "")).startswith("director-patient-")


def trust_priority(asset: dict[str, Any]) -> int:
    try:
        configured = int(asset.get("trustPriority", 0) or 0)
    except (TypeError, ValueError):
        configured = 0
    return max(configured, 100 if person_interaction(asset) else 0)


def score_asset(asset: dict[str, Any], query: set[str], preferred_tags: set[str]) -> tuple[int, list[str], list[str]]:
    title_tokens = tokens(str(asset.get("sourceTitle", "")))
    caption_tokens = tokens(str(asset.get("caption", "")))
    filename_tokens = tokens(str(asset.get("filename", "")))
    context_tokens = tokens(str(asset.get("context", "")))
    asset_tokens = set(str(value).lower() for value in asset.get("tokens", []) if value)
    tags = set(str(value) for value in asset.get("tags", []) if value)
    title_hits = query & title_tokens
    caption_hits = query & caption_tokens
    filename_hits = query & filename_tokens
    context_hits = query & context_tokens
    token_hits = query & asset_tokens
    tag_hits = preferred_tags & tags
    semantic_hits = title_hits | caption_hits | filename_hits | context_hits | token_hits
    score = (
        len(title_hits) * 5 + len(caption_hits) * 8 + len(filename_hits) * 8
        + len(context_hits) * 3 + len(token_hits) * 2 + len(tag_hits) * 3
    )
    if str(asset.get("positionBand")) == "body":
        score += 1
    return score, sorted(semantic_hits), sorted(tag_hits)


def identity_fields(asset: dict[str, Any]) -> tuple[str, str, str, tuple[str, str]]:
    return (
        str(asset.get("url", "")),
        str(asset.get("sha256", "")),
        str(asset.get("duplicateGroup", "")),
        (str(asset.get("filename", "")).lower(), str(asset.get("caption", "")).lower()),
    )


def public_item(
    asset: dict[str, Any], *, score: int, semantic_hits: list[str], tag_hits: list[str],
    selection_role: str, reused_from_recent: bool,
) -> dict[str, Any]:
    origin = str(asset.get("origin"))
    asset_id = str(asset.get("id", ""))
    common: dict[str, Any] = {
        "id": asset_id, "origin": origin, "sha256": asset.get("sha256", ""),
        "sourcePostUrl": asset.get("sourcePostUrl", ""), "sourceTitle": asset.get("sourceTitle", ""),
        "sourceDate": asset.get("sourceDate", ""), "filename": asset.get("filename", ""),
        "caption": asset.get("caption", ""), "context": asset.get("context", ""),
        "positionBand": asset.get("positionBand", "body"), "tags": asset.get("tags", []),
        "sceneType": asset.get("sceneType", ""),
        "personInteraction": bool(asset.get("personInteraction")),
        "directorVisible": bool(asset.get("directorVisible")),
        "trustPriority": trust_priority(asset),
        "matchedTerms": semantic_hits, "matchedTypeTags": tag_hits, "score": score,
        "selectionRole": selection_role, "reusedFromRecent": reused_from_recent,
    }
    url = str(asset.get("url", ""))
    local_path = bundled_file(asset)
    common["url"] = url
    common["bundledPath"] = str(asset.get("bundledPath", ""))
    common["bundledFile"] = str(local_path) if local_path else ""
    common["htmlAttributes"] = {
        "data-real-photo": "true", "data-media-origin": origin, "data-goldhand-media": asset_id,
        "data-media-sha256": str(asset.get("sha256", "")),
        "data-reference-source-url": url, "src": url, "referrerpolicy": "no-referrer",
    }
    return common


def recommend(
    library: dict[str, Any], *, topic: str, keyword: str, article_type: str, count: int,
    recent_ids: set[str], recent_hashes: set[str] | None = None,
) -> dict[str, Any]:
    requested = max(MIN_REAL_PHOTOS, min(count, MAX_REAL_PHOTOS))
    recent_hashes = recent_hashes or set()
    query = tokens(f"{topic} {keyword}")
    preferred_tags = TYPE_TAGS[article_type]
    candidates: list[tuple[int, int, int, dict[str, Any], list[str], list[str], bool]] = []
    for asset in bundled_assets(library):
        if not is_safe_candidate(asset):
            continue
        score, semantic_hits, tag_hits = score_asset(asset, query, preferred_tags)
        is_recent = str(asset.get("id", "")) in recent_ids or (
            bool(str(asset.get("sha256", ""))) and str(asset.get("sha256")) in recent_hashes
        )
        candidates.append((score, -int(asset.get("postOrder", 9999)), -int(asset.get("imageOrder", 9999)), asset, semantic_hits, tag_hits, is_recent))

    def rank(item: tuple[int, int, int, dict[str, Any], list[str], list[str], bool]) -> tuple[int, int, int, int, str]:
        return (trust_priority(item[3]), item[0], item[1], item[2], str(item[3].get("id")))

    fresh_human_semantic = sorted(
        (item for item in candidates if not item[6] and item[4] and person_interaction(item[3])),
        key=rank,
        reverse=True,
    )
    fresh_human_trust = sorted(
        (item for item in candidates if not item[6] and not item[4] and person_interaction(item[3])),
        key=rank,
        reverse=True,
    )
    recent_human_trust = sorted(
        (item for item in candidates if item[6] and person_interaction(item[3])),
        key=rank,
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    seen_descriptors: set[tuple[str, str]] = set()
    seen_duplicate_groups: set[str] = set()
    per_post: dict[str, int] = {}

    def take(items: list[tuple[int, int, int, dict[str, Any], list[str], list[str], bool]], limit: int, role: str) -> None:
        for score, _, _, asset, semantic_hits, tag_hits, is_recent in items:
            if len(selected) >= limit:
                break
            url, digest, duplicate_group, descriptor = identity_fields(asset)
            log_no = str(asset.get("sourceLogNo", ""))
            if (url and url in seen_urls) or (digest and digest in seen_hashes):
                continue
            if descriptor in seen_descriptors or (duplicate_group and duplicate_group in seen_duplicate_groups):
                continue
            if log_no and per_post.get(log_no, 0) >= 6:
                continue
            selected.append(public_item(asset, score=score, semantic_hits=semantic_hits, tag_hits=tag_hits, selection_role=role, reused_from_recent=is_recent))
            if url:
                seen_urls.add(url)
            if digest:
                seen_hashes.add(digest)
            seen_descriptors.add(descriptor)
            if duplicate_group:
                seen_duplicate_groups.add(duplicate_group)
            if log_no:
                per_post[log_no] = per_post.get(log_no, 0) + 1

    take(fresh_human_semantic, requested, "director-patient-topic-match")
    take(fresh_human_trust, requested, "director-patient-trust")
    fresh_count = len(selected)
    if len(selected) < MIN_REAL_PHOTOS:
        take(recent_human_trust, MIN_REAL_PHOTOS, "recent-director-patient-fallback")

    selected_count = len(selected)
    status = "complete" if selected_count >= requested else "minimum-complete" if selected_count >= MIN_REAL_PHOTOS else "shortage"
    reused_count = sum(bool(item.get("reusedFromRecent")) for item in selected)
    return {
        "status": status, "requested": requested, "minimum": MIN_REAL_PHOTOS, "maximum": MAX_REAL_PHOTOS,
        "selectedCount": selected_count, "freshCount": fresh_count, "fallbackRecentTrustCount": reused_count,
        "missingToMinimum": max(0, MIN_REAL_PHOTOS - selected_count), "missingToRequested": max(0, requested - selected_count),
        "policy": "플러그인 내장 사진 중 새 원장-환자 치료·진찰·상담·검사 장면만 사용 → 6장 미만일 때만 최근의 같은 승인 사진 재사용; 로고·간판·건물·약·환제·탕약·제품·장비·빈 공간 fallback 금지",
        "query": {"topic": topic, "keyword": keyword, "type": article_type}, "selected": selected,
    }


def main() -> int:
    args = parse_args()
    try:
        library = load_json(args.library, required=True)
        state = load_json(args.state)
        state_ids, state_hashes = recent_media(state)
        result = recommend(
            library, topic=args.topic, keyword=args.keyword, article_type=args.article_type, count=args.count,
            recent_ids=state_ids | set(args.recent_id),
            recent_hashes=state_hashes | set(args.recent_hash),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"미디어 추천 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']} ({result['selectedCount']}/{result['requested']}, 최소 {result['minimum']})")
        for item in result["selected"]:
            location = item.get("bundledFile") or item.get("url") or ""
            fallback = " [최근 신뢰 사진 재사용]" if item["reusedFromRecent"] else ""
            print(f"{item['id']}\t{item['selectionRole']}\t{item['filename']}\t{location}{fallback}")
        if result["missingToMinimum"]:
            print(f"안전한 실제 사진 부족: 최소 기준까지 {result['missingToMinimum']}장 부족합니다.")
    return 0 if result["status"] != "shortage" else 1


if __name__ == "__main__":
    raise SystemExit(main())
