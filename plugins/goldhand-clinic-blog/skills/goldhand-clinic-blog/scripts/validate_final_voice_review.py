#!/usr/bin/env python3
"""Validate the final writing-voice rehear record without judging prose by quota."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = SKILL_DIR / "assets" / "writing-voice-final-review-contract.json"


def compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).lower()


def nonempty_paragraphs(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    return [item.strip() for item in value]


def validate_case(case: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def add(code: str, detail: str) -> None:
        issues.append({"severity": "error", "code": code, "detail": detail})

    final_body = nonempty_paragraphs(case.get("finalBody"))
    if final_body is None:
        add("final-body-invalid", "finalBody에는 비어 있지 않은 최종 문단 배열이 필요합니다.")
        final_body = []

    title = str(case.get("title", "")).strip()
    review = case.get("writingVoiceReview")
    if not isinstance(review, dict):
        add("writing-voice-review-missing", "writingVoiceReview 최종 재청취 기록이 필요합니다.")
        return {
            "status": "fail",
            "metrics": {"changedParagraphs": 0, "revisions": 0, "errors": len(issues)},
            "issues": issues,
        }

    expected_id = str(contract.get("id", ""))
    expected_skill = str(contract.get("sourceSkill", ""))
    expected_stage = str(contract.get("stage", ""))
    if review.get("contractId") != expected_id:
        add("writing-voice-contract-id", f"contractId는 {expected_id}여야 합니다.")
    if review.get("skillName") != expected_skill:
        add("writing-voice-skill-name", f"skillName은 {expected_skill}여야 합니다.")
    if review.get("stage") != expected_stage:
        add("writing-voice-stage", f"최종 재청취 단계는 {expected_stage}여야 합니다.")
    if review.get("finalStatus") != "pass":
        add("writing-voice-status", "finalStatus가 pass가 아닙니다.")

    if str(review.get("beforeTitle", "")).strip() != title:
        add("writing-voice-title-changed", "최종 문장 검수에서 확정 제목을 바꾸면 안 됩니다.")

    checks = review.get("reviewChecks")
    if not isinstance(checks, dict):
        add("writing-voice-review-checks-missing", "전체 재청취 확인값이 없습니다.")
        checks = {}
    for key in contract.get("requiredReviewChecks", []):
        if checks.get(key) is not True:
            add("writing-voice-review-check-failed", f"최종 재청취 항목 {key}가 통과하지 못했습니다.")

    frozen = review.get("frozenMaterial")
    if not isinstance(frozen, dict):
        add("writing-voice-frozen-material-missing", "내용·구조 동결 확인값이 없습니다.")
        frozen = {}
    for key in contract.get("requiredFrozenMaterialChecks", []):
        if frozen.get(key) is not True:
            add("writing-voice-frozen-material-failed", f"동결 항목 {key}가 보존되지 않았습니다.")

    before_body = nonempty_paragraphs(review.get("beforeBody"))
    if before_body is None:
        add("writing-voice-before-body-invalid", "beforeBody에는 검수 전 전체 문단 배열이 필요합니다.")
        before_body = []
    if len(before_body) != len(final_body):
        add(
            "writing-voice-paragraph-structure-changed",
            f"최종 문장 검수 전후 문단 수가 다릅니다: {len(before_body)} -> {len(final_body)}",
        )

    changed_indexes = {
        index
        for index, (before, after) in enumerate(zip(before_body, final_body), start=1)
        if before != after
    }
    raw_revisions = review.get("revisions")
    if not isinstance(raw_revisions, list):
        add("writing-voice-revisions-invalid", "revisions는 배열이어야 합니다.")
        raw_revisions = []

    revision_indexes: set[int] = set()
    revision_contract = contract.get("revisionContract", {})
    signals = [str(value) for value in revision_contract.get("positiveAccountSignals", [])]
    generic_accounts = [compact(value) for value in revision_contract.get("genericAccountsForbidden", [])]
    for revision in raw_revisions:
        if not isinstance(revision, dict):
            add("writing-voice-revision-invalid", "각 revision은 객체여야 합니다.")
            continue
        paragraph_index = revision.get("paragraphIndex")
        if not isinstance(paragraph_index, int) or paragraph_index < 1 or paragraph_index > len(final_body):
            add("writing-voice-revision-index", f"유효하지 않은 paragraphIndex입니다: {paragraph_index}")
            continue
        if paragraph_index in revision_indexes:
            add("writing-voice-revision-duplicate", f"{paragraph_index}번 문단 수정 기록이 중복입니다.")
            continue
        revision_indexes.add(paragraph_index)
        expected_before = before_body[paragraph_index - 1] if paragraph_index <= len(before_body) else ""
        expected_after = final_body[paragraph_index - 1]
        if str(revision.get("before", "")).strip() != expected_before:
            add("writing-voice-revision-before-mismatch", f"{paragraph_index}번 문단의 수정 전 문장이 다릅니다.")
        if str(revision.get("after", "")).strip() != expected_after:
            add("writing-voice-revision-after-mismatch", f"{paragraph_index}번 문단의 수정 후 문장이 최종 원고와 다릅니다.")
        if expected_before == expected_after:
            add("writing-voice-unnecessary-revision", f"{paragraph_index}번 문단은 바뀌지 않았는데 수정 기록이 있습니다.")
        expressive_job = str(revision.get("expressiveJob", "")).strip()
        compact_job = compact(expressive_job)
        has_signal = any(signal in expressive_job for signal in signals)
        generic_only = any(value and value in compact_job for value in generic_accounts) and not has_signal
        if len(compact_job) < 8 or not has_signal or generic_only:
            add(
                "writing-voice-expressive-job-missing",
                f"{paragraph_index}번 수정에는 '더 자연스럽게'가 아니라 표현이 수행할 구체적인 일을 적어야 합니다.",
            )

    if revision_indexes != changed_indexes:
        add(
            "writing-voice-unaccounted-change",
            f"실제 변경 문단 {sorted(changed_indexes)}과 수정 기록 {sorted(revision_indexes)}이 다릅니다.",
        )

    decision = review.get("decision")
    allowed_decisions = set(contract.get("allowedDecisions", []))
    if decision not in allowed_decisions:
        add("writing-voice-decision-invalid", f"decision은 {sorted(allowed_decisions)} 중 하나여야 합니다.")
    elif changed_indexes and decision != "revised":
        add("writing-voice-decision-mismatch", "문장을 수정했다면 decision은 revised여야 합니다.")
    elif not changed_indexes and decision != "no-change-needed":
        add("writing-voice-forced-edit", "수정할 문장이 없다면 억지로 고치지 말고 no-change-needed로 기록합니다.")

    if any("–" in paragraph for paragraph in final_body):
        add("writing-voice-en-dash", "최종 산문에서 en dash는 쓰지 않습니다.")

    return {
        "status": "fail" if issues else "pass",
        "metrics": {
            "changedParagraphs": len(changed_indexes),
            "revisions": len(raw_revisions),
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
        print(f"writing-voice 최종 검수 입력을 읽지 못했습니다: {exc}", file=sys.stderr)
        return 2

    raw_cases = payload.get("cases") if isinstance(payload, dict) else None
    cases = raw_cases if isinstance(raw_cases, list) else [payload]
    results = [validate_case(case, contract) for case in cases if isinstance(case, dict)]
    if len(results) != len(cases):
        results.append(
            {
                "status": "fail",
                "metrics": {"changedParagraphs": 0, "revisions": 0, "errors": 1},
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
