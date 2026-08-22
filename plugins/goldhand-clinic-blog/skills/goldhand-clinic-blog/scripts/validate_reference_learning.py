#!/usr/bin/env python3
"""Validate the portable editorial-reasoning profiles used before drafting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"
DEFAULT_FAMILY = SKILL_DIR / "assets" / "two-reader-hooks-reference-family.json"
REQUIRED_LESSONS = {
    "specific-number-low-friction-topic-payoff",
    "authority-is-an-evidence-slot-not-a-copy-slot",
    "reader-question-as-self-identification",
    "topic-specific-recap-trust-emotion",
    "observable-spoken-korean",
}
REQUIRED_NUMERIC_CHAIN = [
    "specific-number",
    "perceived-concreteness",
    "low-effort",
    "attention",
    "topic-specific-payoff",
]
SOURCE_SENTENCE_FRAGMENTS = (
    "3분만집중해서읽어보세요",
    "무릎통증으로부터벗어나는실마리를찾으실수있을겁니다",
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"파일을 찾을 수 없습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 형식이 올바르지 않습니다: {path}:{exc.lineno}:{exc.colno}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"최상위 값은 객체여야 합니다: {path}")
    return value


def text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def require_text(value: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    result = text(value.get(key))
    if not result:
        errors.append(f"비어 있지 않은 문자열이 필요합니다: {path}.{key}")
    return result


def validate_intelligence(data: dict[str, Any], family: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion은 1이어야 합니다.")
    if data.get("learningMode") != "curated-portable-editorial-reasoning":
        errors.append("learningMode는 curated-portable-editorial-reasoning이어야 합니다.")
    if data.get("modelTrainingClaim") is not False:
        errors.append("이 자산은 모델 파인튜닝을 주장할 수 없습니다.")

    family_ids = string_list(family.get("allowedMasterIds"))
    declared_ids = string_list(data.get("allowedMasterIds"))
    if set(declared_ids) != set(family_ids) or len(declared_ids) != len(set(declared_ids)):
        errors.append("allowedMasterIds는 검토 완료 11편을 중복 없이 포함해야 합니다.")

    contract = data.get("globalDecisionContract")
    if not isinstance(contract, dict):
        errors.append("globalDecisionContract 객체가 필요합니다.")
        contract = {}
    for key in (
        "principleNotPhrase",
        "oneReferenceOneReadingExperience",
        "goldhandAdaptation",
        "goldhandVoiceRole",
    ):
        require_text(contract, key, "$.globalDecisionContract", errors)
    for key in ("analysisBeforeDraft", "sourceSentenceImitationBlocked", "sourceFactReplacementRequired"):
        if contract.get(key) is not True:
            errors.append(f"globalDecisionContract.{key}=true가 필요합니다.")
    if contract.get("maximumConsecutiveSourceWords") != 6:
        errors.append("maximumConsecutiveSourceWords는 6이어야 합니다.")
    if len(string_list(contract.get("decisionRecordFields"))) < 8:
        errors.append("집필 전 판단 기록 필드는 8개 이상이어야 합니다.")

    lessons = data.get("approvedLessons")
    if not isinstance(lessons, list):
        errors.append("approvedLessons 배열이 필요합니다.")
        lessons = []
    lesson_ids: list[str] = []
    for index, lesson in enumerate(lessons, start=1):
        path = f"$.approvedLessons[{index}]"
        if not isinstance(lesson, dict):
            errors.append(f"객체가 필요합니다: {path}")
            continue
        lesson_id = require_text(lesson, "id", path, errors)
        if lesson_id:
            lesson_ids.append(lesson_id)
        if lesson.get("status") != "user-approved":
            errors.append(f"승인된 피드백만 공용 학습 자료에 넣을 수 있습니다: {path}")
        if len(string_list(lesson.get("psychologyChain"))) < 3:
            errors.append(f"심리 작동 순서가 3단계 이상 필요합니다: {path}.psychologyChain")
        require_text(lesson, "transferRule", path, errors)
    if set(lesson_ids) != REQUIRED_LESSONS or len(lesson_ids) != len(set(lesson_ids)):
        errors.append("approvedLessons는 등록된 사용자 승인 교훈 5개를 중복 없이 포함해야 합니다.")

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("profiles 객체가 필요합니다.")
        profiles = {}
    if set(profiles) != set(family_ids) or len(profiles) != len(family_ids):
        errors.append("profiles는 검토 완료 11편과 정확히 대응해야 합니다.")

    seen_urls: set[str] = set()
    for master_id in family_ids:
        profile = profiles.get(master_id)
        path = f"$.profiles.{master_id}"
        if not isinstance(profile, dict):
            errors.append(f"프로필 객체가 필요합니다: {master_id}")
            continue
        require_text(profile, "sourceTitle", path, errors)
        source_url = require_text(profile, "sourceUrl", path, errors)
        require_text(profile, "readerState", path, errors)
        if source_url in seen_urls:
            errors.append(f"sourceUrl이 중복됐습니다: {source_url}")
        seen_urls.add(source_url)
        if not source_url.startswith("https://blog.naver.com/wi-parkclinic/"):
            errors.append(f"등록된 Wipark 원문 URL이 아닙니다: {master_id}")

        title_mechanism = profile.get("titleMechanism")
        if not isinstance(title_mechanism, dict):
            errors.append(f"titleMechanism 객체가 필요합니다: {master_id}")
            title_mechanism = {}
        title_primary = require_text(title_mechanism, "primaryId", f"{path}.titleMechanism", errors)
        title_allowed = string_list(title_mechanism.get("allowedIds"))
        if title_primary not in title_allowed or not title_allowed:
            errors.append(f"제목 primaryId는 allowedIds에 포함돼야 합니다: {master_id}")
        require_text(title_mechanism, "readerPsychology", f"{path}.titleMechanism", errors)
        require_text(title_mechanism, "goldhandAdaptation", f"{path}.titleMechanism", errors)

        opening = profile.get("openingMechanism")
        if not isinstance(opening, dict):
            errors.append(f"openingMechanism 객체가 필요합니다: {master_id}")
            opening = {}
        opening_primary = require_text(opening, "primaryDeviceId", f"{path}.openingMechanism", errors)
        opening_allowed = string_list(opening.get("allowedDeviceIds"))
        if opening_primary not in opening_allowed or not opening_allowed:
            errors.append(f"도입 primaryDeviceId는 allowedDeviceIds에 포함돼야 합니다: {master_id}")
        for key in ("attentionLogic", "topicPayoff", "whyItWorks"):
            require_text(opening, key, f"{path}.openingMechanism", errors)

        beats = profile.get("flowBeats")
        if not isinstance(beats, list) or len(beats) < 4:
            errors.append(f"flowBeats는 4개 이상이어야 합니다: {master_id}")
            beats = []
        beat_ids: list[str] = []
        for index, beat in enumerate(beats, start=1):
            beat_path = f"{path}.flowBeats[{index}]"
            if not isinstance(beat, dict):
                errors.append(f"객체가 필요합니다: {beat_path}")
                continue
            beat_id = require_text(beat, "id", beat_path, errors)
            if beat_id:
                beat_ids.append(beat_id)
            require_text(beat, "purpose", beat_path, errors)
            require_text(beat, "transition", beat_path, errors)
        if len(beat_ids) != len(set(beat_ids)):
            errors.append(f"flowBeats ID가 중복됐습니다: {master_id}")

        micro = profile.get("microExpressionPatterns")
        if not isinstance(micro, list) or len(micro) < 3:
            errors.append(f"microExpressionPatterns는 3개 이상이어야 합니다: {master_id}")
            micro = []
        for index, pattern in enumerate(micro, start=1):
            micro_path = f"{path}.microExpressionPatterns[{index}]"
            if not isinstance(pattern, dict):
                errors.append(f"객체가 필요합니다: {micro_path}")
                continue
            for key in ("function", "shape", "adaptationRule"):
                require_text(pattern, key, micro_path, errors)

        trust = profile.get("trustMechanism")
        if not isinstance(trust, dict):
            errors.append(f"trustMechanism 객체가 필요합니다: {master_id}")
            trust = {}
        if not string_list(trust.get("sourceFactSlots")):
            errors.append(f"sourceFactSlots가 비었습니다: {master_id}")
        require_text(trust, "goldhandRule", f"{path}.trustMechanism", errors)
        if trust.get("omitWhenUnsupported") is not True:
            errors.append(f"omitWhenUnsupported=true가 필요합니다: {master_id}")

        closing = profile.get("closingMechanism")
        if not isinstance(closing, dict):
            errors.append(f"closingMechanism 객체가 필요합니다: {master_id}")
            closing = {}
        closing_primary = require_text(closing, "primaryId", f"{path}.closingMechanism", errors)
        closing_allowed = string_list(closing.get("allowedIds"))
        if closing_primary not in closing_allowed or not closing_allowed:
            errors.append(f"마무리 primaryId는 allowedIds에 포함돼야 합니다: {master_id}")
        for key in ("readerEmotion", "adaptationRule"):
            require_text(closing, key, f"{path}.closingMechanism", errors)

    knee = profiles.get("INFO06", {}) if isinstance(profiles, dict) else {}
    knee_opening = knee.get("openingMechanism", {}) if isinstance(knee, dict) else {}
    if knee_opening.get("numericPrincipleChain") != REQUIRED_NUMERIC_CHAIN:
        errors.append("INFO06에는 구체적 숫자에서 주제 보상으로 이어지는 5단계 심리 원리가 필요합니다.")
    summer = profiles.get("INFO08", {}) if isinstance(profiles, dict) else {}
    summer_opening = summer.get("openingMechanism", {}) if isinstance(summer, dict) else {}
    if summer_opening.get("primaryDeviceId") != "specific-number-low-friction-topic-payoff":
        errors.append("INFO08의 2분 사례는 가변 시간 장치의 근거로 유지해야 합니다.")

    compact_payload = "".join(json.dumps(data, ensure_ascii=False).split())
    for fragment in SOURCE_SENTENCE_FRAGMENTS:
        if fragment in compact_payload:
            errors.append(f"레퍼런스 완성 문장을 학습 자산에 그대로 넣을 수 없습니다: {fragment}")
    if "sourceToneBlocked" in json.dumps(data, ensure_ascii=False):
        errors.append("sourceToneBlocked는 설득 원리 학습을 막으므로 사용할 수 없습니다.")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intelligence", type=Path, default=DEFAULT_INTELLIGENCE)
    parser.add_argument("--family", type=Path, default=DEFAULT_FAMILY)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_json(args.intelligence)
        family = load_json(args.family)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate_intelligence(data, family)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(
            "Reference writing intelligence is valid: "
            f"{len(data['profiles'])} profiles, {len(data['approvedLessons'])} approved lessons."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
