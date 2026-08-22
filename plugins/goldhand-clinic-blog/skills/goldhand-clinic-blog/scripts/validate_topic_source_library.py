#!/usr/bin/env python3
"""Validate the Beomeo topic-only source library and its hard role boundary."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "beomeo-topic-idea-library.json"
DEFAULT_INVENTORY = SKILL_DIR / "references" / "beomeo-source-inventory.md"
EXPECTED_SOURCE_ROLE = "topic-idea-and-coverage-questions-only"
EXPECTED_BLOG_ID = "beomeo_sm"
EXPECTED_BLOG_URL = "https://blog.naver.com/beomeo_sm"
EXPECTED_AUDIT_DATE = "2026-08-20"
EXPECTED_POST_COUNT = 69
REQUIRED_CLUSTERS = {
    "chuna",
    "traffic-accident",
    "pain",
    "digestive",
    "respiratory",
    "tonic",
    "growth",
    "weight-management",
}
REQUIRED_DENIED_USES = {
    "titlePattern",
    "articleStructure",
    "prose",
    "formatting",
    "medicalClaim",
    "clinicFact",
    "case",
    "sentence",
    "media",
}
ALLOWED_PAYLOAD_KEYS = {"sourceTitle", "topicIdea", "coverageQuestions"}
FORBIDDEN_EXACT_KEYS = {
    "writingMasterId",
    "compatibleWritingMasterIds",
    "titlePatternId",
    "titlePatternDescription",
    "questionPlacement",
    "openingMode",
    "solutionPreviewMode",
    "answerAgenda",
    "renderContract",
    "bodyText",
    "sourceHtml",
    "claims",
    "cases",
    "media",
}
FORBIDDEN_KEY_WORDS = {
    "title",
    "pattern",
    "hook",
    "structure",
    "outline",
    "section",
    "paragraph",
    "opening",
    "introduction",
    "body",
    "closing",
    "conclusion",
    "prose",
    "copy",
    "draft",
    "template",
    "format",
    "formatting",
    "style",
    "tone",
    "claim",
    "claims",
    "fact",
    "facts",
    "case",
    "cases",
    "sentence",
    "sentences",
    "media",
    "image",
    "images",
    "video",
    "videos",
    "content",
    "answer",
    "answers",
    "evidence",
    "citation",
    "citations",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"라이브러리를 찾을 수 없습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 형식이 올바르지 않습니다: {path}:{exc.lineno}:{exc.colno}") from exc
    if not isinstance(value, dict):
        raise ValueError("라이브러리 최상위 값은 객체여야 합니다.")
    return value


def parse_inventory(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"감사 목록을 찾을 수 없습니다: {path}") from exc
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r"^\|\s*(?P<number>\d+)\s*\|\s*(?P<post_id>\d{12})\s*\|\s*"
        r"(?P<title>.*?)\s*\|\s*(?P<url>https://blog\.naver\.com/beomeo_sm/\d{12})\s*\|\s*$"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            rows.append(match.groupdict())
    if len(rows) != EXPECTED_POST_COUNT:
        raise ValueError(
            f"감사 목록의 공개 글 수가 {EXPECTED_POST_COUNT}편이 아닙니다: {len(rows)}편"
        )
    return rows


def split_key_words(key: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    return {part.lower() for part in re.findall(r"[A-Za-z]+", expanded)}


def find_forbidden_payload_keys(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key not in ALLOWED_PAYLOAD_KEYS:
                blocked = split_key_words(key) & FORBIDDEN_KEY_WORDS
                if key in FORBIDDEN_EXACT_KEYS or blocked:
                    reason = ", ".join(sorted(blocked)) if blocked else "explicitly forbidden"
                    errors.append(
                        f"작성·구조·사실·내용 payload 키를 둘 수 없습니다: {child_path} "
                        f"({reason})"
                    )
            errors.extend(find_forbidden_payload_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(find_forbidden_payload_keys(child, f"{path}[{index}]"))
    return errors


def require_string(item: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"비어 있지 않은 문자열이 필요합니다: {path}.{key}")
        return ""
    return value.strip()


def require_string_list(
    item: dict[str, Any],
    key: str,
    path: str,
    errors: list[str],
    *,
    minimum: int = 1,
) -> list[str]:
    value = item.get(key)
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or any(not isinstance(entry, str) or not entry.strip() for entry in value)
    ):
        errors.append(f"문자열 {minimum}개 이상의 배열이 필요합니다: {path}.{key}")
        return []
    return [entry.strip() for entry in value]


def validate_source_posts(
    library: dict[str, Any],
    inventory_rows: list[dict[str, str]],
    errors: list[str],
) -> set[str]:
    source_posts = library.get("sourcePosts")
    if not isinstance(source_posts, list):
        errors.append("sourcePosts는 배열이어야 합니다.")
        return set()
    if len(source_posts) != EXPECTED_POST_COUNT:
        errors.append(f"sourcePosts는 {EXPECTED_POST_COUNT}편이어야 합니다: {len(source_posts)}편")

    expected_by_id = {row["post_id"]: row for row in inventory_rows}
    seen_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    seen_urls: set[str] = set()
    blocked_terms = library.get("blockedNamedProductsAndDevices")
    if not isinstance(blocked_terms, list) or any(
        not isinstance(term, str) or not term.strip() for term in blocked_terms
    ):
        errors.append("blockedNamedProductsAndDevices는 비어 있지 않은 문자열 배열이어야 합니다.")
        blocked_terms = []

    for index, post in enumerate(source_posts):
        path = f"$.sourcePosts[{index}]"
        if not isinstance(post, dict):
            errors.append(f"객체가 필요합니다: {path}")
            continue
        item_id = require_string(post, "id", path, errors)
        post_id = require_string(post, "sourcePostId", path, errors)
        source_title = require_string(post, "sourceTitle", path, errors)
        source_url = require_string(post, "sourceUrl", path, errors)
        require_string(post, "eligibilityReason", path, errors)
        require_string_list(post, "topicClusters", path, errors)
        require_string_list(post, "subjectIds", path, errors)
        if not isinstance(post.get("autoEligible"), bool):
            errors.append(f"불리언이 필요합니다: {path}.autoEligible")
        if item_id != f"BM{post_id}":
            errors.append(f"id는 BM+sourcePostId 형식이어야 합니다: {path}.id")
        if item_id in seen_ids:
            errors.append(f"중복 sourcePosts id: {item_id}")
        if post_id in seen_source_ids:
            errors.append(f"중복 sourcePostId: {post_id}")
        if source_url in seen_urls:
            errors.append(f"중복 sourceUrl: {source_url}")
        seen_ids.add(item_id)
        seen_source_ids.add(post_id)
        seen_urls.add(source_url)

        expected = expected_by_id.get(post_id)
        if expected is None:
            errors.append(f"감사 목록에 없는 sourcePostId: {post_id}")
        else:
            if source_title != expected["title"]:
                errors.append(f"감사 목록과 제목이 다릅니다: {post_id}")
            if source_url != expected["url"]:
                errors.append(f"감사 목록과 URL이 다릅니다: {post_id}")

        matching_blocked_terms = [term for term in blocked_terms if term in source_title]
        if matching_blocked_terms and post.get("autoEligible") is not False:
            errors.append(
                f"고유 장비·프로그램 원문은 autoEligible=false여야 합니다: {post_id} "
                f"({', '.join(matching_blocked_terms)})"
            )

    expected_source_ids = set(expected_by_id)
    if seen_source_ids != expected_source_ids:
        missing = sorted(expected_source_ids - seen_source_ids)
        extra = sorted(seen_source_ids - expected_source_ids)
        if missing:
            errors.append(f"감사 목록에서 빠진 글 ID: {', '.join(missing)}")
        if extra:
            errors.append(f"감사 목록에 없는 글 ID: {', '.join(extra)}")
    return seen_ids


def validate_topic_ideas(
    library: dict[str, Any],
    source_ids: set[str],
    errors: list[str],
) -> None:
    topic_ideas = library.get("topicIdeas")
    if not isinstance(topic_ideas, list) or not topic_ideas:
        errors.append("selector가 읽을 top-level topicIdeas 배열이 비어 있습니다.")
        return
    blocked_terms = [
        term
        for term in library.get("blockedNamedProductsAndDevices", [])
        if isinstance(term, str) and term.strip()
    ]
    seen_ids: set[str] = set()
    seen_semantic_ids: set[str] = set()
    eligible_clusters: set[str] = set()
    source_titles = {
        post.get("sourceTitle")
        for post in library.get("sourcePosts", [])
        if isinstance(post, dict)
    }

    for index, idea in enumerate(topic_ideas):
        path = f"$.topicIdeas[{index}]"
        if not isinstance(idea, dict):
            errors.append(f"객체가 필요합니다: {path}")
            continue
        item_id = require_string(idea, "id", path, errors)
        topic_idea = require_string(idea, "topicIdea", path, errors)
        cluster = require_string(idea, "topicCluster", path, errors)
        require_string(idea, "primarySubjectId", path, errors)
        require_string(idea, "intentId", path, errors)
        semantic_id = require_string(idea, "semanticTopicId", path, errors)
        require_string(idea, "eligibilityReason", path, errors)
        require_string_list(idea, "subjectIds", path, errors)
        require_string_list(idea, "dedupeKeys", path, errors, minimum=2)
        require_string_list(idea, "topicTerms", path, errors, minimum=3)
        coverage_questions = require_string_list(
            idea, "coverageQuestions", path, errors, minimum=2
        )
        referenced_sources = require_string_list(idea, "sourcePostIds", path, errors)
        if idea.get("autoEligible") is not True:
            errors.append(f"정규화 topicIdeas는 autoEligible=true여야 합니다: {path}")
        else:
            eligible_clusters.add(cluster)
        if item_id in seen_ids:
            errors.append(f"중복 topicIdeas id: {item_id}")
        if semantic_id in seen_semantic_ids:
            errors.append(f"중복 semanticTopicId: {semantic_id}")
        seen_ids.add(item_id)
        seen_semantic_ids.add(semantic_id)
        if topic_idea in source_titles:
            errors.append(f"원문 제목을 topicIdea로 그대로 사용할 수 없습니다: {item_id}")
        for source_id in referenced_sources:
            if source_id not in source_ids:
                errors.append(f"존재하지 않는 sourcePostIds 참조: {path} -> {source_id}")

        active_text = " ".join(
            [
                topic_idea,
                *[str(value) for value in idea.get("dedupeKeys", [])],
                *[str(value) for value in idea.get("topicTerms", [])],
                *coverage_questions,
            ]
        )
        leaked_terms = sorted({term for term in blocked_terms if term in active_text})
        if leaked_terms:
            errors.append(
                f"자동 주제 payload에 고유 장비·프로그램명이 남아 있습니다: {item_id} "
                f"({', '.join(leaked_terms)})"
            )

    missing_clusters = REQUIRED_CLUSTERS - eligible_clusters
    if missing_clusters:
        errors.append(
            "필수 정보성 주제군에 자동 선택 아이디어가 없습니다: "
            + ", ".join(sorted(missing_clusters))
        )


def validate_library(library: dict[str, Any], inventory_rows: list[dict[str, str]]) -> list[str]:
    errors = find_forbidden_payload_keys(library)
    if library.get("schemaVersion") != 1:
        errors.append("schemaVersion은 1이어야 합니다.")
    if library.get("sourceRole") != EXPECTED_SOURCE_ROLE:
        errors.append(f"sourceRole은 {EXPECTED_SOURCE_ROLE}이어야 합니다.")
    if library.get("sourceBlogId") != EXPECTED_BLOG_ID:
        errors.append(f"sourceBlogId는 {EXPECTED_BLOG_ID}여야 합니다.")
    if library.get("sourceBlogUrl") != EXPECTED_BLOG_URL:
        errors.append(f"sourceBlogUrl은 {EXPECTED_BLOG_URL}이어야 합니다.")
    if library.get("auditedAt") != EXPECTED_AUDIT_DATE:
        errors.append(f"auditedAt은 {EXPECTED_AUDIT_DATE}이어야 합니다.")
    if library.get("auditedPublicPostCount") != EXPECTED_POST_COUNT:
        errors.append(f"auditedPublicPostCount는 {EXPECTED_POST_COUNT}이어야 합니다.")

    boundary = library.get("boundaryPolicy")
    if not isinstance(boundary, dict):
        errors.append("boundaryPolicy 객체가 필요합니다.")
    else:
        if boundary.get("mayInform") != ["topicIdea", "coverageQuestions"]:
            errors.append("boundaryPolicy.mayInform은 topicIdea와 coverageQuestions만 허용해야 합니다.")
        denied_uses = boundary.get("mustNeverInform")
        if not isinstance(denied_uses, list) or not REQUIRED_DENIED_USES.issubset(
            {str(value) for value in denied_uses}
        ):
            errors.append("boundaryPolicy.mustNeverInform에 모든 작성·사실 금지 역할이 필요합니다.")

    required_clusters = library.get("requiredTopicClusters")
    if not isinstance(required_clusters, list) or set(required_clusters) != REQUIRED_CLUSTERS:
        errors.append("requiredTopicClusters가 필수 8개 주제군과 정확히 일치해야 합니다.")

    source_ids = validate_source_posts(library, inventory_rows, errors)
    validate_topic_ideas(library, source_ids, errors)
    return errors


def main() -> int:
    args = parse_args()
    try:
        library = load_json(args.library)
        inventory_rows = parse_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate_library(library, inventory_rows)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(
            "Beomeo topic source library is valid: "
            f"{len(library['sourcePosts'])} source posts, "
            f"{len(library['topicIdeas'])} normalized topic ideas."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
