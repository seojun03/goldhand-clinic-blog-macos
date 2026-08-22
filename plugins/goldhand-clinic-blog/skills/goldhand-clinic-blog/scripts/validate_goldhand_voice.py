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

    for value in forbidden.get("emoticons", []):
        if value and str(value) in text:
            error("emoticon", f"금지된 이모티콘·장식: {value}")
    emoji = re.search("[\U0001F1E6-\U0001FAFF\u2600-\u27BF]", text)
    if emoji:
        error("emoji", f"이모지는 사용할 수 없습니다: {emoji.group(0)}")
    for phrase in forbidden.get("aiTemplatePhrases", []):
        if phrase and str(phrase) in text:
            error("ai-template-phrase", f"AI 템플릿 표현을 실제 장면과 원장 말투로 다시 쓰세요: {phrase}")
    for rule in forbidden.get("aiRegisterPatterns", []):
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
