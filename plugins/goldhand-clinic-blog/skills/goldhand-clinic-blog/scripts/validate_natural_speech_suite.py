#!/usr/bin/env python3
"""Validate a sequential Goldhand plain-draft natural-speech evaluation suite."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = SKILL_DIR / "assets" / "goldhand-official-voice-profile.json"
DEFAULT_BRIEFS = SKILL_DIR / "assets" / "wipark-content-briefs.json"
DEFAULT_FINAL_VOICE_CONTRACT = SKILL_DIR / "assets" / "writing-voice-final-review-contract.json"
VOICE_VALIDATOR_PATH = Path(__file__).with_name("validate_goldhand_voice.py")
FINAL_VOICE_VALIDATOR_PATH = Path(__file__).with_name("validate_final_voice_review.py")


def load_voice_validator() -> Any:
    spec = importlib.util.spec_from_file_location("goldhand_voice_validator", VOICE_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_goldhand_voice.py를 불러올 수 없습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_final_voice_validator() -> Any:
    spec = importlib.util.spec_from_file_location("final_voice_review_validator", FINAL_VOICE_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_final_voice_review.py를 불러올 수 없습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def word_tokens(value: str) -> list[str]:
    return re.findall(r"[가-힣A-Za-z0-9]+", value.lower())


def body_text(case: dict[str, Any]) -> str:
    paragraphs = case.get("finalBody")
    if not isinstance(paragraphs, list) or not all(isinstance(item, str) and item.strip() for item in paragraphs):
        return ""
    return "\n".join(item.strip() for item in paragraphs)


def sentence_count(paragraph: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", paragraph.strip()) if part.strip()])


def longest_equal_run(values: list[int]) -> int:
    longest = 0
    current = 0
    previous: int | None = None
    for value in values:
        if value == previous:
            current += 1
        else:
            previous = value
            current = 1
        longest = max(longest, current)
    return longest


def wrap_for_voice(case: dict[str, Any], profile_id: str, source_url: str) -> str:
    body = body_text(case)
    return (
        f'<article data-goldhand-voice-profile="{profile_id}" '
        f'data-content-reference-source="{source_url}">\n{body}\n</article>'
    )


def repeated_cross_case_phrases(cases: list[dict[str, Any]], width: int = 8) -> list[dict[str, Any]]:
    owners: dict[tuple[str, ...], set[int]] = {}
    greeting_tokens = tuple(word_tokens("안녕하세요, 금손한의원 박준희 원장입니다."))
    for case in cases:
        iteration = int(case.get("iteration", 0))
        tokens = word_tokens(body_text(case))
        for index in range(max(0, len(tokens) - width + 1)):
            shingle = tuple(tokens[index:index + width])
            if shingle[: len(greeting_tokens)] == greeting_tokens:
                continue
            owners.setdefault(shingle, set()).add(iteration)
    repeated = [
        {"phrase": " ".join(shingle), "iterations": sorted(iterations)}
        for shingle, iterations in owners.items()
        if len(iterations) >= 2
    ]
    # Adjacent overlapping shingles describe the same copied run. One example per
    # identical owner set keeps the report readable without weakening the gate.
    compacted: list[dict[str, Any]] = []
    seen_owner_sets: set[tuple[int, ...]] = set()
    for item in repeated:
        owner_key = tuple(item["iterations"])
        if owner_key in seen_owner_sets:
            continue
        seen_owner_sets.add(owner_key)
        compacted.append(item)
    return compacted


def validate_suite(
    suite: dict[str, Any],
    profile: dict[str, Any],
    briefs_payload: dict[str, Any],
    *,
    expected_count: int | None = None,
) -> dict[str, Any]:
    voice = load_voice_validator()
    final_voice = load_final_voice_validator()
    issues: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    cases = suite.get("cases")
    briefs = briefs_payload.get("briefs", {})
    profile_id = str(profile.get("profileId", "goldhand-official-voice-v1"))

    def add(code: str, detail: str, iteration: int | None = None) -> None:
        item: dict[str, Any] = {"severity": "error", "code": code, "detail": detail}
        if iteration is not None:
            item["iteration"] = iteration
        issues.append(item)

    try:
        final_voice_contract = json.loads(DEFAULT_FINAL_VOICE_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add("writing-voice-contract-load", f"writing-voice 최종 검수 계약을 읽지 못했습니다: {exc}")
        final_voice_contract = {}

    if not isinstance(cases, list) or not cases:
        add("suite-cases-missing", "cases 배열에 한 편 이상의 원고가 필요합니다.")
        cases = []
    if len(cases) > 20:
        add("suite-count-over-limit", f"반복 검수는 최대 20편입니다. 현재 {len(cases)}편입니다.")
    if expected_count is not None and len(cases) != expected_count:
        add("suite-count-mismatch", f"요청한 검수 편수는 {expected_count}편인데 현재 {len(cases)}편입니다.")

    iterations = [case.get("iteration") for case in cases if isinstance(case, dict)]
    if iterations != list(range(1, len(cases) + 1)):
        add("iteration-sequence", "iteration은 1부터 끊김 없이 생성 순서대로 기록해야 합니다.")

    for raw_case in cases:
        if not isinstance(raw_case, dict):
            add("case-invalid", "각 case는 객체여야 합니다.")
            continue
        iteration = int(raw_case.get("iteration", 0))
        brief_id = str(raw_case.get("briefId", ""))
        brief = briefs.get(brief_id)
        if not isinstance(brief, dict):
            add("brief-id-invalid", f"존재하지 않는 briefId입니다: {brief_id}", iteration)
            continue
        text = body_text(raw_case)
        if not text:
            add("body-missing", "finalBody에 빈 문자열이 아닌 문단 배열이 필요합니다.", iteration)
            continue

        keyword = str(raw_case.get("keyword", "")).strip()
        title = str(raw_case.get("title", "")).strip()
        if not keyword or title.count(keyword) != 1:
            add("title-keyword-count", "제목의 정확 키워드는 한 번이어야 합니다.", iteration)
        body_keyword_count = text.count(keyword) if keyword else 0
        if body_keyword_count not in {2, 3}:
            add(
                "body-keyword-count",
                f"평문 후처리 원고의 정확 키워드는 2~3회여야 합니다. 현재 {body_keyword_count}회입니다.",
                iteration,
            )

        char_count = len(compact(title + text))
        if not 1400 <= char_count <= 1800:
            add("draft-length", f"제목+평문 공백 제외 글자 수는 1400~1800자여야 합니다. 현재 {char_count}자입니다.", iteration)

        paragraph_counts = [sentence_count(paragraph) for paragraph in raw_case["finalBody"][1:]]
        count_frequencies = {count: paragraph_counts.count(count) for count in set(paragraph_counts)}
        dominant_ratio = max(count_frequencies.values(), default=0) / max(1, len(paragraph_counts))
        uniform_run = longest_equal_run(paragraph_counts)
        if len(paragraph_counts) >= 10 and len(count_frequencies) < 2:
            add(
                "paragraph-cadence-single-template",
                "모든 본문 문단이 같은 문장 수입니다. 실제 발화처럼 짧고 긴 문단을 섞으세요.",
                iteration,
            )
        if len(paragraph_counts) >= 10 and dominant_ratio > 0.88:
            add(
                "paragraph-cadence-dominance",
                f"같은 문장 수의 문단 비율이 {dominant_ratio:.0%}입니다. 문단마다 같은 세 문장 틀을 반복하지 마세요.",
                iteration,
            )
        if uniform_run > 6:
            add(
                "paragraph-cadence-run",
                f"문장 수가 같은 문단이 {uniform_run}개 연속입니다. 설명 호흡을 실제 발화처럼 나누세요.",
                iteration,
            )

        expected_atom_ids = [str(atom.get("id", "")) for atom in brief.get("orderedContentAtoms", [])]
        coverage = raw_case.get("atomCoverage")
        if not isinstance(coverage, dict) or set(coverage) != set(expected_atom_ids):
            add(
                "atom-coverage-keys",
                f"내용 원자 대응 키가 정확하지 않습니다. 필요: {', '.join(expected_atom_ids)}",
                iteration,
            )
        else:
            for atom_id in expected_atom_ids:
                evidence = coverage.get(atom_id)
                if not isinstance(evidence, str) or not evidence.strip() or evidence not in text:
                    add("atom-evidence-missing", f"{atom_id}의 본문 내 정확한 근거 구절이 없습니다.", iteration)

        review = raw_case.get("manualReview")
        if not isinstance(review, dict):
            add("manual-review-missing", "직접 낭독 검수 결과가 없습니다.", iteration)
        else:
            for key in ("soundsSpoken", "onePassMeaning", "sceneIsVisible", "noTemplateFlow"):
                if review.get(key) is not True:
                    add("manual-review-failed", f"직접 검수 항목 {key}가 통과하지 못했습니다.", iteration)
            if review.get("finalStatus") != "pass":
                add("manual-review-status", "최종 직접 검수 상태가 pass가 아닙니다.", iteration)
            history = review.get("revisionHistory")
            if not isinstance(history, list) or not history:
                add("revision-history-missing", "초안 검수와 수정 내역을 최소 한 줄 기록해야 합니다.", iteration)

        voice_result = voice.validate(
            wrap_for_voice(raw_case, profile_id, str(brief.get("sourceUrl", ""))),
            profile,
        )
        if voice_result.get("status") != "pass":
            for voice_issue in voice_result.get("issues", []):
                add(
                    f"voice:{voice_issue.get('code', 'unknown')}",
                    str(voice_issue.get("detail", "말투 검사 실패")),
                    iteration,
                )
        final_voice_result = final_voice.validate_case(raw_case, final_voice_contract)
        if final_voice_result.get("status") != "pass":
            for review_issue in final_voice_result.get("issues", []):
                add(
                    f"writing-voice:{review_issue.get('code', 'unknown')}",
                    str(review_issue.get("detail", "writing-voice 최종 재청취 실패")),
                    iteration,
                )
        results.append(
            {
                "iteration": iteration,
                "briefId": brief_id,
                "title": title,
                "characters": char_count,
                "bodyKeywordCount": body_keyword_count,
                "paragraphSentenceCounts": paragraph_counts,
                "dominantParagraphSentenceCountRatio": round(dominant_ratio, 3),
                "longestUniformParagraphRun": uniform_run,
                "voice": voice_result,
                "finalWritingVoiceReview": final_voice_result,
            }
        )

    repeated_phrases = repeated_cross_case_phrases([case for case in cases if isinstance(case, dict)])
    for item in repeated_phrases:
        add(
            "cross-draft-template-copy",
            f"서로 다른 원고에 같은 8어절 문장 틀이 남았습니다: {item['phrase']} / {item['iterations']}",
        )

    return {
        "status": "fail" if issues else "pass",
        "metrics": {
            "caseCount": len(cases),
            "passedCases": sum(
                1
                for result in results
                if result["voice"].get("status") == "pass"
                and result["finalWritingVoiceReview"].get("status") == "pass"
            ),
            "briefIds": [result["briefId"] for result in results],
            "crossDraftRepeatedPhraseGroups": len(repeated_phrases),
            "errors": len(issues),
        },
        "cases": results,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--briefs", type=Path, default=DEFAULT_BRIEFS)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        suite = json.loads(args.input.read_text(encoding="utf-8"))
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        briefs = json.loads(args.briefs.read_text(encoding="utf-8"))
        result = validate_suite(suite, profile, briefs, expected_count=args.expected_count)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(f"말투 반복검수 입력을 읽지 못했습니다: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"cases: {result['metrics']['caseCount']}")
        for issue in result["issues"]:
            prefix = f"[{issue.get('iteration')}] " if issue.get("iteration") else ""
            print(f"[ERROR] {prefix}{issue['code']}: {issue['detail']}")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
