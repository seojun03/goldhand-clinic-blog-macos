#!/usr/bin/env python3
"""Find and merge topic-matched general-information atoms for one Goldhand article."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BRIEFS = SKILL_DIR / "assets" / "wipark-content-briefs.json"
DEFAULT_PROFILES = SKILL_DIR / "assets" / "reference-master-profiles.json"
DEFAULT_USER_LIBRARY = SKILL_DIR / "assets" / "user-general-information-references.json"

TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")
NUMBERED_PROMISE = re.compile(r"(?P<count>\d+)\s*(?:가지|단계|기준|이유|방법|원칙|포인트)")
HANGUL = re.compile(r"[가-힣]")

STOP_TERMS = {
    "광주",
    "동천동",
    "한의원",
    "금손한의원",
    "추천",
    "정보",
    "관련",
    "제목",
    "본문",
    "가지",
    "방법",
    "알아보기",
    "알려주는",
    "원장",
    "원장님",
    "원인",
    "증상",
    "치료",
    "주의",
    "검사",
    "경우",
    "핵심",
    "질문",
    "조건",
    "포인트",
    "단계",
    "기준",
    "이유",
    "원칙",
}

TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "불면": ("불면증", "수면장애", "잠들기 어려움", "자주 깨는", "중도각성", "새벽각성", "수면"),
    "안면마비": ("얼굴마비", "구안와사", "벨마비"),
    "오십견": ("동결견", "유착성 관절낭염", "어깨가 안 올라감"),
    "추나요법": ("추나", "수기치료"),
    "무릎통증": ("무릎 통증", "슬관절 통증", "무릎이 아픈"),
    "갱년기": ("폐경", "완경", "안면홍조", "폐경기"),
    "체중관리": ("비만", "다이어트", "체중 감량", "요요"),
    "보약": ("기력저하", "기력 회복", "보약 복용", "한약"),
    "트라우마": ("외상 후 스트레스", "외상후스트레스", "PTSD"),
    "공황": ("공황장애", "공황 발작", "불안 발작"),
}

SOURCE_REQUIRED_CONTEXT: dict[str, tuple[str, ...]] = {
    "INFO10": ("갱년기", "폐경", "완경", "안면홍조"),
    "INFO11": ("트라우마", "외상후스트레스", "외상 후 스트레스", "ptsd"),
}

ATOM_REQUIRED_CONTEXT: dict[str, tuple[str, ...]] = {
    "INFO04-A2": ("공황", "불안", "우울", "정신건강", "두근거림", "가슴 답답"),
    "INFO04-A4": ("공황", "불안", "우울", "정신건강", "정신건강의학과"),
}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).lower().replace("\u200b", " ").strip()


def compact(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", normalize(value))


def tokens(value: str) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall(normalize(value))
        if token not in STOP_TERMS
    }


def unique_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        signature = compact(cleaned)
        if cleaned and signature not in seen:
            seen.add(signature)
            result.append(cleaned)
    return result


def query_terms(topic: str, title: str, keyword: str) -> set[str]:
    title_without_keyword = normalize(title).replace(normalize(keyword), " ") if keyword else title
    raw = f"{topic} {title_without_keyword}"
    result = tokens(raw)
    raw_compact = compact(raw)
    for canonical, aliases in TOPIC_ALIASES.items():
        family = (canonical, *aliases)
        if any(compact(term) and compact(term) in raw_compact for term in family):
            result.update(normalize(term) for term in family)
    return result


def topical_terms(topic: str) -> set[str]:
    """Return only subject anchors; generic title devices must never select a source."""
    result = tokens(topic)
    topic_compact = compact(topic)
    for canonical, aliases in TOPIC_ALIASES.items():
        family = (canonical, *aliases)
        if any(compact(term) and compact(term) in topic_compact for term in family):
            result.update(normalize(term) for term in family)
    return result


def has_context(raw_query: str, required: tuple[str, ...] | list[str]) -> bool:
    query = compact(raw_query)
    return any(compact(term) in query for term in required if compact(term))


def text_score(value: str, terms: set[str]) -> int:
    haystack = compact(value)
    score = 0
    for term in terms:
        needle = compact(term)
        if len(needle) < 2:
            continue
        if needle in haystack:
            score += min(10, max(2, len(needle)))
    return score


def source_atoms(source: dict[str, Any]) -> list[dict[str, Any]]:
    raw = source.get("generalInformationAtoms", source.get("orderedContentAtoms", []))
    if not isinstance(raw, list):
        return []
    atoms = [item for item in raw if isinstance(item, dict)]
    if source.get("sourceType") != "reviewed-reference-brief":
        atoms = [item for item in atoms if item.get("generalInformationOnly") is True]
    return atoms


def built_in_sources(briefs: dict[str, Any], profiles: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    profile_map = profiles.get("profiles", {}) if isinstance(profiles, dict) else {}
    for source_id, brief in briefs.get("briefs", {}).items():
        if not isinstance(brief, dict):
            continue
        profile = profile_map.get(source_id, {}) if isinstance(profile_map, dict) else {}
        result.append(
            {
                "id": str(source_id),
                "sourceTitle": str(profile.get("sourceTitle", brief.get("topic", ""))),
                "sourceUrl": str(brief.get("sourceUrl", "")),
                "sourceType": "reviewed-reference-brief",
                "sourceClinicName": "위석부부한의원",
                "topic": str(brief.get("topic", "")),
                "topicTags": [],
                "readerConcerns": brief.get("readerConcerns", []),
                "generalInformationAtoms": brief.get("orderedContentAtoms", []),
                "blockedFromSource": brief.get("blockedFromSource", []),
                "blockedEntities": [
                    "위석부부한의원",
                    "위석부부 한의원",
                    "위석 원장",
                    "박경화",
                    "송정동",
                    "광산구",
                    "광주송정역",
                ],
                "generalInformationOnly": True,
                "sourceClinicFactsBlocked": True,
                "sourceSentencesBlocked": True,
                "reviewStatus": "general-information-only-reviewed",
            }
        )
    return result


def user_sources(library: dict[str, Any]) -> list[dict[str, Any]]:
    raw = library.get("sources", []) if isinstance(library, dict) else []
    required_flags = (
        "generalInformationOnly",
        "sourceClinicFactsBlocked",
        "sourceSentencesBlocked",
        "sourceCasesAndResultsBlocked",
    )
    return (
        [
            item
            for item in raw
            if isinstance(item, dict) and all(item.get(flag) is True for flag in required_flags)
        ]
        if isinstance(raw, list)
        else []
    )


def source_allowed(source: dict[str, Any], raw_query: str) -> bool:
    source_id = str(source.get("id", ""))
    required = source.get("requiredContextTerms", SOURCE_REQUIRED_CONTEXT.get(source_id, ()))
    if isinstance(required, list):
        required_terms: tuple[str, ...] | list[str] = required
    else:
        required_terms = required if isinstance(required, tuple) else ()
    return not required_terms or has_context(raw_query, required_terms)


def atom_allowed(source: dict[str, Any], atom: dict[str, Any], raw_query: str) -> bool:
    atom_id = str(atom.get("id", ""))
    required = atom.get("requiredContextTerms", ATOM_REQUIRED_CONTEXT.get(atom_id, ()))
    if isinstance(required, list):
        required_terms: tuple[str, ...] | list[str] = required
    else:
        required_terms = required if isinstance(required, tuple) else ()
    return not required_terms or has_context(raw_query, required_terms)


def atom_text(atom: dict[str, Any]) -> str:
    values: list[str] = [str(atom.get("role", ""))]
    for key in ("observables", "meaning"):
        raw = atom.get(key, [])
        if isinstance(raw, list):
            values.extend(str(value) for value in raw)
    return " ".join(values)


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def merge_atoms(candidates: list[dict[str, Any]], *, maximum: int = 12) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (-int(item["score"]), str(item["sourceAtomId"]))):
        candidate_tokens = tokens(
            " ".join(candidate.get("observables", []) + candidate.get("meaning", []))
        )
        match: dict[str, Any] | None = None
        for existing in merged:
            existing_tokens = tokens(
                " ".join(existing.get("observables", []) + existing.get("meaning", []))
            )
            same_role = compact(str(existing.get("role", ""))) == compact(str(candidate.get("role", "")))
            if same_role and jaccard(candidate_tokens, existing_tokens) >= 0.55:
                match = existing
                break
            if jaccard(candidate_tokens, existing_tokens) >= 0.72:
                match = existing
                break
        if match is None:
            if len(merged) >= maximum:
                continue
            merged.append(
                {
                    "id": f"GENERAL-A{len(merged) + 1}",
                    "role": candidate.get("role", "general-information"),
                    "observables": unique_strings(list(candidate.get("observables", []))),
                    "meaning": unique_strings(list(candidate.get("meaning", []))),
                    "sourceIds": [candidate["sourceId"]],
                    "sourceAtomIds": [candidate["sourceAtomId"]],
                    "generalInformationOnly": True,
                    "relevanceScore": int(candidate["score"]),
                }
            )
            continue
        match["observables"] = unique_strings(match["observables"] + list(candidate.get("observables", [])))
        match["meaning"] = unique_strings(match["meaning"] + list(candidate.get("meaning", [])))
        match["sourceIds"] = unique_strings(match["sourceIds"] + [candidate["sourceId"]])
        match["sourceAtomIds"] = unique_strings(match["sourceAtomIds"] + [candidate["sourceAtomId"]])
        match["relevanceScore"] = max(int(match["relevanceScore"]), int(candidate["score"]))
    return merged


def promised_answer_count(title: str) -> int | None:
    values = [int(match.group("count")) for match in NUMBERED_PROMISE.finditer(normalize(title))]
    if not values:
        return None
    return values[0] if len(set(values)) == 1 else -1


def korean_web_queries(topic: str, title: str, keyword: str) -> list[str]:
    title_angle = normalize(title)
    if keyword:
        title_angle = title_angle.replace(normalize(keyword), " ")
    title_angle = NUMBERED_PROMISE.sub(" ", title_angle)
    angle_words = [
        word
        for word in TOKEN_RE.findall(title_angle)
        if word not in STOP_TERMS and word not in tokens(topic)
    ][:7]
    candidates = [
        " ".join([topic, *angle_words]).strip(),
        f"{topic} 원인 증상 생활관리".strip(),
        f"{topic} 치료 주의 검사 필요한 경우".strip(),
        f"{topic} 국가건강정보포털".strip(),
    ]
    result = unique_strings(candidates)
    return [query for query in result if HANGUL.search(query)]


def select_information(
    topic: str,
    title: str,
    keyword: str,
    briefs: dict[str, Any],
    profiles: dict[str, Any],
    user_library: dict[str, Any],
    *,
    answer_count: int | None = None,
) -> dict[str, Any]:
    topic = normalize(topic)
    title = normalize(title)
    keyword = normalize(keyword)
    raw_query = f"{topic} {title.replace(keyword, ' ') if keyword else title}".strip()
    terms = query_terms(topic, title, keyword)
    anchors = topical_terms(topic)
    sources = built_in_sources(briefs, profiles) + user_sources(user_library)
    matched_sources: list[dict[str, Any]] = []
    atom_candidates: list[dict[str, Any]] = []

    for source in sources:
        if not source_allowed(source, raw_query):
            continue
        anchor_haystack = " ".join(
            [
                str(source.get("sourceTitle", "")),
                str(source.get("topic", "")),
                *[str(value) for value in source.get("topicTags", []) if isinstance(value, str)],
            ]
        )
        source_haystack = " ".join(
            [
                anchor_haystack,
                *[str(value) for value in source.get("readerConcerns", []) if isinstance(value, str)],
            ]
        )
        # A source must name the requested subject in its title/topic/tags. A stray
        # word inside one atom (for example "수면" in a weight-management article)
        # is not enough to treat the whole source as insomnia information.
        topical_score = text_score(anchor_haystack, anchors)
        if topical_score <= 0:
            continue
        source_score = text_score(source_haystack, terms)
        local_candidates: list[dict[str, Any]] = []
        for atom in source_atoms(source):
            if not atom_allowed(source, atom, raw_query):
                continue
            atom_score = text_score(atom_text(atom), terms)
            local_candidates.append(
                {
                    "sourceId": str(source.get("id", "")),
                    "sourceAtomId": str(atom.get("id", "")),
                    "role": str(atom.get("role", "general-information")),
                    "observables": [str(value) for value in atom.get("observables", [])],
                    "meaning": [str(value) for value in atom.get("meaning", [])],
                    "score": topical_score * 10 + source_score + atom_score,
                }
            )
        if not local_candidates:
            continue
        matched_sources.append(
            {
                "id": str(source.get("id", "")),
                "sourceTitle": str(source.get("sourceTitle", "")),
                "sourceUrl": str(source.get("sourceUrl", "")),
                "sourceType": str(source.get("sourceType", "user-reference")),
                "title": str(source.get("sourceTitle", "")),
                "url": str(source.get("sourceUrl", "")),
                "kind": "stored-reference",
                "publisher": str(source.get("sourceClinicName", source.get("sourcePublisher", "저장 레퍼런스"))),
                "retrievedBy": "stored-library",
                "score": max(int(item["score"]) for item in local_candidates),
                "matchedAtomIds": [item["sourceAtomId"] for item in local_candidates],
                "blockedEntities": unique_strings(
                    [str(value) for value in source.get("blockedEntities", [])]
                ),
                "sourceClinicFactsBlocked": True,
                "sourceSentencesBlocked": True,
                "sourceCasesResultsProgramsMediaBlocked": True,
                "sourceSentenceCopyBlocked": True,
                "generalInformationOnly": True,
            }
        )
        atom_candidates.extend(local_candidates)

    matched_sources.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    merged = merge_atoms(atom_candidates)
    inferred_count = promised_answer_count(title)
    required_answer_count = answer_count if answer_count is not None else inferred_count
    invalid_count = required_answer_count == -1
    minimum_atoms = max(2, required_answer_count or 0) if not invalid_count else 2
    stored_sufficient = bool(matched_sources) and len(merged) >= minimum_atoms and not invalid_count
    queries = korean_web_queries(topic, title, keyword)
    status = "stored-sufficient" if stored_sufficient else "stored-plus-web-required" if matched_sources else "web-required"
    return {
        "status": status,
        "topic": topic,
        "title": title,
        "mainKeyword": keyword,
        "queryTerms": sorted(terms),
        "topicalAnchorTerms": sorted(anchors),
        "storedSources": matched_sources,
        "mergedInformationAtoms": merged,
        "coverage": {
            "matchedSourceCount": len(matched_sources),
            "mergedAtomCount": len(merged),
            "minimumAtomCount": minimum_atoms,
            "storedInformationSufficient": stored_sufficient,
            "agentTitleCoverageReviewRequired": True,
        },
        "titleContract": {
            "promisedAnswerCount": None if inferred_count in (None, -1) else inferred_count,
            "requestedAnswerCount": answer_count,
            "exactNumberedAnswerCountRequired": required_answer_count not in (None, -1),
            "existingGoldhandArticleStructureMustRemainUnchanged": True,
        },
        "webSearch": {
            "required": not stored_sufficient,
            "trigger": "stored atoms do not fully answer the confirmed title",
            "engine": "naver",
            "language": "ko-KR",
            "queries": queries,
            "execution": "background-http-or-system-web-no-gui",
            "requiresBrowser": False,
            "requiresLogin": False,
            "minimumIndependentSources": 2,
            "officialKoreanMedicalSourceRequiredForTreatmentOrSafety": True,
            "seoKeywordExcludedFromSearchQuery": True,
        },
        "sourcePolicy": {
            "multipleRelevantReferencesAllowed": True,
            "semanticDeduplicationRequired": True,
            "generalInformationOnly": True,
            "sourceClinicFactsBlocked": True,
            "sourceCasesResultsProgramsMediaBlocked": True,
            "goldhandClinicInformationAuthority": "references/clinic-facts.md",
            "sourceSentenceCopyBlocked": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--keyword", default="")
    parser.add_argument("--answer-count", type=int)
    parser.add_argument("--briefs", type=Path, default=DEFAULT_BRIEFS)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--user-library", type=Path, default=DEFAULT_USER_LIBRARY)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        briefs = json.loads(args.briefs.read_text(encoding="utf-8"))
        profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
        user_library = json.loads(args.user_library.read_text(encoding="utf-8"))
        result = select_information(
            args.topic,
            args.title,
            args.keyword,
            briefs,
            profiles,
            user_library,
            answer_count=args.answer_count,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"일반 정보 선택 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"저장 레퍼런스: {result['coverage']['matchedSourceCount']}편")
        print(f"중복 제거 정보 원자: {result['coverage']['mergedAtomCount']}개")
        print(f"네이버 보충 검색: {'필요' if result['webSearch']['required'] else '불필요'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
