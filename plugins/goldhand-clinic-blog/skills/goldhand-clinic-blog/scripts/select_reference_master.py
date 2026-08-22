#!/usr/bin/env python3
"""Select exactly one same-type reference master for a Goldhand article."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = SKILL_DIR / "assets" / "reference-master-profiles.json"
FAMILY_ID = "two-or-three-reader-concern-hooks-solution-preview-info"
ALLOWED_TYPES = ("정보전달형",)
DEFAULTS = {"정보전달형": "INFO01"}

INTENT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("질문 2가지", "언제 검사", "다른 기관", "안전 기준", "응급"), ("INFO03",)),
    (("효과 보는 사람", "못 보는 사람", "반응이 다른", "공통점"), ("INFO04",)),
    (("건강보험", "보험 적용", "적용 기준", "비용", "횟수"), ("INFO05",)),
    (("회복 원칙", "움직임 분석", "구조적 원인", "통증 반복"), ("INFO06",)),
    (("치료방법", "치료 방법", "단계별", "핵심"), ("INFO07",)),
    (("시기 2가지", "시작 시기", "언제 시작", "예방과 회복"), ("INFO08",)),
    (("주의사항", "중단 이후", "유지", "요요"), ("INFO09",)),
    (("일반 치료의 한계", "치료 원리", "오래가는", "증상 원인"), ("INFO10",)),
    (("극복 방법", "몸과 마음", "오래된 불편", "두 갈래"), ("INFO11",)),
    (("성공 조건", "같은 노력", "다른 결과", "몸의 변화"), ("INFO12",)),
    (("치료받아도", "받아도 소용", "생활습관", "직장인"), ("INFO01",)),
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[^0-9a-z가-힣]+", " ", value).strip()


def tokens(value: str) -> set[str]:
    return {token for token in normalize(value).split() if len(token) >= 2}


def score_profile(profile_id: str, profile: dict[str, object], query: str) -> tuple[int, list[str]]:
    query_normalized = normalize(query)
    query_tokens = tokens(query)
    score = 0
    matches: list[str] = []
    for raw_tag in profile.get("selectionTags", []):
        tag = str(raw_tag)
        normalized_tag = normalize(tag)
        tag_tokens = tokens(tag)
        if normalized_tag and normalized_tag in query_normalized:
            score += 18
            matches.append(tag)
        else:
            overlap = query_tokens & tag_tokens
            if overlap:
                score += 5 * len(overlap)
                matches.append(tag)
    best_for = str(profile.get("bestFor", ""))
    best_overlap = query_tokens & tokens(best_for)
    score += 2 * len(best_overlap)
    for phrases, profile_ids in INTENT_RULES:
        normalized_phrases = tuple(normalize(phrase) for phrase in phrases)
        matches_rule = [phrase for phrase in normalized_phrases if phrase and phrase in query_normalized]
        if matches_rule and profile_id in profile_ids:
            score += 30 + 5 * (len(matches_rule) - 1)
            matches.extend(matches_rule)
    if re.search(r"2\s*가지|두\s*가지", query_normalized) and profile_id in {
        "INFO01",
        "INFO03",
        "INFO05",
        "INFO06",
        "INFO08",
        "INFO09",
        "INFO11",
    }:
        score += 8
    if profile_id == DEFAULTS.get(str(profile.get("type"))):
        score += 1
    return score, sorted(set(matches))


def select(
    profiles: dict[str, dict[str, object]],
    article_type: str,
    title: str,
    topic: str,
    *,
    allow_manual: bool = False,
) -> dict[str, object]:
    if article_type != "정보전달형":
        raise ValueError("이 스킬은 독자 고민 2~3개·해결 방향 예고형 정보전달 글만 작성합니다.")
    query = " ".join(value for value in (title, topic) if value).strip()
    candidates: list[dict[str, object]] = []
    for profile_id, profile in profiles.items():
        if profile.get("type") != article_type:
            continue
        if profile.get("referenceFamilyId") != FAMILY_ID:
            continue
        if profile.get("autoEligible") is not True and not allow_manual:
            continue
        score, matches = score_profile(profile_id, profile, query)
        candidates.append(
            {
                "id": profile_id,
                "score": score,
                "matchedTags": matches,
                "sourceTitle": profile.get("sourceTitle"),
                "sourceUrl": profile.get("sourceUrl"),
                "bestFor": profile.get("bestFor"),
                "autoEligible": profile.get("autoEligible") is True,
            }
        )
    if not candidates:
        raise ValueError(f"선택 가능한 {article_type} 레퍼런스가 없습니다.")
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    selected = candidates[0]
    return {
        "status": "selected",
        "type": article_type,
        "title": title,
        "topic": topic,
        "selected": selected,
        "alternatives": candidates[1:3],
        "policy": "selected.id 한 편은 글쓰기 흐름에만 사용하고 꾸밈은 네이버 순정 goldhand-naver-native-v4로 고정",
        "referenceFamilyId": FAMILY_ID,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, choices=ALLOWED_TYPES)
    parser.add_argument("--title", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--allow-manual", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.profiles.read_text(encoding="utf-8"))
        result = select(
            data["profiles"],
            args.type,
            args.title,
            args.topic,
            allow_manual=args.allow_manual,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"레퍼런스 선택 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        chosen = result["selected"]
        print(f"selected: {chosen['id']}")
        print(f"source: {chosen['sourceTitle']}")
        print(f"url: {chosen['sourceUrl']}")
        print(f"matched: {', '.join(chosen['matchedTags']) or '기본 적합도'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
