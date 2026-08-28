#!/usr/bin/env python3
"""Validate the five-title choice step for Goldhand Clinic blog automation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = SKILL_DIR / "assets" / "title-recommendation-contract.json"
DEFAULT_EVIDENCE = SKILL_DIR / "references" / "clinic-facts.md"
DEFAULT_WRITING_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"
TITLE_VALIDATOR_PATH = Path(__file__).with_name("validate_title.py")


def load_title_validator():
    spec = importlib.util.spec_from_file_location(
        "goldhand_title_validator_for_recommendations",
        TITLE_VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"제목 검증기를 불러올 수 없습니다: {TITLE_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TITLE_VALIDATOR = load_title_validator()


def add(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    detail: str,
    *,
    candidate_index: int | None = None,
) -> None:
    issue: dict[str, Any] = {"severity": severity, "code": code, "detail": detail}
    if candidate_index is not None:
        issue["candidateIndex"] = candidate_index
    issues.append(issue)


def normalized_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [TITLE_VALIDATOR.normalize(str(item)) for item in value if TITLE_VALIDATOR.normalize(str(item))]


def validate_recommendations(
    payload: dict[str, Any],
    *,
    contract: dict[str, Any],
    evidence: str,
    writing_intelligence: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    candidate_results: list[dict[str, Any]] = []
    keyword = TITLE_VALIDATOR.normalize(str(payload.get("mainKeyword", "")))
    topic = TITLE_VALIDATOR.normalize(str(payload.get("topic", "")))
    workflow_stage = TITLE_VALIDATOR.normalize(
        str(
            payload.get(
                "workflowStage",
                contract.get("defaultWorkflowStage", "master-aware"),
            )
        )
    )
    title_first = workflow_stage == "title-first"
    reference_master_id = TITLE_VALIDATOR.normalize(str(payload.get("referenceMasterId", "")))
    candidates = payload.get("candidates")
    expected_count = int(contract.get("candidateCount", 5))
    career_expression = TITLE_VALIDATOR.normalize(str(contract.get("careerExpression", "11년차")))
    allowed_answer_counts = {
        int(value)
        for value in contract.get("numberedAnswerCounts", [1, 2, 3])
        if isinstance(value, int)
    }
    strong_expressions = normalized_list(contract.get("strongExpressions"))
    weak_expressions = normalized_list(contract.get("weakExpressionsBlocked"))
    reader_stake_values = set(normalized_list(contract.get("readerStakeValues")))
    reader_stake_terms = contract.get("readerStakeTerms", {})

    if not keyword:
        add(issues, "error", "main-keyword-empty", "메인키워드가 비어 있습니다.")
    if not topic:
        add(issues, "error", "topic-empty", "글 주제가 비어 있습니다.")
    if workflow_stage not in {"title-first", "master-aware"}:
        add(
            issues,
            "error",
            "workflow-stage-invalid",
            "workflowStage는 title-first 또는 master-aware여야 합니다.",
        )
    if title_first and reference_master_id:
        add(
            issues,
            "error",
            "title-first-reference-master-preselected",
            "빠른 제목 단계에서는 편집 마스터를 먼저 고르지 않습니다.",
        )
    elif not title_first and not reference_master_id:
        add(issues, "error", "reference-master-id-empty", "제목 장치를 고를 레퍼런스 ID가 비어 있습니다.")
    if not isinstance(candidates, list):
        add(issues, "error", "candidates-not-list", "candidates는 제목 후보 목록이어야 합니다.")
        candidates = []
    if len(candidates) != expected_count:
        add(
            issues,
            "error",
            "candidate-count",
            f"제목 후보가 {len(candidates)}개입니다. 정확히 {expected_count}개가 필요합니다.",
        )

    seen_titles: set[str] = set()
    career_candidate_count = 0
    numbered_candidate_count = 0
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            add(issues, "error", "candidate-not-object", "제목 후보는 객체여야 합니다.", candidate_index=index)
            continue

        title = TITLE_VALIDATOR.normalize(str(candidate.get("title", "")))
        title_mechanism_id = TITLE_VALIDATOR.normalize(str(candidate.get("titleMechanismId", "")))
        reader_stake = TITLE_VALIDATOR.normalize(str(candidate.get("readerStake", "")))
        raw_answer_count = candidate.get("answerCount")
        answer_count = raw_answer_count if isinstance(raw_answer_count, int) else None

        compact_title = TITLE_VALIDATOR.compact(title)
        if compact_title in seen_titles:
            add(issues, "error", "duplicate-title", "서로 다른 제목 5개를 제시해야 합니다.", candidate_index=index)
        elif compact_title:
            seen_titles.add(compact_title)

        matched_strong = next((value for value in strong_expressions if value in title), "")
        if not matched_strong:
            add(
                issues,
                "error",
                "strong-wording-missing",
                "최악의·반드시·망치는·놓치면 손해처럼 직관적이고 강한 표현이 필요합니다.",
                candidate_index=index,
            )
        matched_weak = next((value for value in weak_expressions if value in title), "")
        if matched_weak:
            add(
                issues,
                "error",
                "weak-wording",
                f"약한 표현을 더 직관적인 표현으로 바꿔야 합니다: {matched_weak}",
                candidate_index=index,
            )

        if reader_stake not in reader_stake_values:
            add(
                issues,
                "error",
                "reader-stake-invalid",
                "readerStake는 benefit 또는 loss-prevention이어야 합니다.",
                candidate_index=index,
            )
        else:
            stake_terms = normalized_list(
                reader_stake_terms.get(reader_stake, []) if isinstance(reader_stake_terms, dict) else []
            )
            if stake_terms and not any(term in title for term in stake_terms):
                add(
                    issues,
                    "error",
                    "reader-stake-not-visible",
                    "독자가 얻는 이득 또는 피할 손해가 제목 문구에 바로 보여야 합니다.",
                    candidate_index=index,
                )

        promises = [
            int(match.group("count"))
            for match in TITLE_VALIDATOR.NUMBERED_PROMISE.finditer(title)
        ]
        if promises:
            numbered_candidate_count += 1
            if any(value not in allowed_answer_counts for value in promises):
                add(
                    issues,
                    "error",
                    "numbered-hook-out-of-range",
                    "제목의 답 개수는 1가지, 2가지, 3가지만 사용합니다.",
                    candidate_index=index,
                )
        if career_expression and career_expression in title:
            career_candidate_count += 1
        if contract.get("numericHookRequiredPerCandidate") is True and not (
            promises or (career_expression and career_expression in title)
        ):
            add(
                issues,
                "error",
                "numeric-hook-missing",
                f"각 후보는 {career_expression} 또는 1~3가지 숫자 장치를 사용해야 합니다.",
                candidate_index=index,
            )
        if not promises and raw_answer_count is not None:
            add(
                issues,
                "error",
                "answer-count-without-promise",
                "숫자 답 약속이 없는 제목에는 answerCount를 넣지 않습니다.",
                candidate_index=index,
            )
        if title_first and title_mechanism_id:
            add(
                issues,
                "error",
                "title-first-mechanism-preselected",
                "빠른 제목 단계에서는 레퍼런스 제목 장치를 먼저 고르지 않습니다.",
                candidate_index=index,
            )

        result = TITLE_VALIDATOR.validate_title(
            title,
            keyword,
            evidence=career_expression if title_first else evidence,
            answer_count=answer_count,
            editorial_close=not title_first,
            writing_intelligence=writing_intelligence,
            reference_master_id="" if title_first else reference_master_id,
            title_mechanism_id="" if title_first else title_mechanism_id,
        )
        candidate_results.append(
            {
                "candidateIndex": index,
                "title": title,
                "readerStake": reader_stake,
                "matchedStrongExpression": matched_strong,
                "validation": result,
            }
        )

    minimum_career = int(contract.get("minimumCareerCandidateCount", 1))
    minimum_numbered = int(contract.get("minimumNumberedCandidateCount", 3))
    if career_candidate_count < minimum_career:
        add(
            issues,
            "error",
            "career-candidate-count",
            f"{career_expression}를 활용한 후보가 최소 {minimum_career}개 필요합니다.",
        )
    if numbered_candidate_count < minimum_numbered:
        add(
            issues,
            "error",
            "numbered-candidate-count",
            f"1~3가지 답 개수를 활용한 후보가 최소 {minimum_numbered}개 필요합니다.",
        )

    candidate_errors = sum(
        item["severity"] == "error"
        for result in candidate_results
        for item in result["validation"]["issues"]
    )
    candidate_warnings = sum(
        item["severity"] == "warning"
        for result in candidate_results
        for item in result["validation"]["issues"]
    )
    errors = sum(item["severity"] == "error" for item in issues) + candidate_errors
    warnings = sum(item["severity"] == "warning" for item in issues) + candidate_warnings
    return {
        "status": "fail" if errors else "warning" if warnings else "pass",
        "contractId": str(contract.get("contractId", "")),
        "metrics": {
            "workflowStage": workflow_stage,
            "researchDeferred": title_first,
            "referenceMasterDeferred": title_first,
            "candidateCount": len(candidates),
            "uniqueTitleCount": len(seen_titles),
            "careerCandidateCount": career_candidate_count,
            "numberedCandidateCount": numbered_candidate_count,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
        "candidateResults": candidate_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--writing-intelligence", type=Path, default=DEFAULT_WRITING_INTELLIGENCE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        title_first = (
            isinstance(payload, dict)
            and isinstance(contract, dict)
            and payload.get(
                "workflowStage",
                contract.get("defaultWorkflowStage", "master-aware"),
            )
            == "title-first"
        )
        evidence = "" if title_first else args.evidence.read_text(encoding="utf-8")
        writing_intelligence = (
            {}
            if title_first
            else json.loads(args.writing_intelligence.read_text(encoding="utf-8"))
        )
        if not all(isinstance(value, dict) for value in (payload, contract, writing_intelligence)):
            raise ValueError("입력 JSON의 최상위 값은 객체여야 합니다.")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"제목 추천 검증 입력을 읽지 못했습니다: {exc}", file=sys.stderr)
        return 2

    result = validate_recommendations(
        payload,
        contract=contract,
        evidence=evidence,
        writing_intelligence=writing_intelligence,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"제목 후보 수: {result['metrics']['candidateCount']}")
        for issue in result["issues"]:
            index = f" 후보 {issue['candidateIndex']}" if "candidateIndex" in issue else ""
            print(f"[{issue['severity'].upper()}]{index} {issue['code']}: {issue['detail']}")
        for candidate_result in result["candidateResults"]:
            for issue in candidate_result["validation"]["issues"]:
                print(
                    f"[{issue['severity'].upper()}] 후보 {candidate_result['candidateIndex']} "
                    f"{issue['code']}: {issue['detail']}"
                )
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
