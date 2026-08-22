#!/usr/bin/env python3
"""Validate a Goldhand Clinic blog title before drafting."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = SKILL_DIR / "references" / "clinic-facts.md"
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "topic-idea-library.json"
DEFAULT_WRITING_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"

FORBIDDEN = {
    "daily-post": re.compile(r"일상글|소소하루"),
    "specialist": re.compile(r"(?:전문의|통증\s*전문|소아\s*전문|갑상선\s*전문|다이어트\s*전문)"),
    "superlative": re.compile(r"(?:지역\s*1위|광주\s*1위|전국\s*1위|유일|최고|최상|가장\s*잘|무조건|완치|100\s*%)"),
    "unsupported-metric": re.compile(r"(?:누적\s*환자|누적\s*추나|재방문율|소개율|만족도|후기\s*수)"),
    "wrong-obesity-credential": re.compile(r"한방\s*비만\s*치료\s*인증\s*전문\s*한의사"),
    "wrong-ministry-credential": re.compile(r"보건복지부\s*인증\s*(?:약침\s*치료|골타\s*요법|한의원)"),
    "reference-business-leak": re.compile(
        r"(?:위석\s*부부\s*한의원|위석\s*원장|박경화|송정동|광산구|광주송정역|영광통|송정농협)"
    ),
    "reference-metric-leak": re.compile(
        r"(?:29\s*,?\s*000\s*명|2\s*만\s*9\s*천\s*명|2\s*만\s*5\s*천\s*명|70\s*%\s*(?:소개|지인))"
    ),
}
EMOTICON = re.compile(r"(?:\^\^|ㅎㅎ|ㅠㅠ|ㅜㅜ|♥|❤|♡|#[0-9A-Za-z가-힣_]+)")
EMOJI = re.compile("[\U0001F1E6-\U0001FAFF\u2600-\u27BF]")
NUMBERED_PROMISE = re.compile(r"(?P<count>\d+)\s*(?:가지|단계|기준|이유|방법|원칙|포인트)")
NUMERIC_CLAIM = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:년차|년|개월|일|시간|분|회|명|건|%|퍼센트)")
FAMILY_ID = "two-or-three-reader-concern-hooks-solution-preview-info"


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\u200b", "").strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", normalize(value))


def add(issues: list[dict[str, str]], severity: str, code: str, detail: str) -> None:
    issues.append({"severity": severity, "code": code, "detail": detail})


def validate_title(
    title: str,
    keyword: str,
    *,
    evidence: str = "",
    answer_count: int | None = None,
    library: dict[str, object] | None = None,
    idea_reference_id: str = "",
    pattern_id: str = "",
    editorial_close: bool = False,
    writing_intelligence: dict[str, object] | None = None,
    reference_master_id: str = "",
    title_mechanism_id: str = "",
) -> dict[str, object]:
    title = normalize(title)
    keyword = normalize(keyword)
    issues: list[dict[str, str]] = []
    selected_idea: dict[str, object] | None = None

    if not title:
        add(issues, "error", "title-empty", "제목이 비어 있습니다.")
    if not keyword:
        add(issues, "error", "keyword-empty", "메인키워드가 비어 있습니다.")

    keyword_count = title.count(keyword) if keyword else 0
    if keyword_count != 1:
        add(issues, "error", "title-keyword-count", f"정확 메인키워드 {keyword_count}회; 1회가 필요합니다.")
    elif len(compact(title[: title.find(keyword)])) > 8:
        add(issues, "warning", "keyword-not-early", "메인키워드를 제목 앞부분으로 옮길 수 있는지 확인하세요.")

    length = len(compact(title))
    if length > 50:
        add(issues, "error", "title-too-long", f"공백 제외 {length}자; 50자를 넘으면 발행할 수 없습니다.")
    elif length > 40:
        add(issues, "warning", "title-long", f"공백 제외 {length}자; 40자 이내로 압축을 권장합니다.")
    elif length < 22:
        add(issues, "warning", "title-short", f"공백 제외 {length}자; 22~40자를 권장합니다.")

    for code, pattern in FORBIDDEN.items():
        match = pattern.search(title)
        if match:
            add(issues, "error", code, f"금지된 제목 표현: {match.group(0)}")
    for code, pattern in (("emoticon", EMOTICON), ("emoji", EMOJI)):
        match = pattern.search(title)
        if match:
            add(issues, "error", code, f"장식 문자를 제거하세요: {match.group(0)}")

    promises = [int(match.group("count")) for match in NUMBERED_PROMISE.finditer(title)]
    if promises:
        if answer_count is None:
            add(issues, "error", "answer-count-required", "숫자 약속이 있는 제목은 --answer-count로 실제 답 개수를 확인해야 합니다.")
        elif any(count != answer_count for count in promises):
            add(issues, "error", "answer-count-mismatch", f"제목 약속 {promises}와 실제 답 {answer_count}개가 다릅니다.")

    selected_mechanism: dict[str, object] | None = None
    if editorial_close or reference_master_id or title_mechanism_id:
        if not reference_master_id:
            add(
                issues,
                "error",
                "reference-master-id-required",
                "편집 레퍼런스의 제목 심리를 확인하려면 --reference-master-id가 필요합니다.",
            )
        if not title_mechanism_id:
            add(
                issues,
                "error",
                "title-mechanism-id-required",
                "제목이 선택한 레퍼런스의 어떤 설득 장치를 옮겼는지 --title-mechanism-id로 표시해야 합니다.",
            )
        profiles = writing_intelligence.get("profiles", {}) if isinstance(writing_intelligence, dict) else {}
        profile = profiles.get(reference_master_id) if isinstance(profiles, dict) else None
        if reference_master_id and not isinstance(profile, dict):
            add(
                issues,
                "error",
                "reference-master-id-unknown",
                f"편집 판단 프로필에 없는 레퍼런스입니다: {reference_master_id}",
            )
        elif isinstance(profile, dict):
            mechanism = profile.get("titleMechanism")
            if not isinstance(mechanism, dict):
                add(issues, "error", "title-mechanism-profile-missing", "선택한 레퍼런스에 제목 심리 프로필이 없습니다.")
            else:
                selected_mechanism = mechanism
                allowed = mechanism.get("allowedIds", [])
                allowed_ids = [str(value) for value in allowed] if isinstance(allowed, list) else []
                if title_mechanism_id and title_mechanism_id not in allowed_ids:
                    add(
                        issues,
                        "error",
                        "title-mechanism-mismatch",
                        f"{reference_master_id}에서 허용한 제목 장치는 {allowed_ids}이며 입력값은 {title_mechanism_id}입니다.",
                    )

    evidence_compact = compact(evidence)
    for match in NUMERIC_CLAIM.finditer(title):
        claim = match.group(0)
        if compact(claim) not in evidence_compact:
            add(issues, "error", "unsupported-title-number", f"내장 사실에서 확인되지 않은 수치: {claim}")

    if idea_reference_id or pattern_id:
        if not idea_reference_id or not pattern_id:
            add(
                issues,
                "error",
                "idea-reference-incomplete",
                "주제 참고 글 ID와 제목 패턴 ID를 함께 지정해야 합니다.",
            )
        elif not isinstance(library, dict):
            add(issues, "error", "idea-library-missing", "주제 아이디어 라이브러리를 읽지 못했습니다.")
        else:
            articles = library.get("articles", [])
            if isinstance(articles, list):
                selected_idea = next(
                    (
                        item
                        for item in articles
                        if isinstance(item, dict) and str(item.get("id", "")) == idea_reference_id
                    ),
                    None,
                )
            if selected_idea is None:
                add(issues, "error", "idea-reference-unknown", f"등록되지 않은 주제 참고 글: {idea_reference_id}")
            else:
                if selected_idea.get("referenceFamilyId") != FAMILY_ID:
                    add(issues, "error", "idea-reference-family", "허용된 독자 고민 2~3개·해결 방향 예고형 참고 글이 아닙니다.")
                if selected_idea.get("sourceContentType") != "정보전달형":
                    add(issues, "error", "idea-reference-type", "정보전달형 참고 글만 사용할 수 있습니다.")
                if selected_idea.get("minimumReaderHookCount") != 2 or selected_idea.get("maximumReaderHookCount") != 3:
                    add(issues, "error", "idea-reference-hook-count", "도입 독자 고민을 2~3개 허용하는 참고 글만 사용할 수 있습니다.")
                if selected_idea.get("requiresSolutionPreviewBeforeBody") is not True:
                    add(issues, "error", "idea-reference-solution-preview", "본문 전 해결 방향 예고가 확인된 참고 글만 사용할 수 있습니다.")
                if selected_idea.get("sourceFactsBlocked") is not True:
                    add(issues, "error", "idea-facts-not-blocked", "원문 사실 차단이 확인되지 않은 참고 글입니다.")
                expected_pattern = str(selected_idea.get("titlePatternId", ""))
                if pattern_id != expected_pattern:
                    add(
                        issues,
                        "error",
                        "title-pattern-mismatch",
                        f"선택한 참고 글의 제목 패턴은 {expected_pattern}이며 입력값은 {pattern_id}입니다.",
                    )

    errors = sum(item["severity"] == "error" for item in issues)
    warnings = sum(item["severity"] == "warning" for item in issues)
    return {
        "status": "fail" if errors else "warning" if warnings else "pass",
        "metrics": {
            "editorialClose": editorial_close,
            "nonWhitespaceChars": length,
            "keywordCount": keyword_count,
            "answerPromises": promises,
            "referenceMasterId": reference_master_id,
            "titleMechanismId": title_mechanism_id,
            "titleMechanismPsychology": str(selected_mechanism.get("readerPsychology", "")) if selected_mechanism else "",
            "ideaReferenceId": idea_reference_id,
            "titlePatternId": pattern_id,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--answer-count", type=int)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--writing-intelligence", type=Path, default=DEFAULT_WRITING_INTELLIGENCE)
    parser.add_argument("--idea-reference-id", default="")
    parser.add_argument("--pattern-id", default="")
    parser.add_argument("--reference-master-id", default="")
    parser.add_argument("--title-mechanism-id", default="")
    parser.add_argument(
        "--editorial-close",
        action="store_true",
        help="레퍼런스의 제목 말투와 정보 전개를 밀착 재구성하는 모드입니다.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        evidence = args.evidence.read_text(encoding="utf-8") if args.evidence.exists() else ""
        library = json.loads(args.library.read_text(encoding="utf-8")) if args.library.exists() else None
        writing_intelligence = (
            json.loads(args.writing_intelligence.read_text(encoding="utf-8"))
            if args.writing_intelligence.exists()
            else None
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"근거 또는 주제 라이브러리를 읽지 못했습니다: {exc}", file=sys.stderr)
        return 2
    result = validate_title(
        args.title,
        args.keyword,
        evidence=evidence,
        answer_count=args.answer_count,
        library=library,
        idea_reference_id=args.idea_reference_id.strip(),
        pattern_id=args.pattern_id.strip(),
        editorial_close=args.editorial_close,
        writing_intelligence=writing_intelligence,
        reference_master_id=args.reference_master_id.strip(),
        title_mechanism_id=args.title_mechanism_id.strip(),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"공백 제외 제목 길이: {result['metrics']['nonWhitespaceChars']}")
        for issue in result["issues"]:
            print(f"[{issue['severity'].upper()}] {issue['code']}: {issue['detail']}")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
