#!/usr/bin/env python3
"""Select a fresh semantic topic plus independent editorial and writing masters."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "topic-idea-library.json"
DEFAULT_TOPIC_SOURCE_LIBRARY = SKILL_DIR / "assets" / "beomeo-topic-idea-library.json"
DEFAULT_EDITORIAL_PROFILE_LIBRARY = SKILL_DIR / "assets" / "beomeo-editorial-master-profiles.json"
TOPIC_SOURCE_ROLE = "topic-idea-and-coverage-questions-only"
EDITORIAL_SOURCE_ROLE = "title-tone-content-sequence-only"
EDITORIAL_PROFILE_LIVE_REQUIRED = "live-source-audit-required"
EDITORIAL_PROFILE_UNAVAILABLE = "unavailable"

GENERIC_TOPIC_STOPWORDS = {
    "광주",
    "한의원",
    "추천",
    "금손한의원",
    "한의사",
    "한의사가",
    "관련",
    "정보",
    "이야기",
    "질문",
    "특징",
    "가지",
    "두가지",
    "세가지",
    "알려드립니다",
    "알아보기",
}

# The order is intentional: treatment/drug families are the primary subject when
# a legacy title also contains a symptom that the treatment was used for.
SUBJECT_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"위고비|마운자로|wegovy|mounjaro|glp\s*[-_]?\s*1", re.I), "glp1-obesity-medication"),
    (re.compile(r"추나요법|추나"), "chuna-manual-therapy"),
    (re.compile(r"일자목|거북목"), "cervical-posture-disorder"),
)

PROHIBITED_TOPIC_SOURCE_KEYS = {
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
    "facts",
    "clinicFacts",
    "sentences",
    "sourceSentences",
    "media",
    "images",
    "contacts",
    "programs",
}


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


def stable_number(*parts: str) -> int:
    payload = "\u241f".join(parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest(), 16)


def date_score(value: str) -> int:
    parts = [int(part) for part in re.findall(r"\d+", value)[:3]]
    return parts[0] * 10_000 + parts[1] * 100 + parts[2] if len(parts) == 3 else 0


def tokens(value: str) -> set[str]:
    result = {
        token
        for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", value.lower())
        if token not in GENERIC_TOPIC_STOPWORDS
    }
    for pattern, canonical in SUBJECT_ALIASES:
        if pattern.search(value):
            result.add(canonical)
    return result


def string_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_identifier(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^0-9a-z가-힣]+", "-", value.lower())).strip("-")


def canonical_subject(value: str) -> str:
    for pattern, canonical in SUBJECT_ALIASES:
        if pattern.search(value):
            return canonical
    return normalize_identifier(value)


def subject_ids_from(values: Iterable[str], text_value: str = "") -> list[str]:
    result: list[str] = []

    def add(value: str) -> None:
        canonical = canonical_subject(value)
        if canonical and canonical not in GENERIC_TOPIC_STOPWORDS and canonical not in result:
            result.append(canonical)

    for pattern, canonical in SUBJECT_ALIASES:
        if pattern.search(text_value):
            add(canonical)
    for value in values:
        add(value)
    return result


def normalize_intent(value: str, text_value: str = "") -> str:
    normalized = normalize_identifier(value)
    if normalized:
        if re.search(r"risk|warning|주의|위험|방치", normalized):
            return "risk-warning"
        if re.search(r"self-care|생활|관리|예방", normalized):
            return "self-care"
        if re.search(r"treatment|decision|치료|적용|선택", normalized):
            return "treatment-decision"
        if re.search(r"symptom|cause|증상|원인|구분", normalized):
            return "symptom-cause"
        if re.search(r"comparison|비교|차이", normalized):
            return "comparison"
        return normalized
    if re.search(r"비교|차이|vs|어떤\s*것", text_value, re.I):
        return "comparison"
    if re.search(r"부작용|주의|금기|위험|방치|소용없", text_value):
        return "risk-warning"
    if re.search(r"보험|비용|가격", text_value):
        return "cost-insurance"
    if re.search(r"원리|작용|효과|변화", text_value):
        return "mechanism-effect"
    if re.search(r"대상|적합|선택|기준|치료|추나|약침|침|한약", text_value):
        return "treatment-decision"
    if re.search(r"생활습관|음식|관리|예방|운동|스트레칭", text_value):
        return "self-care"
    if re.search(r"원인|이유|증상|구분", text_value):
        return "symptom-cause"
    return "general-information"


def canonical_dedupe_key(value: str) -> str:
    subject = canonical_subject(value)
    return subject or normalize_identifier(value)


def load_json(path: Path, *, missing: dict[str, object] | None = None) -> dict[str, object]:
    if not path.exists() and missing is not None:
        return missing
    return json.loads(path.read_text(encoding="utf-8"))


def infer_legacy_idea_type(item: dict[str, object]) -> str:
    article_type = str(item.get("type", ""))
    if article_type == "업체소개형":
        return "clinic-trust"
    if article_type == "사례공유형":
        return "case-journey"
    if article_type == "스토리텔링형":
        return "doctor-philosophy"
    text_value = f"{item.get('title', '')} {item.get('topic', '')}"
    if re.search(r"주의|방치|소용없|모르면|위험|절대|안\s*되는", text_value):
        return "risk-warning"
    if re.search(r"생활습관|음식|관리|예방|운동|스트레칭", text_value):
        return "self-care"
    if re.search(r"치료|추나|약침|침|한약|보험|복용|보약", text_value):
        return "treatment-decision"
    return "symptom-cause" if article_type == "정보전달형" else ""


def infer_legacy_pattern(item: dict[str, object]) -> str:
    text_value = f"{item.get('titlePattern', '')} {item.get('title', '')} {item.get('topic', '')}"
    numbered = bool(re.search(r"(?:\d+|두|세)\s*가지", text_value))
    if re.search(r"공통점|특징", text_value):
        return "reader-commonality-numbered" if numbered else "reader-commonality"
    if re.search(r"모르면|소용없|방치|주의", text_value):
        return "warning-consequence-numbered" if numbered else "warning-consequence"
    if re.search(r"왜|이유", text_value):
        return "reason-explained"
    if re.search(r"실례|사례|치료된|호전|완화|경험", text_value):
        return "case-outcome-journey"
    if numbered:
        return "expert-answer-numbered"
    if re.search(r"방법|가이드|원칙|핵심|기준", text_value):
        return "how-to-principle"
    return ""


def infer_legacy_master(item: dict[str, object]) -> str:
    article_type = str(item.get("type", ""))
    text_value = f"{item.get('title', '')} {item.get('topic', '')} {item.get('titlePattern', '')}"
    rules = {
        "업체소개형": (
            (r"비교|선택\s*기준|3\s*가지\s*기준", "COMP01"),
            (r"맞춤|가족|협진", "COMP02"),
            (r"통합|몸\s*전체|한\s*부위", "COMP03"),
            (r"심리|검사상\s*이상|몸과\s*마음", "COMP04"),
        ),
        "사례공유형": (
            (r"공통점\s*2|둘\s*이상", "CASE03"),
            (r"공통점", "CASE01"),
        ),
        "스토리텔링형": (
            (r"전환점|철학|가족\s*경험", "STORY02"),
            (r"개원|한\s*자리|지역", "STORY01"),
        ),
    }
    for pattern, master_id in rules.get(article_type, ()):
        if re.search(pattern, text_value):
            return master_id
    return ""


def recent_entries(state: dict[str, object]) -> list[dict[str, object]]:
    entries = state.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [item for item in entries if isinstance(item, dict)][:3]


def recent_dimensions(state: dict[str, object]) -> tuple[set[str], set[str], set[str], set[str]]:
    normalized_entries = recent_entries(state)
    idea_types = {
        value
        for item in normalized_entries
        if (value := str(item.get("ideaType") or infer_legacy_idea_type(item)))
    }
    patterns = {
        value
        for item in normalized_entries
        if (value := str(item.get("titlePatternId") or infer_legacy_pattern(item)))
    }
    urls = {str(item.get("ideaReferenceUrl")) for item in normalized_entries if item.get("ideaReferenceUrl")}
    masters = {
        value
        for item in normalized_entries
        if (value := str(item.get("writingMasterId") or infer_legacy_master(item)))
    }
    return idea_types, patterns, urls, masters


def semantic_signature(item: dict[str, object]) -> dict[str, object]:
    text_value = " ".join(
        str(item.get(field, ""))
        for field in (
            "title",
            "topic",
            "topicIdea",
            "mainKeyword",
            "ideaReferenceTitle",
            "topicSourceTitle",
        )
    )
    explicit_subjects = string_list(item.get("subjectIds"))
    primary_raw = str(item.get("primarySubjectId", "")).strip()
    subjects = subject_ids_from(([primary_raw] if primary_raw else []) + explicit_subjects, text_value)
    if not subjects:
        subjects = subject_ids_from(sorted(tokens(text_value)))
    primary_subject = canonical_subject(primary_raw) if primary_raw else (subjects[0] if subjects else "")
    intent = normalize_intent(
        str(item.get("topicIntent") or item.get("intentId") or item.get("ideaType") or ""),
        text_value,
    )
    # Preserve the library's canonical public ID in output/state. Comparison is
    # normalized inside semantic_overlap so harmless punctuation/case drift in
    # legacy history does not weaken the duplicate gate.
    semantic_id = str(item.get("semanticTopicId", "")).strip()
    if not semantic_id:
        source_url = str(item.get("topicSourceUrl") or item.get("ideaReferenceUrl") or "")
        source_match = re.search(r"/(\d{6,})", source_url)
        if source_match:
            semantic_id = f"source-{source_match.group(1)}"
        elif primary_subject:
            semantic_id = f"{primary_subject}-{intent}"
    explicit_keys = string_list(item.get("dedupeKeys"))
    if explicit_keys:
        dedupe_keys = {canonical_dedupe_key(value) for value in explicit_keys if canonical_dedupe_key(value)}
    else:
        dedupe_keys = {canonical_dedupe_key(value) for value in tokens(text_value)}
        dedupe_keys.update(subjects)
        if intent:
            dedupe_keys.add(intent)
    return {
        "semanticTopicId": semantic_id,
        "topicCluster": normalize_identifier(str(item.get("topicCluster", ""))),
        "primarySubjectId": primary_subject,
        "subjectIds": subjects,
        "topicIntent": intent,
        "dedupeKeys": sorted(dedupe_keys),
    }


def semantic_overlap(left: dict[str, object], right: dict[str, object]) -> bool:
    left_id = str(left.get("semanticTopicId", ""))
    right_id = str(right.get("semanticTopicId", ""))
    if left_id and right_id and normalize_identifier(left_id) == normalize_identifier(right_id):
        return True
    left_primary = str(left.get("primarySubjectId", ""))
    right_primary = str(right.get("primarySubjectId", ""))
    if left_primary and right_primary and left_primary == right_primary:
        return True
    left_subjects = set(string_list(left.get("subjectIds")))
    right_subjects = set(string_list(right.get("subjectIds")))
    left_intent = str(left.get("topicIntent", ""))
    right_intent = str(right.get("topicIntent", ""))
    if left_subjects & right_subjects and left_intent and left_intent == right_intent:
        return True
    left_keys = {canonical_dedupe_key(value) for value in string_list(left.get("dedupeKeys"))}
    right_keys = {canonical_dedupe_key(value) for value in string_list(right.get("dedupeKeys"))}
    if left_keys and right_keys:
        similarity = len(left_keys & right_keys) / len(left_keys | right_keys)
        if similarity >= 0.5:
            return True
    return False


def eligible_wipark_articles(library: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, Any], str, set[str]]:
    articles = library.get("articles", [])
    registry = library.get("writingMasterRegistry", {})
    family_id = str(library.get("referenceFamilyId", ""))
    allowed_reference_ids = {str(value) for value in library.get("allowedReferenceIds", [])}
    allowed_master_ids = {str(value) for value in library.get("allowedMasterIds", [])}
    if not isinstance(articles, list) or not isinstance(registry, dict):
        raise ValueError("주제 아이디어 라이브러리 형식이 올바르지 않습니다.")
    if family_id != "two-or-three-reader-concern-hooks-solution-preview-info":
        raise ValueError("독자 고민 2~3개·해결 방향 예고형 라이브러리가 아닙니다.")
    if not allowed_reference_ids or not allowed_master_ids:
        raise ValueError("허용 레퍼런스 목록이 비어 있습니다.")
    eligible = [
        article
        for article in articles
        if isinstance(article, dict)
        and str(article.get("id")) in allowed_reference_ids
        and article.get("referenceFamilyId") == family_id
        and article.get("sourceContentType") == "정보전달형"
        and article.get("minimumReaderHookCount") == 2
        and article.get("maximumReaderHookCount") == 3
        and article.get("allowedReaderHookCounts") == [2, 3]
        and article.get("requiresSolutionPreviewBeforeBody") is True
        and article.get("sourceFactsBlocked") is True
        and any(
            master_id in allowed_master_ids
            and master_id in registry
            and registry[master_id].get("type") == "정보전달형"
            and registry[master_id].get("autoEligible") is True
            for master_id in article.get("compatibleWritingMasterIds", [])
        )
    ]
    if not eligible:
        raise ValueError("선택 가능한 Wipark 글쓰기 마스터가 없습니다.")
    return eligible, registry, family_id, allowed_master_ids


def wipark_topic_candidate(article: dict[str, object], library: dict[str, object]) -> dict[str, object]:
    topic_terms = string_list(article.get("topicTerms"))
    topic_idea = str(article.get("sourceTitle", "")).strip()
    profile = semantic_signature(
        {
            "semanticTopicId": f"wipark-{article.get('id', '')}",
            "topicIdea": topic_idea,
            "subjectIds": topic_terms,
            "ideaType": article.get("primaryType", ""),
            "dedupeKeys": topic_terms + [str(article.get("primaryType", ""))],
        }
    )
    agendas = string_list(article.get("answerAgenda"))
    coverage = string_list(article.get("readerQuestion")) + [f"{agenda}는 어떤 기준으로 살펴봐야 하는가?" for agenda in agendas]
    return {
        "topicSourceId": str(article.get("id", "")),
        "topicSourceTitle": str(article.get("sourceTitle", "")),
        "topicSourceUrl": str(article.get("sourceUrl", "")),
        "topicSourceUrls": [str(article.get("sourceUrl", ""))],
        "topicSourcePublishedAt": str(article.get("publishedAt", "")),
        "topicSourceBlogId": str(library.get("sourceBlogId", "wi-parkclinic")),
        "topicSourceRole": TOPIC_SOURCE_ROLE,
        "topicSourcePostIds": [str(article.get("id", ""))],
        "editorialMasterId": str(article.get("id", "")),
        "editorialReferenceTitle": str(article.get("sourceTitle", "")),
        "editorialReferenceUrl": str(article.get("sourceUrl", "")),
        "editorialSourceRole": EDITORIAL_SOURCE_ROLE,
        "editorialProfileStatus": "ready",
        "editorialCandidateId": str(article.get("id", "")),
        "editorialCandidateTitle": str(article.get("sourceTitle", "")),
        "editorialCandidateUrl": str(article.get("sourceUrl", "")),
        "topicIdea": topic_idea,
        "coverageQuestions": coverage,
        "topicTerms": topic_terms,
        "broadKeywordPriority": int(article.get("broadKeywordPriority", 0)),
        "_wiparkArticleId": str(article.get("id", "")),
        **profile,
    }


def empty_editorial_selection(candidate: dict[str, object] | None = None) -> dict[str, str]:
    candidate = candidate or {}
    has_candidate = bool(candidate)
    return {
        "editorialMasterId": "",
        "editorialReferenceTitle": "",
        "editorialReferenceUrl": "",
        "editorialSourceRole": "",
        "editorialProfileStatus": EDITORIAL_PROFILE_LIVE_REQUIRED if has_candidate else EDITORIAL_PROFILE_UNAVAILABLE,
        "editorialCandidateId": str(candidate.get("id", "")),
        "editorialCandidateTitle": str(candidate.get("sourceTitle", "")),
        "editorialCandidateUrl": str(candidate.get("sourceUrl", "")),
    }


def editorial_selection_for_topic(
    idea: dict[str, object],
    source_posts: list[dict[str, object]],
    profile_library: dict[str, object] | None,
) -> dict[str, str]:
    """Resolve a preaudited master or expose one source candidate for live audit."""
    if not profile_library:
        return empty_editorial_selection(source_posts[0] if len(source_posts) == 1 else None)
    if str(profile_library.get("sourceRole", "")) != EDITORIAL_SOURCE_ROLE:
        raise ValueError(
            "허용되지 않은 편집 마스터 역할: "
            f"{profile_library.get('sourceRole') or '(비어 있음)'}"
        )
    assignments = profile_library.get("topicIdeaAssignments", {})
    candidate_assignments = profile_library.get("liveAuditCandidateAssignments", {})
    profiles = profile_library.get("profiles", {})
    if not isinstance(assignments, dict) or not isinstance(candidate_assignments, dict) or not isinstance(profiles, dict):
        raise ValueError("범어 편집 마스터 프로필 형식이 올바르지 않습니다.")

    idea_id = str(idea.get("id", ""))
    source_by_id = {str(post.get("id", "")): post for post in source_posts}
    assignment = assignments.get(idea_id)
    if assignment is None:
        source_ids = string_list(idea.get("sourcePostIds"))
        if len(source_ids) == 1:
            candidate_id = source_ids[0]
        else:
            candidate_assignment = candidate_assignments.get(idea_id)
            if not isinstance(candidate_assignment, dict):
                return empty_editorial_selection()
            candidate_id = str(candidate_assignment.get("primaryEditorialCandidate", "")).strip()
            if not candidate_id or candidate_id not in source_ids:
                raise ValueError(f"live audit 후보는 해당 주제의 sourcePostIds 중 한 편이어야 합니다: {idea_id}")
            if not str(candidate_assignment.get("selectionReason", "")).strip():
                raise ValueError(f"live audit 후보 선택 이유가 필요합니다: {idea_id}")
        candidate = source_by_id.get(candidate_id)
        if not candidate:
            raise ValueError(f"주제 소스에 없는 live audit 후보입니다: {idea_id} -> {candidate_id}")
        return empty_editorial_selection(candidate)
    if not isinstance(assignment, dict):
        raise ValueError(f"편집 마스터 배정은 객체여야 합니다: {idea_id}")
    master_id = assignment.get("primaryEditorialSource")
    if not isinstance(master_id, str) or not master_id.strip():
        raise ValueError(f"primaryEditorialSource 한 편이 필요합니다: {idea_id}")
    master_id = master_id.strip()
    if master_id not in string_list(idea.get("sourcePostIds")):
        raise ValueError(
            f"편집 마스터는 해당 주제의 sourcePostIds 중 한 편이어야 합니다: "
            f"{idea_id} -> {master_id}"
        )
    profile = profiles.get(master_id)
    if not isinstance(profile, dict):
        raise ValueError(f"등록되지 않은 편집 마스터입니다: {master_id}")
    if str(profile.get("id", "")) != master_id:
        raise ValueError(f"편집 마스터 ID가 프로필 키와 다릅니다: {master_id}")
    if str(profile.get("sourceRole", "")) != EDITORIAL_SOURCE_ROLE:
        raise ValueError(f"편집 마스터 역할이 올바르지 않습니다: {master_id}")
    if idea_id not in string_list(profile.get("appliesToTopicIdeaIds")):
        raise ValueError(f"편집 마스터에 주제 배정이 선언되지 않았습니다: {master_id} -> {idea_id}")

    source_post = source_by_id.get(master_id)
    if not source_post:
        raise ValueError(f"주제 소스에 없는 편집 마스터입니다: {master_id}")
    for key in ("sourcePostId", "sourceTitle", "sourceUrl"):
        if str(profile.get(key, "")) != str(source_post.get(key, "")):
            raise ValueError(f"편집 마스터와 주제 소스의 {key}가 다릅니다: {master_id}")

    return {
        "editorialMasterId": master_id,
        "editorialReferenceTitle": str(profile.get("sourceTitle", "")),
        "editorialReferenceUrl": str(profile.get("sourceUrl", "")),
        "editorialSourceRole": EDITORIAL_SOURCE_ROLE,
        "editorialProfileStatus": "ready",
        "editorialCandidateId": master_id,
        "editorialCandidateTitle": str(profile.get("sourceTitle", "")),
        "editorialCandidateUrl": str(profile.get("sourceUrl", "")),
    }


def external_topic_candidates(
    topic_library: dict[str, object],
    editorial_profile_library: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    role = str(topic_library.get("sourceRole", ""))
    if role != TOPIC_SOURCE_ROLE:
        raise ValueError(f"허용되지 않은 주제 소스 역할: {role or '(비어 있음)'}")
    raw_ideas = topic_library.get("topicIdeas", topic_library.get("topics", topic_library.get("articles", [])))
    raw_posts = topic_library.get("sourcePosts", [])
    if not isinstance(raw_ideas, list) or not isinstance(raw_posts, list):
        raise ValueError("주제 소스 라이브러리 형식이 올바르지 않습니다.")
    posts: dict[str, dict[str, object]] = {}
    for post in raw_posts:
        if not isinstance(post, dict):
            continue
        for key in (post.get("id"), post.get("sourcePostId")):
            if key:
                posts[str(key)] = post
    if editorial_profile_library is None and DEFAULT_EDITORIAL_PROFILE_LIBRARY.exists():
        editorial_profile_library = load_json(DEFAULT_EDITORIAL_PROFILE_LIBRARY)
    candidates: list[dict[str, object]] = []
    for idea in raw_ideas:
        if not isinstance(idea, dict) or idea.get("autoEligible") is False:
            continue
        prohibited = sorted(PROHIBITED_TOPIC_SOURCE_KEYS & set(idea))
        if prohibited:
            raise ValueError(f"주제 소스가 글쓰기 구조를 포함합니다: {', '.join(prohibited)}")
        source_post_ids = string_list(idea.get("sourcePostIds"))
        source_posts = [posts[value] for value in source_post_ids if value in posts]
        first_post = source_posts[0] if source_posts else {}
        source_urls = [str(post.get("sourceUrl", "")) for post in source_posts if str(post.get("sourceUrl", ""))]
        source_title = str(first_post.get("sourceTitle") or idea.get("sourceTitle") or idea.get("topicIdea") or "")
        source_url = str(first_post.get("sourceUrl") or idea.get("sourceUrl") or topic_library.get("sourceBlogUrl") or "")
        editorial = editorial_selection_for_topic(idea, source_posts, editorial_profile_library)
        semantic_input = dict(idea)
        semantic_input["topicIntent"] = idea.get("topicIntent") or idea.get("intentId") or ""
        profile = semantic_signature(semantic_input)
        topic_idea = str(idea.get("topicIdea", "")).strip()
        if not topic_idea or not str(idea.get("id", "")).strip() or not profile["primarySubjectId"]:
            continue
        candidates.append(
            {
                "topicSourceId": str(idea.get("id", "")),
                "topicSourceTitle": source_title,
                "topicSourceUrl": source_url,
                "topicSourceUrls": source_urls or ([source_url] if source_url else []),
                "topicSourcePublishedAt": str(first_post.get("publishedAt") or idea.get("publishedAt") or ""),
                "topicSourceBlogId": str(topic_library.get("sourceBlogId", "")),
                "topicSourceRole": role,
                "topicSourcePostIds": source_post_ids,
                "topicIdea": topic_idea,
                "coverageQuestions": string_list(idea.get("coverageQuestions")),
                "topicTerms": string_list(idea.get("topicTerms")),
                "broadKeywordPriority": int(idea.get("broadKeywordPriority", 0)),
                **editorial,
                **profile,
            }
        )
    if not candidates:
        raise ValueError("선택 가능한 외부 정보성 주제 아이디어가 없습니다.")
    return candidates


def choose_master(
    options: list[str],
    registry: dict[str, Any],
    recent_masters: set[str],
    selected_masters: set[str],
    source_url: str,
    keyword: str,
    seed: str,
    article_id: str,
    master_query: str,
) -> str:
    usable = [master_id for master_id in options if master_id in registry and registry[master_id].get("autoEligible") is True]
    if not usable:
        raise ValueError(f"등록된 자동 글쓰기 마스터가 없습니다: {article_id}")
    query_tokens = tokens(master_query)
    return max(
        usable,
        key=lambda master_id: (
            len(
                query_tokens
                & tokens(
                    f"{registry[master_id].get('label', '')} {registry[master_id].get('bestFor', '')} "
                    + " ".join(str(value) for value in registry[master_id].get("selectionTags", []))
                )
            ),
            str(registry[master_id].get("sourceUrl", "")) == source_url,
            master_id not in recent_masters,
            master_id not in selected_masters,
            stable_number(keyword, seed, article_id, master_id),
        ),
    )


def choose_topic_candidates(
    candidates: list[dict[str, object]],
    state: dict[str, object],
    keyword: str,
    topic: str,
    count: int,
    seed: str,
    *,
    balance_sources: bool = False,
) -> list[dict[str, object]]:
    history = recent_entries(state)
    recent_profiles = [semantic_signature(item) for item in history]
    recent_source_urls = {
        str(item.get("topicSourceUrl") or item.get("ideaReferenceUrl"))
        for item in history
        if item.get("topicSourceUrl") or item.get("ideaReferenceUrl")
    }
    recent_clusters = {str(profile.get("topicCluster", "")) for profile in recent_profiles if profile.get("topicCluster")}
    query_tokens = tokens(f"{keyword} {topic}")
    broad_clinic_query = "한의원" in keyword and not query_tokens and not topic.strip()
    selected: list[dict[str, object]] = []
    selected_ids: set[str] = set()
    selected_blogs: set[str] = set()
    available_blogs = {str(item.get("topicSourceBlogId", "")) for item in candidates if item.get("topicSourceBlogId")}
    preferred_first_blog = ""
    if balance_sources and available_blogs:
        recent_blog_counts = {blog_id: 0 for blog_id in available_blogs}
        for item in history:
            blog_id = str(item.get("topicSourceBlogId", ""))
            if not blog_id:
                source_url = str(item.get("topicSourceUrl") or item.get("ideaReferenceUrl") or "")
                if "beomeo_sm" in source_url:
                    blog_id = "beomeo_sm"
                elif "wi-parkclinic" in source_url:
                    blog_id = "wi-parkclinic"
            if blog_id in recent_blog_counts:
                recent_blog_counts[blog_id] += 1
        minimum_count = min(recent_blog_counts.values())
        least_recent_blogs = sorted(blog_id for blog_id, value in recent_blog_counts.items() if value == minimum_count)
        # Start a new history with the newly approved topic-only source, then
        # alternate naturally as schema-v3 history accumulates.
        preferred_first_blog = "beomeo_sm" if "beomeo_sm" in least_recent_blogs else least_recent_blogs[0]

    for slot in range(count):
        blockers = recent_profiles + [semantic_signature(item) for item in selected]
        remaining = [
            candidate
            for candidate in candidates
            if str(candidate.get("topicSourceId", "")) not in selected_ids
            and not (set(string_list(candidate.get("topicSourceUrls"))) & recent_source_urls)
            and not any(semantic_overlap(candidate, blocker) for blocker in blockers)
        ]
        if not remaining:
            raise ValueError("no-semantic-fresh-topic")
        candidate = max(
            remaining,
            key=lambda item: (
                len(
                    query_tokens
                    & tokens(
                        " ".join(
                            [
                                str(item.get("topicIdea", "")),
                                " ".join(string_list(item.get("topicTerms"))),
                                " ".join(string_list(item.get("coverageQuestions"))),
                            ]
                        )
                    )
                ),
                (
                    str(item.get("topicSourceBlogId", "")) == preferred_first_blog
                    if not selected_blogs
                    else str(item.get("topicSourceBlogId", "")) not in selected_blogs
                )
                if balance_sources
                else False,
                int(item.get("broadKeywordPriority", 0)) if broad_clinic_query and not balance_sources else 0,
                str(item.get("topicCluster", "")) not in recent_clusters,
                stable_number(keyword, topic, seed, str(slot), str(item.get("topicSourceId", ""))),
                date_score(str(item.get("topicSourcePublishedAt", ""))),
            ),
        )
        selected.append(candidate)
        selected_ids.add(str(candidate.get("topicSourceId", "")))
        selected_blogs.add(str(candidate.get("topicSourceBlogId", "")))
    return selected


def select_ideas(
    library: dict[str, object],
    state: dict[str, object],
    keyword: str,
    *,
    topic: str = "",
    count: int = 1,
    seed: str = "",
    topic_source_library: dict[str, object] | None = None,
    editorial_profile_library: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    eligible, registry, family_id, allowed_master_ids = eligible_wipark_articles(library)
    seed = seed or date.today().isoformat()
    legacy_mode = topic_source_library is None
    wipark_topics = [wipark_topic_candidate(article, library) for article in eligible]
    if not legacy_mode and editorial_profile_library is None and DEFAULT_EDITORIAL_PROFILE_LIBRARY.exists():
        editorial_profile_library = load_json(DEFAULT_EDITORIAL_PROFILE_LIBRARY)
    topic_candidates = (
        wipark_topics
        if legacy_mode
        else external_topic_candidates(topic_source_library, editorial_profile_library) + wipark_topics
    )
    selected_topics = choose_topic_candidates(
        topic_candidates,
        state,
        keyword,
        topic,
        count,
        seed,
        balance_sources=not legacy_mode,
    )

    recent_types, recent_patterns, recent_urls, recent_masters = recent_dimensions(state)
    selected_pattern_ids: set[str] = set()
    selected_types: set[str] = set()
    selected_patterns: set[str] = set()
    selected_masters: set[str] = set()
    selections: list[dict[str, object]] = []

    for slot, topic_candidate in enumerate(selected_topics):
        if topic_candidate.get("_wiparkArticleId"):
            article = next(item for item in eligible if str(item.get("id")) == topic_candidate["_wiparkArticleId"])
        else:
            available = [item for item in eligible if str(item.get("id")) not in selected_pattern_ids]
            fresh_urls = [item for item in available if str(item.get("sourceUrl")) not in recent_urls]
            pool = fresh_urls or available
            if not pool:
                raise ValueError("선택 가능한 Wipark 글쓰기 패턴이 없습니다.")
            pattern_query_tokens = tokens(
                " ".join(
                    [
                        keyword,
                        topic,
                        str(topic_candidate.get("topicIdea", "")),
                        " ".join(string_list(topic_candidate.get("topicTerms"))),
                        " ".join(string_list(topic_candidate.get("coverageQuestions"))),
                    ]
                )
            )
            article = max(
                pool,
                key=lambda item: (
                    len(pattern_query_tokens & {str(term).lower() for term in item.get("topicTerms", [])}),
                    str(item.get("primaryType")) not in recent_types,
                    str(item.get("primaryType")) not in selected_types,
                    str(item.get("titlePatternId")) not in recent_patterns,
                    str(item.get("titlePatternId")) not in selected_patterns,
                    date_score(str(item.get("publishedAt", ""))),
                    stable_number(keyword, topic, seed, str(slot), str(item.get("id", ""))),
                ),
            )

        source_url = str(article["sourceUrl"])
        master_id = choose_master(
            [str(value) for value in article.get("compatibleWritingMasterIds", []) if str(value) in allowed_master_ids],
            registry,
            recent_masters,
            selected_masters,
            source_url,
            keyword,
            seed,
            str(article["id"]),
            " ".join(
                [
                    keyword,
                    topic,
                    str(topic_candidate.get("topicIdea", "")),
                    " ".join(string_list(topic_candidate.get("coverageQuestions"))),
                    str(article.get("sourceTitle", "")),
                    str(article.get("readerQuestion", "")),
                ]
            ),
        )
        master = registry[master_id]
        selections.append(
            {
                "topicSourceId": topic_candidate["topicSourceId"],
                "topicSourceTitle": topic_candidate["topicSourceTitle"],
                "topicSourceUrl": topic_candidate["topicSourceUrl"],
                "topicSourceUrls": topic_candidate["topicSourceUrls"],
                "topicSourcePublishedAt": topic_candidate["topicSourcePublishedAt"],
                "topicSourceBlogId": topic_candidate["topicSourceBlogId"],
                "topicSourceRole": topic_candidate["topicSourceRole"],
                "topicSourcePostIds": topic_candidate["topicSourcePostIds"],
                "editorialMasterId": str(topic_candidate.get("editorialMasterId", "")),
                "editorialReferenceTitle": str(topic_candidate.get("editorialReferenceTitle", "")),
                "editorialReferenceUrl": str(topic_candidate.get("editorialReferenceUrl", "")),
                "editorialSourceRole": str(topic_candidate.get("editorialSourceRole", "")),
                "editorialProfileStatus": str(topic_candidate.get("editorialProfileStatus", "")),
                "editorialCandidateId": str(topic_candidate.get("editorialCandidateId", "")),
                "editorialCandidateTitle": str(topic_candidate.get("editorialCandidateTitle", "")),
                "editorialCandidateUrl": str(topic_candidate.get("editorialCandidateUrl", "")),
                "topicSourceControlsTitlePattern": False,
                "topicSourceControlsStructure": False,
                "topicSourceControlsFormatting": False,
                "topicSourceControlsClinicFacts": False,
                "semanticTopicId": topic_candidate["semanticTopicId"],
                "topicCluster": topic_candidate["topicCluster"],
                "primarySubjectId": topic_candidate["primarySubjectId"],
                "subjectIds": topic_candidate["subjectIds"],
                "topicIntent": topic_candidate["topicIntent"],
                "dedupeKeys": topic_candidate["dedupeKeys"],
                "topicIdea": topic_candidate["topicIdea"],
                "coverageQuestions": topic_candidate["coverageQuestions"],
                "ideaReferenceId": article["id"],
                "ideaReferenceTitle": article["sourceTitle"],
                "ideaReferenceUrl": source_url,
                "ideaType": article["primaryType"],
                "ideaTypeLabel": article["primaryTypeLabel"],
                "sourceContentType": article["sourceContentType"],
                "referenceFamilyId": family_id,
                "minimumReaderHookCount": 2,
                "maximumReaderHookCount": 3,
                "allowedReaderHookCounts": [2, 3],
                "requiresSolutionPreviewBeforeBody": True,
                "questionPlacement": article["questionPlacement"],
                "openingMode": article["openingMode"],
                "solutionPreviewMode": article["solutionPreviewMode"],
                "titlePatternId": article["titlePatternId"],
                "titlePatternDescription": article["titlePatternDescription"],
                "topicTerms": topic_candidate["topicTerms"],
                "patternReferenceTopicTerms": article["topicTerms"],
                "readerQuestion": article["readerQuestion"],
                "answerAgenda": article["answerAgenda"],
                "writingMasterId": master_id,
                "writingMasterLabel": master["label"],
                "writingReferenceUrl": master["sourceUrl"],
                "factPolicy": (
                    "선택한 Wipark 주제 원문 바로 그 한 편의 제목 장치·질문 위치·정보 순서·문장 호흡만 사용합니다. "
                    if str(topic_candidate.get("topicSourceBlogId", "")) == "wi-parkclinic"
                    else "범어 정규화 주제는 중복 검사에만 쓰고, ready 편집 마스터 또는 본문 감사가 필요한 candidate 한 편 외의 Wipark 글은 레이아웃 호환값일 뿐 말투·구조를 통제하지 않습니다. "
                )
                + "꾸밈은 네이버 순정 goldhand-naver-native-v4로 고정합니다. 실제 내용은 금손한의원 사실과 별도로 확인한 권위 자료로 새로 쓰며 원문의 업체·수치·주장·사례·문장·사진은 모두 폐기합니다.",
            }
        )
        selected_pattern_ids.add(str(article["id"]))
        selected_types.add(str(article["primaryType"]))
        selected_patterns.add(str(article["titlePatternId"]))
        selected_masters.add(master_id)
    return selections


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--topic", default="")
    parser.add_argument("--count", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--seed", default="")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--topic-source-library", type=Path, default=DEFAULT_TOPIC_SOURCE_LIBRARY)
    parser.add_argument(
        "--editorial-profile-library",
        type=Path,
        default=DEFAULT_EDITORIAL_PROFILE_LIBRARY,
    )
    parser.add_argument("--state", type=Path, default=default_state_path())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selections = select_ideas(
        load_json(args.library),
        load_json(args.state, missing={"maxEntries": 3, "entries": []}),
        args.keyword.strip(),
        topic=args.topic.strip(),
        count=args.count,
        seed=args.seed,
        topic_source_library=load_json(args.topic_source_library),
        editorial_profile_library=load_json(args.editorial_profile_library),
    )
    print(json.dumps({"keyword": args.keyword.strip(), "selections": selections}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
