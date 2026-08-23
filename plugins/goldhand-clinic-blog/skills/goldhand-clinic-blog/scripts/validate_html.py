#!/usr/bin/env python3
"""Validate the generated Goldhand Clinic Naver copy page."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_SNIPPETS = {
    "copy-root": 'id="naver-copy-root"',
    "copy-button": 'id="copy-for-naver"',
    "clipboard-item": "ClipboardItem",
    "html-mime": "text/html",
    "plain-mime": "text/plain",
    "copy-fallback": "execCommand('copy')",
    "copy-preview": "__goldhandCopyPreview",
    "bold-underline-reminder": "굵게·밑줄·취소선",
    "mobile-breakpoint": "@media (max-width:640px)",
    "writing-master": "data-master-reference-id=",
    "decoration-master": "data-decoration-master-reference-id=",
    "reference-source": "data-reference-source=",
    "goldhand-design-system": 'data-goldhand-design-system="goldhand-naver-native-v4"',
    "mobile-group": 'data-mobile-group="true"',
    "fixed-highlight": 'data-goldhand-emphasis="highlight"',
    "fixed-underline": 'data-reference-underline-role="key-point"',
    "fixed-red-text": 'data-goldhand-emphasis="red"',
    "native-quotation": 'data-naver-native-component="quotation"',
    "native-divider": 'data-naver-native-component="divider"',
    "native-subheading": 'data-naver-native-component="subheading"',
    "native-table": 'data-naver-native-component="table"',
    "native-table-preset": 'data-native-table-preset="naver-table1-default"',
    "credential-table": 'data-native-table-purpose="credential"',
    "summary-table": 'data-native-table-purpose="article-summary"',
    "clinic-hours-table": 'data-native-table-purpose="clinic-hours"',
    "contact-table": 'data-native-table-purpose="clinic-info"',
    "native-copy-sanitizer": "stripInternalMetadata",
    "editorial-copy-sanitizer": "name.startsWith('data-editorial-')",
    "article-wrapper-strip": "root.querySelector('article')",
    "closing-supplement-disabled": "requiresNativeFinisher:false",
    "native-input-buffer": "INPUT_BUFFER_DATA;",
    "native-copy-component-preservation": "element.matches('.se-component.se-oglink,.se-component.se-placesMap')",
}


def add(issues: list[dict[str, str]], severity: str, code: str, detail: str) -> None:
    issues.append({"severity": severity, "code": code, "detail": detail})


def attr_values(fragment: str, attribute: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(attribute)}\s*=\s*(['\"])(.*?)\1", re.I | re.S)
    return [match.group(2).strip() for match in pattern.finditer(fragment)]


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


def validate_html(raw: str, *, max_megabytes: float = 30.0) -> dict[str, object]:
    issues: list[dict[str, str]] = []
    editorial_close = bool(
        re.search(
            r"<article\b[^>]*(?:\bdata-editorial-mode\s*=\s*['\"]close-adaptation['\"]|"
            r"\bdata-editorial-profile-status\s*=\s*['\"]ready['\"])",
            raw,
            flags=re.I | re.S,
        )
    )
    for code, snippet in REQUIRED_SNIPPETS.items():
        if editorial_close and code == "summary-table":
            continue
        if snippet not in raw:
            add(issues, "error", code, f"필수 복사 페이지 요소가 없습니다: {snippet}")

    article_count = len(re.findall(r"<article\b", raw, flags=re.I))
    if article_count != 1:
        add(issues, "error", "article-count", f"복사 페이지의 article이 {article_count}개입니다.")
    copy_root_count = len(re.findall(r"\bid\s*=\s*['\"]naver-copy-root['\"]", raw, flags=re.I))
    if copy_root_count != 1:
        add(issues, "error", "copy-root-count", f"naver-copy-root가 {copy_root_count}개입니다.")
    if not re.search(r"<main\b[^>]*\bid\s*=\s*['\"]naver-copy-root['\"][^>]*>\s*<article\b", raw, flags=re.I | re.S):
        add(issues, "error", "article-outside-copy-root", "복사 대상 main 안에 article 하나가 직접 있어야 합니다.")
    article_match = re.search(r"<article\b[^>]*>.*?</article>", raw, flags=re.I | re.S)
    if article_match and re.search(r"<h1\b|GOLDHAND\s+CLINIC|data-goldhand-role\s*=\s*['\"]doctor-note['\"]", article_match.group(0), flags=re.I):
        add(issues, "error", "legacy-article-template", "복사 본문에 중복 제목 또는 고정 금손 디자인 흔적이 있습니다.")
    if article_match and re.search(r"\bdata-goldhand-box\s*=", article_match.group(0), flags=re.I):
        add(issues, "error", "custom-box-marker", "CSS 카드용 data-goldhand-box가 남아 있습니다.")
    if article_match:
        article_html = article_match.group(0)
        forbidden_closing_patterns = (
            r"data-goldhand-closing-links\s*=",
            r"(?:&lt;|<)함께 보면 좋은 글(?:&gt;|>)",
            r"class\s*=\s*['\"][^'\"]*\bse-oglink\b",
            r"class\s*=\s*['\"][^'\"]*\bse-placesMap\b",
            r"https://blog\.naver\.com/goldhand7582_/\d+",
            r"https://map\.naver\.com/p/entry/place/1598180269",
        )
        if any(re.search(pattern, article_html, flags=re.I | re.S) for pattern in forbidden_closing_patterns):
            add(
                issues,
                "error",
                "closing-supplement-forbidden",
                "운영정보 뒤의 함께 보면 좋은 글·최신 블로그 링크·네이버 지도는 출력하지 않아야 합니다.",
            )
        if re.search(r"<figcaption\b", article_html, flags=re.I):
            add(issues, "error", "visible-image-caption-forbidden", "복사용 HTML에 보이는 이미지 캡션이 남아 있습니다.")
        real_photo_count = len(
            re.findall(r"<img\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>", article_html, flags=re.I | re.S)
        )
        trust_photo_count = len(
            re.findall(r"<img\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"])[^>]*>", article_html, flags=re.I | re.S)
        )
        generated_image_count = len(
            re.findall(r"<img\b(?=[^>]*\bdata-media-provider\s*=\s*['\"]gpt-image['\"])[^>]*>", article_html, flags=re.I | re.S)
        )
        if editorial_close and not 1 <= real_photo_count <= 2:
            add(issues, "error", "real-photo-count", f"복사용 HTML의 실제 금손 사진은 1~2장이어야 합니다. 현재 {real_photo_count}장입니다.")
        if editorial_close and trust_photo_count != 1:
            add(issues, "error", "trust-photo-count", f"복사용 HTML의 마무리 신뢰 사진은 실제 진료 사진과 별도로 정확히 1장이어야 합니다. 현재 {trust_photo_count}장입니다.")
        if editorial_close and not 3 <= generated_image_count <= 4:
            add(issues, "error", "generated-image-count", f"복사용 HTML의 GPT Image는 3~4장이어야 합니다. 현재 {generated_image_count}장입니다.")
        solution_matches: list[re.Match[str]] = []
        credential_matches = list(
            re.finditer(
                r"<table\b(?=[^>]*\bdata-native-table-purpose\s*=\s*['\"]credential['\"])[^>]*>.*?</table>",
                article_html,
                flags=re.I | re.S,
            )
        )
        if len(credential_matches) != 1:
            add(
                issues,
                "error",
                "credential-table-count",
                f"금손한의원 소개 credential 표는 정확히 1개여야 합니다. 현재 {len(credential_matches)}개입니다.",
            )
        else:
            solution_matches = list(
                re.finditer(
                    r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]solution-preview['\"])[^>]*>.*?</(?P=tag)>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
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
                    contains_only_preview_gaps(article_html[solution_match.end():credential_match.start()])
                    or contains_only_preview_gaps_and_before_credential_photo(
                        article_html[solution_match.end():credential_match.start()]
                    )
                ):
                    add(
                        issues,
                        "error",
                        "credential-not-immediately-after-solution-preview",
                        "해결 방향 예고와 금손한의원 소개 credential 표 사이에는 빈 preview-gap 또는 before-credential 실제 사진 1장만 둘 수 있습니다.",
                    )
            intro_matches = list(
                re.finditer(
                    r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"](?:reader-question|greeting-authority)['\"])[^>]*>.*?</(?P=tag)>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            if any(match.end() > credential_match.start() for match in intro_matches):
                add(
                    issues,
                    "error",
                    "intro-role-after-credential",
                    "모든 reader-question과 greeting-authority는 금손한의원 소개 credential 표보다 먼저 끝나야 합니다.",
                )
            first_body_marker = re.search(
                r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>"
                r"|<[a-z][\w:-]*\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]section-heading['\"])[^>]*>",
                article_html,
                flags=re.I | re.S,
            )
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
            elif not contains_only_preview_gaps(article_html[credential_match.end():first_body_marker.start()]):
                add(
                    issues,
                    "error",
                    "credential-not-immediately-before-first-body-marker",
                    "금손한의원 소개 credential 표와 첫 정보 본문 divider·section-heading 사이에는 빈 preview-gap 외의 본문·이미지·표를 둘 수 없습니다.",
                )
        if editorial_close:
            real_figures = list(
                re.finditer(
                    r"<figure\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>.*?</figure>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            trust_figures = list(
                re.finditer(
                    r"<figure\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"])[^>]*>.*?</figure>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            trust_context_matches = list(
                re.finditer(
                    r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]credential-trust-context['\"])[^>]*>.*?</(?P=tag)>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            generated_figures = list(
                re.finditer(
                    r"<figure\b(?=[^>]*\bdata-media-provider\s*=\s*['\"]gpt-image['\"])[^>]*>.*?</figure>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            neutral_matches = list(
                re.finditer(
                    r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]neutral-close['\"])[^>]*>.*?</(?P=tag)>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            section_heading_matches = explanatory_heading_candidates(article_html)
            clinic_heading_matches = list(
                re.finditer(
                    r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]clinic-hours-heading['\"])[^>]*>.*?</(?P=tag)>",
                    article_html,
                    flags=re.I | re.S,
                )
            )
            if len(real_figures) == 1:
                if not re.search(
                    r"<figure\b(?=[^>]*\bdata-real-photo-slot\s*=\s*['\"]before-credential['\"])",
                    real_figures[0].group(0),
                    flags=re.I | re.S,
                ):
                    add(issues, "error", "real-photo-layout-invalid", "실제 사진 1장 구성은 원장 소개표 바로 위 before-credential 슬롯만 허용합니다.")
                elif len(solution_matches) == 1 and len(credential_matches) == 1 and not (
                    solution_matches[0].end() <= real_figures[0].start()
                    < real_figures[0].end() <= credential_matches[0].start()
                ):
                    add(issues, "error", "real-photo-before-credential-position", "before-credential 실제 사진은 해결 방향 예고 뒤 원장 소개표 바로 위에 있어야 합니다.")
            elif len(real_figures) == 2:
                if any(
                    not re.search(
                        r"<figure\b(?=[^>]*\bdata-real-photo-slot\s*=\s*['\"]closing-trust['\"])",
                        figure.group(0),
                        flags=re.I | re.S,
                    )
                    for figure in real_figures
                ):
                    add(issues, "error", "real-photo-layout-invalid", "실제 사진 2장 구성은 글마무리 closing-trust 슬롯 두 장만 허용합니다.")
                elif len(neutral_matches) == 1 and len(clinic_heading_matches) == 1:
                    clinical_tail_end = trust_figures[0].start() if len(trust_figures) == 1 else clinic_heading_matches[0].start()
                    if not all(
                        neutral_matches[0].end() <= figure.start() < figure.end() <= clinical_tail_end
                        for figure in real_figures
                    ):
                        add(issues, "error", "real-photo-closing-trust-position", "closing-trust 실제 진료 사진 두 장은 neutral-close 뒤, 별도 마무리 신뢰 사진 바로 앞에 있어야 합니다.")
                    closing_tail = article_html[real_figures[0].start():clinical_tail_end]
                    closing_tail = re.sub(r"<figure\b(?=[^>]*\bdata-real-photo-slot\s*=\s*['\"]closing-trust['\"])[^>]*>.*?</figure>", "", closing_tail, flags=re.I | re.S)
                    closing_tail = re.sub(r"<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>", "", closing_tail, flags=re.I | re.S)
                    closing_tail = re.sub(r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>", "", closing_tail, flags=re.I | re.S)
                    closing_tail = re.sub(r"<!--.*?-->|</?(?:section|div)\b[^>]*>", "", closing_tail, flags=re.I | re.S)
                    if closing_tail.strip():
                        add(issues, "error", "real-photo-closing-trust-not-adjacent", "closing-trust 실제 진료 사진은 다른 본문·표 없이 별도 마무리 신뢰 구간 바로 앞에 둡니다.")
            elif real_figures:
                add(issues, "error", "real-photo-layout-invalid", "실제 사진은 원장 소개표 위 1장 또는 글마무리 2장 중 한 구성만 허용합니다.")

            if trust_context_matches:
                add(issues, "error", "visible-trust-photo-context-forbidden", "복사용 HTML에는 마무리 신뢰 사진을 설명하는 별도 문단을 출력하지 않습니다.")
            if len(trust_figures) == 1 and len(neutral_matches) == 1 and len(clinic_heading_matches) == 1:
                trust_figure = trust_figures[0]
                if not (
                    neutral_matches[0].end() <= trust_figure.start()
                    < trust_figure.end() <= clinic_heading_matches[0].start()
                ):
                    add(issues, "error", "trust-photo-position", "마무리 신뢰 사진은 neutral-close 뒤, 진료시간 안내 앞의 마지막 이미지로 둡니다.")
                if not re.search(r"\bdata-trust-photo-slot\s*=\s*['\"]closing-credential-trust['\"]", trust_figure.group(0), flags=re.I):
                    add(issues, "error", "trust-photo-slot-invalid", "마무리 신뢰 사진은 closing-credential-trust 슬롯이어야 합니다.")
                if not re.search(r"\bdata-image-placement\s*=\s*['\"]closing-credential-trust['\"]", trust_figure.group(0), flags=re.I):
                    add(issues, "error", "trust-photo-placement-marker", "마무리 신뢰 사진은 별도 설명 문장 없이 closing-credential-trust 위치에 둡니다.")
                trust_tail = article_html[trust_figure.end():clinic_heading_matches[0].start()]
                trust_tail = re.sub(r"<p\b(?=[^>]*\bdata-preview-gap\s*=\s*['\"]true['\"])[^>]*>.*?</p>", "", trust_tail, flags=re.I | re.S)
                trust_tail = re.sub(r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>", "", trust_tail, flags=re.I | re.S)
                trust_tail = re.sub(r"<!--.*?-->|</?(?:section|div)\b[^>]*>", "", trust_tail, flags=re.I | re.S)
                if trust_tail.strip() or re.search(r"<img\b", article_html[trust_figure.end():clinic_heading_matches[0].start()], flags=re.I):
                    add(issues, "error", "trust-photo-not-last-image", "마무리 신뢰 사진 뒤에는 진료시간 안내 전까지 다른 본문·표·이미지를 둘 수 없습니다.")

            early_start: int | None = None
            first_section_end: int | None = None
            early_end: int | None = None
            if len(credential_matches) == 1 and len(neutral_matches) == 1:
                credential = credential_matches[0]
                neutral = neutral_matches[0]
                body_dividers = list(
                    re.finditer(
                        r"<hr\b[^>]*>",
                        article_html,
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
                    if (heading := divider_following_element(article_html, divider, neutral.start())) is not None
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
                    for match in visual_paragraph_heading_candidates(article_html)
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
                if not re.search(
                    r"<figure\b(?=[^>]*\bdata-image-zone\s*=\s*['\"]early-explanatory-body['\"])",
                    figure.group(0),
                    flags=re.I | re.S,
                ):
                    add(issues, "error", "generated-image-zone-missing", f"GPT 이미지 {index}는 early-explanatory-body 구간 표시가 필요합니다.")
                if early_start is not None and early_end is not None and not (
                    early_start <= figure.start() < figure.end() <= early_end
                ):
                    add(issues, "error", "generated-image-outside-early-body", f"GPT 이미지 {index}는 원장 소개표 뒤 첫 두 개 설명 섹션 안에 배치해야 합니다.")
            if (
                generated_figures
                and early_start is not None
                and first_section_end is not None
                and not any(early_start <= figure.start() < figure.end() <= first_section_end for figure in generated_figures)
            ):
                add(issues, "error", "generated-image-first-section-missing", "GPT 이미지 3~4장 가운데 최소 1장은 첫 번째 설명 섹션에 있어야 합니다.")
        tables = re.findall(r"<table\b[^>]*>.*?</table>", article_html, flags=re.I | re.S)
        clinic_info_matches = list(
            re.finditer(
                r"<table\b(?=[^>]*\bdata-native-table-purpose\s*=\s*['\"]clinic-info['\"])[^>]*>.*?</table>",
                article_html,
                flags=re.I | re.S,
            )
        )
        clinic_hours_matches = list(
            re.finditer(
                r"<table\b(?=[^>]*\bdata-native-table-purpose\s*=\s*['\"]clinic-hours['\"])[^>]*>.*?</table>",
                article_html,
                flags=re.I | re.S,
            )
        )
        if len(clinic_hours_matches) != 1:
            add(issues, "error", "clinic-hours-count", f"진료시간 표는 정확히 1개여야 합니다. 현재 {len(clinic_hours_matches)}개입니다.")
        else:
            clinic_hours_html = clinic_hours_matches[0].group(0)
            clinic_hours_rows = len(re.findall(r"<tr\b", clinic_hours_html, flags=re.I))
            if clinic_hours_rows != 4:
                add(issues, "error", "clinic-hours-row-count", f"진료시간 표는 제목 행을 포함해 4행이어야 합니다. 현재 {clinic_hours_rows}행입니다.")
            for excluded in ("공휴일", "설·추석"):
                if excluded in clinic_hours_html:
                    add(issues, "error", "clinic-hours-excluded-row", f"진료시간 표의 자동 출력 제외 항목이 남아 있습니다: {excluded}")
            if clinic_info_matches and clinic_hours_matches[0].end() > clinic_info_matches[0].start():
                add(issues, "error", "clinic-hours-order", "진료시간 표는 위치·전화 운영정보 표보다 앞에 있어야 합니다.")
        if len(clinic_info_matches) != 1:
            add(issues, "error", "clinic-info-count", f"운영정보 표는 정확히 1개여야 합니다. 현재 {len(clinic_info_matches)}개입니다.")
        else:
            clinic_info_html = clinic_info_matches[0].group(0)
            clinic_info_rows = len(re.findall(r"<tr\b", clinic_info_html, flags=re.I))
            if clinic_info_rows != 4:
                add(issues, "error", "clinic-info-row-count", f"운영정보 표는 제목 행을 포함해 4행이어야 합니다. 현재 {clinic_info_rows}행입니다.")
            for excluded in ("카카오톡", "@금손한의원", "네이버 예약"):
                if excluded in clinic_info_html:
                    add(issues, "error", "clinic-info-excluded-row", f"운영정보 표의 자동 출력 제외 항목이 남아 있습니다: {excluded}")
            trailing = re.sub(r"</article>\s*$", "", article_html[clinic_info_matches[0].end():], flags=re.I)
            if not contains_only_preview_gaps(trailing):
                add(issues, "error", "clinic-info-not-last", "운영정보 표 뒤에는 다른 본문·링크·지도 컴포넌트를 둘 수 없습니다.")
        non_table_html = re.sub(r"<table\b[^>]*>.*?</table>", "", article_html, flags=re.I | re.S)
        if re.search(
            r"(?:^|;)\s*(?:border(?:-(?:top|right|bottom|left|radius))?|box-shadow|background-image)\s*:",
            non_table_html,
            flags=re.I,
        ):
            add(issues, "error", "custom-box-css", "표 밖에 외부 카드 CSS가 남아 있습니다.")
        valid_table_count = 3 <= len(tables) <= 4 if editorial_close else len(tables) == 4
        if not valid_table_count:
            requirement = "가치입증·진료시간·운영정보 표와 선택 요약표를 합쳐 3~4개" if editorial_close else "가치입증·요약·진료시간·운영정보 순정 표가 각각"
            add(issues, "error", "native-table-count", f"{requirement} 필요합니다. 현재 {len(tables)}개입니다.")
        for index, table in enumerate(tables, start=1):
            is_clinic_info = 'data-native-table-purpose="clinic-info"' in table
            is_clinic_hours = 'data-native-table-purpose="clinic-hours"' in table
            if 'data-naver-native-component="table"' not in table or 'data-native-table-preset="naver-table1-default"' not in table:
                add(issues, "error", "native-table-contract", f"표 {index}에 네이버 표1 계약이 없습니다.")
            table_tag = re.search(r"<table\b[^>]*>", table, flags=re.I)
            table_opening = table_tag.group(0) if table_tag else ""
            normalized_table = re.sub(r"\s+", "", table_opening).lower()
            if "width:100%" not in normalized_table or "border-collapse:collapse" not in normalized_table:
                add(issues, "error", "native-table-layout", f"표 {index}에 100% 너비와 붙은 셀 구분선 설정이 없습니다.")
            cells = re.findall(r"<t[dh]\b[^>]*>", table, flags=re.I | re.S)
            for cell_index, cell in enumerate(cells, start=1):
                normalized_cell = re.sub(r"\s+", "", cell).lower()
                if "border:1pxsolid#d6d6d6" not in normalized_cell:
                    add(issues, "error", "table-cell-grid", f"표 {index} 셀 {cell_index}에 회색 구분선이 없습니다.")
                if "text-align:center" not in normalized_cell or "vertical-align:middle" not in normalized_cell:
                    add(issues, "error", "table-cell-center", f"표 {index} 셀 {cell_index}이 가로·세로 중앙 정렬이 아닙니다.")
                if is_clinic_info and not all(
                    snippet in normalized_cell
                    for snippet in ("width:100%", "height:64px", "line-height:1.8", "word-break:keep-all")
                ):
                    add(
                        issues,
                        "error",
                        "clinic-info-stacked-rows",
                        f"운영정보 표 셀 {cell_index}은 100% 폭의 1열 적층 행과 64px 기본 높이·중앙 가독성 설정을 사용해야 합니다.",
                    )
                if is_clinic_hours:
                    expected_width = "width:24%" if (cell_index - 1) % 3 == 0 else "width:38%"
                    if not all(
                        snippet in normalized_cell
                        for snippet in (expected_width, "height:64px", "line-height:1.8", "word-break:keep-all")
                    ):
                        add(
                            issues,
                            "error",
                            "clinic-hours-column-layout",
                            f"진료시간 표 셀 {cell_index}은 24:38:38 폭과 64px 높이·중앙 가독성 설정을 사용해야 합니다.",
                        )
        alignment_html = article_html
        for match in re.finditer(
            r"<(?P<tag>p|h[2-6]|blockquote)\b(?P<attrs>[^>]*)>",
            alignment_html,
            flags=re.I | re.S,
        ):
            normalized = re.sub(r"\s+", "", match.group("attrs")).lower()
            if "text-align:center" not in normalized:
                add(issues, "error", "article-text-center", f"{match.group('tag').lower()} 요소가 중앙 정렬이 아닙니다.")
        highlight_count = len(re.findall(r"data-goldhand-emphasis\s*=\s*['\"]highlight['\"]", article_html, flags=re.I))
        underline_count = len(re.findall(r"data-reference-underline-role\s*=\s*['\"]key-point['\"]", article_html, flags=re.I))
        red_count = len(re.findall(r"data-goldhand-emphasis\s*=\s*['\"]red['\"]", article_html, flags=re.I))
        total_emphasis = highlight_count + underline_count + red_count
        if highlight_count != 3:
            add(issues, "error", "highlight-count", f"노란 하이라이트는 정확히 3개여야 합니다. 현재 {highlight_count}개입니다.")
        if not 2 <= underline_count <= 3:
            add(issues, "error", "underline-count", f"밑줄은 2~3개여야 합니다. 현재 {underline_count}개입니다.")
        if not 1 <= red_count <= 2:
            add(issues, "error", "red-text-count", f"빨간 글씨는 1~2개여야 합니다. 현재 {red_count}개입니다.")
        if not 6 <= total_emphasis <= 8:
            add(issues, "error", "emphasis-total-count", f"전체 강조는 6~8개여야 합니다. 현재 {total_emphasis}개입니다.")

    if "data-local-image=" in raw:
        add(issues, "error", "local-image-not-published", "로컬 이미지가 네이버 복사용 HTTPS 주소로 게시되지 않았습니다.")
    for src in re.findall(r"<img\b[^>]*\bsrc\s*=\s*['\"](.*?)['\"]", raw, flags=re.I | re.S):
        if src.startswith(("/", "file:", "~/")):
            add(issues, "error", "local-path-leak", f"공유할 수 없는 로컬 이미지 경로: {src[:120]}")
        if src.startswith("data:image/"):
            add(issues, "error", "naver-rejected-data-image", "네이버 붙여넣기에서 제외되는 data URI 이미지가 남아 있습니다.")
        elif not src.startswith("https://"):
            add(issues, "error", "invalid-image-source", f"허용되지 않은 이미지 src: {src[:120]}")

    for tag in re.findall(r"<img\b[^>]*\bdata-reference-source-url\s*=\s*['\"].*?['\"][^>]*>", raw, flags=re.I | re.S):
        if not re.search(r"\breferrerpolicy\s*=\s*['\"]no-referrer['\"]", tag, flags=re.I):
            add(issues, "error", "referrer-policy-missing", "공식 이미지에 no-referrer가 없습니다.")

    if "\\u2060" not in raw and "\u2060" not in raw and "&#8288;" not in raw:
        add(issues, "error", "gap-preservation-missing", "U+2060 문단 간격 보존 처리가 없습니다.")
    if not re.search(r"max-width\s*:\s*580px", raw, flags=re.I):
        add(issues, "error", "desktop-width-missing", "580px 데스크톱 본문 폭이 없습니다.")

    size_bytes = len(raw.encode("utf-8"))
    real_photo_count = len(re.findall(r"<img\b(?=[^>]*\bdata-real-photo\s*=\s*['\"]true['\"])[^>]*>", raw, flags=re.I | re.S))
    trust_photo_count = len(re.findall(r"<img\b(?=[^>]*\bdata-trust-photo\s*=\s*['\"]true['\"])[^>]*>", raw, flags=re.I | re.S))
    generated_image_count = len(re.findall(r"<img\b(?=[^>]*\bdata-media-provider\s*=\s*['\"]gpt-image['\"])[^>]*>", raw, flags=re.I | re.S))
    if size_bytes > max_megabytes * 1024 * 1024:
        add(issues, "warning", "large-html", f"HTML이 {size_bytes / 1024 / 1024:.1f}MB입니다. 복사 페이지가 불필요하게 큽니다.")

    errors = sum(item["severity"] == "error" for item in issues)
    warnings = sum(item["severity"] == "warning" for item in issues)
    return {
        "status": "fail" if errors else "warning" if warnings else "pass",
        "metrics": {
            "editorialClose": editorial_close,
            "articleCount": article_count,
            "copyRootCount": copy_root_count,
            "sizeBytes": size_bytes,
            "realPhotos": real_photo_count,
            "trustPhotos": trust_photo_count,
            "generatedImages": generated_image_count,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--max-megabytes", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = args.input.read_text(encoding="utf-8")
        result = validate_html(raw, max_megabytes=args.max_megabytes)
    except (OSError, UnicodeError) as exc:
        print(f"HTML 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"파일 크기: {result['metrics']['sizeBytes']} bytes")
        for issue in result["issues"]:
            print(f"[{issue['severity'].upper()}] {issue['code']}: {issue['detail']}")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
