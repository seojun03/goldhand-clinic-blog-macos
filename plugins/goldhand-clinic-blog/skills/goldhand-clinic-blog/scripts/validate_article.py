#!/usr/bin/env python3
"""Strict publication validator for Goldhand Clinic Naver articles."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = SKILL_DIR / "assets" / "media-library.json"
DEFAULT_EVIDENCE = SKILL_DIR / "references" / "clinic-facts.md"
DEFAULT_WRITING_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"
FINAL_WRITING_VOICE_REVIEW_ID = "writing-voice-final-rehear-v1"
ALLOWED_TYPES = {"정보전달형"}
EXCLUDED_ROLES = {"cta", "contact", "map", "source", "caption", "media", "proof"}
MOBILE_EXEMPT_REFERENCE_ROLES = {
    "reader-question",
    "greeting-authority",
    "section-heading",
    "credential-proof",
    "evidence-media",
    "divider",
    "contact",
    "clinic-hours-heading",
    "clinic-hours",
}
EXACT_GREETING = "안녕하세요, 금손한의원 박준희 원장입니다."
FIXED_CONTACT = (
    "금손한의원",
    "전남광주통합특별시 서구 유림로98번길 3, 2층",
    "동천파출소",
    "동천동 행정복지센터",
    "062-515-7582",
    "09:30~20:00",
    "09:30~18:00",
    "09:00~13:00",
)
FORBIDDEN_FIXED_CONTACT = ("공휴일", "설·추석", "카카오톡", "@금손한의원", "네이버 예약")

FORBIDDEN = {
    "daily-post": re.compile(r"일상글"),
    "specialist": re.compile(r"(?:전문의|통증\s*전문|소아\s*전문|갑상선\s*전문|다이어트\s*전문)"),
    "guarantee": re.compile(r"(?:완치|무조건|반드시\s*(?:낫|호전)|100\s*%|효과를\s*보장|확실히\s*(?:낫|좋아))"),
    "superlative": re.compile(r"(?:지역\s*1위|광주\s*1위|전국\s*1위|유일한|최고의|최상급|가장\s*잘하는)"),
    "unsupported-metric": re.compile(r"(?:누적\s*환자|누적\s*추나|차트\s*번호.{0,12}환자|재방문율|소개율|만족도|후기\s*수)"),
    "wrong-obesity-credential": re.compile(r"한방\s*비만\s*치료\s*인증\s*전문\s*한의사"),
    "wrong-ministry-credential": re.compile(r"보건복지부\s*인증\s*(?:약침\s*치료|골타\s*요법|한의원)"),
    "remote-treatment": re.compile(r"카카오톡.{0,25}(?:비대면\s*(?:진료|치료|처방)|원격\s*(?:진료|치료))"),
    "standalone-365": re.compile(r"365일\s*진료"),
    "old-address": re.compile(r"광주광역시\s*서구\s*유림로98번길"),
    "aggressive-cta": re.compile(r"(?:지금\s*바로|당장|늦기\s*전에|서둘러|꼭\s*내원|반드시\s*내원|예약을\s*서두)"),
    "topic-source-business-leak": re.compile(
        r"(?:설명한의원|김병규\s*(?:대표)?원장|린다이어트|엑소웨이브|미주안|미주란|라디쥬|"
        r"보폐고\s*엔오|스파인\s*MT|쿨쎄라|라라샷|퓨라셀|라인약침)"
    ),
}
TOPIC_SOURCE_URL = re.compile(
    r"https?://(?:m\.|blog\.)?naver\.com/(?:PostView\.naver\?[^\"'<>\s]*blogId=beomeo_sm|beomeo_sm(?:/|\b))",
    re.I,
)
EDITORIAL_MASTER_ID = re.compile(r"(?P<prefix>BM|WP)(?P<post_id>\d{12})$")
EDITORIAL_REFERENCE_URL = re.compile(
    r"https?://(?:m\.|blog\.)?naver\.com/(?P<blog_id>beomeo_sm|wi-parkclinic)/(?P<post_id>\d{12})(?:[/?#].*)?$",
    re.I,
)
PRODUCTION_RESIDUE = {
    "placeholder": re.compile(r"(?:\{\{[^{}]+\}\}|\[\s*(?:사진|이미지|입력|작성|추가)[^\]]*\]|<\s*(?:입력|작성|추가)[^>]*>|\bT(?:ODO|BD)\b)", re.I),
    "internal-label": re.compile(r"\b(?:CHECK\s*\d+|FACT[-_]\d+|TEMP[-_]\d+|titlePromise|readerDecision|safeAuto|requiresReview)\b", re.I),
    "source-list": re.compile(r"(?m)^\s*(?:#{1,6}\s*)?(?:출처|참고문헌|References?)\s*:?")
}
EMOTICON = re.compile(r"(?:\^\^|ㅎㅎ|ㅠㅠ|ㅜㅜ|♥|❤|♡|#[0-9A-Za-z가-힣_]+)")
EMOJI = re.compile("[\U0001F1E6-\U0001FAFF\u2600-\u27BF]")
CASE_OR_EFFECT = re.compile(
    r"(?:환자.{0,24}(?:말했|호전|개선|나아|좋아|경과)|"
    r"내원.{0,24}(?:후|경과|호전|개선)|치료\s*(?:후|경과)|호전|개선|나아졌|좋아졌|효과를\s*(?:봤|보았)|회복\s*과정)"
)
DISCLAIMER = re.compile(r"(?:개인차|사람마다\s*다|상태에\s*따라\s*다|진찰이\s*필요|의료진.{0,12}상의)")
NUMBERED_PROMISE = re.compile(r"(?P<count>\d+)\s*(?:가지|단계|기준|이유|방법|원칙|포인트)")
NUMBERED_HEADING = re.compile(r"^\s*(?P<count>\d+)\s*[.．)\]]")
NUMERIC_CLAIM = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|퍼센트|명|건|회|년차|년|개월|주|일|시간|분)")
SOLUTION_PREVIEW_CUE = re.compile(r"(?:오늘은|이\s*글에서는|이\s*글에서|아래에서는|지금부터).{0,90}(?:정리|설명|말씀|살펴|알려)", re.S)
SOLUTION_PAYOFF_CUE = re.compile(r"(?:구분|기준|판단|확인|이해|순서|놓치|살펴)")
READING_COMMITMENT_TEXT = re.compile(r"(?:읽|집중|살펴)", re.S)
HOOK_TOKEN_STOP = {"광주", "한의원", "금손한의원", "어떻게", "무엇", "정말", "경우", "있을까요", "할까요"}
STACKED_ABSTRACT_HOOK = re.compile(r"(?:피로|기분|불편|증상).{0,28}(?:이어지|겹치|반복되)나요\?")
FORBIDDEN_REAL_PHOTO_DESCRIPTOR = re.compile(r"(?:로고|logo|건물\s*외관|건물\s*외부|환제|제품\s*포장|장비|원내\s*공간)", re.I)
REAL_PHOTO_SLOTS = {"before-credential", "closing-trust"}
TRUST_PHOTO_SLOT = "closing-credential-trust"
ALLOWED_CLOSING_TRUST_SCENES = {
    "director-agreement-pose",
    "director-community-pose",
    "credential-detail",
}


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", value)
    value = re.sub(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]", " ", value)
    return value


def visible_text(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"</?(?:p|div|section|header|footer|article|h[1-6]|blockquote|li|tr|figure|figcaption|br)\b[^>]*>", "\n\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return normalize(html.unescape(value))


def compact(value: str) -> str:
    return re.sub(r"\s+", "", visible_text(value))


def article_fragment(raw: str) -> str:
    matches = re.findall(r"<article\b[^>]*>.*?</article>", raw, flags=re.I | re.S)
    if len(matches) != 1:
        raise ValueError("입력에는 <article> 하나만 있어야 합니다.")
    return matches[0]


def attr_values(fragment: str, attribute: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(attribute)}\s*=\s*(['\"])(.*?)\1", re.I | re.S)
    return [html.unescape(match.group(2)).strip() for match in pattern.finditer(fragment)]


def without_editorial_reference_source(fragment: str) -> str:
    """Hide the one allowed Beomeo URL attribute before leak scanning."""

    return re.sub(
        r"(\bdata-editorial-reference-source\s*=\s*['\"])(.*?)(['\"])",
        r"\1EDITORIAL_REFERENCE_SOURCE\3",
        fragment,
        flags=re.I | re.S,
    )


def editorial_source_checks(
    article: str,
    issues: list[dict[str, object]],
    writing_intelligence: dict[str, object] | None = None,
) -> dict[str, str]:
    article_tag_match = re.search(r"<article\b[^>]*>", article, re.I | re.S)
    article_tag = article_tag_match.group(0) if article_tag_match else ""
    master_values = attr_values(article_tag, "data-editorial-master-id")
    source_values = attr_values(article_tag, "data-editorial-reference-source")
    role_values = attr_values(article_tag, "data-editorial-source-role")
    status_values = attr_values(article_tag, "data-editorial-profile-status")
    voice_review_values = attr_values(article_tag, "data-writing-voice-review")
    voice_status_values = attr_values(article_tag, "data-writing-voice-status")
    for attribute, tag_values in (
        ("data-editorial-master-id", master_values),
        ("data-editorial-reference-source", source_values),
        ("data-editorial-source-role", role_values),
        ("data-editorial-profile-status", status_values),
        ("data-writing-voice-review", voice_review_values),
        ("data-writing-voice-status", voice_status_values),
    ):
        if len(attr_values(article, attribute)) != len(tag_values):
            add(
                issues,
                "error",
                "editorial-attribute-outside-article-tag",
                f"{attribute}는 <article> 시작 태그에만 선언해야 합니다.",
            )

    if len(master_values) != 1:
        add(
            issues,
            "error",
            "editorial-master-id-count",
            f"data-editorial-master-id가 {len(master_values)}개입니다. 정확히 1개가 필요합니다.",
        )
    if len(source_values) != 1:
        add(
            issues,
            "error",
            "editorial-reference-source-count",
            f"data-editorial-reference-source가 {len(source_values)}개입니다. 정확히 1개가 필요합니다.",
        )

    master_id = master_values[0] if len(master_values) == 1 else ""
    source_url = source_values[0] if len(source_values) == 1 else ""
    master_match = EDITORIAL_MASTER_ID.fullmatch(master_id)
    source_match = EDITORIAL_REFERENCE_URL.fullmatch(source_url)
    if master_id and master_match is None:
        add(issues, "error", "editorial-master-id-invalid", f"등록 형식이 아닌 편집 마스터 ID입니다: {master_id}")
    if source_url and source_match is None:
        add(
            issues,
            "error",
            "editorial-reference-source-invalid",
            "편집 레퍼런스는 등록된 범어 또는 Wipark 원문의 정확한 공개 URL이어야 합니다.",
        )
    if master_match and source_match and master_match.group("post_id") != source_match.group("post_id"):
        add(
            issues,
            "error",
            "editorial-reference-source-mismatch",
            f"편집 마스터 {master_id}와 원문 URL의 글 번호가 다릅니다.",
        )
    if master_match and source_match:
        expected_prefix = "BM" if source_match.group("blog_id") == "beomeo_sm" else "WP"
        if master_match.group("prefix") != expected_prefix:
            add(
                issues,
                "error",
                "editorial-reference-source-prefix-mismatch",
                f"편집 마스터 {master_id}와 원문 블로그가 다릅니다.",
            )
    if len(role_values) > 1:
        add(
            issues,
            "error",
            "editorial-source-role-count",
            "data-editorial-source-role은 최대 1개만 선언할 수 있습니다.",
        )
    elif role_values and role_values[0] not in {
        "title-tone-content-sequence-only",
        "topic-reader-concerns-general-information-sequence-only",
        "editorial-reasoning-content-flow-and-expression-principles",
    }:
        add(
            issues,
            "error",
            "editorial-source-role-invalid",
            "편집 레퍼런스 역할은 레퍼런스 편집 판단과 금손 사실 재구성 역할이어야 합니다.",
        )
    if status_values != ["ready"]:
        add(
            issues,
            "error",
            "editorial-profile-status-not-ready",
            "원문 본문 감사와 프로필 검증을 마친 data-editorial-profile-status=ready 글만 발행할 수 있습니다.",
        )
    profile_id = ""
    title_mechanism_id = ""
    closing_mechanism_id = ""
    intelligence_id = ""
    final_voice_review_id = ""
    final_voice_status = ""
    if source_match and source_match.group("blog_id") == "wi-parkclinic":
        profiles = writing_intelligence.get("profiles", {}) if isinstance(writing_intelligence, dict) else {}
        matching_profiles = [
            (str(key), value)
            for key, value in profiles.items()
            if isinstance(value, dict) and str(value.get("sourceUrl", "")) == source_url
        ] if isinstance(profiles, dict) else []
        if len(matching_profiles) != 1:
            add(
                issues,
                "error",
                "reference-writing-profile-source-unknown",
                "선택한 Wipark 원문과 일치하는 편집 판단 프로필이 없습니다.",
            )
        else:
            expected_profile_id, learning_profile = matching_profiles[0]
            profile_values = attr_values(article_tag, "data-reference-writing-profile")
            intelligence_values = attr_values(article_tag, "data-reference-writing-intelligence")
            title_values = attr_values(article_tag, "data-title-mechanism")
            closing_values = attr_values(article_tag, "data-closing-mechanism")
            if profile_values != [expected_profile_id]:
                add(
                    issues,
                    "error",
                    "reference-writing-profile-mismatch",
                    f"data-reference-writing-profile은 {expected_profile_id}여야 합니다.",
                )
            else:
                profile_id = expected_profile_id
            expected_intelligence = str(writing_intelligence.get("id", "")) if isinstance(writing_intelligence, dict) else ""
            if intelligence_values != [expected_intelligence]:
                add(
                    issues,
                    "error",
                    "reference-writing-intelligence-mismatch",
                    f"data-reference-writing-intelligence는 {expected_intelligence}여야 합니다.",
                )
            else:
                intelligence_id = expected_intelligence
            title_contract = learning_profile.get("titleMechanism", {})
            allowed_titles = title_contract.get("allowedIds", []) if isinstance(title_contract, dict) else []
            if len(title_values) != 1 or title_values[0] not in allowed_titles:
                add(
                    issues,
                    "error",
                    "article-title-mechanism-mismatch",
                    f"선택한 프로필의 제목 장치는 {allowed_titles} 중 하나여야 합니다.",
                )
            else:
                title_mechanism_id = title_values[0]
            closing_contract = learning_profile.get("closingMechanism", {})
            allowed_closings = closing_contract.get("allowedIds", []) if isinstance(closing_contract, dict) else []
            if len(closing_values) != 1 or closing_values[0] not in allowed_closings:
                add(
                    issues,
                    "error",
                    "article-closing-mechanism-mismatch",
                    f"선택한 프로필의 마무리 장치는 {allowed_closings} 중 하나여야 합니다.",
                )
            else:
                closing_mechanism_id = closing_values[0]
        if voice_review_values != [FINAL_WRITING_VOICE_REVIEW_ID]:
            add(
                issues,
                "error",
                "writing-voice-review-missing",
                f"최종 글쓰기 검수는 data-writing-voice-review={FINAL_WRITING_VOICE_REVIEW_ID}여야 합니다.",
            )
        else:
            final_voice_review_id = voice_review_values[0]
        if voice_status_values != ["pass"]:
            add(
                issues,
                "error",
                "writing-voice-status-not-pass",
                "writing-voice 최종 재청취를 통과한 data-writing-voice-status=pass가 필요합니다.",
            )
        else:
            final_voice_status = voice_status_values[0]
    return {
        "editorialMasterId": master_id,
        "editorialReferenceSource": source_url,
        "editorialProfileStatus": status_values[0] if len(status_values) == 1 else "",
        "referenceWritingProfileId": profile_id,
        "referenceWritingIntelligenceId": intelligence_id,
        "titleMechanismId": title_mechanism_id,
        "closingMechanismId": closing_mechanism_id,
        "finalWritingVoiceReviewId": final_voice_review_id,
        "finalWritingVoiceStatus": final_voice_status,
    }


def remove_tag_blocks(value: str, tags: tuple[str, ...]) -> str:
    result = value
    for tag in tags:
        pattern = re.compile(rf"<{tag}\b[^>]*>.*?</{tag}>", re.I | re.S)
        previous = None
        while result != previous:
            previous = result
            result = pattern.sub(" ", result)
    return result


def remove_excluded_roles(value: str) -> str:
    result = value
    roles = "|".join(sorted(EXCLUDED_ROLES))
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-goldhand-role\s*=\s*['\"](?:{roles})['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    previous = None
    while result != previous:
        previous = result
        result = pattern.sub(" ", result)
    result = remove_tag_blocks(result, ("header", "figure", "figcaption", "table"))
    result = re.sub(r"<h1\b[^>]*>.*?</h1>", " ", result, flags=re.I | re.S)
    return result


def paragraphs(value: str) -> list[str]:
    text = re.sub(r"</?(?:p|div|section|header|footer|h[1-6]|blockquote|li|br)\b[^>]*>", "\n\n", value, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return [re.sub(r"\s+", " ", visible_text(part)).strip() for part in re.split(r"\n\s*\n+", text) if compact(part)]


def role_blocks(article: str, role: str) -> list[str]:
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-goldhand-role\s*=\s*['\"]{re.escape(role)}['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    return [match.group(0) for match in pattern.finditer(article)]


def reference_role_blocks(article: str, roles: tuple[str, ...]) -> list[str]:
    alternatives = "|".join(re.escape(role) for role in roles)
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"](?:{alternatives})['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    return [match.group(0) for match in pattern.finditer(article)]


def reference_role_matches(article: str, roles: tuple[str, ...]) -> list[re.Match[str]]:
    alternatives = "|".join(re.escape(role) for role in roles)
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"](?:{alternatives})['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    return list(pattern.finditer(article))


def explanatory_heading_candidates(article: str) -> list[re.Match[str]]:
    """Find body headings even when one or both contract markers were removed."""
    patterns = (
        re.compile(
            r"<(?P<tag>[a-z][\w:-]*)\b"
            r"(?=[^>]*(?:\bdata-reference-role\s*=\s*['\"]section-heading['\"]"
            r"|\bdata-naver-native-component\s*=\s*['\"]subheading['\"]))"
            r"[^>]*>.*?</(?P=tag)>",
            re.I | re.S,
        ),
        re.compile(r"<(?P<tag>h[1-6])\b[^>]*>.*?</(?P=tag)>", re.I | re.S),
    )
    matches_by_span: dict[tuple[int, int], re.Match[str]] = {}
    for pattern in patterns:
        for match in pattern.finditer(article):
            matches_by_span[(match.start(), match.end())] = match
    return [matches_by_span[span] for span in sorted(matches_by_span)]


def has_explanatory_heading_contract(match: re.Match[str]) -> bool:
    opening = re.match(r"<[a-z][\w:-]*\b[^>]*>", match.group(0), flags=re.I | re.S)
    opening_tag = opening.group(0) if opening else ""
    return (
        attr_values(opening_tag, "data-reference-role") == ["section-heading"]
        and attr_values(opening_tag, "data-naver-native-component") == ["subheading"]
    )


def divider_following_element(
    article: str,
    divider: re.Match[str],
    region_end: int,
) -> re.Match[str] | None:
    """Return the first substantive element after a body divider."""
    skippable = re.compile(
        r"(?:\s+|<!--.*?-->|</?(?:section|div)\b[^>]*>"
        r"|<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>)*",
        re.I | re.S,
    )
    prefix = skippable.match(article, divider.end(), region_end)
    start = prefix.end() if prefix else divider.end()
    element = re.compile(
        r"<(?P<tag>[a-z][\w:-]*)\b[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    return element.match(article, start, region_end)


def visual_paragraph_heading_candidates(article: str) -> list[re.Match[str]]:
    """Find markerless p elements that still use the contract's heading typography."""
    candidates = list(
        re.finditer(
            r"<p\b[^>]*>.*?</p>",
            article,
            flags=re.I | re.S,
        )
    )
    result: list[re.Match[str]] = []
    for match in candidates:
        opening = re.match(r"<p\b[^>]*>", match.group(0), flags=re.I | re.S)
        style_values = attr_values(opening.group(0) if opening else "", "style")
        style = style_values[0].lower() if len(style_values) == 1 else ""
        size_values = [
            float(value)
            for value in re.findall(r"font-size\s*:\s*(\d+(?:\.\d+)?)px\b", style)
        ]
        weight_values = [
            float(value)
            for value in re.findall(r"font-weight\s*:\s*(\d+(?:\.\d+)?)\b", style)
        ]
        large_text = any(value >= 18.0 for value in size_values)
        heading_weight = bool(
            any(value >= 600.0 for value in weight_values)
            or re.search(r"font-weight\s*:\s*(?:bold|bolder)\b", style)
        )
        if large_text and heading_weight:
            result.append(match)
    return result


def credential_table_matches(article: str) -> list[re.Match[str]]:
    pattern = re.compile(
        r"<table\b(?=[^>]*\bdata-native-table-purpose\s*=\s*['\"]credential['\"])[^>]*>.*?</table>",
        re.I | re.S,
    )
    return list(pattern.finditer(article))


def first_information_body_marker(article: str) -> re.Match[str] | None:
    pattern = re.compile(
        r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>"
        r"|<[a-z][\w:-]*\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]section-heading['\"])[^>]*>",
        re.I | re.S,
    )
    return pattern.search(article)


def contains_only_preview_gaps(fragment: str) -> bool:
    remainder = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    remainder = re.sub(
        r"<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>",
        "",
        remainder,
        flags=re.I | re.S,
    )
    remainder = re.sub(r"</?(?:section|div)\b[^>]*>", "", remainder, flags=re.I | re.S)
    return not remainder.strip()


def contains_only_preview_gaps_and_before_credential_photo(fragment: str) -> bool:
    """Allow one marked trust photo between the solution preview and credential table."""
    figures = list(
        re.finditer(
            r"<figure\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])(?=[^>]*\bdata-real-photo-slot\s*=\s*['\"]before-credential['\"])[^>]*>.*?</figure>",
            fragment,
            flags=re.I | re.S,
        )
    )
    if len(figures) != 1:
        return False
    remainder = fragment[:figures[0].start()] + fragment[figures[0].end():]
    return contains_only_preview_gaps(remainder)


def credential_placement_issues(article: str) -> list[dict[str, str]]:
    """Return the standalone credential placement gate for builders and validators."""

    issues: list[dict[str, str]] = []
    solution_matches = reference_role_matches(article, ("solution-preview",))
    credential_matches = credential_table_matches(article)
    if len(credential_matches) != 1:
        add(
            issues,
            "error",
            "credential-table-count",
            f"금손한의원 소개 credential 표는 정확히 1개여야 합니다. 현재 {len(credential_matches)}개입니다.",
        )
        return issues

    credential_match = credential_matches[0]
    if len(solution_matches) == 1:
        solution_match = solution_matches[0]
        if credential_match.start() < solution_match.end():
            add(
                issues,
                "error",
                "credential-before-solution-preview",
                "금손한의원 소개 credential 표는 도입과 해결 방향 예고가 모두 끝난 뒤에 배치해야 합니다.",
            )
        elif not (
            contains_only_preview_gaps(article[solution_match.end():credential_match.start()])
            or contains_only_preview_gaps_and_before_credential_photo(
                article[solution_match.end():credential_match.start()]
            )
        ):
            add(
                issues,
                "error",
                "credential-not-immediately-after-solution-preview",
                "해결 방향 예고와 금손한의원 소개 credential 표 사이에는 빈 preview-gap 또는 before-credential 실제 사진 1장만 둘 수 있습니다.",
            )

    late_intro_roles = [
        match
        for match in reference_role_matches(article, ("reader-question", "greeting-authority"))
        if match.end() > credential_match.start()
    ]
    if late_intro_roles:
        add(
            issues,
            "error",
            "intro-role-after-credential",
            "모든 reader-question과 greeting-authority는 금손한의원 소개 credential 표보다 먼저 끝나야 합니다.",
        )

    first_body_marker = first_information_body_marker(article)
    if first_body_marker is None:
        add(
            issues,
            "error",
            "first-information-body-marker-missing",
            "금손한의원 소개 credential 표 뒤에 첫 정보 본문 divider 또는 section-heading이 필요합니다.",
        )
    elif credential_match.end() > first_body_marker.start():
        add(
            issues,
            "error",
            "credential-after-first-body-marker",
            "금손한의원 소개 credential 표는 첫 정보 본문 divider·section-heading보다 앞에 배치해야 합니다.",
        )
    elif not contains_only_preview_gaps(article[credential_match.end():first_body_marker.start()]):
        add(
            issues,
            "error",
            "credential-not-immediately-before-first-body-marker",
            "금손한의원 소개 credential 표와 첫 정보 본문 divider·section-heading 사이에는 빈 preview-gap 외의 본문·이미지·표를 둘 수 없습니다.",
        )
    return issues


def meaningful_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", normalize(value).lower())
        if token not in HOOK_TOKEN_STOP
    }


def remove_mobile_exempt_blocks(article: str) -> str:
    alternatives = "|".join(sorted(MOBILE_EXEMPT_REFERENCE_ROLES))
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"](?:{alternatives})['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    result = article
    previous = None
    while result != previous:
        previous = result
        result = pattern.sub(" ", result)
    return remove_tag_blocks(result, ("header", "footer", "figure", "figcaption", "table", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"))


def mobile_group_checks(article: str, issues: list[dict[str, object]]) -> dict[str, int]:
    fragment = remove_mobile_exempt_blocks(article)
    paragraph_pattern = re.compile(r"<p\b(?P<attrs>[^>]*)>(?P<body>.*?)</p>", re.I | re.S)
    matches = list(paragraph_pattern.finditer(fragment))
    group_count = 0
    max_line_chars = 0
    line_count_total = 0
    for index, match in enumerate(matches, start=1):
        attrs = match.group("attrs")
        attrs_lower = attrs.lower()
        body = match.group("body")
        if "data-preview-gap" in attrs_lower or "data-naver-gap" in attrs_lower:
            continue
        if not compact(body):
            continue
        if not re.search(r"\bdata-mobile-group\s*=\s*['\"]true['\"]", attrs, re.I):
            add(
                issues,
                "error",
                "mobile-group-marker-missing",
                f"일반 본문 문단 {index}에 data-mobile-group=\"true\"가 없습니다.",
            )
            continue
        group_count += 1
        lines = [
            re.sub(r"\s+", " ", visible_text(part)).strip()
            for part in re.split(r"<br\b[^>]*>", body, flags=re.I)
        ]
        lines = [line for line in lines if compact(line)]
        line_count_total += len(lines)
        if len(lines) not in {2, 3}:
            add(
                issues,
                "error",
                "mobile-group-line-count",
                f"모바일 문단 {group_count}은 {len(lines)}줄입니다. 2줄 또는 3줄이어야 합니다.",
            )
        for line_index, line in enumerate(lines, start=1):
            chars = len(compact(line))
            max_line_chars = max(max_line_chars, chars)
            if chars < 4 or chars > 24:
                add(
                    issues,
                    "error",
                    "mobile-line-length",
                    f"모바일 문단 {group_count}의 {line_index}번째 줄이 공백 제외 {chars}자입니다. 4~24자로 씁니다.",
                )
        following = fragment[match.end():]
        if not re.match(
            r"\s*<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>",
            following,
            re.I | re.S,
        ):
            add(
                issues,
                "error",
                "mobile-group-gap-missing",
                f"모바일 문단 {group_count} 뒤에 data-preview-gap 빈 줄이 없습니다.",
            )
    if group_count == 0:
        add(issues, "error", "mobile-group-missing", "모바일 2~3줄 일반 본문 묶음이 없습니다.")
    return {
        "mobileGroupCount": group_count,
        "mobileVisualLineCount": line_count_total,
        "maxMobileLineChars": max_line_chars,
    }


def add(issues: list[dict[str, object]], severity: str, code: str, detail: str, paragraph: int | None = None) -> None:
    item: dict[str, object] = {"severity": severity, "code": code, "detail": detail}
    if paragraph is not None:
        item["paragraph"] = paragraph
    issues.append(item)


def load_media_library(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = data.get("assets", []) if isinstance(data, dict) else []
    return {
        str(asset.get("id")): asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("id")
    }


def previous_completed_entry(
    state: dict[str, object], *, current_title: str = ""
) -> dict[str, object] | None:
    entries = state.get("entries", []) if isinstance(state, dict) else []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if current_title and str(entry.get("title", "")).strip() == current_title.strip():
            continue
        return entry
    return None


def recent_media_policy(
    state: dict[str, object], *, current_title: str = ""
) -> tuple[set[str], set[str], list[set[str]], list[set[str]]]:
    ids: set[str] = set()
    hashes: set[str] = set()
    id_sets: list[set[str]] = []
    hash_sets: list[set[str]] = []
    entry = previous_completed_entry(state, current_title=current_title)
    for entry in [entry] if entry is not None else []:
        entry_ids = {str(value).strip() for value in entry.get("realMediaIds", []) if str(value).strip()}
        entry_hashes = {str(value).strip() for value in entry.get("realMediaHashes", []) if str(value).strip()}
        ids.update(entry_ids)
        hashes.update(entry_hashes)
        if entry_ids:
            id_sets.append(entry_ids)
        if entry_hashes:
            hash_sets.append(entry_hashes)
    return ids, hashes, id_sets, hash_sets


def recent_trust_media_policy(
    state: dict[str, object], *, current_title: str = ""
) -> tuple[set[str], set[str]]:
    """Return only the immediately previous article's separate trust media."""

    entry = previous_completed_entry(state, current_title=current_title)
    if entry is None:
        return set(), set()
    ids = {str(value).strip() for value in entry.get("trustMediaIds", []) if str(value).strip()}
    hashes = {str(value).strip() for value in entry.get("trustMediaHashes", []) if str(value).strip()}
    return ids, hashes


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundled_asset_path(asset: dict[str, object]) -> Path | None:
    raw = str(asset.get("bundledPath", "")).strip()
    if not raw:
        return None
    candidate = (SKILL_DIR / raw).resolve()
    try:
        candidate.relative_to(SKILL_DIR.resolve())
    except ValueError:
        return None
    return candidate


def containing_figure(article: str, image_tag: str) -> re.Match[str] | None:
    return next(
        (
            match
            for match in re.finditer(r"<figure\b[^>]*>.*?</figure>", article, flags=re.I | re.S)
            if image_tag in match.group(0)
        ),
        None,
    )


def real_figure_checks(
    article: str,
    figure_match: re.Match[str] | None,
    image_index: int,
    issues: list[dict[str, object]],
    *,
    asset: dict[str, object] | None = None,
    image_tag: str = "",
) -> None:
    if figure_match is None:
        add(issues, "error", "real-photo-figure-missing", f"실제 사진 {image_index}가 figure 안에 있지 않습니다.")
        return
    figure = figure_match.group(0)
    opening_match = re.match(r"<figure\b[^>]*>", figure, flags=re.I | re.S)
    opening = opening_match.group(0) if opening_match else ""
    slot_values = attr_values(opening, "data-real-photo-slot")
    slot = slot_values[0] if len(slot_values) == 1 else ""
    if attr_values(opening, "data-real-photo") != ["true"]:
        add(issues, "error", "real-photo-figure-marker-missing", f"실제 사진 {image_index} figure에 data-real-photo=true가 필요합니다.")
    if slot not in REAL_PHOTO_SLOTS:
        add(
            issues,
            "error",
            "real-photo-slot-invalid",
            f"실제 사진 {image_index}는 before-credential 또는 closing-trust 슬롯이어야 합니다.",
        )
    closing_gallery = slot == "closing-trust"
    expected_placement = "closing-clinical-gallery" if closing_gallery else "after-related-paragraph"
    if attr_values(opening, "data-image-placement") != [expected_placement]:
        detail = (
            f"실제 사진 {image_index}는 글마무리 실제 진료 사진 구간에 배치합니다."
            if closing_gallery
            else f"실제 사진 {image_index}는 관련 문단 바로 뒤에 배치합니다."
        )
        add(issues, "error", "real-photo-placement-marker", detail)
    if not re.search(r"\btext-align\s*:\s*center", opening, flags=re.I):
        add(issues, "error", "real-photo-not-centered", f"실제 사진 {image_index} figure가 중앙 정렬이 아닙니다.")
    anchors_values = attr_values(opening, "data-image-anchor")
    anchors = [item.strip() for item in anchors_values[0].split("|") if item.strip()] if len(anchors_values) == 1 else []
    previous_text = ""
    if not closing_gallery and not anchors:
        add(issues, "error", "real-photo-anchor-missing", f"실제 사진 {image_index}에 관련 문단 핵심어가 없습니다.")
    elif not closing_gallery:
        prefix = article[:figure_match.start()]
        while True:
            before = prefix
            prefix = re.sub(
                r"\s*<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>(?:(?!</p>).)*</p>\s*$",
                "",
                prefix,
                flags=re.I | re.S,
            )
            prefix = re.sub(r"\s*</(?:section|div)>\s*$", "", prefix, flags=re.I | re.S)
            if prefix == before:
                break
        prior = list(re.finditer(r"<p\b(?P<attrs>[^>]*)>(?P<body>.*?)</p>", prefix, flags=re.I | re.S))
        previous = prior[-1] if prior and not prefix[prior[-1].end():].strip() else None
        if previous is None or not re.search(r"\bdata-mobile-group\s*=\s*['\"]true['\"]", previous.group("attrs"), flags=re.I):
            add(issues, "error", "real-photo-related-paragraph-missing", f"실제 사진 {image_index} 바로 앞에 관련 모바일 문단이 없습니다.")
        else:
            previous_text = visible_text(previous.group("body"))
            if not any(compact(anchor) in compact(previous_text) for anchor in anchors):
                add(issues, "error", "real-photo-anchor-mismatch", f"실제 사진 {image_index}의 핵심어가 바로 앞 문단에 없습니다.")

    if asset is not None:
        placement_terms = [str(value).strip() for value in asset.get("placementTerms", []) if str(value).strip()]
        approved_alt = str(asset.get("approvedAlt", "")).strip()
        if not approved_alt or (not closing_gallery and not placement_terms):
            add(
                issues,
                "error",
                "real-photo-context-metadata-missing",
                (
                    f"실제 사진 {image_index} 자산에 approvedAlt가 필요합니다."
                    if closing_gallery
                    else f"실제 사진 {image_index} 자산에 승인 placementTerms와 approvedAlt가 필요합니다."
                ),
            )
        elif not closing_gallery:
            approved_anchors = [
                anchor
                for anchor in anchors
                if any(compact(anchor) == compact(term) for term in placement_terms)
            ]
            if not approved_anchors:
                add(
                    issues,
                    "error",
                    "real-photo-anchor-not-approved",
                    f"실제 사진 {image_index}의 anchor는 사진 장면을 특정하는 승인 핵심어여야 합니다.",
                )
            elif not any(compact(anchor) in compact(previous_text) for anchor in approved_anchors):
                add(
                    issues,
                    "error",
                    "real-photo-context-mismatch",
                    f"실제 사진 {image_index}의 바로 앞 문단이 승인 장면({', '.join(approved_anchors)})을 실제로 설명하지 않습니다.",
                )
        if approved_alt:
            alt_values = attr_values(image_tag, "alt")
            if alt_values != [approved_alt]:
                add(
                    issues,
                    "error",
                    "real-photo-alt-mismatch",
                    f"실제 사진 {image_index}의 alt는 승인 장면 설명과 정확히 같아야 합니다.",
                )
    if re.search(r"<figcaption\b", figure, flags=re.I):
        add(issues, "error", "visible-image-caption-forbidden", f"실제 사진 {image_index} 아래에 보이는 캡션을 쓰면 안 됩니다.")


def trust_figure_checks(
    article: str,
    figure_match: re.Match[str] | None,
    image_index: int,
    issues: list[dict[str, object]],
    *,
    asset: dict[str, object] | None = None,
    image_tag: str = "",
) -> None:
    """Validate the separate closing credential/director trust photo."""

    if figure_match is None:
        add(issues, "error", "trust-photo-figure-missing", f"마무리 신뢰 사진 {image_index}가 figure 안에 있지 않습니다.")
        return
    figure = figure_match.group(0)
    opening_match = re.match(r"<figure\b[^>]*>", figure, flags=re.I | re.S)
    opening = opening_match.group(0) if opening_match else ""
    if attr_values(opening, "data-trust-photo") != ["true"]:
        add(issues, "error", "trust-photo-figure-marker-missing", f"마무리 신뢰 사진 {image_index} figure에 data-trust-photo=true가 필요합니다.")
    if attr_values(opening, "data-trust-photo-slot") != [TRUST_PHOTO_SLOT]:
        add(issues, "error", "trust-photo-slot-invalid", f"마무리 신뢰 사진 {image_index}는 {TRUST_PHOTO_SLOT} 슬롯이어야 합니다.")
    if attr_values(opening, "data-image-placement") != ["after-related-paragraph"]:
        add(issues, "error", "trust-photo-placement-marker", f"마무리 신뢰 사진 {image_index}는 관련 신뢰 문단 바로 뒤에 배치합니다.")
    if not re.search(r"\btext-align\s*:\s*center", opening, flags=re.I):
        add(issues, "error", "trust-photo-not-centered", f"마무리 신뢰 사진 {image_index} figure가 중앙 정렬이 아닙니다.")

    anchor_values = attr_values(opening, "data-image-anchor")
    anchors = [item.strip() for item in anchor_values[0].split("|") if item.strip()] if len(anchor_values) == 1 else []
    if not anchors:
        add(issues, "error", "trust-photo-anchor-missing", f"마무리 신뢰 사진 {image_index}에 장면 핵심어가 없습니다.")

    prefix = article[:figure_match.start()]
    while True:
        before = prefix
        prefix = re.sub(
            r"\s*<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>(?:(?!</p>).)*</p>\s*$",
            "",
            prefix,
            flags=re.I | re.S,
        )
        prefix = re.sub(r"\s*</(?:section|div)>\s*$", "", prefix, flags=re.I | re.S)
        if prefix == before:
            break
    prior = list(re.finditer(r"<p\b(?P<attrs>[^>]*)>(?P<body>.*?)</p>", prefix, flags=re.I | re.S))
    previous = prior[-1] if prior and not prefix[prior[-1].end():].strip() else None
    previous_text = ""
    if previous is None:
        add(issues, "error", "trust-photo-context-missing", f"마무리 신뢰 사진 {image_index} 바로 앞에 신뢰 맥락 문단이 없습니다.")
    else:
        attrs = previous.group("attrs")
        previous_text = visible_text(previous.group("body"))
        if not re.search(r"\bdata-reference-role\s*=\s*['\"]credential-trust-context['\"]", attrs, flags=re.I):
            add(issues, "error", "trust-photo-context-role-missing", f"마무리 신뢰 사진 {image_index} 앞 문단의 역할 표시가 없습니다.")
        if not re.search(r"\bdata-goldhand-role\s*=\s*['\"]proof['\"]", attrs, flags=re.I):
            add(issues, "error", "trust-photo-context-proof-missing", f"마무리 신뢰 사진 {image_index} 앞 문단은 proof로 표시해야 합니다.")
        if not re.search(r"\bdata-mobile-group\s*=\s*['\"]true['\"]", attrs, flags=re.I):
            add(issues, "error", "trust-photo-context-mobile-group", f"마무리 신뢰 사진 {image_index} 앞 문단은 모바일 문단이어야 합니다.")
        if anchors and not any(compact(anchor) in compact(previous_text) for anchor in anchors):
            add(issues, "error", "trust-photo-anchor-mismatch", f"마무리 신뢰 사진 {image_index}의 핵심어가 바로 앞 신뢰 문단에 없습니다.")

    if asset is not None:
        placement_terms = [str(value).strip() for value in asset.get("closingTrustPlacementTerms", []) if str(value).strip()]
        approved_alt = str(asset.get("closingTrustApprovedAlt", "")).strip()
        context_text = str(asset.get("closingTrustContextText", "")).strip()
        if not placement_terms or not approved_alt or not context_text:
            add(issues, "error", "trust-photo-context-metadata-missing", f"마무리 신뢰 사진 {image_index} 자산의 승인 문맥·alt 메타데이터가 비어 있습니다.")
        else:
            if not any(any(compact(anchor) == compact(term) for term in placement_terms) for anchor in anchors):
                add(issues, "error", "trust-photo-anchor-not-approved", f"마무리 신뢰 사진 {image_index}의 anchor가 승인 장면 핵심어와 다릅니다.")
            if compact(previous_text) != compact(context_text):
                add(issues, "error", "trust-photo-context-mismatch", f"마무리 신뢰 사진 {image_index} 앞 문단은 검수된 장면 설명과 정확히 같아야 합니다.")
            if attr_values(image_tag, "alt") != [approved_alt]:
                add(issues, "error", "trust-photo-alt-mismatch", f"마무리 신뢰 사진 {image_index}의 alt는 승인 장면 설명과 정확히 같아야 합니다.")
    if re.search(r"<figcaption\b", figure, flags=re.I):
        add(issues, "error", "visible-image-caption-forbidden", f"마무리 신뢰 사진 {image_index} 아래에 보이는 캡션을 쓰면 안 됩니다.")


def trust_layout_checks(article: str, issues: list[dict[str, object]]) -> None:
    """Keep one trust image after the close and as the final image before hours."""

    figures = list(
        re.finditer(
            r"<figure\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"])[^>]*>.*?</figure>",
            article,
            flags=re.I | re.S,
        )
    )
    contexts = reference_role_matches(article, ("credential-trust-context",))
    neutral = reference_role_matches(article, ("neutral-close",))
    clinic = reference_role_matches(article, ("clinic-hours-heading",))
    if len(figures) != 1 or len(contexts) != 1:
        return
    figure = figures[0]
    context = contexts[0]
    if len(neutral) == 1 and len(clinic) == 1:
        if not (neutral[0].end() <= context.start() < context.end() <= figure.start() < figure.end() <= clinic[0].start()):
            add(issues, "error", "trust-photo-position", "마무리 신뢰 사진은 neutral-close 뒤, 진료시간 안내 앞의 마지막 이미지로 둡니다.")
        bridge = article[context.end():figure.start()]
        if not contains_only_preview_gaps(bridge):
            add(issues, "error", "trust-photo-context-not-adjacent", "신뢰 맥락 문단과 마무리 신뢰 사진 사이에는 preview-gap만 둘 수 있습니다.")
        tail = article[figure.end():clinic[0].start()]
        tail = re.sub(r"<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>", "", tail, flags=re.I | re.S)
        tail = re.sub(r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>", "", tail, flags=re.I | re.S)
        tail = re.sub(r"<!--.*?-->|</?(?:section|div)\b[^>]*>", "", tail, flags=re.I | re.S)
        if tail.strip() or re.search(r"<img\b", article[figure.end():clinic[0].start()], flags=re.I):
            add(issues, "error", "trust-photo-not-last-image", "마무리 신뢰 사진 뒤에는 진료시간 안내 전까지 다른 본문·표·이미지를 둘 수 없습니다.")


def media_layout_checks(article: str, issues: list[dict[str, object]]) -> None:
    """Enforce the two real-photo layouts and keep GPT images in the first two body sections."""
    figure_matches = list(re.finditer(r"<figure\b[^>]*>.*?</figure>", article, flags=re.I | re.S))
    real_figures = [
        match
        for match in figure_matches
        if re.search(r"<img\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>", match.group(0), flags=re.I | re.S)
    ]
    generated_figures = [
        match
        for match in figure_matches
        if re.search(r"<img\b(?=[^>]*\bdata-media-provider\s*=\s*['\"]gpt-image['\"])[^>]*>", match.group(0), flags=re.I | re.S)
    ]
    solution_matches = reference_role_matches(article, ("solution-preview",))
    credential_matches = credential_table_matches(article)
    neutral_matches = reference_role_matches(article, ("neutral-close",))
    clinic_heading_matches = reference_role_matches(article, ("clinic-hours-heading",))
    trust_context_matches = reference_role_matches(article, ("credential-trust-context",))
    section_heading_matches = explanatory_heading_candidates(article)

    if len(real_figures) == 1:
        opening = re.match(r"<figure\b[^>]*>", real_figures[0].group(0), flags=re.I | re.S)
        slot = attr_values(opening.group(0) if opening else "", "data-real-photo-slot")
        if slot != ["before-credential"]:
            add(
                issues,
                "error",
                "real-photo-layout-invalid",
                "실제 사진 1장 구성은 원장 소개표 바로 위 before-credential 슬롯만 허용합니다.",
            )
        elif len(solution_matches) == 1 and len(credential_matches) == 1:
            figure = real_figures[0]
            solution = solution_matches[0]
            credential = credential_matches[0]
            if not (solution.end() <= figure.start() < figure.end() <= credential.start()):
                add(
                    issues,
                    "error",
                    "real-photo-before-credential-position",
                    "before-credential 실제 사진은 해결 방향 예고가 끝난 뒤 원장 소개표 바로 위에 있어야 합니다.",
                )
            bridge = article[solution.end():credential.start()]
            if not contains_only_preview_gaps_and_before_credential_photo(bridge):
                add(
                    issues,
                    "error",
                    "real-photo-before-credential-not-adjacent",
                    "해결 방향 예고와 원장 소개표 사이에는 실제 사진 1장과 preview-gap만 둘 수 있습니다.",
                )
    elif len(real_figures) == 2:
        slots: list[str] = []
        for figure in real_figures:
            opening = re.match(r"<figure\b[^>]*>", figure.group(0), flags=re.I | re.S)
            values = attr_values(opening.group(0) if opening else "", "data-real-photo-slot")
            slots.append(values[0] if len(values) == 1 else "")
        if slots != ["closing-trust", "closing-trust"]:
            add(
                issues,
                "error",
                "real-photo-layout-invalid",
                "실제 사진 2장 구성은 글마무리 closing-trust 슬롯 두 장만 허용합니다.",
            )
        elif len(neutral_matches) == 1 and len(clinic_heading_matches) == 1:
            neutral = neutral_matches[0]
            clinic_heading = clinic_heading_matches[0]
            clinical_tail_end = trust_context_matches[0].start() if len(trust_context_matches) == 1 else clinic_heading.start()
            if not all(neutral.end() <= figure.start() < figure.end() <= clinical_tail_end for figure in real_figures):
                add(
                    issues,
                    "error",
                    "real-photo-closing-trust-position",
                    "closing-trust 실제 진료 사진 두 장은 neutral-close 뒤, 별도 마무리 신뢰 사진 바로 앞에 있어야 합니다.",
                )
            closing_tail = article[real_figures[0].start():clinical_tail_end]
            closing_tail = re.sub(
                r"<figure\b(?=[^>]*\bdata-real-photo-slot\s*=\s*['\"]closing-trust['\"])[^>]*>.*?</figure>",
                "",
                closing_tail,
                flags=re.I | re.S,
            )
            closing_tail = re.sub(
                r"<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>",
                "",
                closing_tail,
                flags=re.I | re.S,
            )
            closing_tail = re.sub(
                r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>",
                "",
                closing_tail,
                flags=re.I | re.S,
            )
            closing_tail = re.sub(r"<!--.*?-->|</?(?:section|div)\b[^>]*>", "", closing_tail, flags=re.I | re.S)
            if closing_tail.strip():
                add(
                    issues,
                    "error",
                    "real-photo-closing-trust-not-adjacent",
                    "closing-trust 실제 진료 사진은 다른 본문·표 없이 별도 마무리 신뢰 구간 바로 앞에 둡니다.",
                )
    elif real_figures:
        add(
            issues,
            "error",
            "real-photo-layout-invalid",
            "실제 사진은 원장 소개표 위 1장 또는 글마무리 2장 중 한 구성만 허용합니다.",
        )

    early_start: int | None = None
    first_section_end: int | None = None
    early_end: int | None = None
    if len(credential_matches) == 1 and len(neutral_matches) == 1:
        credential = credential_matches[0]
        neutral = neutral_matches[0]
        body_dividers = list(
            re.finditer(
                r"<hr\b[^>]*>",
                article,
                flags=re.I | re.S,
            )
        )
        body_dividers = [
            match
            for match in body_dividers
            if credential.end() <= match.start() < neutral.start()
        ]
        paired_body_headings = [
            heading
            for divider in body_dividers
            if (heading := divider_following_element(article, divider, neutral.start())) is not None
        ]
        invalid_body_headings = [
            match
            for match in paired_body_headings
            if match.group("tag").lower() not in {"h2", "p"}
            or not has_explanatory_heading_contract(match)
        ]
        if len(paired_body_headings) != len(body_dividers):
            invalid_body_headings.append(body_dividers[len(paired_body_headings)])
        if invalid_body_headings:
            add(
                issues,
                "error",
                "section-heading-markers-invalid",
                "각 설명 구분선 바로 뒤의 h2 또는 p 소제목에는 data-reference-role=section-heading과 data-naver-native-component=subheading을 함께 표시해야 합니다.",
            )
        valid_body_headings = [
            match
            for match in paired_body_headings
            if match.group("tag").lower() in {"h2", "p"}
            and has_explanatory_heading_contract(match)
        ]
        if not valid_body_headings:
            add(
                issues,
                "error",
                "body-section-heading-missing",
                "원장 소개표 뒤 설명 본문에서 두 표식이 모두 있는 소제목을 최소 1개 찾아야 합니다.",
            )
        paired_spans = {(match.start(), match.end()) for match in paired_body_headings}
        recognizable_body_headings = [
            match
            for match in section_heading_matches
            if credential.end() <= match.start() < neutral.start()
        ]
        recognizable_body_headings.extend(
            match
            for match in visual_paragraph_heading_candidates(article)
            if credential.end() <= match.start() < neutral.start()
        )
        recognizable_by_span = {
            (match.start(), match.end()): match
            for match in recognizable_body_headings
        }
        unpaired_headings = [
            match
            for span, match in recognizable_by_span.items()
            if span not in paired_spans
        ]
        if unpaired_headings:
            add(
                issues,
                "error",
                "section-heading-divider-pair-invalid",
                "설명 소제목은 본문 구분선 바로 뒤에 있어야 합니다.",
            )
        boundary_by_span = {
            (match.start(), match.end()): match
            for match in paired_body_headings
        }
        boundary_by_span.update(recognizable_by_span)
        body_headings = [boundary_by_span[span] for span in sorted(boundary_by_span)]
        if body_headings:
            early_start = body_headings[0].end()
            first_section_end = body_headings[1].start() if len(body_headings) >= 2 else neutral.start()
            early_end = body_headings[2].start() if len(body_headings) >= 3 else neutral.start()

    for index, figure in enumerate(generated_figures, start=1):
        opening = re.match(r"<figure\b[^>]*>", figure.group(0), flags=re.I | re.S)
        if attr_values(opening.group(0) if opening else "", "data-image-zone") != ["early-explanatory-body"]:
            add(
                issues,
                "error",
                "generated-image-zone-missing",
                f"GPT 이미지 {index}는 data-image-zone=early-explanatory-body로 표시해야 합니다.",
            )
        if early_start is not None and early_end is not None and not (
            early_start <= figure.start() < figure.end() <= early_end
        ):
            add(
                issues,
                "error",
                "generated-image-outside-early-body",
                f"GPT 이미지 {index}는 원장 소개표 뒤 첫 두 개 설명 섹션 안에 배치해야 합니다.",
            )
    if (
        generated_figures
        and early_start is not None
        and first_section_end is not None
        and not any(early_start <= figure.start() < figure.end() <= first_section_end for figure in generated_figures)
    ):
        add(
            issues,
            "error",
            "generated-image-first-section-missing",
            "GPT 이미지 3~4장 가운데 최소 1장은 첫 번째 설명 섹션에 있어야 합니다.",
        )


def generated_figure_placement_checks(
    article: str,
    figure_match: re.Match[str] | None,
    image_index: int,
    issues: list[dict[str, object]],
) -> None:
    if figure_match is None:
        add(issues, "error", "generated-image-figure-missing", f"GPT 이미지 {image_index}가 figure 안에 있지 않습니다.")
        return

    figure = figure_match.group(0)
    opening = re.match(r"<figure\b[^>]*>", figure, flags=re.I | re.S)
    opening_tag = opening.group(0) if opening else ""
    if attr_values(opening_tag, "data-image-placement") != ["after-related-paragraph"]:
        add(
            issues,
            "error",
            "generated-image-placement-marker",
            f"GPT 이미지 {image_index}는 data-image-placement=after-related-paragraph로 표시해야 합니다.",
        )

    anchor_values = attr_values(opening_tag, "data-image-anchor")
    anchors = [value.strip() for value in anchor_values[0].split("|") if value.strip()] if len(anchor_values) == 1 else []
    if not anchors:
        add(
            issues,
            "error",
            "generated-image-anchor-missing",
            f"GPT 이미지 {image_index}에 관련 문단 핵심어 data-image-anchor가 없습니다.",
        )
        return

    prefix = article[:figure_match.start()]
    preview_gap = re.compile(
        r"\s*<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>(?:(?!</p>).)*</p>\s*$",
        re.I | re.S,
    )
    without_gap = preview_gap.sub("", prefix)
    paragraph_matches = list(
        re.finditer(r"<p\b(?P<attrs>[^>]*)>(?P<body>.*?)</p>", without_gap, flags=re.I | re.S)
    )
    previous = paragraph_matches[-1] if paragraph_matches and not without_gap[paragraph_matches[-1].end():].strip() else None
    if previous is None or not re.search(
        r"\bdata-mobile-group\s*=\s*['\"]true['\"]",
        previous.group("attrs") if previous else "",
        flags=re.I,
    ):
        add(
            issues,
            "error",
            "generated-image-related-paragraph-missing",
            f"GPT 이미지 {image_index} 바로 앞에 관련 모바일 설명 문단이 없습니다.",
        )
        return

    paragraph_text = compact(visible_text(previous.group("body")))
    if not any(compact(anchor) in paragraph_text for anchor in anchors):
        add(
            issues,
            "error",
            "generated-image-anchor-mismatch",
            f"GPT 이미지 {image_index}의 핵심어({', '.join(anchors)})가 바로 앞 문단에 없습니다.",
        )


def image_checks(
    article: str,
    issues: list[dict[str, object]],
    media_library: dict[str, dict[str, object]],
    *,
    require_generated: bool = False,
    require_real: bool = False,
    require_trust: bool = False,
) -> dict[str, object]:
    image_tags = re.findall(r"<img\b[^>]*>", article, flags=re.I | re.S)
    urls: set[str] = set()
    official = 0
    local = 0
    generated = 0
    real_photos = 0
    real_official = 0
    real_bundled = 0
    trust_photos = 0
    trust_official = 0
    trust_bundled = 0
    real_ids: set[str] = set()
    real_hashes: set[str] = set()
    trust_ids: set[str] = set()
    trust_hashes: set[str] = set()
    official_ids: set[str] = set()
    for index, tag in enumerate(image_tags, start=1):
        source = re.search(r"\bdata-reference-source-url\s*=\s*['\"](.*?)['\"]", tag, flags=re.I | re.S)
        local_path = re.search(r"\bdata-local-image\s*=\s*['\"](.*?)['\"]", tag, flags=re.I | re.S)
        provider = attr_values(tag, "data-media-provider")
        is_real = attr_values(tag, "data-real-photo") == ["true"]
        is_trust = attr_values(tag, "data-trust-photo") == ["true"]
        if is_real:
            real_photos += 1
        if is_trust:
            trust_photos += 1
        if is_real and is_trust:
            add(issues, "error", "photo-role-not-exclusive", f"이미지 {index}는 실제 진료 사진과 마무리 신뢰 사진을 동시에 표시할 수 없습니다.")
        if provider == ["gpt-image"]:
            generated += 1
            reference_urls = attr_values(tag, "data-generation-reference-url")
            if not local_path:
                add(issues, "error", "generated-image-local-path-missing", f"GPT 이미지 {index}의 로컬 생성본 경로가 없습니다.")
            else:
                local += 1
                path = Path(html.unescape(local_path.group(1))).expanduser()
                if not path.is_absolute() or not path.is_file():
                    add(issues, "error", "generated-image-file-missing", f"GPT 생성 이미지 파일을 읽을 수 없습니다: {path}")
            if attr_values(tag, "data-generation-reference-creator") != ["callilife"]:
                add(issues, "error", "generated-reference-creator-invalid", f"GPT 이미지 {index}의 레퍼런스 크리에이터가 callilife가 아닙니다.")
            if len(reference_urls) != 1 or not re.fullmatch(
                r"https://ogqmarket\.naver\.com/artworks/stockImage/detail\?artworkId=[0-9a-f]+",
                reference_urls[0] if reference_urls else "",
                flags=re.I,
            ):
                add(issues, "error", "generated-reference-url-invalid", f"GPT 이미지 {index}의 OGQ 레퍼런스 작품 링크가 정확하지 않습니다.")
            if attr_values(tag, "data-generation-owner-authorization") != ["user-confirmed"]:
                add(issues, "error", "generated-owner-authorization-missing", f"GPT 이미지 {index}에 사용자 소유 확인 표시가 없습니다.")
            if attr_values(tag, "data-generation-content-preservation") != ["medical-information-layout"]:
                add(
                    issues,
                    "error",
                    "generated-content-preservation-missing",
                    f"GPT 이미지 {index}에 의학 정보와 구도 보존 표시가 없습니다.",
                )
            variation_modes = attr_values(tag, "data-generation-variation-mode")
            allowed_variation_modes = {
                "person-identity-subtle-variation",
                "nonperson-style-subtle-variation",
            }
            if len(variation_modes) != 1 or variation_modes[0] not in allowed_variation_modes:
                add(
                    issues,
                    "error",
                    "generated-variation-mode-invalid",
                    f"GPT 이미지 {index}의 미세 변경 방식이 허용된 두 유형 중 하나가 아닙니다.",
                )
            if attr_values(tag, "data-generation-similarity-target"):
                add(
                    issues,
                    "error",
                    "generated-legacy-similarity-target",
                    f"GPT 이미지 {index}에 폐기된 유사도 수치 기준이 남아 있습니다.",
                )

            if is_real:
                add(issues, "error", "generated-image-marked-real", f"GPT 이미지 {index}를 실제 사진으로 표시할 수 없습니다.")
            if is_trust:
                add(issues, "error", "generated-image-marked-trust", f"GPT 이미지 {index}를 마무리 신뢰 사진으로 표시할 수 없습니다.")
            figure_match = containing_figure(article, tag)
            figure = figure_match.group(0) if figure_match else ""
            generated_figure_placement_checks(article, figure_match, index, issues)
            if re.search(r"<figcaption\b", figure, flags=re.I):
                add(issues, "error", "visible-image-caption-forbidden", f"GPT 이미지 {index} 아래에 보이는 캡션을 쓰면 안 됩니다.")
        elif source:
            official += 1
            figure_match = containing_figure(article, tag)
            if not is_real and not is_trust:
                add(issues, "error", "official-real-photo-marker-missing", f"공식 사진 {index}에 data-real-photo=true가 필요합니다.")
            if is_real:
                real_official += 1
            if is_trust:
                trust_official += 1
            if attr_values(tag, "data-media-origin") != ["goldhand-bundled-official-library"]:
                add(issues, "error", "official-photo-origin-invalid", f"공식 사진 {index}의 출처 표시가 잘못됐습니다.")
            url = html.unescape(source.group(1)).strip()
            if not url.startswith("https://"):
                add(issues, "error", "official-image-not-https", f"공식 이미지 {index}의 원본 URL이 HTTPS가 아닙니다.")
            if url in urls:
                add(issues, "error", "duplicate-image", f"같은 공식 이미지가 중복되었습니다: {url}")
            urls.add(url)
            if not re.search(r"\breferrerpolicy\s*=\s*['\"]no-referrer['\"]", tag, flags=re.I):
                add(issues, "error", "referrer-policy-missing", f"공식 이미지 {index}에 no-referrer가 없습니다.")
            media_id = re.search(r"\bdata-goldhand-media\s*=\s*['\"](.*?)['\"]", tag, flags=re.I)
            if media_id:
                asset_id = media_id.group(1)
                if asset_id in official_ids:
                    add(issues, "error", "duplicate-official-photo-id", f"같은 공식 사진 ID가 중복됐습니다: {asset_id}")
                official_ids.add(asset_id)
                asset = media_library.get(asset_id)
                bundle = bundled_asset_path(asset) if asset else None
                expected_hash = str(asset.get("sha256", "")) if asset else ""
                tag_hashes = attr_values(tag, "data-media-sha256")
                common_approval = bool(
                    asset
                    and asset.get("url") == url
                    and bundle is not None
                    and bundle.is_file()
                    and expected_hash
                    and len(tag_hashes) == 1
                    and tag_hashes[0] == expected_hash
                    and file_sha256(bundle) == expected_hash
                )
                if is_real:
                    if asset_id in real_ids:
                        add(issues, "error", "duplicate-real-photo-id", f"같은 실제 사진 ID가 중복됐습니다: {asset_id}")
                    real_ids.add(asset_id)
                    real_figure_checks(article, figure_match, index, issues, asset=asset, image_tag=tag)
                    descriptor = " ".join(
                        str(asset.get(field, ""))
                        for field in ("filename", "caption", "sceneType")
                    ) if asset else ""
                    person_scene_ok = bool(
                        asset
                        and asset.get("personInteraction") is True
                        and asset.get("directorVisible") is True
                        and str(asset.get("sceneType", "")).startswith("director-patient-")
                        and FORBIDDEN_REAL_PHOTO_DESCRIPTOR.search(descriptor) is None
                    )
                    if asset and not person_scene_ok:
                        add(
                            issues,
                            "error",
                            "nonperson-or-logo-real-photo-forbidden",
                            f"실제 사진 {asset_id}는 원장 치료·진찰·상담 장면이 아니거나 로고·사물·공간 사진입니다.",
                        )
                    if (
                        not common_approval
                        or not asset
                        or asset.get("safeAuto") is not True
                        or asset.get("requiresReview") is True
                        or not person_scene_ok
                    ):
                        add(issues, "error", "unapproved-official-image", f"안전 인덱스와 일치하지 않는 공식 이미지: {asset_id}")
                    else:
                        real_bundled += 1
                        real_hashes.add(expected_hash)
                elif is_trust:
                    if asset_id in trust_ids:
                        add(issues, "error", "duplicate-trust-photo-id", f"같은 마무리 신뢰 사진 ID가 중복됐습니다: {asset_id}")
                    trust_ids.add(asset_id)
                    trust_figure_checks(article, figure_match, index, issues, asset=asset, image_tag=tag)
                    trust_scene_ok = bool(
                        asset
                        and asset.get("closingTrustEligible") is True
                        and asset.get("closingTrustReviewed") is True
                        and asset.get("closingTrustRequiresReview") is False
                        and str(asset.get("closingTrustSceneType", "")) in ALLOWED_CLOSING_TRUST_SCENES
                        and (
                            asset.get("closingTrustDirectorVisible") is True
                            or asset.get("closingTrustDocumentVisible") is True
                        )
                    )
                    if not common_approval or not trust_scene_ok:
                        add(issues, "error", "unapproved-closing-trust-image", f"검수된 마무리 신뢰 인덱스와 일치하지 않는 공식 이미지: {asset_id}")
                    else:
                        trust_bundled += 1
                        trust_hashes.add(expected_hash)
            else:
                if is_real:
                    real_figure_checks(article, figure_match, index, issues, image_tag=tag)
                if is_trust:
                    trust_figure_checks(article, figure_match, index, issues, image_tag=tag)
                add(issues, "error", "official-image-id-missing", f"공식 이미지 {index}에 data-goldhand-media가 없습니다.")
        elif local_path:
            local += 1
            path = Path(html.unescape(local_path.group(1))).expanduser()
            if not path.is_absolute() or not path.is_file():
                add(issues, "error", "local-image-missing", f"사용자 이미지 경로를 읽을 수 없습니다: {path}")
            if is_real:
                real_figure_checks(article, containing_figure(article, tag), index, issues)
                add(issues, "error", "local-real-photo-forbidden", f"실제 금손 사진 {index}는 사용자 로컬 경로가 아니라 플러그인 내장 라이브러리에서 선택해야 합니다.")
            if is_trust:
                trust_figure_checks(article, containing_figure(article, tag), index, issues)
                add(issues, "error", "local-trust-photo-forbidden", f"마무리 신뢰 사진 {index}는 사용자 로컬 경로가 아니라 플러그인 내장 검수 라이브러리에서 선택해야 합니다.")
        else:
            add(issues, "error", "untracked-image", f"이미지 {index}에 공식 URL 또는 사용자 로컬 경로가 없습니다.")
    if real_photos > 2:
        add(issues, "error", "real-photo-count-maximum", f"실제 금손한의원 사진이 {real_photos}장입니다. 최대 2장입니다.")
    if require_real and not 1 <= real_photos <= 2:
        add(issues, "error", "real-photo-count", f"실제 금손한의원 사진이 {real_photos}장입니다. 1~2장이 필요합니다.")
    if trust_photos > 1:
        add(issues, "error", "trust-photo-count-maximum", f"마무리 신뢰 사진이 {trust_photos}장입니다. 정확히 1장만 사용합니다.")
    if require_trust and trust_photos != 1:
        add(issues, "error", "trust-photo-count", f"마무리 신뢰 사진이 {trust_photos}장입니다. 진료 사진과 별도로 정확히 1장이 필요합니다.")
    if require_generated and not 3 <= generated <= 4:
        add(issues, "error", "generated-image-count", f"callilife 레퍼런스로 만든 GPT 이미지가 {generated}장입니다. 3~4장이 필요합니다.")
    real_photo_slots: list[str] = []
    for figure_match in re.finditer(r"<figure\b[^>]*>.*?</figure>", article, flags=re.I | re.S):
        figure = figure_match.group(0)
        if not re.search(r"<img\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>", figure, flags=re.I | re.S):
            continue
        opening_match = re.match(r"<figure\b[^>]*>", figure, flags=re.I | re.S)
        slot_values = attr_values(opening_match.group(0) if opening_match else "", "data-real-photo-slot")
        real_photo_slots.append(slot_values[0] if len(slot_values) == 1 else "")
    return {
        "images": len(image_tags), "officialImages": official, "localImages": local,
        "generatedImages": generated, "realPhotos": real_photos,
        "realOfficialPhotos": real_official, "realBundledPhotos": real_bundled,
        "realPhotoSlots": real_photo_slots,
        "realMediaIds": sorted(real_ids), "realMediaHashes": sorted(real_hashes),
        "trustPhotos": trust_photos, "trustOfficialPhotos": trust_official,
        "trustBundledPhotos": trust_bundled,
        "trustMediaIds": sorted(trust_ids), "trustMediaHashes": sorted(trust_hashes),
    }


def validate_article(
    raw: str,
    title: str,
    keyword: str,
    *,
    min_chars: int = 1400,
    max_chars: int = 1800,
    media_library: dict[str, dict[str, object]] | None = None,
    evidence: str = "",
    editorial_close: bool = False,
    writing_intelligence: dict[str, object] | None = None,
    recent_media_ids: set[str] | None = None,
    recent_media_hashes: set[str] | None = None,
    recent_trust_media_ids: set[str] | None = None,
    recent_trust_media_hashes: set[str] | None = None,
) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    raw = normalize(raw)
    title = normalize(title).strip()
    keyword = normalize(keyword).strip()
    try:
        article = article_fragment(raw)
    except ValueError as exc:
        add(issues, "error", "article-count", str(exc))
        article = raw

    if re.search(r"<figcaption\b", article, flags=re.I):
        add(issues, "error", "visible-image-caption-forbidden", "이미지 아래에 보이는 figcaption은 사용할 수 없습니다.")

    type_match = re.search(r"<article\b[^>]*\bdata-goldhand-type\s*=\s*['\"](.*?)['\"]", article, flags=re.I | re.S)
    article_type = html.unescape(type_match.group(1)).strip() if type_match else ""
    if article_type not in ALLOWED_TYPES:
        add(issues, "error", "invalid-type", f"허용되지 않은 글 유형: {article_type or '없음'}")

    if editorial_close and writing_intelligence is None:
        try:
            writing_intelligence = json.loads(DEFAULT_WRITING_INTELLIGENCE.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            add(issues, "error", "reference-writing-intelligence-load", str(exc))
            writing_intelligence = {}

    editorial_metrics = editorial_source_checks(article, issues, writing_intelligence) if editorial_close else {
        "editorialMasterId": "",
        "editorialReferenceSource": "",
        "editorialProfileStatus": "",
        "referenceWritingProfileId": "",
        "referenceWritingIntelligenceId": "",
        "titleMechanismId": "",
        "closingMechanismId": "",
        "finalWritingVoiceReviewId": "",
        "finalWritingVoiceStatus": "",
    }

    question_matches = reference_role_matches(article, ("reader-question",))
    hook_texts: list[str] = []
    allowed_question_counts = {2, 3}
    if len(question_matches) not in allowed_question_counts:
        add(
            issues,
            "error",
            "reader-question-count",
            f"도입 독자 고민 인용은 2~3개여야 합니다. 현재 {len(question_matches)}개입니다.",
        )
    else:
        for index, match in enumerate(question_matches, start=1):
            block = match.group(0)
            hook_text = re.sub(r"\s+", " ", visible_text(block)).strip()
            hook_texts.append(hook_text)
            if match.group("tag").lower() != "blockquote":
                add(issues, "error", "reader-question-not-quote", f"독자 고민 {index}은 blockquote 인용구여야 합니다.")
            source = re.search(
                r"\bdata-question-source\s*=\s*['\"]representative-reader-concern['\"]",
                block,
                flags=re.I,
            )
            if not source:
                add(
                    issues,
                    "error",
                    "reader-question-source-missing",
                    f"독자 고민 {index}은 실제 환자 발화가 아니라 대표 고민임을 표시해야 합니다.",
                )
            hook_chars = len(compact(hook_text))
            if hook_chars < 10 or hook_chars > 90:
                add(issues, "error", "reader-question-length", f"독자 고민 {index}은 공백 제외 10~90자로 씁니다.")
        if not (meaningful_tokens(title) & meaningful_tokens(" ".join(hook_texts))):
            add(issues, "error", "reader-question-title-disconnect", "독자 고민이 제목의 핵심 문제와 연결되지 않습니다.")

        because_hooks = [text for text in hook_texts if "때문에" in text]
        if len(because_hooks) > 1:
            add(
                issues,
                "error",
                "reader-question-parallel-because-template",
                "도입 질문 여러 개를 모두 ‘증상명 때문에 …나요?’ 틀로 쓰면 안 됩니다. 서로 다른 생활 장면과 문장 호흡으로 다시 쓰세요.",
            )
        for index, hook_text in enumerate(hook_texts, start=1):
            if STACKED_ABSTRACT_HOOK.search(hook_text):
                add(
                    issues,
                    "error",
                    "reader-question-abstract-symptom-stack",
                    f"독자 고민 {index}은 피로·기분 같은 증상 목록을 추상 서술어로 묶지 말고 실제 생활어로 물어야 합니다.",
                )

    intro_role_matches = reference_role_matches(article, ("reader-question", "greeting-authority"))
    intro_roles = [
        (attr_values(match.group(0), "data-reference-role") or [""])[0]
        for match in intro_role_matches
    ]
    expected_intro_roles = ["reader-question"] * len(question_matches) + ["greeting-authority"]
    if intro_roles != expected_intro_roles:
        add(
            issues,
            "error",
            "opening-hook-greeting-order",
            "첫 보이는 도입은 독자 질문 2~3개가 연속으로 나온 뒤 고정 인사가 정확히 한 번 이어져야 합니다.",
        )

    intro_device_id = ""
    reader_payoff = ""
    solution_matches = reference_role_matches(article, ("solution-preview",))
    if len(solution_matches) != 1:
        add(
            issues,
            "error",
            "solution-preview-count",
            f"본문 전에 무엇을 풀어줄지 예고하는 문단은 정확히 1개여야 합니다. 현재 {len(solution_matches)}개입니다.",
        )
    else:
        solution_match = solution_matches[0]
        solution_block = solution_match.group(0)
        solution_text = re.sub(r"\s+", " ", visible_text(solution_block)).strip()
        solution_chars = len(compact(solution_text))
        if editorial_close:
            if solution_chars < 10:
                add(issues, "error", "solution-preview-empty", "해결 방향 예고는 빈 역할 마커가 아니라 실제 산문이어야 합니다.")
        else:
            if solution_chars < 80 or solution_chars > 420:
                add(issues, "error", "solution-preview-length", "해결 방향 예고 문단은 공백 제외 80~420자로 씁니다.")
            if not SOLUTION_PREVIEW_CUE.search(solution_text):
                add(issues, "error", "solution-preview-scope", "해결 방향 예고 문단에서 이번 글이 설명할 범위를 분명히 밝히세요.")
            if not SOLUTION_PAYOFF_CUE.search(solution_text):
                add(issues, "error", "solution-preview-payoff", "해결 방향 예고 문단에 독자가 얻게 될 구분·판단 기준을 넣으세요.")
        if editorial_close:
            solution_tag_match = re.match(r"<[a-z][\w:-]*\b[^>]*>", solution_block, re.I | re.S)
            solution_tag = solution_tag_match.group(0) if solution_tag_match else ""
            device_values = attr_values(solution_tag, "data-intro-persuasion-device")
            payoff_values = attr_values(solution_tag, "data-reader-payoff")
            if len(device_values) != 1:
                add(
                    issues,
                    "error",
                    "intro-persuasion-device-count",
                    "해결 방향 예고에는 선택한 레퍼런스의 도입 설득 장치를 정확히 한 개 표시해야 합니다.",
                )
            else:
                intro_device_id = device_values[0]
            if len(payoff_values) != 1 or len(compact(payoff_values[0])) < 6:
                add(
                    issues,
                    "error",
                    "reader-payoff-missing",
                    "읽을 이유가 되는 주제별 보상을 data-reader-payoff에 구체적으로 표시해야 합니다.",
                )
            else:
                reader_payoff = payoff_values[0]
                if compact(reader_payoff) not in compact(solution_text):
                    add(
                        issues,
                        "error",
                        "reader-payoff-not-visible",
                        "data-reader-payoff의 구체적인 보상은 해결 방향 예고 문장에 실제로 보여야 합니다.",
                    )
                if not (meaningful_tokens(reader_payoff) & meaningful_tokens(f"{title} {' '.join(hook_texts)}")):
                    add(
                        issues,
                        "error",
                        "reader-payoff-topic-disconnect",
                        "도입 보상이 제목이나 독자 고민의 핵심 문제와 연결되지 않습니다.",
                    )

            learning_profile: dict[str, object] = {}
            profile_id = editorial_metrics.get("referenceWritingProfileId", "")
            profiles = writing_intelligence.get("profiles", {}) if isinstance(writing_intelligence, dict) else {}
            if profile_id and isinstance(profiles, dict):
                raw_learning_profile = profiles.get(profile_id, {})
                if isinstance(raw_learning_profile, dict):
                    learning_profile = raw_learning_profile
            opening_contract = learning_profile.get("openingMechanism", {}) if learning_profile else {}
            allowed_devices = opening_contract.get("allowedDeviceIds", []) if isinstance(opening_contract, dict) else []
            if learning_profile and intro_device_id not in allowed_devices:
                add(
                    issues,
                    "error",
                    "intro-persuasion-device-mismatch",
                    f"{profile_id}에서 허용한 도입 장치는 {allowed_devices}이며 입력값은 {intro_device_id or '없음'}입니다.",
                )

            reading_hooks = reference_role_matches(solution_block, ("reading-time-hook",))
            if intro_device_id == "specific-number-low-friction-topic-payoff":
                if len(reading_hooks) != 1:
                    add(
                        issues,
                        "error",
                        "reading-time-hook-count",
                        f"구체적 숫자로 읽기 부담을 낮추는 장치를 선택했으므로 읽기 안내가 정확히 1개여야 합니다. 현재 {len(reading_hooks)}개입니다.",
                    )
                else:
                    hook_block = reading_hooks[0].group(0)
                    hook_text = re.sub(r"\s+", " ", visible_text(hook_block)).strip()
                    minute_values = attr_values(hook_block, "data-reading-minutes")
                    minutes = int(minute_values[0]) if len(minute_values) == 1 and minute_values[0].isdigit() else 0
                    if minutes < 1 or minutes > 5:
                        add(
                            issues,
                            "error",
                            "reading-time-minutes-invalid",
                            "읽기 시간은 실제 글의 밀도에 맞춘 1~5분의 구체적인 숫자여야 합니다.",
                        )
                    if not minutes or not re.search(rf"{minutes}\s*분", hook_text):
                        add(
                            issues,
                            "error",
                            "reading-time-text-invalid",
                            "data-reading-minutes의 숫자가 보이는 읽기 안내 문장과 일치해야 합니다.",
                        )
                    if not READING_COMMITMENT_TEXT.search(hook_text):
                        add(
                            issues,
                            "error",
                            "reading-commitment-missing",
                            "분 단위 숫자에는 읽기나 집중처럼 낮은 노력의 약속이 함께 있어야 합니다.",
                        )
            elif reading_hooks:
                hook_block = reading_hooks[0].group(0)
                add(
                    issues,
                    "error",
                    "reading-time-device-mismatch",
                    "분 단위 읽기 안내를 썼다면 도입 장치를 specific-number-low-friction-topic-payoff로 표시해야 합니다.",
                )

            intro_highlights = re.findall(
                r"<span\b(?=[^>]*data-goldhand-emphasis\s*=\s*['\"]highlight['\"])[^>]*>.*?</span>",
                solution_block,
                flags=re.I | re.S,
            )
            if len(intro_highlights) != 1:
                add(
                    issues,
                    "error",
                    "intro-highlight-count",
                    f"도입 핵심 단어·공감 문구의 노란 하이라이트는 정확히 1개여야 합니다. 현재 {len(intro_highlights)}개입니다.",
                )
        if question_matches and max(match.start() for match in question_matches) > solution_match.start():
            add(issues, "error", "solution-preview-before-hooks", "해결 방향 예고는 독자 고민 인용 2개 뒤에 와야 합니다.")
        early_body_roles = [
            match
            for match in reference_role_matches(article, ("section-heading", "explanation"))
            if match.start() < solution_match.start()
        ]
        if early_body_roles:
            add(issues, "error", "body-before-solution-preview", "첫 정보 소제목·설명보다 해결 방향 예고 문단이 먼저 와야 합니다.")

    issues.extend(credential_placement_issues(article))

    closing_payoff = ""
    if editorial_close:
        closing_matches = reference_role_matches(article, ("neutral-close",))
        if len(closing_matches) != 1:
            add(
                issues,
                "error",
                "reference-closing-count",
                f"선택한 레퍼런스의 마무리 감정을 재구성한 neutral-close가 정확히 1개여야 합니다. 현재 {len(closing_matches)}개입니다.",
            )
        else:
            closing_block = closing_matches[0].group(0)
            closing_text = re.sub(r"\s+", " ", visible_text(closing_block)).strip()
            closing_values = attr_values(closing_block, "data-closing-payoff")
            if len(closing_values) != 1 or len(compact(closing_values[0])) < 4:
                add(
                    issues,
                    "error",
                    "closing-payoff-missing",
                    "마무리에는 본문의 직접 답이나 독자에게 남길 감정을 data-closing-payoff로 표시해야 합니다.",
                )
            else:
                closing_payoff = closing_values[0]
                if compact(closing_payoff) not in compact(closing_text):
                    add(
                        issues,
                        "error",
                        "closing-payoff-not-visible",
                        "data-closing-payoff의 구체적인 회수 문구가 마무리 문장에 실제로 보여야 합니다.",
                    )

    h1 = re.findall(r"<h1\b[^>]*>.*?</h1>", article, flags=re.I | re.S)
    if h1:
        add(
            issues,
            "error",
            "duplicate-title-heading",
            "article 안에 h1을 넣지 않습니다. 제목은 네이버 제목 입력란에 별도로 제공합니다.",
        )

    mobile_metrics = mobile_group_checks(article, issues)

    eligible_html = remove_excluded_roles(article)
    prose_paragraphs = paragraphs(eligible_html)
    body_text = "\n\n".join(prose_paragraphs)
    combined_chars = len(compact(title + body_text))
    if combined_chars < min_chars:
        add(issues, "error", "article-too-short", f"제목+실제 본문 공백 제외 {combined_chars}자; 최소 {min_chars}자입니다.")
    if combined_chars > max_chars:
        add(issues, "error", "article-too-long", f"제목+실제 본문 공백 제외 {combined_chars}자; 최대 {max_chars}자입니다.")

    title_keyword_count = title.count(keyword) if keyword else 0
    keyword_paragraphs = [index for index, paragraph in enumerate(prose_paragraphs, start=1) if keyword and keyword in paragraph]
    body_keyword_count = sum(paragraph.count(keyword) for paragraph in prose_paragraphs) if keyword else 0
    if title_keyword_count != 1:
        add(issues, "error", "title-keyword-count", f"제목의 정확 메인키워드가 {title_keyword_count}회입니다.")
    if editorial_close:
        if body_keyword_count not in {2, 3}:
            add(
                issues,
                "error",
                "body-keyword-count",
                f"editorial-close 일반 본문의 정확 메인키워드가 {body_keyword_count}회입니다. 2~3회가 필요합니다.",
            )
    elif body_keyword_count != 5:
        add(issues, "error", "body-keyword-count", f"일반 본문의 정확 메인키워드가 {body_keyword_count}회입니다.")
    for index, paragraph in enumerate(prose_paragraphs, start=1):
        count = paragraph.count(keyword) if keyword else 0
        if count > 1:
            add(issues, "error", "keyword-repeated-in-paragraph", f"한 문단에 정확 키워드가 {count}회 있습니다.", index)
    required_keyword_paragraphs = body_keyword_count if editorial_close else 5
    if body_keyword_count in ({2, 3} if editorial_close else {5}) and len(keyword_paragraphs) < required_keyword_paragraphs:
        add(
            issues,
            "error",
            "keyword-paragraph-spread",
            f"정확 키워드 {body_keyword_count}회를 서로 다른 문단에 분산해야 합니다.",
        )
    if not editorial_close and keyword_paragraphs and prose_paragraphs:
        last_index = len(prose_paragraphs)
        if min(keyword_paragraphs) > max(3, int(last_index * 0.35)):
            add(issues, "error", "keyword-intro-missing", "도입부에 정확 메인키워드가 없습니다.")
        if max(keyword_paragraphs) < max(1, int(last_index * 0.60)):
            add(issues, "error", "keyword-late-missing", "후반부에 정확 메인키워드가 없습니다.")

    if body_text.count(EXACT_GREETING) != 1:
        add(issues, "error", "greeting", f"고정 인사는 일반 본문에 정확히 한 번 있어야 합니다: {EXACT_GREETING}")
    elif prose_paragraphs:
        greeting_index = next(index for index, paragraph in enumerate(prose_paragraphs) if EXACT_GREETING in paragraph)
        leading = prose_paragraphs[:greeting_index]
        expected_hooks = [re.sub(r"\s+", " ", text).strip() for text in hook_texts]
        if (
            greeting_index not in {2, 3}
            or leading != expected_hooks
            or prose_paragraphs[greeting_index] != EXACT_GREETING
        ):
            add(
                issues,
                "error",
                "greeting-position",
                "글은 독자 질문 2~3개로 바로 시작하고, 그 다음 문단에 고정 인사를 단독으로 써야 합니다.",
            )

    clean_article_text = re.sub(r"\s+", " ", visible_text(article)).strip()
    for code, pattern in FORBIDDEN.items():
        match = pattern.search(clean_article_text)
        if match:
            add(issues, "error", code, f"금지 표현: {match.group(0)}")
    topic_source_url = TOPIC_SOURCE_URL.search(
        without_editorial_reference_source(article) if editorial_close else article
    )
    if topic_source_url:
        add(
            issues,
            "error",
            "topic-source-url-leak",
            "범어 설명한의원 URL은 주제 아이디어 확인용이며 article 내부의 구조·본문·이미지 출처로 넣지 않습니다.",
        )
    for code, pattern in PRODUCTION_RESIDUE.items():
        match = pattern.search(article)
        if match:
            add(issues, "error", code, f"제작 흔적을 제거하세요: {visible_text(match.group(0)).strip() or match.group(0)}")
    for code, pattern in (("emoticon", EMOTICON), ("emoji", EMOJI)):
        match = pattern.search(clean_article_text)
        if match:
            add(issues, "error", code, f"장식 문자를 제거하세요: {match.group(0)}")

    evidence_compact = compact(evidence)
    numeric_claim_source = eligible_html
    for hook in reference_role_matches(numeric_claim_source, ("reading-time-hook",)):
        numeric_claim_source = numeric_claim_source.replace(hook.group(0), " ", 1)
    numeric_claim_text = visible_text(numeric_claim_source)
    checked_numbers: set[str] = set()
    for match in NUMERIC_CLAIM.finditer(title + " " + numeric_claim_text):
        claim = match.group(0)
        normalized_claim = compact(claim)
        if normalized_claim in checked_numbers:
            continue
        checked_numbers.add(normalized_claim)
        if normalized_claim not in evidence_compact:
            add(issues, "error", "unsupported-numeric-claim", f"내장 또는 추가 근거에서 확인되지 않은 수치: {claim}")

    for sentence in re.split(r"(?<=[.!?。])\s+|\n+", body_text):
        if "보건복지부 인증" in sentence and not ("보건복지부 인증 원외탕전실" in sentence and "약침" in sentence):
            add(issues, "error", "certification-misattribution", f"인증 주체와 약침 재료의 관계를 정확히 쓰세요: {sentence[:100]}")
        if "비만" in sentence and "전문가" in sentence and "한방비만치료 전문가과정 수료" not in sentence:
            add(issues, "error", "obesity-course-misattribution", f"비만 교육 이력의 정확한 명칭을 쓰세요: {sentence[:100]}")
        if "11년차" in sentence and "한의사" not in sentence:
            add(issues, "error", "career-context-missing", f"11년차는 한의사 경력에만 연결하세요: {sentence[:100]}")

    clinic_hours_blocks = reference_role_blocks(article, ("clinic-hours",))
    if len(clinic_hours_blocks) != 1:
        add(issues, "error", "clinic-hours-block-count", f"진료시간 블록이 {len(clinic_hours_blocks)}개입니다.")

    contact_blocks = role_blocks(article, "contact")
    if len(contact_blocks) != 1:
        add(issues, "error", "contact-block-count", f"고정 운영정보 블록이 {len(contact_blocks)}개입니다.")
    elif len(clinic_hours_blocks) == 1:
        contact_text = re.sub(
            r"\s+",
            " ",
            visible_text(clinic_hours_blocks[0]) + " " + visible_text(contact_blocks[0]),
        ).strip()
        for expected in FIXED_CONTACT:
            if expected not in contact_text:
                add(issues, "error", "fixed-contact-missing", f"고정 운영정보 누락: {expected}")
        for excluded in FORBIDDEN_FIXED_CONTACT:
            if excluded in contact_text:
                add(issues, "error", "fixed-contact-excluded", f"자동 운영정보 출력 제외 항목이 남아 있습니다: {excluded}")

    if (article_type == "사례공유형" or CASE_OR_EFFECT.search(body_text)) and not DISCLAIMER.search(body_text):
        add(issues, "error", "medical-disclaimer-missing", "사례·치료 경과·효과 내용에는 개인차와 진찰 필요성을 밝혀야 합니다.")

    promises = [int(match.group("count")) for match in NUMBERED_PROMISE.finditer(title)]
    if promises:
        headings = [visible_text(value).strip() for value in re.findall(r"<h[2-4]\b[^>]*>(.*?)</h[2-4]>", eligible_html, flags=re.I | re.S)]
        numbered = [int(match.group("count")) for heading in headings if (match := NUMBERED_HEADING.search(heading))]
        answer_count = max(numbered) if numbered and sorted(set(numbered)) == list(range(1, max(numbered) + 1)) else len(numbered)
        for promise in promises:
            if promise != answer_count:
                add(issues, "error", "title-promise-mismatch", f"제목은 {promise}개를 약속하지만 번호가 붙은 실제 답은 {answer_count}개입니다.")

    try:
        official_assets = load_media_library(DEFAULT_LIBRARY) if media_library is None else media_library
        image_metrics = image_checks(
            article,
            issues,
            official_assets,
            require_generated=editorial_close,
            require_real=editorial_close,
            require_trust=editorial_close,
        )
        if editorial_close:
            media_layout_checks(article, issues)
            trust_layout_checks(article, issues)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add(issues, "error", "image-validation-error", str(exc))
        image_metrics = {
            "images": 0, "officialImages": 0, "localImages": 0, "generatedImages": 0,
            "realPhotos": 0, "realOfficialPhotos": 0, "realBundledPhotos": 0,
            "realPhotoSlots": [],
            "realMediaIds": [], "realMediaHashes": [],
            "trustPhotos": 0, "trustOfficialPhotos": 0, "trustBundledPhotos": 0,
            "trustMediaIds": [], "trustMediaHashes": [],
        }

    current_real_ids = set(str(value) for value in image_metrics.get("realMediaIds", []))
    current_real_hashes = set(str(value) for value in image_metrics.get("realMediaHashes", []))
    recent_media_ids = recent_media_ids or set()
    recent_media_hashes = recent_media_hashes or set()
    reused_recent_ids = current_real_ids & recent_media_ids
    reused_recent_hashes = current_real_hashes & recent_media_hashes
    reused_recent_count = max(len(reused_recent_ids), len(reused_recent_hashes))
    closing_gallery_reuse_allowed = image_metrics.get("realPhotoSlots") == ["closing-trust", "closing-trust"]
    if reused_recent_count and not closing_gallery_reuse_allowed:
        add(
            issues,
            "error",
            "immediately-previous-real-photo-repeat",
            f"바로 직전 완료 글과 같은 실제 사진이 {reused_recent_count}장 있습니다. 직전 글 사진은 한 장도 다시 쓸 수 없습니다.",
        )
    image_metrics["immediatelyPreviousRealPhotoOverlap"] = reused_recent_count
    image_metrics["immediatelyPreviousRealPhotoReuseLimit"] = 2 if closing_gallery_reuse_allowed else 0

    current_trust_ids = set(str(value) for value in image_metrics.get("trustMediaIds", []))
    current_trust_hashes = set(str(value) for value in image_metrics.get("trustMediaHashes", []))
    recent_trust_media_ids = recent_trust_media_ids or set()
    recent_trust_media_hashes = recent_trust_media_hashes or set()
    reused_trust_ids = current_trust_ids & recent_trust_media_ids
    reused_trust_hashes = current_trust_hashes & recent_trust_media_hashes
    reused_trust_count = max(len(reused_trust_ids), len(reused_trust_hashes))
    if reused_trust_count:
        add(
            issues,
            "error",
            "immediately-previous-trust-photo-repeat",
            f"바로 직전 완료 글과 같은 마무리 신뢰 사진이 {reused_trust_count}장 있습니다. 직전 글의 신뢰 사진은 다시 쓸 수 없습니다.",
        )
    image_metrics["immediatelyPreviousTrustPhotoOverlap"] = reused_trust_count
    image_metrics["immediatelyPreviousTrustPhotoReuseLimit"] = 0

    errors = sum(item["severity"] == "error" for item in issues)
    warnings = sum(item["severity"] == "warning" for item in issues)
    return {
        "status": "fail" if errors else "warning" if warnings else "pass",
        "metrics": {
            "editorialClose": editorial_close,
            "type": article_type,
            "nonWhitespaceChars": combined_chars,
            "titleKeywordCount": title_keyword_count,
            "bodyKeywordCount": body_keyword_count,
            "keywordParagraphs": keyword_paragraphs,
            **mobile_metrics,
            **image_metrics,
            **editorial_metrics,
            "introPersuasionDeviceId": intro_device_id,
            "readerPayoff": reader_payoff,
            "closingPayoff": closing_payoff,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--min-chars", type=int, default=1400)
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--media-library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--writing-intelligence", type=Path, default=DEFAULT_WRITING_INTELLIGENCE)
    parser.add_argument("--evidence", action="append", type=Path, default=[])
    parser.add_argument(
        "--editorial-close",
        action="store_true",
        help="제목 말투와 정보 순서를 한 편의 편집 레퍼런스에 밀착시키는 모드입니다.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = args.input.read_text(encoding="utf-8")
        library = load_media_library(args.media_library)
        writing_intelligence = json.loads(args.writing_intelligence.read_text(encoding="utf-8"))
        state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {}
        recent_ids, recent_hashes, _, _ = recent_media_policy(state, current_title=args.title)
        recent_trust_ids, recent_trust_hashes = recent_trust_media_policy(state, current_title=args.title)
        evidence_paths = args.evidence or [DEFAULT_EVIDENCE]
        evidence = "\n".join(path.read_text(encoding="utf-8") for path in evidence_paths if path.exists())
        result = validate_article(
            raw,
            args.title,
            args.keyword,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
            media_library=library,
            evidence=evidence,
            editorial_close=args.editorial_close,
            writing_intelligence=writing_intelligence,
            recent_media_ids=recent_ids,
            recent_media_hashes=recent_hashes,
            recent_trust_media_ids=recent_trust_ids,
            recent_trust_media_hashes=recent_trust_hashes,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"원고 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"제목+본문 공백 제외: {result['metrics']['nonWhitespaceChars']}")
        print(f"정확 키워드: 제목 {result['metrics']['titleKeywordCount']}회 / 본문 {result['metrics']['bodyKeywordCount']}회")
        for issue in result["issues"]:
            where = f" (문단 {issue['paragraph']})" if "paragraph" in issue else ""
            print(f"[{issue['severity'].upper()}] {issue['code']}{where}: {issue['detail']}")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
