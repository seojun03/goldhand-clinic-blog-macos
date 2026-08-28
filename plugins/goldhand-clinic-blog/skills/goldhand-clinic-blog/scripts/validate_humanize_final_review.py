#!/usr/bin/env python3
"""Validate a Goldhand humanize-korean final-pass receipt."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = SKILL_DIR / "assets" / "humanize-korean-final-review-contract.json"


def nonempty_paragraphs(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    return [item.strip() for item in value]


def computed_change_rate(before_body: list[str], final_body: list[str]) -> float:
    before = "\n".join(before_body)
    after = "\n".join(final_body)
    if not before and not after:
        return 0.0
    similarity = difflib.SequenceMatcher(a=before, b=after, autojunk=False).ratio()
    return round((1.0 - similarity) * 100.0, 2)


def validate_case(case: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def add(code: str, detail: str) -> None:
        issues.append({"severity": "error", "code": code, "detail": detail})

    final_body = nonempty_paragraphs(case.get("finalBody"))
    if final_body is None:
        add("final-body-invalid", "finalBody에는 비어 있지 않은 최종 문단 배열이 필요합니다.")
        final_body = []

    if "writingVoiceReview" in case:
        add(
            "humanize-writing-voice-contamination",
            "humanize-korean 비교안에는 writingVoiceReview를 함께 넣거나 writing-voice를 호출하면 안 됩니다.",
        )

    title = str(case.get("title", "")).strip()
    review = case.get("humanizeKoreanReview")
    if not isinstance(review, dict):
        add("humanize-review-missing", "humanizeKoreanReview 최종 윤문 기록이 필요합니다.")
        return {
            "status": "fail",
            "metrics": {"changedParagraphs": 0, "changeRatePercent": 0.0, "errors": len(issues)},
            "issues": issues,
        }

    expected_id = str(contract.get("id", ""))
    expected_skill = str(contract.get("sourceSkill", ""))
    expected_stage = str(contract.get("stage", ""))
    if review.get("contractId") != expected_id:
        add("humanize-contract-id", f"contractId는 {expected_id}여야 합니다.")
    if review.get("skillName") != expected_skill:
        add("humanize-skill-name", f"skillName은 {expected_skill}여야 합니다.")
    if review.get("stage") != expected_stage:
        add("humanize-stage", f"최종 윤문 단계는 {expected_stage}여야 합니다.")
    if review.get("finalStatus") != "pass":
        add("humanize-status", "finalStatus가 pass가 아닙니다.")
    if str(review.get("beforeTitle", "")).strip() != title:
        add("humanize-title-changed", "humanize-korean 최종 윤문에서 확정 제목을 바꾸면 안 됩니다.")

    before_body = nonempty_paragraphs(review.get("beforeBody"))
    if before_body is None:
        add("humanize-before-body-invalid", "beforeBody에는 윤문 전 전체 문단 배열이 필요합니다.")
        before_body = []
    if len(before_body) != len(final_body):
        add(
            "humanize-paragraph-structure-changed",
            f"최종 윤문 전후 문단 수가 다릅니다: {len(before_body)} -> {len(final_body)}",
        )

    checks = review.get("selfChecks")
    if not isinstance(checks, dict):
        add("humanize-self-checks-missing", "humanize-korean 자체검증 6항 기록이 필요합니다.")
        checks = {}
    for key in contract.get("requiredSelfChecks", []):
        if checks.get(key) is not True:
            add("humanize-self-check-failed", f"자체검증 항목 {key}가 통과하지 못했습니다.")

    frozen = review.get("frozenMaterial")
    if not isinstance(frozen, dict):
        add("humanize-frozen-material-missing", "내용·구조 동결 확인값이 없습니다.")
        frozen = {}
    for key in contract.get("requiredFrozenMaterialChecks", []):
        if frozen.get(key) is not True:
            add("humanize-frozen-material-failed", f"동결 항목 {key}가 보존되지 않았습니다.")

    try:
        reported_rate = float(review.get("changeRatePercent"))
    except (TypeError, ValueError):
        reported_rate = -1.0
        add("humanize-change-rate-invalid", "changeRatePercent는 숫자여야 합니다.")
    calculated_rate = computed_change_rate(before_body, final_body)
    if reported_rate >= 0 and abs(reported_rate - calculated_rate) > 0.25:
        add(
            "humanize-change-rate-mismatch",
            f"보고 변경률 {reported_rate:.2f}%와 계산 변경률 {calculated_rate:.2f}%가 다릅니다.",
        )
    max_rate = float(contract.get("maxChangeRatePercent", 30))
    if calculated_rate > max_rate:
        add("humanize-change-rate-over-limit", f"변경률 {calculated_rate:.2f}%가 허용치 {max_rate:.0f}%를 넘었습니다.")

    grade = str(review.get("grade", "")).strip().upper()
    if grade not in set(contract.get("passingGrades", [])):
        add("humanize-grade-not-passing", f"금손 완료본은 A 또는 B 등급이어야 합니다. 현재 {grade or '없음'}입니다.")
    s1_remaining = review.get("s1Remaining")
    s2_remaining = review.get("s2Remaining")
    if not isinstance(s1_remaining, int) or s1_remaining != 0:
        add("humanize-s1-remaining", "잔존 S1 패턴은 0건이어야 합니다.")
    if not isinstance(s2_remaining, int) or s2_remaining < 0 or s2_remaining > 4:
        add("humanize-s2-over-limit", "잔존 S2 패턴은 0~4건이어야 합니다.")
    if grade == "A" and not (10 <= calculated_rate <= 25 and isinstance(s2_remaining, int) and s2_remaining <= 2):
        add("humanize-grade-a-mismatch", "A 등급은 변경률 10~25%, S1 0건, S2 2건 이하를 충족해야 합니다.")

    changed_indexes = {
        index
        for index, (before, after) in enumerate(zip(before_body, final_body), start=1)
        if before != after
    }
    revisions = review.get("revisions")
    if not isinstance(revisions, list):
        add("humanize-revisions-invalid", "revisions는 배열이어야 합니다.")
        revisions = []
    revision_indexes: set[int] = set()
    rule_pattern = re.compile(str(contract.get("ruleIdPattern", r"^[A-J]-[0-9]+$")))
    for revision in revisions:
        if not isinstance(revision, dict):
            add("humanize-revision-invalid", "각 revision은 객체여야 합니다.")
            continue
        paragraph_index = revision.get("paragraphIndex")
        if not isinstance(paragraph_index, int) or paragraph_index < 1 or paragraph_index > len(final_body):
            add("humanize-revision-index", f"유효하지 않은 paragraphIndex입니다: {paragraph_index}")
            continue
        if paragraph_index in revision_indexes:
            add("humanize-revision-duplicate", f"{paragraph_index}번 문단 수정 기록이 중복입니다.")
            continue
        revision_indexes.add(paragraph_index)
        expected_before = before_body[paragraph_index - 1] if paragraph_index <= len(before_body) else ""
        expected_after = final_body[paragraph_index - 1]
        if str(revision.get("before", "")).strip() != expected_before:
            add("humanize-revision-before-mismatch", f"{paragraph_index}번 문단의 수정 전 문장이 다릅니다.")
        if str(revision.get("after", "")).strip() != expected_after:
            add("humanize-revision-after-mismatch", f"{paragraph_index}번 문단의 수정 후 문장이 최종 원고와 다릅니다.")
        rule_ids = revision.get("ruleIds")
        if not isinstance(rule_ids, list) or not rule_ids or any(
            not isinstance(rule_id, str) or rule_pattern.fullmatch(rule_id) is None for rule_id in rule_ids
        ):
            add("humanize-revision-rule-ids", f"{paragraph_index}번 수정에는 유효한 quick-rules ID가 필요합니다.")

    if revision_indexes != changed_indexes:
        add(
            "humanize-unaccounted-change",
            f"실제 변경 문단 {sorted(changed_indexes)}과 수정 기록 {sorted(revision_indexes)}이 다릅니다.",
        )

    decision = review.get("decision")
    allowed_decisions = set(contract.get("allowedDecisions", []))
    if decision not in allowed_decisions:
        add("humanize-decision-invalid", f"decision은 {sorted(allowed_decisions)} 중 하나여야 합니다.")
    elif changed_indexes and decision != "revised":
        add("humanize-decision-mismatch", "문장을 수정했다면 decision은 revised여야 합니다.")
    elif not changed_indexes and decision != "no-change-needed":
        add("humanize-forced-edit", "수정할 문장이 없다면 no-change-needed로 기록합니다.")

    return {
        "status": "fail" if issues else "pass",
        "metrics": {
            "changedParagraphs": len(changed_indexes),
            "changeRatePercent": calculated_rate,
            "grade": grade,
            "errors": len(issues),
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"humanize-korean 최종 검수 입력을 읽지 못했습니다: {exc}", file=sys.stderr)
        return 2

    raw_cases = payload.get("cases") if isinstance(payload, dict) else None
    cases = raw_cases if isinstance(raw_cases, list) else [payload]
    results = [validate_case(case, contract) for case in cases if isinstance(case, dict)]
    if len(results) != len(cases):
        results.append(
            {
                "status": "fail",
                "metrics": {"changedParagraphs": 0, "changeRatePercent": 0.0, "errors": 1},
                "issues": [{"severity": "error", "code": "case-invalid", "detail": "각 case는 객체여야 합니다."}],
            }
        )
    status = "fail" if any(result["status"] == "fail" for result in results) else "pass"
    output = {"status": status, "cases": results}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"status: {status}")
        for index, result in enumerate(results, start=1):
            for issue in result["issues"]:
                print(f"[ERROR] [{index}] {issue['code']}: {issue['detail']}")
    return 1 if status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
