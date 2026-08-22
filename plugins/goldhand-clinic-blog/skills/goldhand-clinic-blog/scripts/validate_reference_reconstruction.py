#!/usr/bin/env python3
"""Validate one-master content flow and the Naver-native decoration system."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = SKILL_DIR / "assets" / "reference-master-profiles.json"
DEFAULT_DESIGN = SKILL_DIR / "assets" / "goldhand-naver-native-design-system.json"
DEFAULT_VALUE_PROOF = SKILL_DIR / "assets" / "goldhand-value-proof-library.json"
FAMILY_ID = "two-or-three-reader-concern-hooks-solution-preview-info"
REFERENCE_BUSINESS_TERMS = (
    "대건청소",
    "도매폰센터",
    "예술가의숲",
    "보스턴에듀",
    "이운철치과",
    "빨강학원",
    "대공부방",
    "양정피티",
    "원주척추병원",
    "위석부부한의원",
    "위석부부 한의원",
    "위석 원장",
    "박경화",
    "광주송정역",
    "송정동",
    "광산구",
    "영광통",
    "송정농협",
    "설명한의원",
    "김병규 대표원장",
    "린다이어트",
    "엑소웨이브",
    "미주안",
    "미주란",
    "라디쥬",
    "보폐고엔오",
    "보폐고 엔오",
    "스파인MT",
    "쿨쎄라",
    "라라샷",
    "퓨라셀",
    "라인약침",
)
TOPIC_SOURCE_URL = re.compile(
    r"https?://(?:m\.|blog\.)?naver\.com/(?:PostView\.naver\?[^\"'<>\s]*blogId=beomeo_sm|beomeo_sm(?:/|\b))",
    re.I,
)
EDITORIAL_MASTER_ID = re.compile(r"(?P<prefix>BM|WP)(?P<post_id>\d{12})$")
EDITORIAL_REFERENCE_URL = re.compile(
    r"https?://(?:m\.|blog\.)?naver\.com/(?P<blog_id>beomeo_sm|wi-parkclinic)/(?P<post_id>\d{12})(?:[/?#].*)?$",
    re.I,
)
REFERENCE_METRIC_PATTERN = re.compile(
    r"(?:29\s*,?\s*000\s*명|2\s*만\s*9\s*천\s*명|2\s*만\s*5\s*천\s*명|70\s*%\s*(?:소개|지인))"
)
LEGACY_TEMPLATE_PATTERNS = {
    "legacy-brand-ribbon": re.compile(r"GOLDHAND\s+CLINIC", re.I),
    "legacy-doctor-card": re.compile(r"data-goldhand-role\s*=\s*['\"]doctor-note['\"]", re.I),
    "legacy-header": re.compile(r"<header\b|<footer\b", re.I),
    "legacy-palette-combination": re.compile(
        r"(?=.*#F8F1DF)(?=.*#9A742F)(?=.*#173E32)", re.I | re.S
    ),
}


def article_fragment(raw: str) -> str:
    matches = re.findall(r"<article\b[^>]*>.*?</article>", raw, flags=re.I | re.S)
    if len(matches) != 1:
        raise ValueError(f"<article>이 {len(matches)}개입니다. 하나만 있어야 합니다.")
    return matches[0]


def attr_values(fragment: str, attribute: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(attribute)}\s*=\s*(['\"])(.*?)\1", re.I | re.S)
    return [html.unescape(match.group(2)).strip() for match in pattern.finditer(fragment)]


def without_editorial_reference_source(fragment: str) -> str:
    return re.sub(
        r"(\bdata-editorial-reference-source\s*=\s*['\"])(.*?)(['\"])",
        r"\1EDITORIAL_REFERENCE_SOURCE\3",
        fragment,
        flags=re.I | re.S,
    )


def editorial_source_issues(tag: str) -> tuple[list[str], str, str]:
    issues: list[str] = []
    master_values = attr_values(tag, "data-editorial-master-id")
    source_values = attr_values(tag, "data-editorial-reference-source")
    role_values = attr_values(tag, "data-editorial-source-role")
    status_values = attr_values(tag, "data-editorial-profile-status")
    if len(master_values) != 1:
        issues.append(f"data-editorial-master-id가 {len(master_values)}개입니다. 정확히 1개여야 합니다.")
    if len(source_values) != 1:
        issues.append(f"data-editorial-reference-source가 {len(source_values)}개입니다. 정확히 1개여야 합니다.")
    master_id = master_values[0] if len(master_values) == 1 else ""
    source_url = source_values[0] if len(source_values) == 1 else ""
    master_match = EDITORIAL_MASTER_ID.fullmatch(master_id)
    source_match = EDITORIAL_REFERENCE_URL.fullmatch(source_url)
    if master_id and master_match is None:
        issues.append(f"등록 형식이 아닌 편집 마스터 ID입니다: {master_id}")
    if source_url and source_match is None:
        issues.append("data-editorial-reference-source는 등록된 범어 또는 Wipark 원문의 정확한 공개 URL이어야 합니다.")
    if master_match and source_match and master_match.group("post_id") != source_match.group("post_id"):
        issues.append(f"편집 마스터 {master_id}와 원문 URL의 글 번호가 다릅니다.")
    if master_match and source_match:
        expected_prefix = "BM" if source_match.group("blog_id") == "beomeo_sm" else "WP"
        if master_match.group("prefix") != expected_prefix:
            issues.append(f"편집 마스터 {master_id}와 원문 블로그가 다릅니다.")
    if len(role_values) > 1:
        issues.append("data-editorial-source-role은 최대 1개만 선언할 수 있습니다.")
    elif role_values and role_values[0] not in {
        "title-tone-content-sequence-only",
        "topic-reader-concerns-general-information-sequence-only",
        "editorial-reasoning-content-flow-and-expression-principles",
    }:
        issues.append("data-editorial-source-role은 등록된 콘텐츠·편집 판단 역할이어야 합니다.")
    if status_values != ["ready"]:
        issues.append("data-editorial-profile-status는 원문 본문 감사와 프로필 검증을 마친 ready여야 합니다.")
    return issues, master_id, source_url


def visible_text(fragment: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", fragment, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def ordered_subsequence(actual: list[str], expected: list[str]) -> bool:
    cursor = 0
    for value in actual:
        if cursor < len(expected) and value == expected[cursor]:
            cursor += 1
    return cursor == len(expected)


def paragraph_styles(fragment: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"<(?:p|h[2-6]|blockquote)\b([^>]*)>", fragment, re.I | re.S)
        if "data-preview-gap" not in match.group(1).lower()
        and "data-naver-gap" not in match.group(1).lower()
    ]


def normalize_css(value: str) -> str:
    return re.sub(r"\s+", "", html.unescape(value)).lower()


def marked_elements(fragment: str, attribute: str, value: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"<(?P<tag>[a-z][\w:-]*)\b(?P<attrs>(?=[^>]*\b{re.escape(attribute)}\s*=\s*['\"]{re.escape(value)}['\"])[^>]*)>",
        re.I | re.S,
    )
    return [(match.group("tag").lower(), match.group("attrs")) for match in pattern.finditer(fragment)]


def css_declarations(attrs: str) -> dict[str, str]:
    styles = attr_values(attrs, "style")
    if not styles:
        return {}
    declarations: dict[str, str] = {}
    for declaration in html.unescape(styles[0]).split(";"):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        declarations[name.strip().lower()] = re.sub(r"\s+", "", value).lower()
    return declarations


def table_elements(fragment: str) -> list[tuple[str, str]]:
    return [
        (match.group("attrs"), match.group("body"))
        for match in re.finditer(r"<table\b(?P<attrs>[^>]*)>(?P<body>.*?)</table>", fragment, re.I | re.S)
    ]


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


def credential_placement_issues(article: str) -> list[str]:
    issues: list[str] = []
    credential_matches = list(
        re.finditer(
            r"<table\b(?=[^>]*\bdata-native-table-purpose\s*=\s*['\"]credential['\"])[^>]*>.*?</table>",
            article,
            re.I | re.S,
        )
    )
    if len(credential_matches) != 1:
        issues.append(f"금손한의원 소개 credential 표가 {len(credential_matches)}개입니다. 정확히 1개여야 합니다.")
        return issues

    solution_matches = list(
        re.finditer(
            r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]solution-preview['\"])[^>]*>.*?</(?P=tag)>",
            article,
            re.I | re.S,
        )
    )
    credential_match = credential_matches[0]
    if len(solution_matches) == 1:
        solution_match = solution_matches[0]
        if credential_match.start() < solution_match.end():
            issues.append("금손한의원 소개 credential 표는 도입과 해결 방향 예고가 모두 끝난 뒤에 배치해야 합니다.")
        elif not (
            contains_only_preview_gaps(article[solution_match.end():credential_match.start()])
            or contains_only_preview_gaps_and_before_credential_photo(
                article[solution_match.end():credential_match.start()]
            )
        ):
            issues.append(
                "해결 방향 예고와 금손한의원 소개 credential 표 사이에는 빈 preview-gap 또는 before-credential 실제 사진 1장만 둘 수 있습니다."
            )

    intro_matches = list(
        re.finditer(
            r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*\bdata-reference-role\s*=\s*['\"](?:reader-question|greeting-authority)['\"])[^>]*>.*?</(?P=tag)>",
            article,
            re.I | re.S,
        )
    )
    if any(match.end() > credential_match.start() for match in intro_matches):
        issues.append(
            "모든 reader-question과 greeting-authority는 금손한의원 소개 credential 표보다 먼저 끝나야 합니다."
        )

    first_body_marker = re.search(
        r"<hr\b(?=[^>]*\bdata-naver-native-component\s*=\s*['\"]divider['\"])[^>]*>"
        r"|<[a-z][\w:-]*\b(?=[^>]*\bdata-reference-role\s*=\s*['\"]section-heading['\"])[^>]*>",
        article,
        re.I | re.S,
    )
    if first_body_marker is None:
        issues.append("금손한의원 소개 credential 표 뒤에 첫 정보 본문 divider 또는 section-heading이 필요합니다.")
    elif credential_match.end() > first_body_marker.start():
        issues.append("금손한의원 소개 credential 표는 첫 정보 본문 divider·section-heading보다 앞에 배치해야 합니다.")
    elif not contains_only_preview_gaps(article[credential_match.end():first_body_marker.start()]):
        issues.append(
            "금손한의원 소개 credential 표와 첫 정보 본문 divider·section-heading 사이에는 빈 preview-gap 외의 본문·이미지·표를 둘 수 없습니다."
        )
    return issues


def effective_column_count(row_html: str) -> int:
    count = 0
    for match in re.finditer(r"<t[dh]\b(?P<attrs>[^>]*)>", row_html, re.I | re.S):
        spans = attr_values(match.group("attrs"), "colspan")
        count += int(spans[0]) if spans and spans[0].isdigit() else 1
    return count


def remove_contact_block(fragment: str) -> str:
    pattern = re.compile(
        r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-goldhand-role\s*=\s*['\"]contact['\"])[^>]*>.*?</(?P=tag)>",
        re.I | re.S,
    )
    return pattern.sub("", fragment)


def direct_paragraph_group_max(fragment: str) -> int:
    fragment = remove_contact_block(fragment)
    body = re.sub(r"^.*?<article\b[^>]*>", "", fragment, count=1, flags=re.I | re.S)
    body = re.sub(r"</article>.*$", "", body, count=1, flags=re.I | re.S)
    events = re.findall(
        r"<p\b(?P<attrs>[^>]*)>(?P<body>.*?)</p>|<(?:figure|section|div|blockquote|h[2-6]|table)\b",
        body,
        re.I | re.S,
    )
    longest = 0
    current = 0
    for attrs, inner in events:
        if not attrs and not inner:
            longest = max(longest, current)
            current = 0
            continue
        if "data-preview-gap" in attrs.lower() or "data-naver-gap" in attrs.lower():
            longest = max(longest, current)
            current = 0
            continue
        if visible_text(inner).replace("\u2060", "").strip():
            current += 1
    return max(longest, current)


def validate(
    raw: str,
    profiles: dict[str, dict[str, object]],
    expected_profile: str = "",
    design: dict[str, object] | None = None,
    value_proof: dict[str, object] | None = None,
    editorial_close: bool = False,
) -> dict[str, object]:
    article = article_fragment(raw)
    issues: list[str] = []
    if re.search(r"<figcaption\b", article, re.I):
        issues.append("이미지 아래에 보이는 figcaption은 사용할 수 없습니다.")
    if design is None:
        design = json.loads(DEFAULT_DESIGN.read_text(encoding="utf-8"))
    if value_proof is None:
        value_proof = json.loads(DEFAULT_VALUE_PROOF.read_text(encoding="utf-8"))
    article_tag = re.search(r"<article\b[^>]*>", article, re.I | re.S)
    tag = article_tag.group(0) if article_tag else ""
    if editorial_close:
        source_contract_issues, editorial_master_id, editorial_reference_source = editorial_source_issues(tag)
        issues.extend(source_contract_issues)
        for attribute in (
            "data-editorial-master-id",
            "data-editorial-reference-source",
            "data-editorial-source-role",
            "data-editorial-profile-status",
        ):
            if len(attr_values(article, attribute)) != len(attr_values(tag, attribute)):
                issues.append(f"{attribute}는 <article> 시작 태그에만 선언해야 합니다.")
    else:
        editorial_master_id = ""
        editorial_reference_source = ""

    master_values = attr_values(tag, "data-master-reference-id")
    decoration_values = attr_values(tag, "data-decoration-master-reference-id")
    source_values = attr_values(tag, "data-reference-source")
    type_values = attr_values(tag, "data-goldhand-type")
    design_values = attr_values(tag, "data-goldhand-design-system")
    if len(master_values) != 1:
        issues.append(f"data-master-reference-id가 {len(master_values)}개입니다.")
    if len(decoration_values) != 1:
        issues.append(f"data-decoration-master-reference-id가 {len(decoration_values)}개입니다.")
    master_id = master_values[0] if len(master_values) == 1 else ""
    decoration_id = decoration_values[0] if len(decoration_values) == 1 else ""
    if master_id and decoration_id and master_id != decoration_id:
        issues.append(f"글쓰기 흐름 마스터 {master_id}와 논리 배치 대조값 {decoration_id}가 다릅니다.")
    if expected_profile and master_id != expected_profile:
        issues.append(f"선택한 마스터는 {master_id or '없음'}이며 요구값은 {expected_profile}입니다.")
    profile = profiles.get(master_id)
    if profile is None:
        issues.append(f"등록되지 않은 마스터 ID입니다: {master_id or '없음'}")
        profile = {}
    if profile and profile.get("referenceFamilyId") != FAMILY_ID:
        issues.append("선택한 마스터가 독자 고민 2~3개·해결 방향 예고형 허용 목록에 없습니다.")

    article_type = type_values[0] if len(type_values) == 1 else ""
    if len(type_values) != 1:
        issues.append(f"data-goldhand-type이 {len(type_values)}개입니다.")
    if article_type != "정보전달형":
        issues.append("이 스킬에서는 정보전달형만 발행할 수 있습니다.")
    if profile and article_type != profile.get("type"):
        issues.append(f"유형 {article_type or '없음'}이 마스터 유형 {profile.get('type')}과 다릅니다.")
    expected_source = str(profile.get("sourceUrl", ""))
    if source_values != [expected_source]:
        issues.append("data-reference-source가 선택한 원문 URL과 정확히 일치하지 않습니다.")

    design_id = str(design.get("id", ""))
    if design_values != [design_id]:
        issues.append(f"data-goldhand-design-system은 {design_id}여야 합니다.")

    used_box_names = attr_values(article, "data-goldhand-box")
    if used_box_names:
        issues.append("CSS 카드용 data-goldhand-box를 사용할 수 없습니다. 네이버 순정 컴포넌트만 사용합니다.")

    forbidden_attributes = {
        str(value).lower() for value in design.get("forbiddenMarkupAttributes", [])
    }
    for attribute in forbidden_attributes:
        if re.search(rf"\b{re.escape(attribute)}\s*=", article, re.I):
            issues.append(f"순정 출력에서 금지된 속성이 있습니다: {attribute}")

    forbidden_css = {
        str(value).lower() for value in design.get("forbiddenArticleCssProperties", [])
    }
    forbidden_non_table_css = {
        str(value).lower() for value in design.get("forbiddenNonTableCssProperties", [])
    }
    opening_tags = re.finditer(
        r"<(?P<tag>[a-z][\w:-]*)\b(?P<attrs>[^>]*)>", article, re.I | re.S
    )
    for element_index, match in enumerate(opening_tags, start=1):
        element_tag = match.group("tag").lower()
        element_attrs = match.group("attrs")
        declarations = css_declarations(element_attrs)
        for property_name in sorted(set(declarations) & forbidden_css):
            issues.append(
                f"네이버 순정 컴포넌트에 외부 CSS {property_name}을 사용할 수 없습니다: {element_tag} {element_index}"
            )
        if element_tag not in {"table", "td", "th"}:
            for property_name in sorted(set(declarations) & forbidden_non_table_css):
                issues.append(
                    f"표 밖 요소에 외부 CSS {property_name}을 사용할 수 없습니다: {element_tag} {element_index}"
                )
        is_registered_highlight = (
            element_tag == "span"
            and attr_values(element_attrs, "data-goldhand-emphasis") == ["highlight"]
            and declarations == {"background-color": "#fff2a8"}
        )
        is_registered_red = (
            element_tag == "span"
            and attr_values(element_attrs, "data-goldhand-emphasis") == ["red"]
            and declarations == {"color": "#e53935", "font-weight": "700"}
        )
        if element_tag not in {"td", "th"} and not is_registered_highlight and {
            "background",
            "background-color",
        } & set(declarations):
            issues.append(
                f"표 셀 밖에 배경색을 넣을 수 없습니다: {element_tag} {element_index}"
            )
        if element_tag not in {"td", "th"} and declarations.get("color") == "#e53935" and not is_registered_red:
            issues.append(
                f"빨간 글씨는 등록된 안전 경계 span에만 사용할 수 있습니다: {element_tag} {element_index}"
            )

    native_specs = design.get("nativeComponents", {})
    native_counts: Counter[str] = Counter()
    for component_name in ("quotation", "divider", "subheading"):
        raw_spec = native_specs.get(component_name, {}) if isinstance(native_specs, dict) else {}
        if not isinstance(raw_spec, dict):
            continue
        elements = marked_elements(article, "data-naver-native-component", component_name)
        native_counts[component_name] = len(elements)
        minimum = int(raw_spec.get("minimumCount", 0))
        maximum = int(raw_spec.get("maximumCount", 999))
        if editorial_close and component_name == "quotation":
            minimum, maximum = 1, 3
        if len(elements) < minimum or len(elements) > maximum:
            issues.append(
                f"네이버 순정 {component_name}이 {len(elements)}개입니다. 허용 범위는 {minimum}~{maximum}개입니다."
            )
        allowed_tags = {
            str(value).lower() for value in raw_spec.get("allowedTags", [])
        }
        expected_tag = str(raw_spec.get("tag", "")).lower()
        for element_tag, attrs in elements:
            if expected_tag and element_tag != expected_tag:
                issues.append(f"네이버 순정 {component_name} 태그는 {expected_tag}여야 합니다.")
            if allowed_tags and element_tag not in allowed_tags:
                issues.append(
                    f"네이버 순정 {component_name} 태그는 {', '.join(sorted(allowed_tags))} 중 하나여야 합니다."
                )
            if component_name == "divider" and attr_values(attrs, "style"):
                issues.append("네이버 순정 divider에는 인라인 스타일을 넣지 않습니다.")
            if component_name == "quotation" and css_declarations(attrs) != {"text-align": "center"}:
                issues.append("네이버 순정 quotation은 text-align:center만 사용해야 합니다.")

    question_elements = marked_elements(article, "data-reference-role", "reader-question")
    for element_tag, attrs in question_elements:
        if element_tag != "blockquote" or attr_values(attrs, "data-naver-native-component") != ["quotation"]:
            issues.append("reader-question은 네이버 순정 quotation blockquote여야 합니다.")
    heading_elements = marked_elements(article, "data-reference-role", "section-heading")
    for element_tag, attrs in heading_elements:
        if element_tag not in {"h2", "p"} or attr_values(attrs, "data-naver-native-component") != ["subheading"]:
            issues.append("section-heading은 박스가 아닌 네이버 순정 subheading이어야 합니다.")

    native_tables = table_elements(article)
    table_spec = native_specs.get("table", {}) if isinstance(native_specs, dict) else {}
    native_counts["table"] = len(native_tables)
    minimum_tables = int(table_spec.get("minimumCount", 0)) if isinstance(table_spec, dict) else 0
    maximum_tables = int(table_spec.get("maximumCount", 999)) if isinstance(table_spec, dict) else 999
    if editorial_close:
        minimum_tables, maximum_tables = 3, 4
    if len(native_tables) < minimum_tables or len(native_tables) > maximum_tables:
        issues.append(
            f"네이버 순정 table이 {len(native_tables)}개입니다. 허용 범위는 {minimum_tables}~{maximum_tables}개입니다."
        )
    allowed_purposes = {
        str(value) for value in table_spec.get("allowedPurposes", [])
    } if isinstance(table_spec, dict) else set()
    required_preset = str(table_spec.get("preset", "")) if isinstance(table_spec, dict) else ""
    table_purposes: Counter[str] = Counter()
    table_design = design.get("tableDesign", {})
    allowed_cell_properties = {
        str(value).lower() for value in table_design.get("allowedCellStyleProperties", [])
    }
    allowed_table_properties = {
        str(value).lower() for value in table_design.get("allowedTableStyleProperties", [])
    }
    purpose_specs = design.get("tablePurposes", {})
    header_cells_by_purpose: dict[str, list[str]] = {}
    value_proof_ids: list[str] = []
    fixed_proof_rows = [
        str(value) for value in value_proof.get("fixedRows", [])
    ] if isinstance(value_proof, dict) else []
    for table_index, (attrs, body) in enumerate(native_tables, start=1):
        if attr_values(attrs, "data-naver-native-component") != ["table"]:
            issues.append(f"표 {table_index}에 data-naver-native-component=table이 없습니다.")
        preset_values = attr_values(attrs, "data-native-table-preset")
        if preset_values != [required_preset]:
            issues.append(f"표 {table_index}는 네이버 공식 표1 프리셋 값 {required_preset}이어야 합니다.")
        purpose_values = attr_values(attrs, "data-native-table-purpose")
        purpose = purpose_values[0] if len(purpose_values) == 1 else ""
        if not purpose or purpose not in allowed_purposes:
            issues.append(f"표 {table_index}의 용도가 등록되지 않았습니다: {purpose or '없음'}")
        else:
            table_purposes[purpose] += 1
        table_style = css_declarations(attrs)
        outside_table = sorted(set(table_style) - allowed_table_properties)
        if outside_table:
            issues.append(
                f"표 {table_index}에 네이버 표 배치 속성 밖의 스타일이 있습니다: {', '.join(outside_table)}"
            )
        if table_style.get("width") != "100%":
            issues.append(f"표 {table_index}의 너비는 100%여야 합니다.")
        if table_style.get("border-collapse") != "collapse":
            issues.append(f"표 {table_index}은 셀 구분선이 붙도록 border-collapse:collapse를 사용해야 합니다.")
        if table_style.get("margin-left") != "auto" or table_style.get("margin-right") != "auto":
            issues.append(f"표 {table_index}은 좌우 여백 auto로 중앙 배치해야 합니다.")
        rows = [match.group(1) for match in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", body, re.I | re.S)]
        raw_purpose_spec = purpose_specs.get(purpose, {}) if isinstance(purpose_specs, dict) else {}
        purpose_spec = raw_purpose_spec if isinstance(raw_purpose_spec, dict) else {}
        minimum_rows = int(purpose_spec.get("minimumRows", 2))
        maximum_rows = int(purpose_spec.get("maximumRows", 999))
        minimum_columns = int(purpose_spec.get("minimumColumns", 2))
        maximum_columns = int(purpose_spec.get("maximumColumns", 999))
        table_visible_text = visible_text(body)
        for forbidden_text in purpose_spec.get("forbiddenVisibleTexts", []):
            forbidden_value = str(forbidden_text)
            if forbidden_value and forbidden_value in table_visible_text:
                issues.append(
                    f"표 {table_index}에 자동 출력 제외 문구가 있습니다: {forbidden_value}"
                )
        if len(rows) < minimum_rows or len(rows) > maximum_rows:
            issues.append(
                f"표 {table_index}은 {len(rows)}행입니다. {purpose or '미등록'} 표 허용 범위는 {minimum_rows}~{maximum_rows}행입니다."
            )
        column_counts = [effective_column_count(row) for row in rows]
        if not column_counts or min(column_counts) < minimum_columns or max(column_counts) > maximum_columns:
            issues.append(
                f"표 {table_index}은 모든 행이 {minimum_columns}~{maximum_columns}열이어야 합니다."
            )
        cell_tags = re.findall(r"<t[dh]\b(?P<attrs>[^>]*)>", body, re.I | re.S)
        for cell_index, cell_attrs in enumerate(cell_tags, start=1):
            declarations = css_declarations(cell_attrs)
            outside = sorted(set(declarations) - allowed_cell_properties)
            if outside:
                issues.append(
                    f"표 {table_index} 셀 {cell_index}에 네이버 셀 속성 밖의 스타일이 있습니다: {', '.join(outside)}"
                )
            if declarations.get("border") != "1pxsolid#d6d6d6":
                issues.append(f"표 {table_index} 셀 {cell_index}에 1px 회색 구분선이 없습니다.")
            if declarations.get("text-align") != "center":
                issues.append(f"표 {table_index} 셀 {cell_index}은 가로 중앙 정렬이어야 합니다.")
            if declarations.get("vertical-align") != "middle":
                issues.append(f"표 {table_index} 셀 {cell_index}은 세로 중앙 정렬이어야 합니다.")
            if purpose == "clinic-info":
                required_width = str(purpose_spec.get("columnWidth", "100%")).lower()
                required_height = str(purpose_spec.get("minimumCellHeight", "64px")).lower()
                required_line_height = str(purpose_spec.get("requiredLineHeight", "1.8")).lower()
                required_word_break = str(purpose_spec.get("requiredWordBreak", "keep-all")).lower()
                if declarations.get("width") != required_width:
                    issues.append(
                        f"운영정보 표 셀 {cell_index}의 적층 행 폭은 모두 {required_width}여야 합니다."
                    )
                if declarations.get("height") != required_height:
                    issues.append(
                        f"운영정보 표 셀 {cell_index}의 기본 높이는 {required_height}여야 합니다."
                    )
                if declarations.get("line-height") != required_line_height:
                    issues.append(
                        f"운영정보 표 셀 {cell_index}의 행간은 {required_line_height}이어야 합니다."
                    )
                if declarations.get("word-break") != required_word_break:
                    issues.append(
                        f"운영정보 표 셀 {cell_index}은 word-break:{required_word_break}을 사용해야 합니다."
                    )
            if purpose == "clinic-hours":
                widths = [str(value).lower() for value in purpose_spec.get("columnWidths", ["24%", "38%", "38%"])]
                required_width = widths[(cell_index - 1) % len(widths)]
                required_height = str(purpose_spec.get("minimumCellHeight", "64px")).lower()
                required_line_height = str(purpose_spec.get("requiredLineHeight", "1.8")).lower()
                required_word_break = str(purpose_spec.get("requiredWordBreak", "keep-all")).lower()
                if declarations.get("width") != required_width:
                    issues.append(
                        f"진료시간 표 셀 {cell_index}의 열 폭은 {required_width}여야 합니다."
                    )
                if declarations.get("height") != required_height:
                    issues.append(
                        f"진료시간 표 셀 {cell_index}의 기본 높이는 {required_height}여야 합니다."
                    )
                if declarations.get("line-height") != required_line_height:
                    issues.append(
                        f"진료시간 표 셀 {cell_index}의 행간은 {required_line_height}이어야 합니다."
                    )
                if declarations.get("word-break") != required_word_break:
                    issues.append(
                        f"진료시간 표 셀 {cell_index}은 word-break:{required_word_break}을 사용해야 합니다."
                    )
        if rows:
            header_cells_by_purpose[purpose] = re.findall(
                r"<t[dh]\b(?P<attrs>[^>]*)>", rows[0], re.I | re.S
            )
        if purpose == "credential" and rows:
            expected_header = str(purpose_spec.get("headerText", ""))
            actual_header = visible_text(rows[0])
            if actual_header != expected_header:
                issues.append(f"가치입증 표 제목은 '{expected_header}'여야 합니다.")
            proof_rows = [visible_text(row) for row in rows[1:]]
            if proof_rows != fixed_proof_rows:
                issues.append(
                    "가치입증 표는 후보 선택 없이 등록된 짧은 경력·강점 6행을 같은 순서로 사용해야 합니다."
                )
            value_proof_ids = [f"FIXED{index:02d}" for index in range(1, len(proof_rows) + 1)]

    if isinstance(purpose_specs, dict):
        for purpose, raw_spec in purpose_specs.items():
            if not isinstance(raw_spec, dict):
                continue
            actual = table_purposes.get(str(purpose), 0)
            minimum = int(raw_spec.get("minimumCount", 0))
            maximum = int(raw_spec.get("maximumCount", 999))
            if editorial_close and str(purpose) == "article-summary":
                minimum, maximum = 0, 1
            if actual < minimum or actual > maximum:
                issues.append(
                    f"네이버 순정 표 용도 {purpose}가 {actual}개입니다. 허용 범위는 {minimum}~{maximum}개입니다."
                )
            if raw_spec.get("requiresGoldHeader") and actual:
                for header_attrs in header_cells_by_purpose.get(str(purpose), []):
                    header_style = css_declarations(header_attrs)
                    background = header_style.get("background-color", header_style.get("background", ""))
                    if background != "#c99f75" or header_style.get("color") != "#ffffff":
                        issues.append(f"{purpose} 표의 첫 행은 금손 골드 배경과 흰 글자를 사용해야 합니다.")

    style_colors = {
        color.lower()
        for style in attr_values(article, "style")
        for color in re.findall(r"#[0-9a-fA-F]{6}", style)
    }
    allowed_colors = {str(value).lower() for value in design.get("allowedArticleHexColors", [])}
    outside_colors = sorted(style_colors - allowed_colors)
    if outside_colors:
        issues.append(f"금손 허용 팔레트 밖의 색상이 있습니다: {', '.join(outside_colors)}")

    if re.search(r"<h1\b", article, re.I):
        issues.append("복사 본문 안에 h1이 있습니다. 제목은 네이버 제목 입력란에만 둡니다.")
    for name, pattern in LEGACY_TEMPLATE_PATTERNS.items():
        if pattern.search(article):
            issues.append(f"고정 금손 템플릿 흔적: {name}")
    if re.search(r"\b(?:class|id)\s*=\s*['\"][^'\"]*\bse-[a-z0-9_-]+", article, re.I):
        issues.append("네이버 내부 se-* 클래스를 복사하지 않습니다.")

    centered_text_tags = re.finditer(
        r"<(?P<tag>p|h[2-6]|blockquote)\b(?P<attrs>[^>]*)>",
        article,
        re.I | re.S,
    )
    for match in centered_text_tags:
        declarations = css_declarations(match.group("attrs"))
        if declarations.get("text-align") != "center":
            issues.append(f"모든 글은 중앙 정렬이어야 합니다: {match.group('tag').lower()}")

    emphasis_spec = design.get("textEmphasis", {})
    highlight_spec = emphasis_spec.get("highlight", {}) if isinstance(emphasis_spec, dict) else {}
    underline_spec = emphasis_spec.get("underline", {}) if isinstance(emphasis_spec, dict) else {}
    red_spec = emphasis_spec.get("red", {}) if isinstance(emphasis_spec, dict) else {}
    highlight_matches = list(
        re.finditer(
            r"<span\b(?P<attrs>(?=[^>]*data-goldhand-emphasis\s*=\s*['\"]highlight['\"])[^>]*)>(?P<body>.*?)</span>",
            article,
            re.I | re.S,
        )
    )
    underline_matches = list(
        re.finditer(
            r"<u\b(?P<attrs>(?=[^>]*data-reference-underline-role\s*=\s*['\"]key-point['\"])[^>]*)>(?P<body>.*?)</u>",
            article,
            re.I | re.S,
        )
    )
    red_matches = list(
        re.finditer(
            r"<span\b(?P<attrs>(?=[^>]*data-goldhand-emphasis\s*=\s*['\"]red['\"])[^>]*)>(?P<body>.*?)</span>",
            article,
            re.I | re.S,
        )
    )
    for label, matches, spec in (
        ("노란 하이라이트", highlight_matches, highlight_spec),
        ("밑줄", underline_matches, underline_spec),
        ("빨간 글씨", red_matches, red_spec),
    ):
        minimum = int(spec.get("minimumCount", 0)) if isinstance(spec, dict) else 0
        maximum = int(spec.get("maximumCount", 999)) if isinstance(spec, dict) else 999
        if len(matches) < minimum or len(matches) > maximum:
            issues.append(f"{label} 강조가 {len(matches)}개입니다. 허용 범위는 {minimum}~{maximum}개입니다.")
    maximum_phrase_chars = int(emphasis_spec.get("maximumNonWhitespaceCharsPerPhrase", 22)) if isinstance(emphasis_spec, dict) else 22
    for match in highlight_matches:
        if css_declarations(match.group("attrs")) != {"background-color": "#fff2a8"}:
            issues.append("하이라이트는 노란 배경색 #FFF2A8만 사용해야 합니다.")
        if len(re.sub(r"\s+", "", visible_text(match.group("body")))) > maximum_phrase_chars:
            issues.append(f"하이라이트 문구는 공백 제외 {maximum_phrase_chars}자를 넘길 수 없습니다.")
    for match in underline_matches:
        if attr_values(match.group("attrs"), "style"):
            issues.append("밑줄은 네이버 순정 <u>만 사용하고 인라인 스타일을 넣지 않습니다.")
        if len(re.sub(r"\s+", "", visible_text(match.group("body")))) > maximum_phrase_chars:
            issues.append(f"밑줄 문구는 공백 제외 {maximum_phrase_chars}자를 넘길 수 없습니다.")
    for match in red_matches:
        if css_declarations(match.group("attrs")) != {"color": "#e53935", "font-weight": "700"}:
            issues.append("빨간 글씨는 #E53935와 굵기 700만 사용해야 합니다.")
        if len(re.sub(r"\s+", "", visible_text(match.group("body")))) > maximum_phrase_chars:
            issues.append(f"빨간 글씨 문구는 공백 제외 {maximum_phrase_chars}자를 넘길 수 없습니다.")
    total_emphasis = len(highlight_matches) + len(underline_matches) + len(red_matches)
    minimum_total = int(emphasis_spec.get("minimumTotalCount", 0)) if isinstance(emphasis_spec, dict) else 0
    maximum_total = int(emphasis_spec.get("maximumTotalCount", 999)) if isinstance(emphasis_spec, dict) else 999
    if total_emphasis < minimum_total or total_emphasis > maximum_total:
        issues.append(f"전체 강조가 {total_emphasis}개입니다. 허용 범위는 {minimum_total}~{maximum_total}개입니다.")
    if any(
        re.search(r"<(?:u\b|span\b[^>]*data-goldhand-emphasis)", match.group("body"), re.I)
        for match in [*highlight_matches, *underline_matches, *red_matches]
    ):
        issues.append("노란 하이라이트·밑줄·빨간 글씨를 서로 겹쳐 쓰지 않습니다.")
    clean_text = visible_text(article)
    for term in REFERENCE_BUSINESS_TERMS:
        if term in clean_text:
            issues.append(f"레퍼런스 업체 정보가 섞였습니다: {term}")
    source_metric = REFERENCE_METRIC_PATTERN.search(clean_text)
    if source_metric:
        issues.append(f"레퍼런스 업체 수치가 섞였습니다: {source_metric.group(0)}")
    topic_source_scan = without_editorial_reference_source(article) if editorial_close else article
    if TOPIC_SOURCE_URL.search(topic_source_scan):
        issues.append("범어 설명한의원 URL은 주제 아이디어 전용이며 article 내부에 넣을 수 없습니다.")
    if expected_source and expected_source in " ".join(
        attr_values(article, "src") + attr_values(article, "data-reference-source-url")
    ):
        issues.append("레퍼런스 원문의 미디어 URL을 복사했습니다.")

    roles = attr_values(article, "data-reference-role")
    role_counts = Counter(roles)
    allowed_question_counts = {2, 3}
    if role_counts.get("reader-question", 0) not in allowed_question_counts:
        issues.append(
            f"도입 reader-question이 {role_counts.get('reader-question', 0)}개입니다. "
            f"2~3개여야 합니다."
        )
    if role_counts.get("solution-preview", 0) != 1:
        issues.append(f"solution-preview가 {role_counts.get('solution-preview', 0)}개입니다. 정확히 1개여야 합니다.")
    issues.extend(credential_placement_issues(article))
    family_contract = profile.get("familyContract", {}) if isinstance(profile, dict) else {}
    if isinstance(family_contract, dict):
        question_positions = [index for index, role in enumerate(roles) if role == "reader-question"]
        greeting_positions = [index for index, role in enumerate(roles) if role == "greeting-authority"]
        solution_positions = [index for index, role in enumerate(roles) if role == "solution-preview"]
        if len(greeting_positions) != 1:
            issues.append(f"greeting-authority가 {len(greeting_positions)}개입니다. 정확히 1개여야 합니다.")
        elif len(question_positions) in allowed_question_counts:
            intro_roles = [role for role in roles if role in {"reader-question", "greeting-authority"}]
            expected_intro_roles = ["reader-question"] * len(question_positions) + ["greeting-authority"]
            if intro_roles != expected_intro_roles:
                issues.append("모든 글은 독자 고민 질문 2~3개가 연속으로 나온 뒤 원장 인사가 와야 합니다.")
        if len(solution_positions) == 1 and len(question_positions) in allowed_question_counts:
            if solution_positions[0] < max(question_positions):
                issues.append("해결 방향 예고는 독자 고민 2~3개 뒤에 와야 합니다.")
    contract = profile.get("renderContract", {}) if isinstance(profile, dict) else {}
    if isinstance(contract, dict):
        minimums = contract.get("requiredRoleMinimums", {})
        if isinstance(minimums, dict):
            for role, minimum in minimums.items():
                if editorial_close and str(role) not in {"reader-question", "solution-preview", "contact"}:
                    continue
                if editorial_close and str(role) == "reader-question":
                    minimum = 1
                actual = role_counts.get(str(role), 0)
                if actual < int(minimum):
                    issues.append(f"역할 {role}이 {actual}개입니다. 최소 {minimum}개가 필요합니다.")
        maximums = contract.get("requiredRoleMaximums", {})
        if isinstance(maximums, dict):
            for role, maximum in maximums.items():
                if editorial_close and str(role) == "reader-question":
                    maximum = 3
                actual = role_counts.get(str(role), 0)
                if actual > int(maximum):
                    issues.append(f"역할 {role}이 {actual}개입니다. 최대 {maximum}개까지 허용합니다.")
        expected_roles = contract.get("requiredOrderedRoles", [])
        if isinstance(expected_roles, list):
            expected = [str(role) for role in expected_roles]
            if editorial_close:
                # The Wipark profile remains the visual/layout master. Beomeo's
                # editorial profile owns the information sequence, so legacy
                # explanation/close beats and duplicate questions do not leak
                # into this ordered-role check.
                expected = [
                    role
                    for role in expected
                    if role in {"reader-question", "solution-preview", "contact"}
                ]
                expected = [
                    role for index, role in enumerate(expected)
                    if index == 0 or role != expected[index - 1]
                ]
            if expected and not ordered_subsequence(roles, expected):
                issues.append(f"레퍼런스 역할 순서가 다릅니다: 실제 {roles}, 필수 {expected}")

        styles = paragraph_styles(remove_contact_block(article))
        centered = sum("text-align:center" in style.replace(" ", "").lower() for style in styles)
        center_ratio = centered / len(styles) if styles else 0.0
        minimum_center = float(contract.get("minimumCenterRatio", 0.0))
        if center_ratio < minimum_center:
            issues.append(f"가운데 정렬 비율 {center_ratio:.3f}; 최소 {minimum_center:.3f}입니다.")
        maximum_center = float(contract.get("maximumCenterRatio", 1.0))
        if center_ratio > maximum_center:
            issues.append(f"가운데 정렬 비율 {center_ratio:.3f}; 최대 {maximum_center:.3f}입니다.")

        underline_tags = re.findall(r"<u\b[^>]*>", article, re.I | re.S)
        required_underlines = int(contract.get("requiredUnderlineMinimum", 0))
        if len(underline_tags) < required_underlines:
            issues.append(f"밑줄이 {len(underline_tags)}개입니다. 최소 {required_underlines}개가 필요합니다.")
        for underline in underline_tags:
            if not attr_values(underline, "data-reference-underline-role"):
                issues.append("역할이 등록되지 않은 밑줄이 있습니다.")
        if re.search(r"text-decoration\s*:", article, re.I):
            issues.append("임의 text-decoration 대신 역할이 등록된 <u>만 사용합니다.")

        maximum_group = int(contract.get("maxConsecutiveBodyParagraphs", 0))
        actual_group = direct_paragraph_group_max(article)
        if maximum_group and actual_group > maximum_group:
            issues.append(f"연속 본문 문단이 {actual_group}개입니다. 최대 {maximum_group}개입니다.")
    else:
        center_ratio = 0.0
        actual_group = 0

    contact_blocks = re.findall(
        r"<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-goldhand-role\s*=\s*['\"]contact['\"])[^>]*>.*?</(?P=tag)>",
        article,
        re.I | re.S,
    )
    if len(contact_blocks) != 1:
        issues.append(f"금손 고정 연락처 블록이 {len(contact_blocks)}개입니다.")
    if roles and roles[-1] != "contact":
        issues.append("contact가 마지막 reference role이 아닙니다.")

    return {
        "status": "pass" if not issues else "fail",
        "metrics": {
            "editorialClose": editorial_close,
            "editorialMasterId": editorial_master_id,
            "editorialReferenceSource": editorial_reference_source,
            "profile": master_id,
            "type": article_type,
            "roles": dict(role_counts),
            "roleSequence": roles,
            "goldhandDesignSystem": design_id,
            "nativeComponents": dict(native_counts),
            "nativeTablePurposes": dict(table_purposes),
            "valueProofIds": value_proof_ids,
            "valueProofItemRows": len(value_proof_ids),
            "highlightCount": len(highlight_matches),
            "underlineCount": len(underline_matches),
            "redTextCount": len(red_matches),
            "articleColors": sorted(style_colors),
            "centerRatio": round(center_ratio, 3),
            "maxConsecutiveBodyParagraphs": actual_group,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", default="")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument(
        "--editorial-close",
        action="store_true",
        help="Wipark는 순정 레이아웃만, 별도 Beomeo 편집 마스터는 제목·내용 순서만 담당합니다.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = args.input.read_text(encoding="utf-8")
        data = json.loads(args.profiles.read_text(encoding="utf-8"))
        result = validate(
            raw,
            data["profiles"],
            args.profile,
            editorial_close=args.editorial_close,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"레퍼런스 재현 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"profile: {result['metrics']['profile']}")
        for issue in result["issues"]:
            print(f"[ERROR] {issue}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
