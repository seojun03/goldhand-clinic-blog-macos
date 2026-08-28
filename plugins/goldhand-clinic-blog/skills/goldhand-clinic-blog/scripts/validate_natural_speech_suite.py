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
DEFAULT_HUMANIZE_CONTRACT = SKILL_DIR / "assets" / "humanize-korean-final-review-contract.json"
VOICE_VALIDATOR_PATH = Path(__file__).with_name("validate_goldhand_voice.py")
FINAL_VOICE_VALIDATOR_PATH = Path(__file__).with_name("validate_final_voice_review.py")
HUMANIZE_VALIDATOR_PATH = Path(__file__).with_name("validate_humanize_final_review.py")
EXACT_GREETING = "안녕하세요, 금손한의원 박준희 원장입니다."
STACKED_ABSTRACT_HOOK = re.compile(r"(?:피로|기분|불편|증상).{0,28}(?:이어지|겹치|반복되)나요\?")
DIRECT_VOICE_AUDIT_ID = "goldhand-direct-voice-sentence-audit-v1"
DIRECT_VOICE_AUDIT_TERMS = (
    "상태",
    "변화",
    "반응",
    "방향",
    "기준",
    "순서",
    "과정",
    "양상",
    "흐름",
    "신호",
    "움직임",
    "생활",
    "모습",
    "단계",
    "차이",
    "범위",
)
BLIND_SPOKEN_REHEAR_ID = "goldhand-blind-spoken-rehear-v3"
BLIND_SENTENCE_MEANING_AUDIT_ID = "goldhand-blind-sentence-meaning-audit-v3"
BLIND_SENTENCE_CHALLENGE_ID = "goldhand-find-one-reason-to-fail-each-sentence-v1"
ALLOWED_CLINIC_UTTERANCE_FORMS = (
    "concrete-patient-scene",
    "concrete-patient-instruction",
    "concrete-history-question",
    "visible-exam-or-palpation-question",
    "concrete-causal-explanation",
    "clinic-decision-and-reason",
    "emergency-sign-and-action",
    "named-treatment-and-reason",
)
INTAKE_SENTENCE_ENDING = re.compile(
    r"(?:묻습니다|말씀해\s*주세요|말해\s*주세요|알려\s*주세요)[.!?]?$"
)
BLIND_SPOKEN_REHEAR_EXCLUDED_INPUTS = (
    "voice-pattern-codes",
    "audit-term-list",
    "validator-results",
    "seo-metrics",
    "reference-prose",
)


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


def load_humanize_validator() -> Any:
    spec = importlib.util.spec_from_file_location("humanize_final_review_validator", HUMANIZE_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_humanize_final_review.py를 불러올 수 없습니다.")
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


def direct_voice_audit_sentences(text: str) -> list[dict[str, Any]]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    results: list[dict[str, Any]] = []
    for sentence in sentences:
        terms = [term for term in DIRECT_VOICE_AUDIT_TERMS if term in sentence]
        if terms:
            results.append({"sentence": sentence, "terms": terms})
    return results


def spoken_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def spoken_sentence_role(sentence: str) -> str:
    value = sentence.strip()
    if value.endswith("?"):
        return "question"
    if not re.search(r"[.!?]$", value):
        return "heading"
    return "statement"


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


def longest_intake_sentence_run(paragraph: str) -> int:
    longest = 0
    current = 0
    for sentence in spoken_sentences(paragraph):
        if INTAKE_SENTENCE_ENDING.search(sentence):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
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
    pre_blind: bool = False,
) -> dict[str, Any]:
    voice = load_voice_validator()
    final_voice = load_final_voice_validator()
    humanize = load_humanize_validator()
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
    try:
        humanize_contract = json.loads(DEFAULT_HUMANIZE_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add("humanize-contract-load", f"humanize-korean 최종 검수 계약을 읽지 못했습니다: {exc}")
        humanize_contract = {}

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
            # 말투 검사는 정보 브리프 오류와 독립적으로 끝까지 실행한다. 그렇지 않으면
            # 잘못된 briefId 하나가 체크리스트·반복 진찰 검사를 전부 건너뛰게 된다.
            brief = {"sourceUrl": "", "orderedContentAtoms": []}
        text = body_text(raw_case)
        if not text:
            add("body-missing", "finalBody에 빈 문자열이 아닌 문단 배열이 필요합니다.", iteration)
            continue

        final_paragraphs = [str(value).strip() for value in raw_case.get("finalBody", [])]
        greeting_indexes = [index for index, paragraph in enumerate(final_paragraphs) if paragraph == EXACT_GREETING]
        greeting_index = greeting_indexes[0] if len(greeting_indexes) == 1 else -1
        if len(greeting_indexes) != 1:
            add("opening-greeting-count", "고정 인사는 finalBody에 정확히 한 번 있어야 합니다.", iteration)
        if greeting_index not in {2, 3}:
            add(
                "opening-greeting-order",
                "finalBody는 서로 다른 생활 장면을 묻는 질문 2~3개로 시작한 뒤 고정 인사가 이어져야 합니다.",
                iteration,
            )
            opening_hooks = final_paragraphs[: max(0, greeting_index)] if greeting_index >= 0 else []
        else:
            opening_hooks = final_paragraphs[:greeting_index]
        if not 2 <= len(opening_hooks) <= 3 or not all(paragraph.endswith("?") for paragraph in opening_hooks):
            add("opening-hook-question-form", "인사 앞에는 물음표로 끝나는 독자 질문 2~3개만 둡니다.", iteration)
        if sum("때문에" in paragraph for paragraph in opening_hooks) > 1:
            add(
                "opening-hook-parallel-because-template",
                "여러 도입 질문을 모두 ‘증상명 때문에 …나요?’ 틀로 쓰면 안 됩니다.",
                iteration,
            )
        for hook_index, paragraph in enumerate(opening_hooks, start=1):
            if STACKED_ABSTRACT_HOOK.search(paragraph):
                add(
                    "opening-hook-abstract-symptom-stack",
                    f"도입 질문 {hook_index}은 피로·기분 같은 증상 목록을 추상 서술어로 묶지 말고 생활 장면으로 물어야 합니다.",
                    iteration,
                )

        keyword = str(raw_case.get("keyword", "")).strip()
        title = str(raw_case.get("title", "")).strip()
        if not keyword or title.count(keyword) != 1:
            add("title-keyword-count", "제목의 정확 키워드는 한 번이어야 합니다.", iteration)
        body_keyword_count = text.count(keyword) if keyword else 0
        if body_keyword_count not in {1, 2}:
            add(
                "body-keyword-count",
                f"평문 후처리 원고의 정확 키워드는 1~2회여야 합니다. 현재 {body_keyword_count}회입니다.",
                iteration,
            )
        approved_keyword_frame = f"저희 {keyword} 금손한의원에서는" if keyword else ""
        if approved_keyword_frame and approved_keyword_frame not in text:
            add(
                "body-keyword-approved-clinic-frame",
                f"정확 키워드는 사용자 승인 구조 '{approved_keyword_frame}' 안에 넣어야 합니다. "
                "키워드를 독자 호명 문장으로 분리하거나 금손한의원을 생략하면 안 됩니다.",
                iteration,
            )

        char_count = len(compact(title + text))
        if not 1400 <= char_count <= 1800:
            add("draft-length", f"제목+평문 공백 제외 글자 수는 1400~1800자여야 합니다. 현재 {char_count}자입니다.", iteration)

        paragraph_counts = [sentence_count(paragraph) for paragraph in final_paragraphs[greeting_index + 1:]]
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
        intake_runs = [longest_intake_sentence_run(paragraph) for paragraph in final_paragraphs]
        longest_intake = max(intake_runs, default=0)
        if longest_intake > 2:
            add(
                "intake-checklist-cadence",
                f"묻습니다·말씀해 주세요 계열 문장이 한 문단에서 {longest_intake}개 연속입니다. 번호 답에는 문진 문장 한 개만 남기고 나머지는 구체적인 이유나 원장의 판단으로 바꾸세요.",
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
            for key in (
                "soundsSpoken",
                "onePassMeaning",
                "sceneIsVisible",
                "noTemplateFlow",
                "clinicSubjectActionPurposeVisible",
                "vagueNounWrappersResolved",
                "directConclusionStrengthPreserved",
                "softAbstractClosingAbsent",
                "readerAddressDirect",
                "connectorsLogicallyEarned",
                "timeViewpointCoherent",
                "noChecklistCadence",
            ):
                if review.get(key) is not True:
                    add("manual-review-failed", f"직접 검수 항목 {key}가 통과하지 못했습니다.", iteration)
            if review.get("finalStatus") != "pass":
                add("manual-review-status", "최종 직접 검수 상태가 pass가 아닙니다.", iteration)
            history = review.get("revisionHistory")
            if not isinstance(history, list) or not history:
                add("revision-history-missing", "초안 검수와 수정 내역을 최소 한 줄 기록해야 합니다.", iteration)
            elif not all(isinstance(item, str) and "→" in item and item.split("→", 1)[0].strip() and item.split("→", 1)[1].strip() for item in history):
                add(
                    "revision-history-not-before-after",
                    "revisionHistory는 실제 수정 전 문장과 수정 후 문장을 `수정 전 → 수정 후` 형식으로 기록해야 합니다.",
                    iteration,
                )

            audit = review.get("directVoiceSentenceAudit")
            expected_audit_sentences = direct_voice_audit_sentences(text)
            if not isinstance(audit, dict):
                add("direct-voice-sentence-audit-missing", "추상 포장어 문장 전수검사 기록이 없습니다.", iteration)
            else:
                if audit.get("contractId") != DIRECT_VOICE_AUDIT_ID:
                    add("direct-voice-sentence-audit-contract", f"전수검사 contractId는 {DIRECT_VOICE_AUDIT_ID}여야 합니다.", iteration)
                if audit.get("searchedTerms") != list(DIRECT_VOICE_AUDIT_TERMS):
                    add("direct-voice-sentence-audit-terms", "추상 포장어 전체 검색 목록이 정확하지 않습니다.", iteration)
                if audit.get("unresolvedCount") != 0:
                    add("direct-voice-sentence-audit-unresolved", "구체 문장으로 해결하지 못한 추상 문장이 남았습니다.", iteration)
                entries = audit.get("sentences")
                if not isinstance(entries, list):
                    add("direct-voice-sentence-audit-sentences", "전수검사 sentences 배열이 필요합니다.", iteration)
                else:
                    normalized_entries: list[dict[str, Any]] = []
                    malformed = False
                    for entry in entries:
                        if not isinstance(entry, dict):
                            malformed = True
                            continue
                        sentence = entry.get("sentence")
                        terms = entry.get("terms")
                        reason = entry.get("concreteReason")
                        if (
                            not isinstance(sentence, str)
                            or not isinstance(terms, list)
                            or not all(isinstance(term, str) for term in terms)
                            or entry.get("decision") != "kept-concrete"
                            or not isinstance(reason, str)
                            or len(reason.strip()) < 8
                        ):
                            malformed = True
                            continue
                        normalized_entries.append({"sentence": sentence.strip(), "terms": terms})
                    if malformed:
                        add(
                            "direct-voice-sentence-audit-entry",
                            "각 전수검사 문장에는 정확한 sentence·terms, decision=kept-concrete, 구체적인 concreteReason이 필요합니다.",
                            iteration,
                        )
                    if normalized_entries != expected_audit_sentences:
                        add(
                            "direct-voice-sentence-audit-coverage",
                            "최종 본문의 추상 포장어 포함 문장을 순서대로 빠짐없이 전수검사해야 합니다.",
                            iteration,
                        )

            blind = review.get("blindSpokenRehear")
            if pre_blind:
                pass
            elif not isinstance(blind, dict):
                add("blind-spoken-rehear-missing", "기계 검사 통과 뒤 실행하는 블라인드 전체 낭독 기록이 없습니다.", iteration)
            else:
                if blind.get("contractId") != BLIND_SPOKEN_REHEAR_ID:
                    add("blind-spoken-rehear-contract", f"블라인드 낭독 contractId는 {BLIND_SPOKEN_REHEAR_ID}여야 합니다.", iteration)
                if blind.get("stage") != "after-mechanical-pass-before-production-assembly":
                    add("blind-spoken-rehear-stage", "블라인드 낭독은 기계 검사 통과 뒤 제작 조립 전에 실행해야 합니다.", iteration)
                if blind.get("reviewerInputMode") != "final-plain-text-only-no-rule-list":
                    add("blind-spoken-rehear-input-mode", "블라인드 낭독에는 최종 평문만 전달하고 금지어·검사표를 전달하면 안 됩니다.", iteration)
                if blind.get("excludedInputs") != list(BLIND_SPOKEN_REHEAR_EXCLUDED_INPUTS):
                    add("blind-spoken-rehear-exclusions", "블라인드 낭독에서 제외할 검사 입력 목록이 정확하지 않습니다.", iteration)
                before_body = blind.get("beforeBody")
                if (
                    not isinstance(before_body, list)
                    or len(before_body) != len(final_paragraphs)
                    or not all(isinstance(item, str) and item.strip() for item in before_body)
                ):
                    add("blind-spoken-rehear-before-body", "블라인드 낭독 직전 전체 beforeBody가 최종 문단 수와 정확히 일치해야 합니다.", iteration)
                    before_body = []
                changed_indexes = [
                    index
                    for index, (before, after) in enumerate(zip(before_body, final_paragraphs), start=1)
                    if before != after
                ]
                revisions = blind.get("revisions")
                if not isinstance(revisions, list):
                    add("blind-spoken-rehear-revisions-invalid", "블라인드 낭독의 revisions는 배열이어야 하며 고칠 곳이 없으면 빈 배열을 허용합니다.", iteration)
                    revisions = []
                revision_indexes: list[int] = []
                malformed_revision = False
                for revision in revisions:
                    if not isinstance(revision, dict):
                        malformed_revision = True
                        continue
                    paragraph_index = revision.get("paragraphIndex")
                    if not isinstance(paragraph_index, int) or not 1 <= paragraph_index <= len(final_paragraphs):
                        malformed_revision = True
                        continue
                    expected_before_paragraph = before_body[paragraph_index - 1] if len(before_body) == len(final_paragraphs) else None
                    before_paragraph = revision.get("before")
                    after_paragraph = revision.get("after")
                    awkward_sentence = revision.get("awkwardSentenceBefore")
                    spoken_sentence = revision.get("spokenSentenceAfter")
                    reason = revision.get("reason")
                    if (
                        before_paragraph != expected_before_paragraph
                        or after_paragraph != final_paragraphs[paragraph_index - 1]
                        or not isinstance(awkward_sentence, str)
                        or awkward_sentence.strip() not in before_paragraph
                        or not isinstance(spoken_sentence, str)
                        or spoken_sentence.strip() not in after_paragraph
                        or awkward_sentence.strip() == spoken_sentence.strip()
                        or not isinstance(reason, str)
                        or len(reason.strip()) < 12
                    ):
                        malformed_revision = True
                        continue
                    revision_indexes.append(paragraph_index)
                if malformed_revision:
                    add(
                        "blind-spoken-rehear-revision-invalid",
                        "블라인드 수정에는 정확한 문단 전후, 어색한 원문, 직접 고친 문장, 구체적인 이유가 필요합니다.",
                        iteration,
                    )
                if sorted(revision_indexes) != changed_indexes:
                    add(
                        "blind-spoken-rehear-revision-coverage",
                        "블라인드 낭독에서 바뀐 모든 문단을 빠짐없이 한 번씩 기록해야 합니다.",
                        iteration,
                    )
                first_pass = blind.get("firstPass")
                if (
                    not isinstance(first_pass, dict)
                    or first_pass.get("wholeDraftRead") is not True
                    or first_pass.get("reviewedSentenceCount") != len(spoken_sentences("\n".join(before_body)))
                    or first_pass.get("awkwardSentenceCount") != len(revisions)
                ):
                    add("blind-spoken-rehear-first-pass", "첫 블라인드 낭독의 전체 문장 수와 발견 건수를 정확히 기록해야 합니다.", iteration)
                second_pass = blind.get("secondPass")
                if (
                    not isinstance(second_pass, dict)
                    or second_pass.get("wholeDraftReadAgain") is not True
                    or second_pass.get("reviewedSentenceCount") != len(spoken_sentences(text))
                    or second_pass.get("remainingAwkwardSentences") != []
                    or second_pass.get("finalStatus") != "pass"
                ):
                    add("blind-spoken-rehear-second-pass", "수정 뒤 전체를 다시 읽고 잔존 어색한 문장 0건과 pass를 기록해야 합니다.", iteration)

                meaning_audit = blind.get("sentenceMeaningAudit")
                expected_spoken_sentences = spoken_sentences(text)
                if not isinstance(meaning_audit, dict):
                    add(
                        "blind-sentence-meaning-audit-missing",
                        "최종 모든 문장의 주어·서술어·조사·병렬 관계를 한 문장씩 확인한 의미 감사가 없습니다.",
                        iteration,
                    )
                else:
                    if meaning_audit.get("contractId") != BLIND_SENTENCE_MEANING_AUDIT_ID:
                        add(
                            "blind-sentence-meaning-audit-contract",
                            f"문장 의미 감사 contractId는 {BLIND_SENTENCE_MEANING_AUDIT_ID}여야 합니다.",
                            iteration,
                        )
                    if meaning_audit.get("reviewMode") != "final-plain-text-sentence-by-sentence-no-rule-list":
                        add(
                            "blind-sentence-meaning-audit-mode",
                            "문장 의미 감사는 규칙 목록 없이 최종 평문만 한 문장씩 읽어야 합니다.",
                            iteration,
                        )
                    if meaning_audit.get("unresolvedCount") != 0:
                        add(
                            "blind-sentence-meaning-audit-unresolved",
                            "주어·서술어·조사·병렬 관계를 해결하지 못한 최종 문장이 남았습니다.",
                            iteration,
                        )
                    audit_entries = meaning_audit.get("sentences")
                    normalized_sentence_audit: list[dict[str, Any]] = []
                    plain_meanings: list[str] = []
                    malformed_sentence_audit = False
                    if not isinstance(audit_entries, list):
                        add(
                            "blind-sentence-meaning-audit-sentences",
                            "최종 모든 문장을 등장 순서대로 기록한 sentences 배열이 필요합니다.",
                            iteration,
                        )
                        audit_entries = []
                    for expected_index, expected_sentence in enumerate(expected_spoken_sentences, start=1):
                        if expected_index > len(audit_entries):
                            malformed_sentence_audit = True
                            continue
                        entry = audit_entries[expected_index - 1]
                        if not isinstance(entry, dict):
                            malformed_sentence_audit = True
                            continue
                        subject = entry.get("literalSubject")
                        predicate = entry.get("literalPredicate")
                        plain_meaning = entry.get("plainMeaning")
                        checks = entry.get("checks")
                        expected_role = spoken_sentence_role(expected_sentence)
                        if (
                            entry.get("index") != expected_index
                            or entry.get("sentence") != expected_sentence
                            or entry.get("role") != expected_role
                            or not isinstance(subject, str)
                            or len(subject.strip()) < 2
                            or subject.strip() in {
                                "문장의 주어",
                                "실제 주어",
                                "해당 문장의 실제 주체",
                                "문장에 직접 적힌 사람이나 대상",
                            }
                            or not isinstance(predicate, str)
                            or len(predicate.strip()) < 2
                            or predicate.strip() in {
                                "문장의 서술어",
                                "실제 서술어",
                                "해당 문장의 실제 서술어",
                                "그 사람이 하거나 대상에 일어나는 일",
                            }
                            or not isinstance(plain_meaning, str)
                            or len(plain_meaning.strip()) < 8
                            or re.search(
                                r"^(?:환자가 )?(?:한 번 듣고 )?(?:바로 )?이해할 수 있는 (?:구체적인 )?뜻(?:입니다)?[.]?$",
                                plain_meaning.strip(),
                            )
                            or not isinstance(checks, dict)
                            or any(
                                checks.get(key) is not True
                                for key in (
                                    "subjectPredicateLogical",
                                    "particlesAndParallelismNatural",
                                    "objectPredicateCompatible",
                                    "literalMeaningMatchesIntent",
                                    "doctorWouldSayVerbatim",
                                    "listenerUnderstandsFirstTime",
                                    "connectorHasLiteralAntecedent",
                                    "timeViewpointCoherent",
                                    "notChecklistCadence",
                                )
                            )
                            or entry.get("verdict") != "pass"
                        ):
                            malformed_sentence_audit = True
                        if isinstance(plain_meaning, str):
                            plain_meanings.append(compact(plain_meaning))
                        normalized_sentence_audit.append(
                            {
                                "index": entry.get("index"),
                                "sentence": entry.get("sentence"),
                                "role": entry.get("role"),
                            }
                        )
                    if len(audit_entries) != len(expected_spoken_sentences):
                        malformed_sentence_audit = True
                    if len(plain_meanings) != len(set(plain_meanings)):
                        malformed_sentence_audit = True
                    if malformed_sentence_audit:
                        add(
                            "blind-sentence-meaning-audit-entry",
                            "모든 최종 문장에 정확한 순서·문장·역할·주어·서술어·평이한 뜻과 의미 검사를 기록해야 합니다.",
                            iteration,
                        )
                    expected_sentence_audit = [
                        {
                            "index": index,
                            "sentence": sentence,
                            "role": spoken_sentence_role(sentence),
                        }
                        for index, sentence in enumerate(expected_spoken_sentences, start=1)
                    ]
                    if normalized_sentence_audit != expected_sentence_audit:
                        add(
                            "blind-sentence-meaning-audit-coverage",
                            "최종 평문의 모든 문장을 등장 순서대로 하나도 빠짐없이 의미 감사해야 합니다.",
                            iteration,
                        )

                    challenger = meaning_audit.get("challengerPass")
                    expected_indexes = list(range(1, len(expected_spoken_sentences) + 1))
                    if (
                        not isinstance(challenger, dict)
                        or challenger.get("contractId") != BLIND_SENTENCE_CHALLENGE_ID
                        or challenger.get("instruction") != "try-to-fail-every-sentence-before-passing"
                        or challenger.get("reviewedSentenceCount") != len(expected_spoken_sentences)
                        or challenger.get("sentenceIndexesChecked") != expected_indexes
                        or challenger.get("failedSentenceIndexes") != []
                        or challenger.get("finalStatus") != "pass"
                    ):
                        add(
                            "blind-sentence-meaning-audit-challenger",
                            "각 문장을 통과시키기 전에 실패 이유를 찾는 반대 검토를 전 문장에 실행하고 잔존 0건을 기록해야 합니다.",
                            iteration,
                        )
                if blind.get("mechanicalValidatorStatusBeforeBlindReview") != "pass":
                    add("blind-spoken-rehear-before-validator", "블라인드 낭독 전 기계 검사 상태가 pass여야 합니다.", iteration)
                if blind.get("mechanicalValidatorRerunAfterBlindEdits") != "pass":
                    add("blind-spoken-rehear-rerun", "블라인드 수정 뒤 기계 검사를 다시 실행해 pass를 기록해야 합니다.", iteration)

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
        final_reviewer = str(raw_case.get("finalVoiceReviewerSkill", "")).strip()
        if not final_reviewer:
            final_reviewer = "humanize-korean" if "humanizeKoreanReview" in raw_case else "writing-voice"
        if final_reviewer == "writing-voice":
            final_voice_result = final_voice.validate_case(raw_case, final_voice_contract)
            issue_prefix = "writing-voice"
            fallback_detail = "writing-voice 최종 재청취 실패"
        elif final_reviewer == "humanize-korean":
            final_voice_result = humanize.validate_case(raw_case, humanize_contract)
            issue_prefix = "humanize-korean"
            fallback_detail = "humanize-korean 최종 윤문 실패"
        else:
            final_voice_result = {
                "status": "fail",
                "metrics": {"errors": 1},
                "issues": [
                    {
                        "code": "final-reviewer-unsupported",
                        "detail": f"지원하지 않는 최종 윤문기입니다: {final_reviewer}",
                    }
                ],
            }
            issue_prefix = "final-reviewer"
            fallback_detail = "최종 윤문기 선택 실패"
        if final_voice_result.get("status") != "pass":
            for review_issue in final_voice_result.get("issues", []):
                add(
                    f"{issue_prefix}:{review_issue.get('code', 'unknown')}",
                    str(review_issue.get("detail", fallback_detail)),
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
                "finalVoiceReviewerSkill": final_reviewer,
                "finalVoiceReview": final_voice_result,
                "finalWritingVoiceReview": final_voice_result if final_reviewer == "writing-voice" else None,
                "finalHumanizeReview": final_voice_result if final_reviewer == "humanize-korean" else None,
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
                and result["finalVoiceReview"].get("status") == "pass"
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
    parser.add_argument(
        "--pre-blind",
        action="store_true",
        help="블라인드 재낭독 직전 1차 기계 검사에서만 사용합니다. 최종 검사는 이 옵션 없이 다시 실행해야 합니다.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        suite = json.loads(args.input.read_text(encoding="utf-8"))
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        briefs = json.loads(args.briefs.read_text(encoding="utf-8"))
        result = validate_suite(
            suite,
            profile,
            briefs,
            expected_count=args.expected_count,
            pre_blind=args.pre_blind,
        )
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
