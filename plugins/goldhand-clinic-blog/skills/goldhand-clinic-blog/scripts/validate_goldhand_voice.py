#!/usr/bin/env python3
"""Reject AI-template prose and enforce the audited Goldhand official voice."""

from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = SKILL_DIR / "assets" / "goldhand-official-voice-profile.json"
NUMBERED_HEADING = re.compile(r"^(?:\d+\s*[.)]|[①②③④⑤⑥⑦⑧⑨⑩])")
DIRECTIVE_SENTENCE_ENDING = re.compile(
    r"(?:세요|마세요|주세요|받으세요|가세요|야\s*합니다|편이\s*낫습니다)[.!?]?$"
)
CLINICAL_REPORT_SENTENCE_ENDING = re.compile(
    r"(?:묻습니다|물어봅니다|여쭤봅니다|봅니다|보겠습니다|"
    r"확인합니다|설명합니다|설명드립니다|정합니다|고릅니다|권합니다|안내합니다)[.!?]?$"
)
CLINICAL_BEAT_ACTION = re.compile(
    r"(?:묻습니다|물어봅니다|여쭤봅니다|말씀해\s*주세요|말해\s*주세요|"
    r"직접\s*봅니다|보겠습니다|직접\s*보겠습니다|누른\s*뒤|눌러|"
    r"돌려\s*보세요|굽혀\s*보세요|한\s*발로\s*서|내려가\s*보세요)"
)
INTAKE_SENTENCE = re.compile(
    r"(?:묻습니다|묻고|물어봅니다|여쭤봅니다|듣습니다|듣고|말씀해\s*(?:주세요|달라고)|말해\s*주세요|"
    r"알려\s*주세요|기억해\s*(?:두세요|주세요)|기록해\s*주세요|적어\s*(?:두세요|오세요)|"
    r"표시해\s*주세요|가져오(?:세요|시고)|보여\s*주세요)"
)
EXTERNAL_REFERRAL_SENTENCE = re.compile(
    r"(?:병원|응급실|신경과|정형외과|내과|위내시경|CT|MRI|X-ray)[^.!?\n]{0,90}"
    r"(?:가야|가세요|진료|검사|받아야|받으세요|미루|권합니다)"
)
PHYSICAL_EXAM_SENTENCE = re.compile(
    r"(?:누르|눌러|돌려\s*보세요|굽혀\s*보세요|한\s*발로\s*(?:서|설)|"
    r"뒤꿈치[^.!?\n]{0,30}(?:들리|뜨)|몸[^.!?\n]{0,25}(?:기우|흔들)|"
    r"골반[^.!?\n]{0,25}(?:기우|높이)|(?:양쪽|좌우)[^.!?\n]{0,35}(?:비교|나란히)|"
    r"압통|절뚝|보폭|가동\s*범위|진찰)"
)
NAMED_TREATMENT_SENTENCE = re.compile(r"(?:침|약침|추나|한약|뜸|부항|골타요법)[^.!?\n]{0,70}(?:치료|처방|권|놓)")
SELF_CARE_DIRECTIVE_SENTENCE = re.compile(
    r"(?:쉬세요|미루세요|멈추세요|피하세요|줄여\s*보세요|천천히\s*(?:드세요|걸으세요)|"
    r"얼음|냉찜질|온찜질|뜨거운\s*찜질|압박붕대|마사지|운동|연습|달리기|등산)"
)
QUESTION_CUE = re.compile(
    r"(?:언제|어디|어느|무엇|무슨|어떤|어떻게|얼마나|몇\s*(?:시|분|시간|번|회|개|칸|숟갈|일|주|달))"
)
RECORD_CUE = re.compile(
    r"(?:날짜|시간|알약\s*개수|달력|메모|기록|적어|표시|사진|약\s*봉투|결과지|가져오|보여\s*주세요)"
)
REPEATED_CLINICAL_BEATS = (
    ("고개 돌리기 진찰", re.compile(r"고개[^.!?\n]{0,55}(?:돌리|돌려|돌아가|돌아가는|돌릴)")),
    ("발목 굽힘과 뒤꿈치 관찰", re.compile(r"(?:발목[^.!?\n]{0,45}굽|뒤꿈치[^.!?\n]{0,30}(?:들리|뜨))")),
    ("한 발 서기 진찰", re.compile(r"한\s*발로[^.!?\n]{0,35}(?:서|설)")),
    ("계단에서 몸 기울기 관찰", re.compile(r"(?:계단|발판)[^.!?\n]{0,65}(?:몸|몸통|골반)[^.!?\n]{0,30}(?:기우|흔들)")),
    ("복숭아뼈 압통 진찰", re.compile(r"복숭아뼈[^.!?\n]{0,55}(?:누르|눌러)")),
    ("목과 어깨 압통 진찰", re.compile(r"(?:목\s*뒤|어깨\s*위)[^.!?\n]{0,55}(?:누르|눌러)")),
    ("명치와 배꼽 위 압통 진찰", re.compile(r"(?:명치|배꼽\s*위)[^.!?\n]{0,55}(?:누르|눌러)")),
)
CLINIC_INFO_HEADING = re.compile(r"^(?:진료(?:시간)?\s*안내|금손한의원|요일\s*[|])$")
ABSTRACT_SLOGAN_SENTENCE = re.compile(
    r"(?:판단|선택|과정|방향|기준|출발|첫걸음|회복|일상)[^.!?\n]{0,55}"
    r"(?:중요|좌우|출발(?:점)?|첫걸음|기본|핵심|답(?:입니다|이죠)|뜻입니다)"
    r"|것,?\s*그것이[^.!?\n]{0,40}(?:출발|첫걸음|핵심|답)"
)
SOFT_OPTIONAL_CLOSING = re.compile(
    r"(?:진료|상담|치료)[^.!?\n]{0,35}(?:받아\s*보셔도|상의해\s*보셔도|해\s*보셔도|보셔도\s*(?:됩니다|좋습니다))"
)


class ProseParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"table", "script", "style"}:
            self.skip_depth += 1
        elif tag == "br" and not self.skip_depth:
            # A mobile visual line break is not a sentence boundary.
            self.parts.append(" ")
        elif tag in {"p", "section", "blockquote", "h2", "h3", "hr"} and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"table", "script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"p", "section", "blockquote", "h2", "h3"} and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def attr_values(fragment: str, name: str) -> list[str]:
    match = re.search(r"<article\b(?P<attrs>[^>]*)>", fragment, re.I | re.S)
    if not match:
        return []
    return re.findall(rf"\b{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", match.group("attrs"), re.I)


def prose_text(fragment: str) -> str:
    parser = ProseParser()
    parser.feed(fragment)
    return re.sub(r"[ \t]+", " ", html.unescape("".join(parser.parts))).strip()


def prose_sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", text)
        if part.strip()
    ]


def validate(fragment: str, profile: dict[str, object]) -> dict[str, object]:
    text = prose_text(fragment)
    compact = re.sub(r"\s+", "", text)
    issues: list[dict[str, str]] = []

    def error(code: str, detail: str) -> None:
        issues.append({"severity": "error", "code": code, "detail": detail})

    profile_id = str(profile.get("profileId", "goldhand-official-voice-v1"))
    if attr_values(fragment, "data-goldhand-voice-profile") != [profile_id]:
        error("voice-profile-missing", f"article에 data-goldhand-voice-profile={profile_id}가 정확히 한 번 필요합니다.")
    if attr_values(fragment, "data-content-reference-source") == []:
        error("content-reference-missing", "주제·내용 원문 URL을 data-content-reference-source에 기록해야 합니다.")

    required = profile.get("requiredSignals", {})
    cadence_limits = profile.get("cadenceLimits", {})
    forbidden = profile.get("forbidden", {})
    greeting = str(required.get("exactGreeting", ""))
    if greeting and text.count(greeting) != 1:
        error("greeting-count", f"고정 인사는 정확히 한 번이어야 합니다. 현재 {text.count(greeting)}회입니다.")
    prose_lines = [
        cleaned
        for line in text.splitlines()
        if (cleaned := re.sub(r"\s+", " ", re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", line)).strip())
    ]
    greeting_indexes = [index for index, line in enumerate(prose_lines) if line == greeting]
    if greeting and len(greeting_indexes) == 1:
        greeting_index = greeting_indexes[0]
        opening_hooks = prose_lines[:greeting_index]
        if greeting_index not in {2, 3} or not all(line.endswith("?") for line in opening_hooks):
            error(
                "opening-hook-greeting-order",
                "글은 서로 다른 생활 장면을 묻는 질문 2~3개로 시작하고, 그 다음에 고정 인사를 써야 합니다.",
            )
        if sum("때문에" in line for line in opening_hooks) > 1:
            error(
                "parallel-because-hook-template",
                "도입 질문마다 증상명만 바꿔 ‘… 때문에 …나요?’ 틀을 반복하지 마세요.",
            )

    for value in forbidden.get("emoticons", []):
        if value and str(value) in text:
            error("emoticon", f"금지된 이모티콘·장식: {value}")
    emoji = re.search("[\U0001F1E6-\U0001FAFF\u2600-\u27BF]", text)
    if emoji:
        error("emoji", f"이모지는 사용할 수 없습니다: {emoji.group(0)}")
    for phrase in forbidden.get("aiTemplatePhrases", []):
        if phrase and str(phrase) in text:
            error("ai-template-phrase", f"AI 템플릿 표현을 실제 장면과 원장 말투로 다시 쓰세요: {phrase}")
    all_register_patterns = forbidden.get("aiRegisterPatterns", [])
    active_pattern_count = int(forbidden.get("activeAiRegisterPatternCount", len(all_register_patterns)))
    for rule in all_register_patterns[:active_pattern_count]:
        if not isinstance(rule, dict):
            continue
        pattern = str(rule.get("pattern", "")).strip()
        if not pattern:
            continue
        try:
            match = re.search(pattern, text, re.I | re.S)
        except re.error as exc:
            error("voice-profile-pattern-invalid", f"말투 프로필 정규식이 잘못되었습니다: {exc}")
            continue
        if match:
            code = str(rule.get("code", "ai-register-pattern"))
            detail = str(rule.get("detail", "실제 진료실에서 말할 법한 짧고 직접적인 한국어로 다시 쓰세요."))
            excerpt = re.sub(r"\s+", " ", match.group(0)).strip()
            error(code, f"{detail} 감지 문장: {excerpt}")

    first_person = len(re.findall(r"(?:제가|저는|저도|저희|박원장)", text))
    conversational = len(
        re.findall(r"(?:죠|거든요|더라구요|네요|세요|했어요|에요|예요)(?:[.!?]|\s|$)", text)
    )
    transitions = sum(text.count(str(value)) for value in required.get("candidTransitions", []))
    sentences = prose_sentences(text)
    structural_quotas_enabled = bool(cadence_limits.get("structuralQuotasEnabled", False))
    maximum_sentence_characters = int(cadence_limits.get("maximumNonWhitespaceCharactersPerSentence", 75))
    maximum_sentence_commas = int(cadence_limits.get("maximumCommasPerSentence", 2))
    longest_sentence_characters = 0
    maximum_commas_in_sentence = 0
    for sentence in sentences:
        if sentence == greeting:
            continue
        sentence_characters = len(re.sub(r"\s+", "", sentence))
        sentence_commas = sentence.count(",") + sentence.count("，")
        longest_sentence_characters = max(longest_sentence_characters, sentence_characters)
        maximum_commas_in_sentence = max(maximum_commas_in_sentence, sentence_commas)
        if structural_quotas_enabled and sentence_characters > maximum_sentence_characters:
            error(
                "overpacked-sentence-length",
                f"한 문장이 공백 제외 {sentence_characters}자입니다. {maximum_sentence_characters}자 이하로 나누되, 장면·이유·행동을 새 문장에 다시 쌓지 말고 핵심만 남기세요. 감지 문장: {sentence}",
            )
        if structural_quotas_enabled and sentence_commas > maximum_sentence_commas:
            error(
                "overpacked-sentence-commas",
                f"한 문장에 쉼표가 {sentence_commas}개입니다. 쉼표로 문진·검사·생활수칙을 이어 붙이지 말고 한 문장에는 한 판단 또는 한 행동만 말하세요. 감지 문장: {sentence}",
            )
        if ABSTRACT_SLOGAN_SENTENCE.search(sentence):
            error(
                "abstract-slogan-summary",
                f"판단·선택·회복·출발 같은 추상어로 교훈이나 표어를 만들지 말고, 지금 어떤 증상이 있으면 무엇을 해야 하는지 직접 쓰세요. 감지 문장: {sentence}",
            )
    scene_noun_pattern = re.compile(
        r"(?:앉|서서|걷|계단|화면|모니터|스마트폰|고개|목|어깨|팔|손|허리|골반|무릎|발|잠|수면|식사|출근|운전|일어나|옷|머리\s*감|가방)"
    )
    scene_action_pattern = re.compile(
        r"(?:아프|뻐근|저리|힘들|빠지|휘청|끌|숙이|돌리|올리|내리|들리|깨|자|먹|걷|앉|서|움직|일하|운전|답답|두근|화끈|붓|지치)"
    )
    concrete_mentions = len(scene_noun_pattern.findall(text))
    concrete_scene_sentences = sum(
        1
        for sentence in sentences
        if scene_noun_pattern.search(sentence) and scene_action_pattern.search(sentence)
    )
    abstract = len(re.findall(r"(?:판단|기준|구분|확인|흐름|단서|과정|방향|조건)", text))
    possibility_phrases = len(
        re.findall(r"(?:수(?:는|도)?\s*없습니다|수(?:도)?\s*있습니다|일\s*수\s*있습니다)", text)
    )
    clinical_process_predicates = len(
        re.findall(
            r"(?:확인(?:합니다|해야\s*합니다|하고|해봐야\s*합니다)|"
            r"살핍니다|살펴야\s*합니다|봅니다|봐야\s*합니다|정합니다|정해야\s*합니다|판단합니다)",
            text,
        )
    )
    priority_transitions = text.count("먼저")
    binary_contrast_transitions = text.count("반대로")
    treatment_names = {
        value
        for value in ("침", "약침", "추나", "물리치료", "한약", "뜸", "부항", "골타요법", "공진단", "경옥고")
        if re.search(
            rf"(?<![가-힣]){re.escape(value)}(?:은|는|이|가|을|를|과|와|으로|만|도|부터|까지)?(?![가-힣])",
            text,
        )
    }

    if first_person < int(required.get("minimumFirstPersonSignalsOutsideGreeting", 2)):
        error("first-person-dropout", "금손 원장의 1인칭 판단이 부족합니다. 확인된 사실 안에서 제가·저는·저희를 자연스럽게 쓰세요.")
    if conversational < int(required.get("minimumConversationalEndings", 2)):
        error("ending-monotony", "~습니다만 이어집니다. 금손 원문의 ~죠·~거든요·~세요 같은 종결을 자연스럽게 섞으세요.")
    if transitions < int(required.get("minimumCandidTransitionSignals", 2)):
        error("candid-transition-dropout", "사실·그런데·하지만·그래서처럼 원장의 솔직한 말 연결이 부족합니다.")
    if concrete_scene_sentences < int(required.get("minimumConcreteDailyScenes", 2)):
        error("concrete-scene-dropout", "추상 설명보다 실제 생활 동작과 몸의 장면을 두 가지 이상 넣으세요.")
    if abstract >= 18 and abstract > concrete_mentions:
        error("abstract-chain", "판단·기준·구분·확인 같은 추상어가 실제 생활 장면보다 많습니다.")

    maximum_possibility = int(cadence_limits.get("maximumPossibilityPhrases", 5))
    if possibility_phrases > maximum_possibility:
        error(
            "possibility-ending-overuse",
            f"~할 수 있습니다류 표현이 {possibility_phrases}회입니다. 가능성 표현을 반복하지 말고 실제 조건과 증상을 바로 말하세요.",
        )
    maximum_process = int(cadence_limits.get("maximumClinicalProcessPredicates", 9))
    if clinical_process_predicates > maximum_process:
        error(
            "repeated-clinical-predicate",
            f"확인합니다·봅니다·정합니다류 진료 서술이 {clinical_process_predicates}회입니다. 같은 판단 동사를 반복하지 말고 환자가 겪는 장면과 이유를 직접 설명하세요.",
        )
    maximum_treatments = int(cadence_limits.get("maximumDistinctTreatmentNames", 3))
    if len(treatment_names) > maximum_treatments:
        error(
            "treatment-catalogue",
            "한 글에서 환자 상태와 직접 연결하지 않은 치료 이름을 늘어놓지 마세요. 감지 치료: "
            + ", ".join(sorted(treatment_names)),
        )
    maximum_priority = int(cadence_limits.get("maximumPriorityTransitions", 5))
    if priority_transitions > maximum_priority:
        error(
            "priority-transition-overuse",
            f"먼저가 {priority_transitions}회입니다. 모든 설명을 우선순위 문장으로 정렬하지 말고 실제 시간과 동작을 바로 말하세요.",
        )
    maximum_binary_contrast = int(cadence_limits.get("maximumBinaryContrastTransitions", 2))
    if binary_contrast_transitions > maximum_binary_contrast:
        error(
            "binary-contrast-overuse",
            f"반대로가 {binary_contrast_transitions}회입니다. 문단마다 A와 B를 대칭시키지 말고 환자가 겪는 장면을 이어 말하세요.",
        )

    maximum_paragraph_sentences = int(cadence_limits.get("maximumSentencesPerParagraph", 5))
    maximum_paragraph_directives = int(cadence_limits.get("maximumDirectiveSentencesPerParagraph", 2))
    maximum_paragraph_reports = int(cadence_limits.get("maximumClinicalReportSentencesPerParagraph", 2))
    longest_paragraph_sentences = 0
    maximum_directives_in_paragraph = 0
    maximum_reports_in_paragraph = 0
    for line_number, line in enumerate(prose_lines, start=1):
        if line == greeting or NUMBERED_HEADING.match(line) or not re.search(r"[.!?]", line):
            continue
        paragraph_sentences = prose_sentences(line)
        sentence_total = len(paragraph_sentences)
        directive_total = sum(bool(DIRECTIVE_SENTENCE_ENDING.search(sentence)) for sentence in paragraph_sentences)
        report_total = sum(bool(CLINICAL_REPORT_SENTENCE_ENDING.search(sentence)) for sentence in paragraph_sentences)
        longest_paragraph_sentences = max(longest_paragraph_sentences, sentence_total)
        maximum_directives_in_paragraph = max(maximum_directives_in_paragraph, directive_total)
        maximum_reports_in_paragraph = max(maximum_reports_in_paragraph, report_total)
        excerpt = re.sub(r"\s+", " ", line).strip()
        if structural_quotas_enabled and sentence_total > maximum_paragraph_sentences:
            error(
                "overloaded-paragraph-cadence",
                f"{line_number}번째 문단이 {sentence_total}문장입니다. 한 문단은 {maximum_paragraph_sentences}문장 이하로 줄이고 판단·이유·핵심 행동만 남기세요. 감지 문단: {excerpt}",
            )
        if structural_quotas_enabled and directive_total > maximum_paragraph_directives:
            error(
                "imperative-checklist-paragraph",
                f"{line_number}번째 문단에 환자 지시가 {directive_total}문장입니다. 생활수칙을 읽어 주지 말고 핵심 행동 한두 개와 그 이유만 남기세요. 감지 문단: {excerpt}",
            )
        if structural_quotas_enabled and report_total > maximum_paragraph_reports:
            error(
                "clinical-report-checklist-paragraph",
                f"{line_number}번째 문단에 묻습니다·봅니다·설명합니다류 진료 보고가 {report_total}문장입니다. 핵심 질문 한두 개와 원장의 구체적인 판단만 남기세요. 감지 문단: {excerpt}",
            )

    answer_preview_sentences = 0
    answer_preview_commas = 0
    maximum_answer_preview = int(cadence_limits.get("maximumAnswerPreviewSentences", 2))
    maximum_answer_preview_commas = int(cadence_limits.get("maximumAnswerPreviewCommas", 1))
    if greeting and len(greeting_indexes) == 1:
        greeting_index = greeting_indexes[0]
        numbered_indexes = [
            index for index, line in enumerate(prose_lines[greeting_index + 1 :], start=greeting_index + 1)
            if NUMBERED_HEADING.match(line)
        ]
        if numbered_indexes:
            first_numbered_index = numbered_indexes[0]
            answer_preview_lines = prose_lines[greeting_index + 1 : first_numbered_index]
            answer_preview_sentences = sum(
                len(prose_sentences(line))
                for line in answer_preview_lines
                if re.search(r"[.!?]", line)
            )
            answer_preview_commas = sum(line.count(",") + line.count("，") for line in answer_preview_lines)
            if structural_quotas_enabled and answer_preview_sentences > maximum_answer_preview:
                error(
                    "answer-preview-overlong",
                    f"고정 인사 뒤 첫 번호 소제목 전 답 선공개가 {answer_preview_sentences}문장입니다. 완전한 결론 {maximum_answer_preview}문장 이하로 끝내고 첫째·둘째 식 항목 계산은 쓰지 마세요.",
                )
            if (
                structural_quotas_enabled
                and not re.search(r"data-reference-role\s*=\s*['\"]section-heading['\"]", fragment, flags=re.I)
                and answer_preview_commas > maximum_answer_preview_commas
            ):
                error(
                    "answer-preview-checklist",
                    f"답 선공개에 쉼표가 {answer_preview_commas}개입니다. 번호 항목의 질문·생활습관·경고 증상을 한 문장에 미리 나열하지 말고 가장 중요한 판단과 행동만 한두 문장으로 말하세요.",
                )

    strict_flat_draft = structural_quotas_enabled and not re.search(
        r"data-reference-role\s*=\s*['\"]section-heading['\"]",
        fragment,
        flags=re.I,
    )
    numbered_indexes = [index for index, line in enumerate(prose_lines) if NUMBERED_HEADING.match(line)]
    section_metrics: list[dict[str, int]] = []
    post_numbered_heading_count = 0
    closing_paragraph_count = 0
    repeated_clinical_beat_count = 0
    closing_sentence_count = 0
    closing_recap_count = 0
    if strict_flat_draft and numbered_indexes:
        content_end = len(prose_lines)
        for index in range(numbered_indexes[-1] + 1, len(prose_lines)):
            if CLINIC_INFO_HEADING.match(prose_lines[index]):
                content_end = index
                break

        post_numbered_headings = [
            index
            for index in range(numbered_indexes[-1] + 1, content_end)
            if not re.search(r"[.!?]", prose_lines[index]) and not NUMBERED_HEADING.match(prose_lines[index])
        ]
        post_numbered_heading_count = len(post_numbered_headings)
        if post_numbered_heading_count != 1:
            error(
                "post-numbered-heading-count",
                f"마지막 번호 답 뒤에는 마무리 소제목 하나만 둬야 합니다. 현재 마침표 없는 추가 소제목이 {post_numbered_heading_count}개입니다.",
            )
        closing_heading_index = post_numbered_headings[-1] if post_numbered_headings else content_end
        closing_heading = prose_lines[closing_heading_index] if closing_heading_index < content_end else ""
        if closing_heading and ABSTRACT_SLOGAN_SENTENCE.search(closing_heading):
            error(
                "abstract-closing-heading",
                f"마무리 소제목을 교훈·표어로 쓰지 마세요. 증상이나 생활 장면과 다음 행동을 바로 말하세요. 감지 소제목: {closing_heading}",
            )
        closing_lines = [
            line
            for line in prose_lines[closing_heading_index + 1 : content_end]
            if re.search(r"[.!?]", line)
        ]
        closing_paragraph_count = len(closing_lines)
        maximum_closing_paragraphs = int(cadence_limits.get("maximumClosingParagraphs", 1))
        maximum_closing_sentences = int(cadence_limits.get("maximumClosingSentences", 2))
        if closing_paragraph_count > maximum_closing_paragraphs:
            error(
                "closing-paragraph-overflow",
                f"마무리 소제목 뒤 산문이 {closing_paragraph_count}문단입니다. 한 문단 안에서 판단 한 문장과 부담 없는 안내 한 문장만 남기세요.",
            )
        closing_sentences = [sentence for line in closing_lines for sentence in prose_sentences(line)]
        closing_sentence_count = len(closing_sentences)
        if closing_sentence_count > maximum_closing_sentences:
            error(
                "closing-sentence-overflow",
                f"마무리 산문이 {closing_sentence_count}문장입니다. {maximum_closing_sentences}문장 이하로 끝내고 본문 내용을 다시 요약하지 마세요.",
            )
        maximum_closing_commas = int(cadence_limits.get("maximumCommasPerClosingSentence", 1))
        for sentence in closing_sentences:
            closing_commas = sentence.count(",") + sentence.count("，")
            if closing_commas > maximum_closing_commas:
                error(
                    "closing-checklist-sentence",
                    f"마무리 한 문장에 쉼표가 {closing_commas}개입니다. 앞의 장면과 행동을 다시 나열하지 말고 증상 기준 한 문장과 다음 행동 한 문장으로 끝내세요. 감지 문장: {sentence}",
                )
            if ABSTRACT_SLOGAN_SENTENCE.search(sentence):
                error(
                    "abstract-closing-slogan",
                    f"마무리에서 판단·선택·출발 같은 추상 표어를 쓰지 마세요. 지금 겪는 증상과 해야 할 행동을 직접 말하세요. 감지 문장: {sentence}",
                )
            if SOFT_OPTIONAL_CLOSING.search(sentence):
                error(
                    "soft-optional-closing",
                    f"진료·상담을 ‘받아 보셔도 됩니다’처럼 흐리지 말고, 불편이 계속되는 구체 조건과 진료 행동을 바로 말하세요. 감지 문장: {sentence}",
                )

        maximum_section_paragraphs = int(cadence_limits.get("maximumParagraphsPerNumberedSection", 2))
        maximum_section_sentences = int(cadence_limits.get("maximumSentencesPerNumberedSection", 4))
        maximum_section_paragraph_sentences = int(
            cadence_limits.get("maximumSentencesPerNumberedSectionParagraph", 2)
        )
        maximum_section_directives = int(cadence_limits.get("maximumDirectiveSentencesPerNumberedSection", 2))
        maximum_section_reports = int(cadence_limits.get("maximumClinicalReportSentencesPerNumberedSection", 2))
        maximum_section_intake = int(cadence_limits.get("maximumIntakeSentencesPerNumberedSection", 1))
        maximum_section_requests = int(cadence_limits.get("maximumPatientRequestSentencesPerNumberedSection", 2))
        maximum_section_referrals = int(cadence_limits.get("maximumReferralSentencesPerNumberedSection", 1))
        maximum_section_action_families = int(cadence_limits.get("maximumActionFamiliesPerNumberedSection", 2))
        maximum_intake_question_cues = int(cadence_limits.get("maximumQuestionCuesPerIntakeSentence", 2))
        maximum_record_cues = int(cadence_limits.get("maximumRecordCuesPerRequestSentence", 1))
        core_section_sentences: list[str] = []
        for position, heading_index in enumerate(numbered_indexes):
            start = heading_index + 1
            if position + 1 < len(numbered_indexes):
                end = numbered_indexes[position + 1]
            else:
                end = closing_heading_index
            section_lines = [line for line in prose_lines[start:end] if re.search(r"[.!?]", line)]
            section_sentences = [sentence for line in section_lines for sentence in prose_sentences(line)]
            directive_total = sum(bool(DIRECTIVE_SENTENCE_ENDING.search(sentence)) for sentence in section_sentences)
            report_total = sum(bool(CLINICAL_REPORT_SENTENCE_ENDING.search(sentence)) for sentence in section_sentences)
            intake_total = sum(bool(INTAKE_SENTENCE.search(sentence)) for sentence in section_sentences)
            patient_request_total = sum(
                bool(DIRECTIVE_SENTENCE_ENDING.search(sentence) or INTAKE_SENTENCE.search(sentence))
                for sentence in section_sentences
            )
            referral_total = sum(bool(EXTERNAL_REFERRAL_SENTENCE.search(sentence)) for sentence in section_sentences)
            action_families = {
                name
                for name, pattern in (
                    ("문진", INTAKE_SENTENCE),
                    ("신체 진찰", PHYSICAL_EXAM_SENTENCE),
                    ("병원 검사", EXTERNAL_REFERRAL_SENTENCE),
                    ("한의 치료", NAMED_TREATMENT_SENTENCE),
                    ("생활수칙", SELF_CARE_DIRECTIVE_SENTENCE),
                )
                if any(pattern.search(sentence) for sentence in section_sentences)
            }
            section_metric = {
                "paragraphs": len(section_lines),
                "sentences": len(section_sentences),
                "directives": directive_total,
                "reports": report_total,
                "intake": intake_total,
                "patientRequests": patient_request_total,
                "referrals": referral_total,
                "actionFamilies": len(action_families),
            }
            section_metrics.append(section_metric)
            core_section_sentences.extend(section_sentences)
            section_number = position + 1
            if len(section_lines) > maximum_section_paragraphs:
                error(
                    "numbered-section-paragraph-overflow",
                    f"{section_number}번 번호 답이 {len(section_lines)}문단입니다. 번호 답 하나는 {maximum_section_paragraphs}문단 이하로 끝내고 같은 문진·진찰·안전을 새 문단으로 늘리지 마세요.",
                )
            for section_line in section_lines:
                section_line_sentences = prose_sentences(section_line)
                if len(section_line_sentences) > maximum_section_paragraph_sentences:
                    error(
                        "numbered-section-paragraph-sentence-overflow",
                        f"{section_number}번 번호 답의 한 문단이 {len(section_line_sentences)}문장입니다. 번호 문단은 {maximum_section_paragraph_sentences}문장 이하로 쓰고 결론·이유·원장 행동을 다른 문장에 반복하지 마세요. 감지 문단: {section_line}",
                    )
            if len(section_sentences) > maximum_section_sentences:
                error(
                    "numbered-section-sentence-overflow",
                    f"{section_number}번 번호 답이 {len(section_sentences)}문장입니다. {maximum_section_sentences}문장 이하에서 결론·장면·이유·핵심 행동만 남기세요.",
                )
            if directive_total > maximum_section_directives:
                error(
                    "numbered-section-directive-checklist",
                    f"{section_number}번 번호 답에 환자 지시가 {directive_total}문장입니다. 문단을 나눠 생활수칙을 이어 쓰지 말고 가장 중요한 행동 {maximum_section_directives}개 이하만 남기세요.",
                )
            if report_total > maximum_section_reports:
                error(
                    "numbered-section-clinical-report-checklist",
                    f"{section_number}번 번호 답에 묻습니다·봅니다류 진료 보고가 {report_total}문장입니다. 같은 질문과 진찰을 되풀이하지 말고 핵심 {maximum_section_reports}문장 이하로 줄이세요.",
                )
            if intake_total > maximum_section_intake:
                error(
                    "numbered-section-intake-checklist",
                    f"{section_number}번 번호 답에 문진·자료 요청 문장이 {intake_total}개입니다. 환자에게 요구할 정보는 한 문장에 핵심 두 항목까지만 남기고 나머지는 원장의 판단과 이유로 바꾸세요.",
                )
            if patient_request_total > maximum_section_requests:
                error(
                    "numbered-section-patient-request-checklist",
                    f"{section_number}번 번호 답에 환자에게 묻거나 시키는 문장이 {patient_request_total}개입니다. 번호 하나는 숙제 목록이 아니라 결론 하나와 이유 하나를 설명해야 합니다.",
                )
            if referral_total > maximum_section_referrals:
                error(
                    "numbered-section-referral-repeat",
                    f"{section_number}번 번호 답에서 병원·응급실·검사 행동을 {referral_total}번 되풀이합니다. 가장 위험한 증상과 해야 할 행동을 한 번만 직접 말하세요.",
                )
            if len(action_families) > maximum_section_action_families:
                error(
                    "numbered-section-scope-sprawl",
                    f"{section_number}번 번호 답에 {', '.join(sorted(action_families))}가 함께 들어갔습니다. 번호 소제목의 결론과 직접 연결되는 행동 종류 {maximum_section_action_families}개 이하만 남기고 다른 소주제는 삭제하세요.",
                )
            for sentence in section_sentences:
                question_cues = len(QUESTION_CUE.findall(sentence)) if INTAKE_SENTENCE.search(sentence) else 0
                if question_cues > maximum_intake_question_cues:
                    error(
                        "stacked-intake-items",
                        f"{section_number}번 번호 답의 한 문진 문장에 질문 항목이 {question_cues}개 들어갔습니다. 핵심 두 항목 이하만 남기세요. 감지 문장: {sentence}",
                    )
                record_cues = len(RECORD_CUE.findall(sentence))
                if record_cues > maximum_record_cues and (
                    DIRECTIVE_SENTENCE_ENDING.search(sentence) or INTAKE_SENTENCE.search(sentence)
                ):
                    error(
                        "record-keeping-checklist",
                        f"날짜·시간·개수·달력·사진·봉투를 한꺼번에 준비시키지 마세요. 기록이나 지참이 꼭 필요하면 한 가지만 요청하세요. 감지 문장: {sentence}",
                    )

        closing_intake = sum(bool(INTAKE_SENTENCE.search(sentence)) for sentence in closing_sentences)
        closing_clinical = sum(
            bool(PHYSICAL_EXAM_SENTENCE.search(sentence) or NAMED_TREATMENT_SENTENCE.search(sentence))
            for sentence in closing_sentences
        )
        core_has_referral = any(EXTERNAL_REFERRAL_SENTENCE.search(sentence) for sentence in core_section_sentences)
        closing_referral = sum(bool(EXTERNAL_REFERRAL_SENTENCE.search(sentence)) for sentence in closing_sentences)
        if closing_intake:
            closing_recap_count += closing_intake
            error(
                "closing-intake-recap",
                "마무리에서 앞서 물은 시각·동작·복용 정보를 다시 요구하지 마세요. 새 문진 없이 가장 중요한 판단과 진료 안내만 남기세요.",
            )
        if closing_clinical:
            closing_recap_count += closing_clinical
            error(
                "closing-clinical-recap",
                "마무리에서 누르는 진찰·동작 검사·치료를 다시 설명하지 마세요. 해당 행동은 번호 답에서 한 번만 씁니다.",
            )
        if core_has_referral and closing_referral:
            closing_recap_count += closing_referral
            error(
                "closing-referral-recap",
                "본문에서 이미 병원 검사나 응급실 행동을 말했습니다. 마무리에서 같은 경고 목록을 다시 복창하지 마세요.",
            )

        core_lines = [
            line
            for line in prose_lines[numbered_indexes[0] + 1 : closing_heading_index]
            if re.search(r"[.!?]", line)
        ]
        core_sentences = [sentence for line in core_lines for sentence in prose_sentences(line)]
        for beat_name, beat_pattern in REPEATED_CLINICAL_BEATS:
            matched_sentences = [
                sentence
                for sentence in core_sentences
                if beat_pattern.search(sentence) and CLINICAL_BEAT_ACTION.search(sentence)
            ]
            if len(matched_sentences) > 1:
                repeated_clinical_beat_count += 1
                error(
                    "repeated-clinical-beat",
                    f"{beat_name}이 진료 행동으로 {len(matched_sentences)}번 나옵니다. 같은 질문·누르는 진찰·동작 관찰은 글 전체에서 한 번만 쓰고 뒤에서는 이유나 판단만 말하세요.",
                )

    formal_run = 0
    longest_formal_run = 0
    for sentence in sentences:
        if re.search(r"(?:습니다|합니다|입니다|됩니다)\.?$", sentence):
            formal_run += 1
            longest_formal_run = max(longest_formal_run, formal_run)
        else:
            formal_run = 0
    if longest_formal_run >= 6:
        error("formal-ending-run", f"격식 종결이 {longest_formal_run}문장 연속입니다. 금손 말투의 호흡 변화가 필요합니다.")

    return {
        "status": "fail" if issues else "pass",
        "metrics": {
            "profileId": profile_id,
            "nonWhitespaceChars": len(compact),
            "firstPersonSignals": first_person,
            "conversationalEndings": conversational,
            "candidTransitions": transitions,
            "concreteDailyScenes": concrete_scene_sentences,
            "concreteMentions": concrete_mentions,
            "abstractTerms": abstract,
            "possibilityPhrases": possibility_phrases,
            "clinicalProcessPredicates": clinical_process_predicates,
            "priorityTransitions": priority_transitions,
            "binaryContrastTransitions": binary_contrast_transitions,
            "distinctTreatmentNames": sorted(treatment_names),
            "longestFormalEndingRun": longest_formal_run,
            "longestSentenceNonWhitespaceCharacters": longest_sentence_characters,
            "maximumCommasInSentence": maximum_commas_in_sentence,
            "longestParagraphSentences": longest_paragraph_sentences,
            "maximumDirectiveSentencesInParagraph": maximum_directives_in_paragraph,
            "maximumClinicalReportSentencesInParagraph": maximum_reports_in_paragraph,
            "answerPreviewSentences": answer_preview_sentences,
            "answerPreviewCommas": answer_preview_commas,
            "numberedSectionMetrics": section_metrics,
            "postNumberedHeadingCount": post_numbered_heading_count,
            "closingParagraphCount": closing_paragraph_count,
            "closingSentenceCount": closing_sentence_count,
            "closingRecapCount": closing_recap_count,
            "repeatedClinicalBeatCount": repeated_clinical_beat_count,
            "naturalSpeechPatternErrors": len(
                [
                    item
                    for item in issues
                    if item["code"]
                    in {
                        "translated-indirect-safety-command",
                        "reader-homework-imperative",
                        "poetic-abstract-payoff",
                        "poetic-body-signal",
                        "abstract-self-management",
                        "over-softened-medical-guidance",
                        "blog-meta-framing",
                        "lesson-afterglow-ending",
                        "literary-body-location",
                        "abstract-gait-description",
                        "abstract-editorial-predicate",
                        "symmetric-caveat-chain",
                        "generic-individual-difference-reset",
                        "possibility-ending-overuse",
                        "repeated-clinical-predicate",
                        "treatment-catalogue",
                        "priority-transition-overuse",
                        "binary-contrast-overuse",
                        "opening-hook-greeting-order",
                        "parallel-because-hook-template",
                        "abstract-symptom-ranking-transition",
                        "stacked-symptom-summary-question",
                        "over-softened-conclusion",
                        "vague-clinic-state-action",
                        "abstract-clinical-sequencing",
                        "vague-deictic-clinic-action",
                        "abstract-body-agency",
                        "abstract-lifestyle-wrapper",
                        "soft-vague-closing",
                        "vague-symptom-wrapper",
                        "abstract-recap-wrapper",
                        "literary-clinical-metaphor",
                        "reportlike-clinical-wrapper",
                        "overpacked-sentence-length",
                        "overpacked-sentence-commas",
                        "abstract-slogan-summary",
                        "answer-preview-checklist",
                        "post-numbered-heading-count",
                        "closing-paragraph-overflow",
                        "numbered-section-paragraph-overflow",
                        "numbered-section-sentence-overflow",
                        "numbered-section-paragraph-sentence-overflow",
                        "numbered-section-directive-checklist",
                        "numbered-section-clinical-report-checklist",
                        "numbered-section-intake-checklist",
                        "numbered-section-patient-request-checklist",
                        "numbered-section-referral-repeat",
                        "numbered-section-scope-sprawl",
                        "stacked-intake-items",
                        "record-keeping-checklist",
                        "closing-sentence-overflow",
                        "closing-checklist-sentence",
                        "abstract-closing-heading",
                        "abstract-closing-slogan",
                        "soft-optional-closing",
                        "closing-intake-recap",
                        "closing-clinical-recap",
                        "closing-referral-recap",
                        "repeated-clinical-beat",
                    }
                ]
            ),
            "errors": len(issues),
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        fragment = args.input.read_text(encoding="utf-8")
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"말투 검수 입력을 읽지 못했습니다: {exc}")
        return 2
    result = validate(fragment, profile)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        for issue in result["issues"]:
            print(f"[ERROR] {issue['code']}: {issue['detail']}")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
