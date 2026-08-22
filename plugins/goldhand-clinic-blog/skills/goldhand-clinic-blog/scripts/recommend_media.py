#!/usr/bin/env python3
"""Recommend approved director-patient clinical photos for one article.

Only visually approved photos of the director treating, examining, consulting,
or explaining to a patient are eligible. Logos, buildings, medicine, equipment,
products, and empty clinic-space photos are never article-photo fallbacks.
One of two layouts is selected before assembly: one context-matched photo
immediately before the credential table, or two actual clinical photos in the
closing trust area. Closing photos do not need to match the article topic.
Fresh approved photos are preferred there, but an immediately previous approved
photo may be reused when that is the only way to keep the two-photo closing
layout. If the selected layout still cannot be filled, the selector reports an
exact decision-required shortage.
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
    "없는", "방법", "이유", "기준", "정보", "블로그", "작성", "원고", "환자", "박준희", "원장", "추천",
}
PLACEMENT_STOPWORDS = STOPWORDS | {"진료", "진찰", "치료", "상담", "설명", "검사", "통증", "증상", "장면"}
TYPE_TAGS = {"정보전달형": set()}
MIN_REAL_PHOTOS = 1
MAX_REAL_PHOTOS = 2
PLACEMENT_MODE_COUNTS = {
    "before-credential": 1,
    "closing-trust": 2,
}
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
    parser.add_argument("--placement-mode", choices=sorted(PLACEMENT_MODE_COUNTS), default="before-credential")
    parser.add_argument("--count", type=int, choices=(1, 2))
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--current-title", default="")
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


def recent_media(state: dict[str, Any], *, current_title: str = "") -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    hashes: set[str] = set()
    entries = state.get("entries", [])
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if current_title and str(entry.get("title", "")).strip() == current_title.strip():
            continue
        ids.update(str(value).strip() for value in entry.get("realMediaIds", []) if str(value).strip())
        hashes.update(str(value).strip() for value in entry.get("realMediaHashes", []) if str(value).strip())
        break
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
        and bool(str(asset.get("approvedAlt", "")).strip())
        and isinstance(asset.get("placementTerms"), list)
        and bool([term for term in asset.get("placementTerms", []) if str(term).strip()])
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


def normalized_compact(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).lower()


def matched_placement_terms(asset: dict[str, Any], query_text: str) -> list[str]:
    """Return scene-specific approved terms genuinely supported by the query."""
    compact_query = normalized_compact(query_text)
    query_tokens = tokens(query_text) - PLACEMENT_STOPWORDS
    matched: list[str] = []
    for raw in asset.get("placementTerms", []):
        term = str(raw).strip()
        if not term:
            continue
        term_tokens = tokens(term) - PLACEMENT_STOPWORDS
        if not term_tokens:
            continue
        if any(
            token in compact_query
            or any(token in query_token or query_token in token for query_token in query_tokens)
            for token in term_tokens
        ):
            matched.append(term)
    return matched


def identity_fields(asset: dict[str, Any]) -> tuple[str, str, str, tuple[str, str]]:
    return (
        str(asset.get("url", "")),
        str(asset.get("sha256", "")),
        str(asset.get("duplicateGroup", "")),
        (str(asset.get("filename", "")).lower(), str(asset.get("caption", "")).lower()),
    )


def public_item(
    asset: dict[str, Any], *, score: int, semantic_hits: list[str], tag_hits: list[str],
    placement_hits: list[str], selection_role: str, reused_from_recent: bool,
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
        "placementTerms": asset.get("placementTerms", []),
        "matchedPlacementTerms": placement_hits,
        "approvedAlt": asset.get("approvedAlt", ""),
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
        "alt": str(asset.get("approvedAlt", "")),
    }
    common["figureAttributes"] = {
        "data-real-photo": "true",
        "data-real-photo-slot": "",
        "data-image-placement": "after-related-paragraph",
    }
    return common


def recommend(
    library: dict[str, Any], *, topic: str, keyword: str, article_type: str, count: int | None,
    recent_ids: set[str], recent_hashes: set[str] | None = None,
    placement_mode: str = "before-credential",
) -> dict[str, Any]:
    if placement_mode not in PLACEMENT_MODE_COUNTS:
        raise ValueError(f"허용되지 않은 실제 사진 배치 모드: {placement_mode}")
    requested = PLACEMENT_MODE_COUNTS[placement_mode] if count is None else count
    if requested != PLACEMENT_MODE_COUNTS[placement_mode]:
        raise ValueError(
            f"{placement_mode} 배치는 실제 사진 {PLACEMENT_MODE_COUNTS[placement_mode]}장으로 고정됩니다."
        )
    recent_hashes = recent_hashes or set()
    query_text = f"{topic} {keyword}"
    query = tokens(query_text)
    preferred_tags = TYPE_TAGS[article_type]
    candidates: list[tuple[int, int, int, dict[str, Any], list[str], list[str], list[str], bool]] = []
    for asset in bundled_assets(library):
        if not is_safe_candidate(asset):
            continue
        score, semantic_hits, tag_hits = score_asset(asset, query, preferred_tags)
        placement_hits = matched_placement_terms(asset, query_text)
        if placement_mode == "before-credential" and not placement_hits:
            continue
        is_recent = str(asset.get("id", "")) in recent_ids or (
            bool(str(asset.get("sha256", ""))) and str(asset.get("sha256")) in recent_hashes
        )
        candidates.append((
            score,
            -int(asset.get("postOrder", 9999)),
            -int(asset.get("imageOrder", 9999)),
            asset,
            semantic_hits,
            tag_hits,
            placement_hits,
            is_recent,
        ))

    def rank(item: tuple[int, int, int, dict[str, Any], list[str], list[str], list[str], bool]) -> tuple[int, int, int, int, str]:
        return (trust_priority(item[3]), item[0], item[1], item[2], str(item[3].get("id")))

    fresh_context_matches = sorted(
        (item for item in candidates if not item[7] and person_interaction(item[3])),
        key=rank,
        reverse=True,
    )
    previous_context_matches = sorted(
        (item for item in candidates if item[7] and person_interaction(item[3])),
        key=rank,
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    seen_descriptors: set[tuple[str, str]] = set()
    seen_duplicate_groups: set[str] = set()
    per_post: dict[str, int] = {}

    def take(
        items: list[tuple[int, int, int, dict[str, Any], list[str], list[str], list[str], bool]],
        limit: int,
        role: str,
    ) -> None:
        for score, _, _, asset, semantic_hits, tag_hits, placement_hits, is_recent in items:
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
            selected.append(public_item(
                asset,
                score=score,
                semantic_hits=semantic_hits,
                tag_hits=tag_hits,
                placement_hits=placement_hits,
                selection_role=role,
                reused_from_recent=is_recent,
            ))
            if url:
                seen_urls.add(url)
            if digest:
                seen_hashes.add(digest)
            seen_descriptors.add(descriptor)
            if duplicate_group:
                seen_duplicate_groups.add(duplicate_group)
            if log_no:
                per_post[log_no] = per_post.get(log_no, 0) + 1

    fresh_role = (
        "not-in-immediately-previous-context-match"
        if placement_mode == "before-credential"
        else "not-in-immediately-previous-approved-clinical-scene"
    )
    take(fresh_context_matches, requested, fresh_role)
    fresh_count = len(selected)
    if placement_mode == "closing-trust" and len(selected) < requested:
        take(
            previous_context_matches,
            requested,
            "immediately-previous-approved-clinical-fallback",
        )
    for item in selected:
        item["figureAttributes"]["data-real-photo-slot"] = placement_mode
        if placement_mode == "closing-trust":
            item["figureAttributes"]["data-image-placement"] = "closing-clinical-gallery"

    selected_count = len(selected)
    reused_recent_count = sum(bool(item.get("reusedFromRecent")) for item in selected)
    status = "complete" if selected_count >= requested else "decision-required"
    return {
        "status": status, "placementMode": placement_mode,
        "requested": requested, "minimum": requested, "maximum": requested,
        "selectedCount": selected_count,
        "freshCount": fresh_count,
        "freshEligibleCount": len(fresh_context_matches),
        "immediatelyPreviousContextEligibleCount": len(previous_context_matches),
        "blockedImmediatelyPreviousCount": len(previous_context_matches),
        "recentContextEligibleCount": len(previous_context_matches),
        "reusedRecentCount": reused_recent_count,
        "fallbackRecentTrustCount": reused_recent_count,
        "recentReuseLimit": requested if placement_mode == "closing-trust" else 0,
        "decisionRequired": selected_count < requested,
        "missingToMinimum": max(0, requested - selected_count),
        "missingToRequested": max(0, requested - selected_count),
        "policy": "before-credential 1장은 승인 placementTerms가 주제와 맞고 직전 완료 글에 없는 사진만 선택한다. closing-trust 2장은 주제 맥락과 무관하게 승인된 실제 치료·진찰·상담·검사 사진을 고르며, 새 사진을 우선하고 부족할 때만 직전 글 승인 사진을 재사용한다. 본문 중간 분산은 금지한다.",
        "query": {"topic": topic, "keyword": keyword, "type": article_type}, "selected": selected,
    }


def main() -> int:
    args = parse_args()
    try:
        library = load_json(args.library, required=True)
        state = load_json(args.state)
        state_ids, state_hashes = recent_media(state, current_title=args.current_title)
        result = recommend(
            library, topic=args.topic, keyword=args.keyword, article_type=args.article_type,
            count=args.count, placement_mode=args.placement_mode,
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
            print(f"{item['id']}\t{item['selectionRole']}\t{item['filename']}\t{location}")
        if result["missingToMinimum"]:
            shortage_label = "문맥에 맞는 실제 사진" if args.placement_mode == "before-credential" else "검수된 실제 진료 사진"
            print(
                f"{shortage_label} 부족: "
                f"새로 선택 가능한 사진 {result['freshEligibleCount']}장, "
                f"직전 글 승인 사진 {result['blockedImmediatelyPreviousCount']}장, "
                f"최소 기준까지 {result['missingToMinimum']}장 부족합니다. "
                "사용자 결정이 필요합니다."
            )
    return 0 if result["status"] != "decision-required" else 1


if __name__ == "__main__":
    raise SystemExit(main())
