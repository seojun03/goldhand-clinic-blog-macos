from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
GPT_IMAGE_FIXTURE = (SKILL_DIR / "assets" / "gpt-image-test-fixture.png").resolve()


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"goldhand_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TITLE_VALIDATOR = load_module("validate_title")
ARTICLE_VALIDATOR = load_module("validate_article")
PAGE_BUILDER = load_module("build_naver_copy_page")
HTML_VALIDATOR = load_module("validate_html")
STATE_RECORDER = load_module("record_article_state")
MEDIA_RECOMMENDER = load_module("recommend_media")
CLOSING_TRUST_RECOMMENDER = load_module("recommend_closing_trust_media")
OFFICIAL_MEDIA_SYNC = load_module("sync_official_media_assets")
MASTER_SELECTOR = load_module("select_reference_master")
REFERENCE_VALIDATOR = load_module("validate_reference_reconstruction")
EDITORIAL_FIDELITY_VALIDATOR = load_module("validate_editorial_fidelity")
COPY_OVERLAP_VALIDATOR = load_module("validate_copy_overlap")
TOPIC_SELECTOR = load_module("select_topic_idea")
TOPIC_SOURCE_VALIDATOR = load_module("validate_topic_source_library")
EDITORIAL_PROFILE_VALIDATOR = load_module("validate_editorial_master_profiles")
GOLDHAND_VOICE_VALIDATOR = load_module("validate_goldhand_voice")
NATURAL_SPEECH_SUITE_VALIDATOR = load_module("validate_natural_speech_suite")
FINAL_WRITING_VOICE_VALIDATOR = load_module("validate_final_voice_review")
WIPARK_CONTENT_SELECTOR = load_module("select_wipark_content_reference")
REFERENCE_LEARNING_VALIDATOR = load_module("validate_reference_learning")
IMAGE_HOST_SETUP = load_module("setup_image_host")

KEYWORD = "동천동 한의원"
TITLE = f"{KEYWORD} 통증이 반복되는 움직임과 생활 기준"
EDITORIAL_TITLE = f"{KEYWORD} 통증이 반복되는 3가지 기준"
QUESTION_TWO = "다른 검사를 먼저 받아야 하는 신호도 있을까요?"
BODY_OPEN = '<section data-reference-role="body">'


def question_markup(text: str) -> str:
    return (
        '<blockquote data-naver-native-component="quotation" data-reference-role="reader-question" '
        'data-question-source="representative-reader-concern" style="text-align:center;" '
        f'>{text}</blockquote>'
    )


def divider_markup() -> str:
    return '<hr data-naver-native-component="divider" data-reference-role="divider">'


def table_markup(purpose: str, rows: list[list[tuple[str, str]]], *, attributes: str = "") -> str:
    cell_contract = "border:1px solid #D6D6D6;text-align:center;vertical-align:middle;"
    clinic_contract = "height:64px;line-height:1.8;word-break:keep-all;" if purpose in {"clinic-hours", "clinic-info"} else ""
    row_markup = "".join(
        "<tr>" + "".join(f'<td style="{style}{clinic_contract}{cell_contract}">{text}</td>' for text, style in row) + "</tr>"
        for row in rows
    )
    extra = f" {attributes.strip()}" if attributes.strip() else ""
    return (
        '<table data-naver-native-component="table" '
        'data-native-table-preset="naver-table1-default" '
        f'data-native-table-purpose="{purpose}"{extra} '
        'style="width:100%;border-collapse:collapse;margin-left:auto;margin-right:auto;">'
        f'<tbody>{row_markup}</tbody></table>'
    )


def move_credential_table_before(article: str, destination_pattern: str) -> str:
    credential = re.search(
        r'<table\b(?=[^>]*data-native-table-purpose="credential")[^>]*>.*?</table>',
        article,
        flags=re.I | re.S,
    )
    if credential is None:
        raise AssertionError("테스트 원고에 credential 표가 없습니다.")
    credential_html = credential.group(0)
    without_credential = article[:credential.start()] + article[credential.end():]
    destination = re.search(destination_pattern, without_credential, flags=re.I | re.S)
    if destination is None:
        raise AssertionError(f"credential 표 이동 목적지를 찾지 못했습니다: {destination_pattern}")
    return without_credential[:destination.start()] + credential_html + without_credential[destination.start():]


def insert_after_reference_role(article: str, role: str, fragment: str) -> str:
    role_match = re.search(
        rf'<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-reference-role="{re.escape(role)}")[^>]*>.*?</(?P=tag)>',
        article,
        flags=re.I | re.S,
    )
    if role_match is None:
        raise AssertionError(f"테스트 원고에 {role} 역할이 없습니다.")
    return article[:role_match.end()] + fragment + article[role_match.end():]


def insert_after_purpose_table(article: str, purpose: str, fragment: str) -> str:
    table = re.search(
        rf'<table\b(?=[^>]*data-native-table-purpose="{re.escape(purpose)}")[^>]*>.*?</table>',
        article,
        flags=re.I | re.S,
    )
    if table is None:
        raise AssertionError(f"테스트 원고에 {purpose} 표가 없습니다.")
    return article[:table.end()] + fragment + article[table.end():]


def move_purpose_table_before(article: str, purpose: str, destination_pattern: str) -> str:
    table = re.search(
        rf'<table\b(?=[^>]*data-native-table-purpose="{re.escape(purpose)}")[^>]*>.*?</table>',
        article,
        flags=re.I | re.S,
    )
    if table is None:
        raise AssertionError(f"테스트 원고에 {purpose} 표가 없습니다.")
    table_html = table.group(0)
    without_table = article[:table.start()] + article[table.end():]
    destination = re.search(destination_pattern, without_table, flags=re.I | re.S)
    if destination is None:
        raise AssertionError(f"{purpose} 표 이동 목적지를 찾지 못했습니다: {destination_pattern}")
    return without_table[:destination.start()] + table_html + without_table[destination.start():]


def move_reference_role_after_purpose_table(article: str, role: str, purpose: str) -> str:
    role_match = re.search(
        rf'<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-reference-role="{re.escape(role)}")[^>]*>.*?</(?P=tag)>',
        article,
        flags=re.I | re.S,
    )
    if role_match is None:
        raise AssertionError(f"테스트 원고에 {role} 역할이 없습니다.")
    role_html = role_match.group(0)
    without_role = article[:role_match.start()] + article[role_match.end():]
    table = re.search(
        rf'<table\b(?=[^>]*data-native-table-purpose="{re.escape(purpose)}")[^>]*>.*?</table>',
        without_role,
        flags=re.I | re.S,
    )
    if table is None:
        raise AssertionError(f"테스트 원고에 {purpose} 표가 없습니다.")
    return without_role[:table.end()] + role_html + without_role[table.end():]


def wrap_first_divider_in_structural_section(article: str) -> str:
    divider = re.search(
        r'<hr\b(?=[^>]*data-naver-native-component="divider")[^>]*>',
        article,
        flags=re.I | re.S,
    )
    if divider is None:
        raise AssertionError("테스트 원고에 첫 divider가 없습니다.")
    return (
        article[:divider.start()]
        + '<section data-editorial-beat="first-information-body">'
        + divider.group(0)
        + "</section>"
        + article[divider.end():]
    )


def move_generated_figures_after_section_heading(
    article: str,
    heading_index: int,
    *,
    count: int | None = None,
) -> str:
    figures = list(
        re.finditer(
            r'<figure\b(?=[^>]*data-media-provider="gpt-image")[^>]*>.*?</figure>',
            article,
            flags=re.I | re.S,
        )
    )
    selected = figures if count is None else figures[:count]
    if not selected:
        raise AssertionError("테스트 원고에 GPT 이미지 figure가 없습니다.")
    payload = "".join(match.group(0) for match in selected)
    pieces: list[str] = []
    cursor = 0
    for match in selected:
        pieces.append(article[cursor:match.start()])
        cursor = match.end()
    pieces.append(article[cursor:])
    without_figures = "".join(pieces)
    headings = list(
        re.finditer(
            r'<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-reference-role="section-heading")[^>]*>.*?</(?P=tag)>',
            without_figures,
            flags=re.I | re.S,
        )
    )
    if heading_index < 0 or heading_index >= len(headings):
        raise AssertionError(f"테스트 원고의 {heading_index + 1}번째 설명 소제목을 찾지 못했습니다.")
    destination = headings[heading_index]
    return without_figures[:destination.end()] + payload + without_figures[destination.end():]


def strip_markers_from_section_heading(
    article: str,
    heading_index: int,
    *,
    convert_to_p: bool = False,
) -> str:
    headings = list(
        re.finditer(
            r'<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-reference-role="section-heading")[^>]*>.*?</(?P=tag)>',
            article,
            flags=re.I | re.S,
        )
    )
    if heading_index < 0 or heading_index >= len(headings):
        raise AssertionError(f"테스트 원고의 {heading_index + 1}번째 설명 소제목을 찾지 못했습니다.")
    heading = headings[heading_index]
    replacement = heading.group(0).replace(' data-reference-role="section-heading"', "").replace(
        ' data-naver-native-component="subheading"',
        "",
    )
    if convert_to_p:
        replacement = re.sub(r"^<h[1-6]\b", "<p", replacement, flags=re.I)
        replacement = re.sub(r"</h[1-6]>$", "</p>", replacement, flags=re.I)
    return article[:heading.start()] + replacement + article[heading.end():]


def remove_divider_before_section_heading(article: str, heading_index: int) -> str:
    headings = list(
        re.finditer(
            r'<(?P<tag>[a-z][\w:-]*)\b(?=[^>]*data-reference-role="section-heading")[^>]*>.*?</(?P=tag)>',
            article,
            flags=re.I | re.S,
        )
    )
    if heading_index < 0 or heading_index >= len(headings):
        raise AssertionError(f"테스트 원고의 {heading_index + 1}번째 설명 소제목을 찾지 못했습니다.")
    heading = headings[heading_index]
    dividers = list(
        re.finditer(
            r'<hr\b[^>]*>',
            article[:heading.start()],
            flags=re.I | re.S,
        )
    )
    if not dividers:
        raise AssertionError("테스트 소제목 앞의 divider를 찾지 못했습니다.")
    divider = dividers[-1]
    return article[:divider.start()] + article[divider.end():]


def make_markerless_p_visually_heading_like(
    article: str,
    heading_text_prefix: str,
    *,
    font_size: str = "19px",
    font_weight: str = "700",
) -> str:
    matches = [
        match
        for match in re.finditer(r'<p\b(?=[^>]*style="text-align:center;")[^>]*>.*?</p>', article, flags=re.I | re.S)
        if heading_text_prefix in match.group(0)
    ]
    if len(matches) != 1:
        raise AssertionError("시각 소제목으로 바꿀 markerless p를 찾지 못했습니다.")
    match = matches[0]
    replacement = match.group(0).replace(
        'style="text-align:center;"',
        f'data-mobile-group="true" style="text-align:center;font-size:{font_size};font-weight:{font_weight};"',
        1,
    )
    return article[:match.start()] + replacement + article[match.end():]


def mobile_markup(text: str, *, first_role: str = "") -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len("".join(candidate.split())) > 22:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) == 1:
        midpoint = max(1, len(words) // 2)
        lines = [" ".join(words[:midpoint]), " ".join(words[midpoint:])]
    if len("".join(lines[-1].split())) < 4 and len(lines) > 1:
        merged = f"{lines[-2]} {lines[-1]}"
        if len("".join(merged.split())) <= 24:
            lines[-2:] = [merged]

    sizes: list[int] = []
    remaining = len(lines)
    while remaining:
        if remaining in {2, 3}:
            sizes.append(remaining)
            break
        if remaining == 4:
            sizes.extend([2, 2])
            break
        sizes.append(3)
        remaining -= 3

    parts: list[str] = []
    cursor = 0
    for group_index, size in enumerate(sizes):
        role = f' data-reference-role="{first_role}"' if group_index == 0 and first_role else ""
        group = "<br>".join(lines[cursor:cursor + size])
        cursor += size
        parts.append(
            f'<p data-mobile-group="true"{role} style="margin:0;text-align:center;color:#4D4D4D;font-size:16px;line-height:1.9;word-break:keep-all;">{group}</p>'
        )
        parts.append('<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>')
    return "".join(parts)


def writing_voice_review(
    title: str,
    before_body: list[str],
    final_body: list[str],
    *,
    expressive_jobs: dict[int, str] | None = None,
) -> dict[str, object]:
    expressive_jobs = expressive_jobs or {}
    revisions = [
        {
            "paragraphIndex": index,
            "before": before,
            "after": after,
            "expressiveJob": expressive_jobs.get(
                index,
                "환자가 뜻을 한 번에 알아듣고 실제 장면을 떠올리도록 직접적인 말로 바꿈",
            ),
        }
        for index, (before, after) in enumerate(zip(before_body, final_body), start=1)
        if before != after
    ]
    return {
        "contractId": "writing-voice-final-rehear-v1",
        "skillName": "writing-voice",
        "stage": "after-complete-visible-prose-and-seo-before-production-assembly",
        "beforeTitle": title,
        "beforeBody": before_body,
        "decision": "revised" if revisions else "no-change-needed",
        "reviewChecks": {
            "wholeDraftReadAtSpeakingSpeed": True,
            "openingHookSetReheardTogether": True,
            "genericConnectiveTissueReviewed": True,
            "flattenedRhythmReviewed": True,
            "attentionAllocationReviewed": True,
            "unsupportedPolishReviewed": True,
            "distinctiveGrainPreserved": True,
            "wholeDraftReheardAfterEdits": True,
        },
        "frozenMaterial": {
            "contentAndOrderPreserved": True,
            "factsAndMedicalBoundariesPreserved": True,
            "claimStrengthPreserved": True,
            "referenceMechanismsPreserved": True,
            "keywordAndTitlePromisePreserved": True,
            "htmlComponentsAndLinksPreserved": True,
        },
        "revisions": revisions,
        "finalStatus": "pass",
    }


def valid_article() -> str:
    paragraphs = [
        "안녕하세요, 금손한의원 박준희 원장입니다.",
        f"{KEYWORD}을 찾는 분 가운데 같은 곳이 자꾸 불편해지는 이유를 몰라 치료 선택을 망설이는 분이 있습니다. 오늘은 아픈 곳만 볼 때 놓치기 쉬운 움직임과 생활 조건, 다른 검사를 먼저 생각할 신호까지 설명하겠습니다. 다리 통증도 같은 순서로 살핍니다.",
        "통증은 한 지점에 느껴져도 그 부위만의 문제로 단정하기 어렵습니다. 목을 돌리는 범위, 어깨뼈의 움직임, 골반과 발의 지지처럼 주변 관절이 함께 움직이는 방식을 차분히 비교해야 합니다.",
        "불편이 시작된 날의 활동량과 수면, 오래 유지한 자세도 중요한 단서입니다. 평소와 다른 운동을 했는지, 한쪽 손만 반복해 썼는지, 쉬었을 때와 움직일 때 차이가 있는지를 정리하면 설명이 구체적이 됩니다.",
        f"제가 {KEYWORD} 진료에서 먼저 듣는 것은 증상의 이름보다 생활 속 장면입니다. 같은 어깨 불편이라도 팔을 들 때와 가만히 있을 때의 양상이 다르고, 목이나 등 움직임이 함께 제한되는지도 사람마다 다릅니다.",
        "진찰에서는 좌우의 범위와 힘을 비교하고 몸이 특정 방향을 피하는지 확인합니다. 통증이 강하다는 이유만으로 여러 치료를 한꺼번에 권하기보다 현재 상태에서 무엇이 우선인지 설명하는 과정이 필요합니다.",
        "뼈 손상이나 심한 신경 증상이 의심되면 한의원 치료보다 영상 검사나 다른 의료기관의 평가를 먼저 권할 수 있습니다. 이런 경계를 분명히 하는 것도 환자가 자신의 상태를 안전하게 이해하는 데 필요한 정보입니다.",
        f"{KEYWORD}에서 침이나 추나, 약침을 이야기할 때도 시술 이름부터 나열하지 않습니다. 움직임 제한과 긴장 부위, 생활 속 반복 요인을 구분한 뒤 각 방법을 왜 고려하는지와 선택하지 않아도 되는 상황을 함께 설명합니다.",
        "집에서는 통증을 참으며 큰 동작을 반복하기보다 편안한 범위 안에서 움직임을 관찰해 보세요. 앉는 높이와 화면 위치를 바꾸었을 때 차이가 있는지, 짧게 걸은 뒤 몸이 어떻게 반응하는지 기록하면 다음 상담에 도움이 됩니다.",
        "무리한 스트레칭은 오히려 예민한 부위를 자극할 수 있습니다. 반동을 주지 않고 호흡이 편한 범위에서 시작하며, 저림이나 힘 빠짐처럼 평소와 다른 신호가 나타나면 스스로 판단해 운동을 이어가지 않는 편이 좋습니다.",
        f"저는 {KEYWORD}을 알아보는 분께 치료 횟수보다 먼저 자신의 몸에서 반복되는 조건을 찾으시라고 말씀드립니다. 어떤 자세에서 시작되고 무엇을 바꾸면 덜 불편한지 알면 진료실 밖에서도 관리의 기준을 세울 수 있습니다.",
        "침으로 충분하다고 판단되는 상태라면 비급여 치료를 무리하게 더하지 않습니다. 다른 접근이 필요하다면 그 이유와 예상되는 과정을 설명하고 선택은 환자에게 둔다는 원칙을 지키려 합니다.",
        "한 번의 설명으로 원인이 모두 정리되지 않을 때도 있습니다. 치료 뒤 반응이 예상과 다르거나 회복이 더디다면 처음 판단을 고집하지 않고 움직임과 생활 조건을 다시 살펴 방향을 조정합니다.",
        "진료실에서 설명을 들은 뒤에는 자신의 말로 다시 정리해 보는 과정도 유용합니다. 불편한 위치만 기억하기보다 시작 동작과 지속 시간, 쉬었을 때의 변화를 함께 적어 두면 다음 점검에서 달라진 부분을 비교하기 쉽습니다.",
        "관리 방법은 오래 해야 한다는 부담보다 생활에 붙일 수 있는 작은 변화에서 시작하는 편이 낫습니다. 의자에 앉는 위치를 조정하고 한 자세를 오래 유지하지 않으며, 몸이 보내는 신호를 기준으로 활동 강도를 조절해 보세요.",
        f"결국 {KEYWORD} 선택에서 중요한 것은 화려한 시술 목록보다 자신의 질문에 구체적인 답을 들을 수 있는지입니다. 필요한 경우 의료진과 현재 상태를 상의하며 검사와 관리의 순서를 차분히 정해 보셔도 좋습니다.",
        "몸의 신호를 이해하는 데 이 글이 작은 기준이 되었으면 합니다. 문의가 필요하다면 현재 가장 불편한 동작과 시작 시점, 함께 나타나는 증상을 정리해 알려 주시면 상담 내용을 더 분명하게 나눌 수 있습니다.",
    ]
    credential_table = table_markup(
        "credential",
        [
            [
                ("금손한의원 소개", "background-color:#C99F75;color:#FFFFFF;font-weight:700;"),
            ],
            [
                ("11년차 한의사 · 2016년 개원", "color:#4D4D4D;"),
            ],
            [
                ("통증·체형·움직임·생활습관을 함께 확인", "color:#4D4D4D;"),
            ],
            [
                ("필요한 치료만 설명하는 과잉 권유 없는 진료", "color:#4D4D4D;"),
            ],
            [
                ("골타요법 관련 교육 · 한방비만치료 전문가과정 수료", "color:#4D4D4D;"),
            ],
            [
                ("근골격계부터 소화·호흡기·여성·소아·보약까지 진료", "color:#4D4D4D;"),
            ],
            [
                ("월·수·금 야간 · 토·일·공휴일 진료", "color:#4D4D4D;"),
            ],
        ],
        attributes='data-reference-role="credential-proof" data-goldhand-role="proof"',
    )
    body_parts: list[str] = [
        '<p data-reference-role="greeting-authority" style="margin:0;text-align:center;color:#4D4D4D;font-size:16px;line-height:1.9;word-break:keep-all;">안녕하세요, 금손한의원 박준희 원장입니다.</p>',
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>',
        '<section data-reference-role="solution-preview">',
        mobile_markup(paragraphs[1]),
        '</section>',
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>',
        credential_table,
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>',
    ]
    heading_before = {
        2: "통증 부위보다 먼저 볼 것",
        7: "치료 선택을 설명하는 기준",
        12: "경과를 다시 살피는 이유",
    }
    for index, paragraph in enumerate(paragraphs[2:], start=2):
        if index in heading_before:
            body_parts.append(divider_markup())
            body_parts.append(
                f'<h2 data-naver-native-component="subheading" data-reference-role="section-heading" style="text-align:center;">{heading_before[index]}</h2>'
            )
            body_parts.append('<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>')
        role = "explanation" if index == 2 else "neutral-close" if index == 16 else ""
        body_parts.append(mobile_markup(paragraph, first_role=role))
    body_parts.append(mobile_markup(
        "아픈 곳만 보지 말고 언제 어떤 동작에서 다시 아픈지도 함께 봐야 합니다."
    ))
    body_parts.append(
        table_markup(
            "article-summary",
            [
                [
                    ("살필 조건", "background-color:#C99F75;color:#FFFFFF;font-weight:700;text-align:center;"),
                    ("기록할 내용", "background-color:#C99F75;color:#FFFFFF;font-weight:700;text-align:center;"),
                ],
                [
                    ("한 자세", "background-color:#F3E8DD;color:#7A5434;font-weight:700;text-align:center;"),
                    ("유지 시간과 몸의 위치", "color:#4D4D4D;"),
                ],
                [
                    ("피하는 동작", "background-color:#F3E8DD;color:#7A5434;font-weight:700;text-align:center;"),
                    ("멈추는 지점과 좌우 차이", "color:#4D4D4D;"),
                ],
            ],
        )
    )
    body_parts.append('<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>')
    body = "".join(body_parts)
    body = body.replace(
        "같은 곳이 자꾸<br>불편해지는 이유를 몰라",
        '<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">같은 곳이 자꾸<br>불편해지는 이유</span>를 몰라',
        1,
    ).replace(
        "통증 부위보다 먼저 볼 것",
        '<u data-reference-underline-role="key-point">통증 부위보다 먼저 볼 것</u>',
        1,
    ).replace(
        "치료 선택을 설명하는 기준",
        '<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">치료 선택을 설명하는 기준</span>',
        1,
    ).replace(
        "경과를 다시 살피는 이유",
        '<u data-reference-underline-role="key-point">경과를 다시 살피는 이유</u>',
        1,
    ).replace(
        "아픈 곳만 보지 말고",
        '<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">아픈 곳만 보지 말고</span>',
        1,
    ).replace(
        "영상 검사나 다른 의료기관의 평가",
        '<span data-goldhand-emphasis="red" style="color:#E53935;font-weight:700;">영상 검사나 다른 의료기관의 평가</span>',
        1,
    ).replace(
        "운동을 이어가지 않는 편",
        '<span data-goldhand-emphasis="red" style="color:#E53935;font-weight:700;">운동을 이어가지 않는 편</span>',
        1,
    )
    clinic_hours = table_markup(
        "clinic-hours",
        [
            [
                ("요일", "width:24%;background-color:#C99F75;color:#FFFFFF;font-weight:700;"),
                ("진료시간", "width:38%;background-color:#C99F75;color:#FFFFFF;font-weight:700;"),
                ("비고", "width:38%;background-color:#C99F75;color:#FFFFFF;font-weight:700;"),
            ],
            [
                ("월·수·금", "width:24%;background-color:#F3E8DD;color:#7A5434;font-weight:700;"),
                ("09:30~20:00", "width:38%;color:#4D4D4D;"),
                ("야간 진료", "width:38%;color:#4D4D4D;"),
            ],
            [
                ("화·목", "width:24%;background-color:#F3E8DD;color:#7A5434;font-weight:700;"),
                ("09:30~18:00", "width:38%;color:#4D4D4D;"),
                ("&nbsp;", "width:38%;color:#4D4D4D;"),
            ],
            [
                ("토·일", "width:24%;background-color:#F3E8DD;color:#7A5434;font-weight:700;"),
                ("09:00~13:00", "width:38%;color:#4D4D4D;"),
                ("&nbsp;", "width:38%;color:#4D4D4D;"),
            ],
        ],
        attributes='data-reference-role="clinic-hours"',
    )
    contact = table_markup(
        "clinic-info",
        [
            [
                ("금손한의원", "width:100%;background-color:#C99F75;color:#FFFFFF;font-weight:700;"),
            ],
            [
                ("위치<br>전남광주통합특별시 서구 유림로98번길 3, 2층", "width:100%;color:#4D4D4D;"),
            ],
            [
                ("찾아오는 길<br>동천파출소·동천동 행정복지센터 건너편", "width:100%;background-color:#FBF8F4;color:#4D4D4D;"),
            ],
            [
                ("전화 062-515-7582", "width:100%;color:#7A5434;font-size:19px;font-weight:700;"),
            ],
        ],
        attributes='data-goldhand-role="contact" data-reference-role="contact"',
    )
    return f"""
    <article data-goldhand-type="정보전달형" data-master-reference-id="INFO03"
      data-writing-voice-review="writing-voice-final-rehear-v1"
      data-writing-voice-status="pass"
      data-decoration-master-reference-id="INFO03"
      data-reference-source="https://blog.naver.com/wi-parkclinic/224337414108"
      data-goldhand-design-system="goldhand-naver-native-v4"
      style="width:100%;max-width:580px;margin:0 auto;color:#4D4D4D;text-align:center;">
      {question_markup("통증이 반복되는 이유를 아픈 곳에서만 찾아도 될까요?")}
      {question_markup(QUESTION_TWO)}
      {BODY_OPEN}{body}</section>
      <p data-reference-role="clinic-hours-heading" style="text-align:center;">진료시간 안내</p>
      {clinic_hours}{contact}
    </article>
    """


def editorial_close_article(*, include_summary: bool = True, one_question: bool = False) -> str:
    article = valid_article().replace(
        'data-goldhand-type="정보전달형"',
        'data-goldhand-type="정보전달형" '
        'data-editorial-master-id="BM224231647991" '
        'data-editorial-reference-source="https://blog.naver.com/beomeo_sm/224231647991" '
        'data-editorial-source-role="title-tone-content-sequence-only" '
        'data-editorial-profile-status="ready"',
        1,
    )
    article = article.replace(KEYWORD, "동천동 진료", 2)
    article = article.replace(
        '<section data-reference-role="solution-preview">',
        '<section data-reference-role="solution-preview" '
        'data-intro-persuasion-device="specific-number-low-friction-topic-payoff" '
        'data-reader-payoff="다른 검사를 먼저 생각할 신호">',
        1,
    )
    article = article.replace(
        'data-reference-role="neutral-close"',
        'data-reference-role="neutral-close" data-closing-payoff="몸의 신호"',
        1,
    )
    reading_hook = (
        '<p data-reference-role="reading-time-hook" data-reading-minutes="3" data-mobile-group="true" '
        'style="margin:0;text-align:center;color:#4D4D4D;font-size:16px;line-height:1.9;word-break:keep-all;">'
        '다리 통증도 함께 반복된다면,<br>딱 3분만 읽어 보세요.</p>'
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>'
    )
    article = article.replace("</section>", reading_hook + "</section>", 1)
    for index, heading in enumerate(
        ("통증 부위보다 먼저 볼 것", "치료 선택을 설명하는 기준", "경과를 다시 살피는 이유"),
        start=1,
    ):
        article = article.replace(heading, f"{index}. {heading}", 1)
    for image_index, anchor in enumerate(("주변 관절", "활동량", "진찰에서는"), start=1):
        generated_figure = (
            '<figure data-media-provider="gpt-image" data-image-zone="early-explanatory-body" '
            'data-image-placement="after-related-paragraph" '
            f'data-image-anchor="{anchor}" data-generation-reference-creator="callilife" '
            'data-generation-owner-authorization="user-confirmed" '
            'data-generation-content-preservation="medical-information-layout" '
            'data-generation-variation-mode="person-identity-subtle-variation" '
            'style="text-align:center;">'
            '<img data-media-provider="gpt-image" '
            f'data-local-image="{GPT_IMAGE_FIXTURE}" '
            'data-generation-reference-creator="callilife" '
            f'data-generation-reference-url="https://ogqmarket.naver.com/artworks/stockImage/detail?artworkId=623801a0b4e1{image_index}" '
            'data-generation-owner-authorization="user-confirmed" '
            'data-generation-content-preservation="medical-information-layout" '
            'data-generation-variation-mode="person-identity-subtle-variation" '
            'src="data:," alt="어깨 관절 운동 범위 설명 이미지"></figure>'
        )
        related_paragraph = re.search(
            rf'<p\b(?=[^>]*data-mobile-group="true")[^>]*>.*?{re.escape(anchor)}.*?</p>'
            r'\s*<p\b(?=[^>]*data-preview-gap="true")[^>]*>.*?</p>',
            article,
            flags=re.I | re.S,
        )
        if related_paragraph is None:
            raise AssertionError(f"GPT 이미지 앞에 둘 모바일 문단을 찾지 못했습니다: {anchor}")
        article = article[:related_paragraph.end()] + generated_figure + article[related_paragraph.end():]
    media_library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
    media_by_id = {item["id"]: item for item in media_library["assets"]}
    media_id = "GH0016"
    anchor = "다리 통증"
    asset = media_by_id[media_id]
    figure = (
        f'<figure data-reference-role="evidence-media" data-goldhand-role="media" '
        f'data-real-photo="true" data-real-photo-slot="before-credential" '
        f'data-media-origin="goldhand-bundled-official-library" '
        f'data-goldhand-media="{media_id}" data-image-placement="after-related-paragraph" '
        f'data-image-anchor="{anchor}" style="margin:28px auto;text-align:center;max-width:580px;">'
        f'<img src="{asset["url"]}" data-real-photo="true" '
        f'data-media-origin="goldhand-bundled-official-library" data-goldhand-media="{media_id}" '
        f'data-media-sha256="{asset["sha256"]}" '
        f'data-reference-source-url="{asset["url"]}" referrerpolicy="no-referrer" '
        f'alt="{asset["approvedAlt"]}" style="display:block;width:100%;height:auto;margin:0 auto;"></figure>'
    )
    solution = re.search(r'<section\b(?=[^>]*data-reference-role="solution-preview")[^>]*>.*?</section>', article, flags=re.I | re.S)
    if solution is None:
        raise AssertionError("실제 사진 앞 solution-preview를 찾지 못했습니다.")
    article = article[:solution.end()] + figure + article[solution.end():]
    trust_id = "GH0042"
    trust_asset = media_by_id[trust_id]
    trust_anchor = trust_asset["closingTrustPlacementTerms"][0]
    trust_context = trust_asset["closingTrustContextText"]
    trust_context_markup = trust_context.replace("와 업무협약", "와<br>업무협약").replace("맺고 기념촬영", "맺고<br>기념촬영")
    trust_block = (
        '<p data-reference-role="credential-trust-context" data-goldhand-role="proof" '
        'data-mobile-group="true" style="margin:0;text-align:center;color:#4D4D4D;'
        f'font-size:16px;line-height:1.9;word-break:keep-all;">{trust_context_markup}</p>'
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>'
        '<figure data-reference-role="credential-trust-media" data-goldhand-role="proof" '
        'data-trust-photo="true" data-trust-photo-slot="closing-credential-trust" '
        'data-media-origin="goldhand-bundled-official-library" '
        f'data-goldhand-media="{trust_id}" data-image-placement="after-related-paragraph" '
        f'data-image-anchor="{trust_anchor}" style="margin:28px auto;text-align:center;max-width:580px;">'
        f'<img src="{trust_asset["url"]}" data-trust-photo="true" '
        'data-media-origin="goldhand-bundled-official-library" '
        f'data-goldhand-media="{trust_id}" data-media-sha256="{trust_asset["sha256"]}" '
        f'data-reference-source-url="{trust_asset["url"]}" referrerpolicy="no-referrer" '
        f'alt="{trust_asset["closingTrustApprovedAlt"]}" '
        'style="display:block;width:100%;height:auto;margin:0 auto;"></figure>'
        '<p data-preview-gap="true" aria-hidden="true" style="margin:0;text-align:center;color:transparent;">&#8288;</p>'
    )
    article = article.replace(
        '<p data-reference-role="clinic-hours-heading"',
        trust_block + '<p data-reference-role="clinic-hours-heading"',
        1,
    )
    if one_question:
        article = article.replace(question_markup(QUESTION_TWO), "", 1)
    if not include_summary:
        article = re.sub(
            r'<table\b(?=[^>]*data-native-table-purpose="article-summary")[^>]*>.*?</table>',
            "",
            article,
            count=1,
            flags=re.I | re.S,
        )
    return article


def editorial_fixture_media_library() -> dict[str, dict[str, object]]:
    """Keep generic article tests focused while production assets stay scene-specific."""
    payload = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
    assets = {item["id"]: dict(item) for item in payload["assets"]}
    return assets


def wipark_editorial_close_article() -> str:
    return editorial_close_article().replace(
        'data-editorial-master-id="BM224231647991"',
        'data-editorial-master-id="WP224337414108"',
        1,
    ).replace(
        'data-editorial-reference-source="https://blog.naver.com/beomeo_sm/224231647991"',
        'data-editorial-reference-source="https://blog.naver.com/wi-parkclinic/224337414108"',
        1,
    ).replace(
        'data-editorial-source-role="title-tone-content-sequence-only"',
        'data-editorial-source-role="editorial-reasoning-content-flow-and-expression-principles"',
        1,
    ).replace(
        'data-editorial-profile-status="ready"',
        'data-editorial-profile-status="ready" '
        'data-reference-writing-profile="INFO03" '
        'data-reference-writing-intelligence="goldhand-reference-writing-intelligence-v1" '
        'data-title-mechanism="urgent-questions-with-direct-answer" '
        'data-closing-mechanism="two-answer-recap-and-calm-next-step"',
        1,
    )


def editorial_fidelity_article() -> str:
    beats = [
        "exercise-effort-frustration",
        "exercise-matters-but-is-not-a-direct-calorie-equation",
        "why-weight-loss-can-stall-despite-exercise",
        "exercise-still-matters-for-loss-and-maintenance",
        "practical-management-direction",
    ]
    body = "".join(
        f'<section data-editorial-beat="{beat}">{index}번째 새 금손 설명 문단입니다.</section>'
        for index, beat in enumerate(beats, start=1)
    )
    return (
        '<article data-editorial-master-id="BM224231647991" '
        'data-editorial-reference-source="https://blog.naver.com/beomeo_sm/224231647991" '
        'data-editorial-source-role="title-tone-content-sequence-only" '
        'data-editorial-profile-status="ready" '
        'data-reference-source="https://blog.naver.com/wi-parkclinic/224337414108">'
        f"{body}</article>"
    )


class TitleTests(unittest.TestCase):
    def test_editorial_close_numeric_title_passes(self) -> None:
        intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(encoding="utf-8")
        )
        result = TITLE_VALIDATOR.validate_title(
            "광주 한의원 추천, 운동해도 살이 안 빠지는 3가지 이유",
            "광주 한의원 추천",
            answer_count=3,
            editorial_close=True,
            writing_intelligence=intelligence,
            reference_master_id="INFO12",
            title_mechanism_id="same-effort-different-result-plus-success-conditions",
        )
        self.assertEqual(result["status"], "pass", result)
        self.assertTrue(result["metrics"]["editorialClose"])

    def test_editorial_close_title_without_number_can_follow_reference_psychology(self) -> None:
        intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(encoding="utf-8")
        )
        result = TITLE_VALIDATOR.validate_title(
            "광주 한의원 추천, 검사에선 괜찮다는데 계단에서 왜 아플까요?",
            "광주 한의원 추천",
            editorial_close=True,
            writing_intelligence=intelligence,
            reference_master_id="INFO06",
            title_mechanism_id="test-normal-but-pain-remains-question",
        )
        self.assertNotEqual(result["status"], "fail", result)
        self.assertEqual(result["metrics"]["answerPromises"], [])

    def test_editorial_close_rejects_title_mechanism_from_another_reference(self) -> None:
        intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(encoding="utf-8")
        )
        result = TITLE_VALIDATOR.validate_title(
            "광주 한의원 추천, 검사에선 괜찮다는데 계단에서 왜 아플까요?",
            "광주 한의원 추천",
            editorial_close=True,
            writing_intelligence=intelligence,
            reference_master_id="INFO06",
            title_mechanism_id="responder-versus-nonresponder-contrast",
        )
        self.assertIn("title-mechanism-mismatch", {item["code"] for item in result["issues"]})

    def test_valid_title_is_not_blocked(self) -> None:
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        library = json.loads((SKILL_DIR / "assets" / "topic-idea-library.json").read_text(encoding="utf-8"))
        result = TITLE_VALIDATOR.validate_title(
            TITLE,
            KEYWORD,
            evidence=evidence,
            library=library,
            idea_reference_id="WP224205420099",
            pattern_id="how-to-principle",
        )
        self.assertNotEqual(result["status"], "fail", result)

    def test_duplicate_keyword_and_daily_post_fail(self) -> None:
        result = TITLE_VALIDATOR.validate_title(f"{KEYWORD} {KEYWORD} 일상글", KEYWORD)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("title-keyword-count", codes)
        self.assertIn("daily-post", codes)

    def test_numbered_promise_requires_matching_answer_count(self) -> None:
        title = f"{KEYWORD} 반복 통증을 살피는 세 가지 기준".replace("세 가지", "3가지")
        result = TITLE_VALIDATOR.validate_title(title, KEYWORD, answer_count=2)
        self.assertIn("answer-count-mismatch", {item["code"] for item in result["issues"]})

    def test_reference_business_and_pattern_mismatch_fail(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "topic-idea-library.json").read_text(encoding="utf-8"))
        result = TITLE_VALIDATOR.validate_title(
            f"{KEYWORD} 위석부부한의원 방식으로 살피는 기준",
            KEYWORD,
            library=library,
            idea_reference_id="WP224205420099",
            pattern_id="warning-consequence",
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("reference-business-leak", codes)
        self.assertIn("title-pattern-mismatch", codes)


class ArticleTests(unittest.TestCase):
    def test_valid_article_passes(self) -> None:
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        result = ARTICLE_VALIDATOR.validate_article(valid_article(), TITLE, KEYWORD, evidence=evidence)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["bodyKeywordCount"], 5)

    def test_contact_keyword_does_not_change_body_count(self) -> None:
        article = valid_article().replace("금손한의원</td>", f"금손한의원 {KEYWORD}</td>", 1)
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD, evidence=evidence)
        self.assertEqual(result["metrics"]["bodyKeywordCount"], 5, result)

    def test_forbidden_claims_fail(self) -> None:
        article = valid_article().replace("작은 기준이 되었으면<br>합니다", "완치를 100% 보장한다고<br>말합니다")
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("guarantee", codes)

    def test_beomeo_topic_source_cannot_leak_into_article(self) -> None:
        article = valid_article().replace(
            "몸의 신호",
            "설명한의원 엑소웨이브 https://blog.naver.com/beomeo_sm/224324776990",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("topic-source-business-leak", codes)
        self.assertIn("topic-source-url-leak", codes)

    def test_duplicate_h1_fails(self) -> None:
        article = valid_article().replace(BODY_OPEN, f"<h1>{TITLE}</h1>{BODY_OPEN}", 1)
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        self.assertIn("duplicate-title-heading", {item["code"] for item in result["issues"]})

    def test_one_or_four_reader_questions_fail_but_three_passes(self) -> None:
        one = valid_article().replace(
            question_markup(QUESTION_TWO),
            "",
        )
        one_result = ARTICLE_VALIDATOR.validate_article(one, TITLE, KEYWORD)
        self.assertIn("reader-question-count", {item["code"] for item in one_result["issues"]})
        three = valid_article().replace(
            BODY_OPEN,
            question_markup("생활 관리는 어디부터 바꿔야 할까요?") + BODY_OPEN,
            1,
        )
        three_result = ARTICLE_VALIDATOR.validate_article(three, TITLE, KEYWORD)
        self.assertNotIn("reader-question-count", {item["code"] for item in three_result["issues"]})
        four = three.replace(
            BODY_OPEN,
            question_markup("진료 뒤에는 무엇을 기록하면 좋을까요?") + BODY_OPEN,
            1,
        )
        four_result = ARTICLE_VALIDATOR.validate_article(four, TITLE, KEYWORD)
        self.assertIn("reader-question-count", {item["code"] for item in four_result["issues"]})

    def test_solution_preview_is_required_before_body(self) -> None:
        missing = valid_article().replace(' data-reference-role="solution-preview"', "", 1)
        result = ARTICLE_VALIDATOR.validate_article(missing, TITLE, KEYWORD)
        self.assertIn("solution-preview-count", {item["code"] for item in result["issues"]})

    def test_credential_table_is_between_solution_preview_and_first_body_section(self) -> None:
        article = valid_article()
        solution = re.search(
            r'<section\b(?=[^>]*data-reference-role="solution-preview")[^>]*>.*?</section>',
            article,
            flags=re.I | re.S,
        )
        credential = re.search(
            r'<table\b(?=[^>]*data-native-table-purpose="credential")[^>]*>.*?</table>',
            article,
            flags=re.I | re.S,
        )
        first_body_marker = re.search(
            r'<hr\b(?=[^>]*data-naver-native-component="divider")[^>]*>'
            r'|<[a-z][\w:-]*\b(?=[^>]*data-reference-role="section-heading")[^>]*>',
            article,
            flags=re.I | re.S,
        )
        self.assertIsNotNone(solution)
        self.assertIsNotNone(credential)
        self.assertIsNotNone(first_body_marker)
        assert solution is not None and credential is not None and first_body_marker is not None
        self.assertLess(solution.end(), credential.start())
        self.assertLess(credential.end(), first_body_marker.start())
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        placement_codes = {
            item["code"]
            for item in result["issues"]
            if item["code"].startswith("credential-")
        }
        self.assertEqual(placement_codes, set(), result)
        self.assertEqual(ARTICLE_VALIDATOR.credential_placement_issues(article), [])

    def test_credential_table_before_solution_preview_fails(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<section\b(?=[^>]*data-reference-role="solution-preview")',
        )
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        self.assertIn("credential-before-solution-preview", {item["code"] for item in result["issues"]})

    def test_credential_table_at_old_end_position_fails(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<table\b(?=[^>]*data-native-table-purpose="clinic-info")',
        )
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        self.assertIn("credential-after-first-body-marker", {item["code"] for item in result["issues"]})

    def test_credential_gaps_reject_intervening_paragraph_and_image(self) -> None:
        paragraph_article = insert_after_reference_role(
            valid_article(),
            "solution-preview",
            '<p data-mobile-group="true" style="text-align:center;">중간 본문입니다.<br>여기에 오면 안 됩니다.</p>',
        )
        paragraph_result = ARTICLE_VALIDATOR.validate_article(paragraph_article, TITLE, KEYWORD)
        self.assertIn(
            "credential-not-immediately-after-solution-preview",
            {item["code"] for item in paragraph_result["issues"]},
        )

        image_article = insert_after_purpose_table(
            valid_article(),
            "credential",
            '<img src="data:image/png;base64,AA==" alt="중간 이미지">',
        )
        image_result = ARTICLE_VALIDATOR.validate_article(image_article, TITLE, KEYWORD)
        self.assertIn(
            "credential-not-immediately-before-first-body-marker",
            {item["code"] for item in image_result["issues"]},
        )

    def test_intro_role_after_credential_fails(self) -> None:
        for role in ("greeting-authority", "reader-question"):
            with self.subTest(role=role):
                article = move_reference_role_after_purpose_table(
                    valid_article(),
                    role,
                    "credential",
                )
                result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
                self.assertIn("intro-role-after-credential", {item["code"] for item in result["issues"]})

    def test_empty_structural_wrapper_before_first_divider_is_allowed(self) -> None:
        article = wrap_first_divider_in_structural_section(valid_article())
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        placement_codes = {
            item["code"]
            for item in result["issues"]
            if item["code"].startswith("credential-") or item["code"] == "intro-role-after-credential"
        }
        self.assertEqual(placement_codes, set(), result)

    def test_reader_questions_are_representative_not_claimed_patient_quotes(self) -> None:
        missing_source = valid_article().replace(
            ' data-question-source="representative-reader-concern"',
            "",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(missing_source, TITLE, KEYWORD)
        self.assertIn("reader-question-source-missing", {item["code"] for item in result["issues"]})

    def test_greeting_before_hooks_is_rejected(self) -> None:
        article = valid_article()
        greeting = re.search(
            r'<p\b(?=[^>]*data-reference-role="greeting-authority")[^>]*>.*?</p>'
            r'\s*<p\b(?=[^>]*data-preview-gap="true")[^>]*>.*?</p>',
            article,
            flags=re.I | re.S,
        )
        self.assertIsNotNone(greeting)
        assert greeting is not None
        article = article[:greeting.start()] + article[greeting.end():]
        article = re.sub(r"(<article\b[^>]*>)", r"\1" + greeting.group(0), article, count=1, flags=re.I | re.S)
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("opening-hook-greeting-order", codes, result)
        self.assertIn("greeting-position", codes, result)

    def test_real_photo_requires_asset_specific_context_and_alt(self) -> None:
        article = editorial_close_article().replace(
            'data-image-anchor="다리 통증"',
            'data-image-anchor="진료"',
            1,
        ).replace(
            'alt="박준희 원장이 방문진료에서 환자의 다리에 침 치료를 하는 장면"',
            'alt="진료 모습"',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("real-photo-anchor-not-approved", codes, result)
        self.assertIn("real-photo-alt-mismatch", codes, result)

    def test_immediately_previous_real_photo_cannot_be_reused(self) -> None:
        article = editorial_close_article()
        library = editorial_fixture_media_library()
        fresh_result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=library,
            recent_media_ids={"GH0017"},
        )
        self.assertNotIn(
            "immediately-previous-real-photo-repeat",
            {item["code"] for item in fresh_result["issues"]},
            fresh_result,
        )
        repeated_result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=library,
            recent_media_ids={"GH0016"},
        )
        self.assertIn(
            "immediately-previous-real-photo-repeat",
            {item["code"] for item in repeated_result["issues"]},
            repeated_result,
        )

    def test_immediately_previous_closing_trust_photo_cannot_be_reused(self) -> None:
        article = editorial_close_article()
        library = editorial_fixture_media_library()
        fresh_result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=library,
            recent_trust_media_ids={"GH0029"},
        )
        self.assertNotIn(
            "immediately-previous-trust-photo-repeat",
            {item["code"] for item in fresh_result["issues"]},
            fresh_result,
        )
        repeated_result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=library,
            recent_trust_media_ids={"GH0042"},
        )
        self.assertIn(
            "immediately-previous-trust-photo-repeat",
            {item["code"] for item in repeated_result["issues"]},
            repeated_result,
        )

    def test_mobile_four_line_group_fails(self) -> None:
        article = valid_article().replace(
            "통증은 한 지점에 느껴져도 그 부위만의 문제로<br>단정하기 어렵습니다. 목을 돌리는 범위, 어깨뼈의",
            "통증은 한 지점에<br>느껴져도 그 부위만의<br>문제로 단정하기 어렵습니다.<br>목을 돌리는 범위, 어깨뼈의",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        self.assertIn("mobile-group-line-count", {item["code"] for item in result["issues"]})

    def test_unmarked_mobile_paragraph_fails(self) -> None:
        article = valid_article().replace(' data-mobile-group="true"', "", 1)
        result = ARTICLE_VALIDATOR.validate_article(article, TITLE, KEYWORD)
        self.assertIn("mobile-group-marker-missing", {item["code"] for item in result["issues"]})

    def test_editorial_close_allows_two_or_three_body_keywords(self) -> None:
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        article = editorial_close_article()
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            evidence=evidence,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["bodyKeywordCount"], 3)
        self.assertEqual(result["metrics"]["editorialMasterId"], "BM224231647991")
        self.assertEqual(result["metrics"]["generatedImages"], 3)
        self.assertEqual(result["metrics"]["realPhotos"], 1)

    def test_specific_number_intro_requires_one_reading_time_hook(self) -> None:
        article = re.sub(
            r'<p\b(?=[^>]*data-reference-role="reading-time-hook")[^>]*>.*?</p>',
            "",
            editorial_close_article(),
            count=1,
            flags=re.I | re.S,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        self.assertIn("reading-time-hook-count", {item["code"] for item in result["issues"]})

    def test_specific_number_intro_allows_two_minutes_with_topic_payoff(self) -> None:
        article = editorial_close_article().replace(
            'data-reading-minutes="3"', 'data-reading-minutes="2"', 1
        ).replace("3분만 읽어", "2분만 읽어", 1)
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            evidence=evidence,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["introPersuasionDeviceId"], "specific-number-low-friction-topic-payoff")

    def test_non_time_intro_device_does_not_require_reading_time_hook(self) -> None:
        article = re.sub(
            r'<p\b(?=[^>]*data-reference-role="reading-time-hook")[^>]*>.*?</p>',
            "",
            editorial_close_article().replace(
                "specific-number-low-friction-topic-payoff",
                "contrast-self-identification",
                1,
            ),
            count=1,
            flags=re.I | re.S,
        )
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            evidence=evidence,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertEqual(result["status"], "pass", result)

    def test_editorial_close_requires_visible_topic_specific_payoff(self) -> None:
        article = editorial_close_article().replace(
            ' data-reader-payoff="다른 검사를 먼저 생각할 신호"',
            "",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        self.assertIn("reader-payoff-missing", {item["code"] for item in result["issues"]})

    def test_editorial_close_requires_intro_highlight(self) -> None:
        article = editorial_close_article().replace(
            '<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">같은 곳이 자꾸<br>불편해지는 이유</span>',
            "같은 곳이 자꾸<br>불편해지는 이유",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        self.assertIn("intro-highlight-count", {item["code"] for item in result["issues"]})

    def test_editorial_close_rejects_invalid_generated_image_contract(self) -> None:
        article = editorial_close_article().replace(
            'data-generation-owner-authorization="user-confirmed"',
            'data-generation-owner-authorization="missing"',
        ).replace(
            'data-generation-content-preservation="medical-information-layout"',
            'data-generation-content-preservation="missing"',
        ).replace(
            'data-generation-variation-mode="person-identity-subtle-variation"',
            'data-generation-variation-mode="full-replica"',
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("generated-owner-authorization-missing", codes)
        self.assertIn("generated-content-preservation-missing", codes)
        self.assertIn("generated-variation-mode-invalid", codes)

    def test_editorial_close_rejects_generated_image_without_related_placement(self) -> None:
        article = editorial_close_article().replace(
            '<figure data-media-provider="gpt-image" data-image-zone="early-explanatory-body" data-image-placement="after-related-paragraph" ',
            '<figure data-media-provider="gpt-image" data-image-zone="early-explanatory-body" ',
            1,
        ).replace(
            'data-image-anchor="주변 관절"',
            'data-image-anchor="소화"',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("generated-image-placement-marker", codes)
        self.assertIn("generated-image-anchor-mismatch", codes)

    def test_editorial_close_rejects_generated_image_after_second_body_section(self) -> None:
        article = move_generated_figures_after_section_heading(
            editorial_close_article(),
            2,
            count=1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertIn(
            "generated-image-outside-early-body",
            {item["code"] for item in result["issues"]},
            result,
        )

    def test_editorial_close_requires_generated_image_in_first_body_section(self) -> None:
        article = move_generated_figures_after_section_heading(
            editorial_close_article(),
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertIn(
            "generated-image-first-section-missing",
            {item["code"] for item in result["issues"]},
            result,
        )

    def test_editorial_close_requires_both_section_heading_markers(self) -> None:
        for removed_marker in (
            ' data-reference-role="section-heading"',
            ' data-naver-native-component="subheading"',
        ):
            with self.subTest(removed_marker=removed_marker):
                article = editorial_close_article().replace(removed_marker, "")
                result = ARTICLE_VALIDATOR.validate_article(
                    article,
                    EDITORIAL_TITLE,
                    KEYWORD,
                    editorial_close=True,
                    media_library=editorial_fixture_media_library(),
                )
                codes = {item["code"] for item in result["issues"]}
                self.assertIn("section-heading-markers-invalid", codes, result)
                self.assertIn("body-section-heading-missing", codes, result)

    def test_editorial_close_cannot_hide_third_p_heading_by_removing_both_markers(self) -> None:
        article = move_generated_figures_after_section_heading(
            editorial_close_article(),
            2,
            count=1,
        )
        article = strip_markers_from_section_heading(article, 2, convert_to_p=True)
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("section-heading-markers-invalid", codes, result)
        self.assertIn("generated-image-outside-early-body", codes, result)

    def test_editorial_close_cannot_hide_third_section_by_removing_divider_and_markers(self) -> None:
        cases = (
            (False, "19px", "700"),
            (True, "19px", "700"),
            (True, "19px", "650"),
            (True, "100px", "700"),
            (True, "16px;font-size:19px", "700"),
            (True, "19px", "400;font-weight:700"),
        )
        for convert_to_p, font_size, font_weight in cases:
            with self.subTest(convert_to_p=convert_to_p, font_size=font_size, font_weight=font_weight):
                article = move_generated_figures_after_section_heading(
                    editorial_close_article(),
                    2,
                    count=1,
                )
                article = remove_divider_before_section_heading(article, 2)
                article = strip_markers_from_section_heading(article, 2, convert_to_p=convert_to_p)
                if convert_to_p:
                    article = make_markerless_p_visually_heading_like(
                        article,
                        "3. ",
                        font_size=font_size,
                        font_weight=font_weight,
                    )
                result = ARTICLE_VALIDATOR.validate_article(
                    article,
                    EDITORIAL_TITLE,
                    KEYWORD,
                    editorial_close=True,
                    media_library=editorial_fixture_media_library(),
                )
                codes = {item["code"] for item in result["issues"]}
                self.assertIn("section-heading-divider-pair-invalid", codes, result)
                self.assertIn("generated-image-outside-early-body", codes, result)

    def test_editorial_close_requires_three_to_four_generated_images(self) -> None:
        article = re.sub(
            r'<figure\b(?=[^>]*data-media-provider="gpt-image")[^>]*>.*?</figure>',
            "",
            editorial_close_article(),
            count=1,
            flags=re.I | re.S,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertIn("generated-image-count", {item["code"] for item in result["issues"]})

    def test_editorial_close_requires_one_or_two_real_photos(self) -> None:
        article = re.sub(
            r'<figure\b(?=[^>]*data-real-photo="true")[^>]*>.*?</figure>',
            "",
            editorial_close_article(),
            count=1,
            flags=re.I | re.S,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
        )
        self.assertIn("real-photo-count", {item["code"] for item in result["issues"]})
        self.assertEqual(result["metrics"]["trustPhotos"], 1)

    def test_editorial_close_requires_one_separate_closing_trust_photo(self) -> None:
        article = re.sub(
            r'<figure\b(?=[^>]*data-trust-photo="true")[^>]*>.*?</figure>',
            "",
            editorial_close_article(),
            count=1,
            flags=re.I | re.S,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
            media_library=editorial_fixture_media_library(),
        )
        self.assertIn("trust-photo-count", {item["code"] for item in result["issues"]})
        self.assertEqual(result["metrics"]["realPhotos"], 1)

    def test_editorial_close_rejects_real_photo_without_related_placement(self) -> None:
        article = editorial_close_article().replace(
            'data-real-photo="true" data-real-photo-slot="before-credential" '
            'data-media-origin="goldhand-bundled-official-library" '
            'data-goldhand-media="GH0016" data-image-placement="after-related-paragraph"',
            'data-real-photo="true" data-real-photo-slot="before-credential" '
            'data-media-origin="goldhand-bundled-official-library" '
            'data-goldhand-media="GH0016"',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
        )
        self.assertIn("real-photo-placement-marker", {item["code"] for item in result["issues"]})

    def test_editorial_close_accepts_two_closing_clinical_photos_before_trust_photo(self) -> None:
        article = re.sub(
            r'<figure\b(?=[^>]*data-real-photo="true")[^>]*>.*?</figure>',
            "",
            editorial_close_article(include_summary=False),
            count=1,
            flags=re.I | re.S,
        )
        media_by_id = editorial_fixture_media_library()
        figures: list[str] = []
        for media_id in ("GH0016", "GH0017"):
            asset = media_by_id[media_id]
            figures.append(
                f'<figure data-reference-role="evidence-media" data-goldhand-role="media" '
                f'data-real-photo="true" data-real-photo-slot="closing-trust" '
                f'data-media-origin="goldhand-bundled-official-library" data-goldhand-media="{media_id}" '
                f'data-image-placement="closing-clinical-gallery" '
                f'style="margin:28px auto;text-align:center;max-width:580px;">'
                f'<img src="{asset["url"]}" data-real-photo="true" '
                f'data-media-origin="goldhand-bundled-official-library" data-goldhand-media="{media_id}" '
                f'data-media-sha256="{asset["sha256"]}" data-reference-source-url="{asset["url"]}" '
                f'referrerpolicy="no-referrer" alt="{asset["approvedAlt"]}" '
                f'style="display:block;width:100%;height:auto;margin:0 auto;"></figure>'
            )
        article = article.replace(
            '<p data-reference-role="credential-trust-context"',
            "".join(figures) + '<p data-reference-role="credential-trust-context"',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
            media_library=media_by_id,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertFalse(any(code.startswith("real-photo-layout") for code in codes), result)
        self.assertNotIn("real-photo-closing-trust-position", codes, result)
        self.assertNotIn("real-photo-closing-trust-not-adjacent", codes, result)
        self.assertNotIn("real-photo-anchor-missing", codes, result)
        self.assertNotIn("real-photo-context-mismatch", codes, result)
        repeated_result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
            media_library=media_by_id,
            recent_media_ids={"GH0016", "GH0017"},
        )
        repeated_codes = {item["code"] for item in repeated_result["issues"]}
        self.assertNotIn("immediately-previous-real-photo-repeat", repeated_codes, repeated_result)
        self.assertEqual(repeated_result["metrics"]["immediatelyPreviousRealPhotoReuseLimit"], 2)

    def test_editorial_close_rejects_visible_image_caption(self) -> None:
        article = editorial_close_article().replace(
            "</figure>",
            '<figcaption style="text-align:center;">금손한의원 진료 모습</figcaption></figure>',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article, EDITORIAL_TITLE, KEYWORD, editorial_close=True,
        )
        self.assertIn("visible-image-caption-forbidden", {item["code"] for item in result["issues"]})

    def test_editorial_close_rejects_one_reader_question(self) -> None:
        evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(encoding="utf-8")
        result = ARTICLE_VALIDATOR.validate_article(
            editorial_close_article(one_question=True),
            EDITORIAL_TITLE,
            KEYWORD,
            evidence=evidence,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("reader-question-count", codes, result)
        self.assertNotIn("topic-source-url-leak", codes, result)

    def test_editorial_close_requires_declared_editorial_source(self) -> None:
        result = ARTICLE_VALIDATOR.validate_article(
            valid_article().replace(KEYWORD, "동천동 진료", 2),
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("editorial-master-id-count", codes)
        self.assertIn("editorial-reference-source-count", codes)

    def test_editorial_close_rejects_unreviewed_candidate_status(self) -> None:
        article = editorial_close_article().replace(
            'data-editorial-profile-status="ready"',
            'data-editorial-profile-status="live-source-audit-required"',
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        self.assertIn(
            "editorial-profile-status-not-ready",
            {item["code"] for item in result["issues"]},
        )

    def test_editorial_close_accepts_same_source_wipark_master(self) -> None:
        article = wipark_editorial_close_article()
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertNotIn("editorial-master-id-invalid", codes, result)
        self.assertNotIn("editorial-reference-source-invalid", codes, result)
        self.assertNotIn("editorial-reference-source-prefix-mismatch", codes, result)
        self.assertNotIn("reference-writing-profile-mismatch", codes, result)
        self.assertNotIn("article-title-mechanism-mismatch", codes, result)
        self.assertNotIn("article-closing-mechanism-mismatch", codes, result)
        self.assertNotIn("intro-persuasion-device-mismatch", codes, result)
        self.assertNotIn("writing-voice-review-missing", codes, result)
        self.assertNotIn("writing-voice-status-not-pass", codes, result)
        self.assertEqual(result["metrics"]["referenceWritingProfileId"], "INFO03")
        self.assertEqual(result["metrics"]["finalWritingVoiceReviewId"], "writing-voice-final-rehear-v1")
        self.assertEqual(result["metrics"]["finalWritingVoiceStatus"], "pass")

    def test_wipark_article_requires_completed_writing_voice_review(self) -> None:
        article = wipark_editorial_close_article().replace(
            ' data-writing-voice-review="writing-voice-final-rehear-v1"',
            "",
            1,
        ).replace(
            ' data-writing-voice-status="pass"',
            "",
            1,
        )
        result = ARTICLE_VALIDATOR.validate_article(
            article,
            EDITORIAL_TITLE,
            KEYWORD,
            editorial_close=True,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("writing-voice-review-missing", codes, result)
        self.assertIn("writing-voice-status-not-pass", codes, result)


class ReferenceMasterTests(unittest.TestCase):
    def profiles(self) -> dict[str, dict[str, object]]:
        data = json.loads((SKILL_DIR / "assets" / "reference-master-profiles.json").read_text(encoding="utf-8"))
        return data["profiles"]

    def test_selector_chooses_one_matching_master(self) -> None:
        result = MASTER_SELECTOR.select(
            self.profiles(),
            "정보전달형",
            "광주 한의원 치료받아도 반복되는 생활습관 2가지",
            "치료 지속과 생활습관",
        )
        self.assertEqual(result["selected"]["id"], "INFO01", result)

    def test_selector_rejects_every_other_content_type(self) -> None:
        with self.assertRaises(ValueError):
            MASTER_SELECTOR.select(self.profiles(), "업체소개형", "광주 한의원", "비교")

    def test_reference_reconstruction_passes(self) -> None:
        result = REFERENCE_VALIDATOR.validate(valid_article(), self.profiles(), "INFO03")
        self.assertEqual(result["status"], "pass", result)

    def test_reference_reconstruction_rejects_credential_before_solution_preview(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<section\b(?=[^>]*data-reference-role="solution-preview")',
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("해결 방향 예고가 모두 끝난 뒤", " ".join(result["issues"]))

    def test_reference_reconstruction_rejects_credential_at_old_end_position(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<table\b(?=[^>]*data-native-table-purpose="clinic-info")',
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("첫 정보 본문 divider·section-heading보다 앞", " ".join(result["issues"]))

    def test_reference_reconstruction_rejects_summary_between_credential_and_body(self) -> None:
        article = move_purpose_table_before(
            valid_article(),
            "article-summary",
            r'<hr\b(?=[^>]*data-naver-native-component="divider")',
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("빈 preview-gap 외의 본문·이미지·표", " ".join(result["issues"]))

    def test_reference_reconstruction_allows_empty_editorial_wrapper_before_body(self) -> None:
        result = REFERENCE_VALIDATOR.validate(
            wrap_first_divider_in_structural_section(valid_article()),
            self.profiles(),
            "INFO03",
        )
        self.assertEqual(result["status"], "pass", result)

    def test_reference_reconstruction_allows_three_reader_questions(self) -> None:
        article = valid_article().replace(
            BODY_OPEN,
            question_markup("생활 관리는 어디부터 바꿔야 할까요?") + BODY_OPEN,
            1,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "pass", result)

    def test_mixed_master_and_legacy_template_fail(self) -> None:
        article = valid_article().replace(
            'data-decoration-master-reference-id="INFO03"',
            'data-decoration-master-reference-id="INFO01"',
        ).replace(
            BODY_OPEN,
            '<header>GOLDHAND CLINIC</header>' + BODY_OPEN,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles())
        self.assertEqual(result["status"], "fail")
        joined = " ".join(result["issues"])
        self.assertIn("글쓰기 흐름 마스터", joined)
        self.assertIn("고정 금손 템플릿", joined)

    def test_source_business_and_noncentered_text_fail(self) -> None:
        article = valid_article().replace("몸의 신호", "위석부부한의원의 신호", 1)
        article = article.replace('style="text-align:center;"', 'style="text-align:left;"', 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        joined = " ".join(result["issues"])
        self.assertIn("레퍼런스 업체 정보", joined)
        self.assertIn("중앙 정렬", joined)

    def test_beomeo_topic_source_is_not_a_structure_reference(self) -> None:
        article = valid_article().replace(
            'data-reference-source="https://blog.naver.com/wi-parkclinic/224337414108"',
            'data-reference-source="https://blog.naver.com/beomeo_sm/224202473239"',
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        joined = " ".join(result["issues"])
        self.assertIn("선택한 원문 URL", joined)
        self.assertIn("주제 아이디어 전용", joined)

    def test_native_table_palette_cannot_change(self) -> None:
        article = valid_article().replace("#C99F75", "#FF0010", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("허용 팔레트 밖", " ".join(result["issues"]))

    def test_custom_css_card_fails(self) -> None:
        article = valid_article().replace(
            BODY_OPEN,
            '<section data-goldhand-box="fake-card" style="border:1px solid #C99F75;border-radius:12px;">가짜 박스</section>'
            + BODY_OPEN,
            1,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        joined = " ".join(result["issues"])
        self.assertIn("data-goldhand-box", joined)
        self.assertIn("border-radius", joined)

    def test_one_cell_fake_table_fails(self) -> None:
        article = valid_article().replace(
            '<td style="background-color:#C99F75;color:#FFFFFF;font-weight:700;text-align:center;border:1px solid #D6D6D6;text-align:center;vertical-align:middle;">기록할 내용</td>',
            '',
            1,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("2~999열", " ".join(result["issues"]))

    def test_missing_table_cell_grid_fails(self) -> None:
        article = valid_article().replace("border:1px solid #D6D6D6;", "", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("회색 구분선", " ".join(result["issues"]))

    def test_non_centered_table_cell_fails(self) -> None:
        article = valid_article().replace("text-align:center;vertical-align:middle;", "text-align:left;vertical-align:top;", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        joined = " ".join(result["issues"])
        self.assertIn("가로 중앙 정렬", joined)
        self.assertIn("세로 중앙 정렬", joined)

    def test_unapproved_value_proof_fails(self) -> None:
        article = valid_article().replace("월·수·금 야간 · 토·일·공휴일 진료", "무조건 빠른 치료와 결과 보장", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("후보 선택 없이", " ".join(result["issues"]))

    def test_missing_text_emphasis_fails(self) -> None:
        article = valid_article().replace(
            '<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">',
            "<span>",
            1,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("노란 하이라이트 강조", " ".join(result["issues"]))

    def test_missing_red_safety_emphasis_fails(self) -> None:
        article = valid_article().replace('data-goldhand-emphasis="red"', 'data-goldhand-emphasis="plain"')
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("빨간 글씨 강조", " ".join(result["issues"]))

    def test_clinic_info_row_width_fails(self) -> None:
        article = valid_article().replace(
            "width:100%;background-color:#C99F75;",
            "width:40%;background-color:#C99F75;",
            1,
        )
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("적층 행 폭", " ".join(result["issues"]))

    def test_clinic_hours_excluded_holiday_text_fails(self) -> None:
        article = valid_article().replace("&nbsp;", "공휴일", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("자동 출력 제외 문구", " ".join(result["issues"]))

    def test_clinic_info_excluded_reservation_text_fails(self) -> None:
        article = valid_article().replace("전화 062-515-7582", "네이버 예약", 1)
        result = REFERENCE_VALIDATOR.validate(article, self.profiles(), "INFO03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("자동 출력 제외 문구", " ".join(result["issues"]))

    def test_editorial_close_rejects_one_question_even_without_summary(self) -> None:
        article = editorial_close_article(include_summary=False, one_question=True)
        result = REFERENCE_VALIDATOR.validate(
            article,
            self.profiles(),
            "INFO03",
            editorial_close=True,
        )
        self.assertEqual(result["status"], "fail", result)
        self.assertIn("2~3개", " ".join(result["issues"]))

    def test_editorial_close_beomeo_url_is_only_allowed_in_editorial_source(self) -> None:
        allowed = REFERENCE_VALIDATOR.validate(
            editorial_close_article(),
            self.profiles(),
            "INFO03",
            editorial_close=True,
        )
        self.assertNotIn("주제 아이디어 전용", " ".join(allowed["issues"]), allowed)
        leaked = editorial_close_article().replace(
            "몸의 신호",
            "https://blog.naver.com/beomeo_sm/224231647991 몸의 신호",
            1,
        )
        result = REFERENCE_VALIDATOR.validate(
            leaked,
            self.profiles(),
            "INFO03",
            editorial_close=True,
        )
        self.assertIn("주제 아이디어 전용", " ".join(result["issues"]))


class EditorialFidelityTests(unittest.TestCase):
    def profiles(self) -> dict[str, dict[str, object]]:
        return EDITORIAL_FIDELITY_VALIDATOR.load_profiles(
            SKILL_DIR / "assets" / "beomeo-editorial-master-profiles.json"
        )

    def test_required_beats_in_profile_order_pass(self) -> None:
        result = EDITORIAL_FIDELITY_VALIDATOR.validate(
            editorial_fidelity_article(),
            self.profiles(),
            "BM224231647991",
        )
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["beatCount"], 5)

    def test_out_of_order_required_beats_fail(self) -> None:
        article = editorial_fidelity_article()
        left = "exercise-matters-but-is-not-a-direct-calorie-equation"
        right = "why-weight-loss-can-stall-despite-exercise"
        article = article.replace(left, "TEMP-BEAT", 1).replace(right, left, 1).replace("TEMP-BEAT", right, 1)
        result = EDITORIAL_FIDELITY_VALIDATOR.validate(
            article,
            self.profiles(),
            "BM224231647991",
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("편집 비트 순서", " ".join(result["issues"]))

    def test_beomeo_url_cannot_replace_layout_source(self) -> None:
        article = editorial_fidelity_article().replace(
            'data-reference-source="https://blog.naver.com/wi-parkclinic/224337414108"',
            'data-reference-source="https://blog.naver.com/beomeo_sm/224231647991"',
        )
        result = EDITORIAL_FIDELITY_VALIDATOR.validate(
            article,
            self.profiles(),
            "BM224231647991",
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("기존 순정 레이아웃 마스터", " ".join(result["issues"]))

    def test_empty_editorial_beat_fails(self) -> None:
        article = editorial_fidelity_article().replace(
            ">5번째 새 금손 설명 문단입니다.</section>",
            "></section>",
            1,
        )
        result = EDITORIAL_FIDELITY_VALIDATOR.validate(
            article,
            self.profiles(),
            "BM224231647991",
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("실제 본문", " ".join(result["issues"]))


class CopyOverlapTests(unittest.TestCase):
    def test_seven_consecutive_words_fail(self) -> None:
        source = "운동을 시작한 뒤 하루 전체의 식사와 휴식까지 함께 살펴야 합니다."
        draft = "설명 앞부분입니다. 운동을 시작한 뒤 하루 전체의 식사와 휴식까지 함께 살펴야 합니다."
        result = COPY_OVERLAP_VALIDATOR.validate(source, draft)
        self.assertEqual(result["status"], "fail")
        self.assertIn("consecutive-copy-overlap", {item["code"] for item in result["issues"]})

    def test_short_distinctive_source_sentence_copy_fails(self) -> None:
        source = "운동직후의 허기는 저녁식탁의 선택까지 조용히바꿉니다."
        draft = "운동직후의 허기는 저녁식탁의 선택까지 조용히바꿉니다. 다른 설명입니다."
        result = COPY_OVERLAP_VALIDATOR.validate(source, draft)
        self.assertEqual(result["status"], "fail")
        self.assertIn("source-sentence-copy", {item["code"] for item in result["issues"]})

    def test_common_search_phrase_can_be_allowlisted(self) -> None:
        source = "운동을 해도 살이 잘 안 빠지는 이유"
        draft = "운동을 해도 살이 잘 안 빠지는 이유"
        result = COPY_OVERLAP_VALIDATOR.validate(source, draft)
        self.assertEqual(result["status"], "pass", result)


class BuilderTests(unittest.TestCase):
    def test_windows_output_and_paste_contract(self) -> None:
        with mock.patch.dict(
            PAGE_BUILDER.os.environ,
            {"GOLDHAND_OUTPUT_DIR": "", "OneDrive": r"C:\\Users\\tester\\OneDrive", "USERPROFILE": r"C:\\Users\\tester"},
            clear=False,
        ), mock.patch.object(PAGE_BUILDER, "windows_desktop_dir", return_value=Path(r"C:\Users\tester\OneDrive\Desktop")):
            self.assertEqual(
                PAGE_BUILDER.default_output_dir("nt"),
                Path(r"C:\Users\tester\OneDrive\Desktop") / "금손한의원 블로그",
            )
        self.assertEqual(PAGE_BUILDER.paste_shortcut("nt"), "Ctrl+V")
        self.assertEqual(PAGE_BUILDER.paste_shortcut("posix"), "⌘V")
        page = PAGE_BUILDER.build_page("윈도우 확인", valid_article(), platform_name="nt")
        self.assertIn("Ctrl+V", page)
        self.assertNotIn("⌘V", page)

    def test_windows_vercel_cli_prefers_cmd_shim(self) -> None:
        def fake_which(candidate: str) -> str | None:
            return r"C:\Users\tester\AppData\Roaming\npm\vercel.cmd" if candidate == "vercel.cmd" else None

        with mock.patch.object(PAGE_BUILDER.shutil, "which", side_effect=fake_which) as which:
            resolved = PAGE_BUILDER.resolve_vercel_cli("nt")
        self.assertEqual(resolved, r"C:\Users\tester\AppData\Roaming\npm\vercel.cmd")
        self.assertEqual(which.call_args_list[0].args, ("vercel.cmd",))

        with mock.patch.object(PAGE_BUILDER.shutil, "which", side_effect=fake_which):
            command = PAGE_BUILDER.vercel_deploy_command("nt")
        self.assertEqual(
            command,
            [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                r"C:\Users\tester\AppData\Roaming\npm\vercel.cmd",
                "--prod",
                "--yes",
            ],
        )

    @unittest.skipUnless(os.name == "nt", "Windows runner regression")
    def test_real_windows_cmd_shim_can_be_executed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            marker = root / "vercel-called.txt"
            shim = root / "vercel.cmd"
            shim.write_text(
                '@echo off\r\n> "%GOLDHAND_VERCEL_MARKER%" echo %*\r\nexit /b 0\r\n',
                encoding="ascii",
            )
            with mock.patch.dict(
                PAGE_BUILDER.os.environ,
                {
                    "PATH": str(root) + os.pathsep + PAGE_BUILDER.os.environ.get("PATH", ""),
                    "GOLDHAND_VERCEL_MARKER": str(marker),
                },
                clear=False,
            ):
                PAGE_BUILDER.deploy_image_host(root, platform_name="nt")
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), "--prod --yes")

    def test_managed_windows_codex_home_owns_state_and_image_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            PAGE_BUILDER.os.environ,
            {"CODEX_HOME": temp_dir},
            clear=True,
        ):
            expected_root = Path(temp_dir).resolve()
            expected_state = expected_root / "state" / "goldhand-clinic-blog" / "recent-articles.json"
            expected_host = expected_root / "state" / "goldhand-clinic-blog" / "image-host.json"
            self.assertEqual(PAGE_BUILDER.default_image_host_config(), expected_host)
            self.assertEqual(WIPARK_CONTENT_SELECTOR.default_state_path(), expected_state)
            self.assertEqual(TOPIC_SELECTOR.default_state_path(), expected_state)
            self.assertEqual(STATE_RECORDER.default_state_path(), expected_state)
            self.assertEqual(MEDIA_RECOMMENDER.default_state_path(), expected_state)
            self.assertEqual(CLOSING_TRUST_RECOMMENDER.default_state_path(), expected_state)

    def test_builder_strips_legacy_visible_image_captions(self) -> None:
        article = editorial_close_article().replace(
            "</figure>",
            '<figcaption style="text-align:center;">금손한의원 건물 외부</figcaption></figure>',
            1,
        )
        cleaned = PAGE_BUILDER.strip_visible_image_captions(article)
        self.assertNotIn("<figcaption", cleaned)
        self.assertNotIn("금손한의원 건물 외부", cleaned)

    def test_builder_preflight_blocks_wrong_credential_position(self) -> None:
        PAGE_BUILDER.validate_credential_placement(valid_article())
        article = move_credential_table_before(
            valid_article(),
            r'<table\b(?=[^>]*data-native-table-purpose="clinic-info")',
        )
        with self.assertRaisesRegex(ValueError, "credential-after-first-body-marker"):
            PAGE_BUILDER.validate_credential_placement(article)

    def test_builder_strips_only_legacy_closing_supplement(self) -> None:
        original = valid_article()
        legacy = original.replace(
            "</article>",
            (
                '<section data-goldhand-closing-links="true">'
                '<p>&lt;함께 보면 좋은 글&gt;</p>'
                '<div class="se-component se-oglink">최신 글</div>'
                '<div class="se-component se-placesMap">금손한의원 지도</div>'
                "</section></article>"
            ),
        )
        cleaned = PAGE_BUILDER.strip_legacy_closing_links(legacy)
        self.assertEqual(cleaned, original)
        self.assertEqual(PAGE_BUILDER.strip_legacy_closing_links(cleaned), original)

        page = PAGE_BUILDER.build_page(TITLE, legacy)
        article = re.search(r"<article\b[^>]*>.*?</article>", page, flags=re.I | re.S).group(0)
        self.assertNotIn('data-goldhand-closing-links="true"', article)
        self.assertNotIn("&lt;함께 보면 좋은 글&gt;", article)
        self.assertNotIn('class="se-component se-oglink', article)
        self.assertNotIn('class="se-component se-placesMap', article)
        self.assertRegex(article, r'data-native-table-purpose="clinic-info"[\s\S]*?</table>\s*</article>$')

    def test_builder_rejects_logo_and_nonperson_actual_photo(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        logo = next(item for item in library["assets"] if item["id"] == "GH0069")
        article = valid_article().replace(
            "</article>",
            (
                f'<img data-real-photo="true" data-goldhand-media="{logo["id"]}" '
                f'data-media-sha256="{logo["sha256"]}" '
                f'data-reference-source-url="{logo["url"]}" src="{logo["url"]}"></article>'
            ),
        )
        with self.assertRaisesRegex(ValueError, "원장 치료·진찰·상담 사진이 아니므로"):
            PAGE_BUILDER.validate_person_media_policy(article, library)

    def test_builder_rejects_unreviewed_closing_trust_photo(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        logo = next(item for item in library["assets"] if item["id"] == "GH0069")
        article = valid_article().replace(
            "</article>",
            (
                f'<img data-trust-photo="true" data-goldhand-media="{logo["id"]}" '
                f'data-media-sha256="{logo["sha256"]}" '
                f'data-reference-source-url="{logo["url"]}" src="{logo["url"]}"></article>'
            ),
        )
        with self.assertRaisesRegex(ValueError, "검수된 협약·수료·기부·봉사 신뢰 사진이 아니므로"):
            PAGE_BUILDER.validate_person_media_policy(article, library)

    def test_local_file_copy_is_synchronous_and_does_not_inject_text_decoration(self) -> None:
        page = PAGE_BUILDER.build_page(TITLE, valid_article())
        self.assertNotIn("run.style.fontWeight = '400'", page)
        self.assertNotIn("run.style.textDecoration = 'none'", page)
        self.assertIn("굵게·밑줄·취소선", page)
        self.assertIn("window.location.protocol === 'file:'", page)
        self.assertIn("복사 실패 · 클립보드가 바뀌지 않았습니다", page)
        self.assertLess(
            page.index("window.location.protocol === 'file:'"),
            page.index("navigator.clipboard?.write"),
        )

    def test_build_page_publishes_local_image_as_https(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "pixel.png"
            image_path.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            article = re.sub(
                r'(<table\b(?=[^>]*data-native-table-purpose="clinic-info"))',
                lambda match: (
                    f'<img src="data:," data-local-image="{image_path}" alt="사용자 이미지" />'
                    f"{match.group(1)}"
                ),
                valid_article(),
                count=1,
            )
            published = PAGE_BUILDER.publish_local_images(
                article,
                root / "host",
                "https://goldhand-images.example",
                deploy=False,
                verify=False,
            )
            rewritten = PAGE_BUILDER.rewrite_img_tags(article, published)
            self.assertIn("https://goldhand-images.example/media/", rewritten)
            self.assertIn('data-reference-source-url="https://goldhand-images.example/media/', rewritten)
            self.assertNotIn("data:image/png;base64,", rewritten)
            self.assertNotIn("data-local-image", rewritten)
            self.assertEqual(len(list((root / "host" / "media").glob("*.png"))), 1)
            page = PAGE_BUILDER.build_page(TITLE, rewritten)
            self.assertIn("ClipboardItem", page)
            self.assertIn("__goldhandCopyPreview", page)
            result = HTML_VALIDATOR.validate_html(page)
            self.assertEqual(result["status"], "pass", result)

    def test_copy_page_rejects_data_uri_images(self) -> None:
        article = valid_article().replace(
            "</article>",
            '<img src="data:image/png;base64,AA==" alt="지원하지 않는 이미지" /></article>',
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        self.assertIn("naver-rejected-data-image", {item["code"] for item in result["issues"]})

    def test_copy_page_rejects_legacy_closing_supplement(self) -> None:
        page = PAGE_BUILDER.build_page(TITLE, valid_article())
        legacy_page = page.replace(
            "</article>",
            (
                '<section data-goldhand-closing-links="true">'
                '<p style="text-align:center;">&lt;함께 보면 좋은 글&gt;</p>'
                '<div class="se-component se-oglink">https://blog.naver.com/goldhand7582_/224379815063</div>'
                '<div class="se-component se-placesMap">https://map.naver.com/p/entry/place/1598180269</div>'
                "</section></article>"
            ),
            1,
        )
        result = HTML_VALIDATOR.validate_html(legacy_page)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("closing-supplement-forbidden", codes)
        self.assertIn("clinic-info-not-last", codes)

    def test_editorial_close_page_allows_two_tables_without_summary(self) -> None:
        article = editorial_close_article(include_summary=False).replace(
            '<article data-goldhand-type="정보전달형"',
            '<article data-goldhand-type="정보전달형" data-editorial-mode="close-adaptation"',
            1,
        )
        article = PAGE_BUILDER.rewrite_img_tags(
            article,
            {GPT_IMAGE_FIXTURE: "https://goldhand-images.example/media/gpt.png"},
        )
        page = PAGE_BUILDER.build_page(TITLE, article)
        result = HTML_VALIDATOR.validate_html(page)
        self.assertEqual(result["status"], "pass", result)
        self.assertTrue(result["metrics"]["editorialClose"])

    def test_copy_page_rejects_generated_image_after_second_body_section(self) -> None:
        article = editorial_close_article(include_summary=False).replace(
            '<article data-goldhand-type="정보전달형"',
            '<article data-goldhand-type="정보전달형" data-editorial-mode="close-adaptation"',
            1,
        )
        article = move_generated_figures_after_section_heading(article, 2, count=1)
        article = PAGE_BUILDER.rewrite_img_tags(
            article,
            {GPT_IMAGE_FIXTURE: "https://goldhand-images.example/media/gpt.png"},
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        self.assertIn(
            "generated-image-outside-early-body",
            {item["code"] for item in result["issues"]},
            result,
        )

    def test_copy_page_cannot_bypass_early_image_gate_by_removing_heading_role(self) -> None:
        article = editorial_close_article(include_summary=False).replace(
            '<article data-goldhand-type="정보전달형"',
            '<article data-goldhand-type="정보전달형" data-editorial-mode="close-adaptation"',
            1,
        )
        article = move_generated_figures_after_section_heading(article, 2, count=1)
        article = article.replace(' data-reference-role="section-heading"', "")
        article = PAGE_BUILDER.rewrite_img_tags(
            article,
            {GPT_IMAGE_FIXTURE: "https://goldhand-images.example/media/gpt.png"},
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("section-heading-markers-invalid", codes, result)
        self.assertIn("body-section-heading-missing", codes, result)
        self.assertIn("generated-image-outside-early-body", codes, result)

    def test_copy_page_cannot_hide_third_p_heading_by_removing_both_markers(self) -> None:
        article = editorial_close_article(include_summary=False).replace(
            '<article data-goldhand-type="정보전달형"',
            '<article data-goldhand-type="정보전달형" data-editorial-mode="close-adaptation"',
            1,
        )
        article = move_generated_figures_after_section_heading(article, 2, count=1)
        article = strip_markers_from_section_heading(article, 2, convert_to_p=True)
        article = PAGE_BUILDER.rewrite_img_tags(
            article,
            {GPT_IMAGE_FIXTURE: "https://goldhand-images.example/media/gpt.png"},
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("section-heading-markers-invalid", codes, result)
        self.assertIn("generated-image-outside-early-body", codes, result)

    def test_copy_page_cannot_hide_third_section_by_removing_divider_and_markers(self) -> None:
        cases = (
            (False, "19px", "700"),
            (True, "19px", "700"),
            (True, "19px", "650"),
            (True, "100px", "700"),
            (True, "16px;font-size:19px", "700"),
            (True, "19px", "400;font-weight:700"),
        )
        for convert_to_p, font_size, font_weight in cases:
            with self.subTest(convert_to_p=convert_to_p, font_size=font_size, font_weight=font_weight):
                article = editorial_close_article(include_summary=False).replace(
                    '<article data-goldhand-type="정보전달형"',
                    '<article data-goldhand-type="정보전달형" data-editorial-mode="close-adaptation"',
                    1,
                )
                article = move_generated_figures_after_section_heading(article, 2, count=1)
                article = remove_divider_before_section_heading(article, 2)
                article = strip_markers_from_section_heading(article, 2, convert_to_p=convert_to_p)
                if convert_to_p:
                    article = make_markerless_p_visually_heading_like(
                        article,
                        "3. ",
                        font_size=font_size,
                        font_weight=font_weight,
                    )
                article = PAGE_BUILDER.rewrite_img_tags(
                    article,
                    {GPT_IMAGE_FIXTURE: "https://goldhand-images.example/media/gpt.png"},
                )
                result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
                codes = {item["code"] for item in result["issues"]}
                self.assertIn("section-heading-divider-pair-invalid", codes, result)
                self.assertIn("generated-image-outside-early-body", codes, result)

    def test_copy_page_rejects_credential_before_solution_preview(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<section\b(?=[^>]*data-reference-role="solution-preview")',
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        self.assertIn("credential-before-solution-preview", {item["code"] for item in result["issues"]})

    def test_copy_page_rejects_credential_at_old_end_position(self) -> None:
        article = move_credential_table_before(
            valid_article(),
            r'<table\b(?=[^>]*data-native-table-purpose="clinic-info")',
        )
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        self.assertIn("credential-after-first-body-marker", {item["code"] for item in result["issues"]})

    def test_copy_page_rejects_content_in_credential_gaps_and_late_intro(self) -> None:
        mutations = (
            (
                insert_after_reference_role(
                    valid_article(),
                    "solution-preview",
                    '<p data-mobile-group="true" style="text-align:center;">중간 본문입니다.<br>여기에 오면 안 됩니다.</p>',
                ),
                "credential-not-immediately-after-solution-preview",
            ),
            (
                insert_after_purpose_table(
                    valid_article(),
                    "credential",
                    '<img src="data:image/png;base64,AA==" alt="중간 이미지">',
                ),
                "credential-not-immediately-before-first-body-marker",
            ),
            (
                move_purpose_table_before(
                    valid_article(),
                    "article-summary",
                    r'<hr\b(?=[^>]*data-naver-native-component="divider")',
                ),
                "credential-not-immediately-before-first-body-marker",
            ),
            (
                move_reference_role_after_purpose_table(
                    valid_article(),
                    "greeting-authority",
                    "credential",
                ),
                "intro-role-after-credential",
            ),
        )
        for article, expected_code in mutations:
            with self.subTest(expected_code=expected_code):
                result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
                self.assertIn(expected_code, {item["code"] for item in result["issues"]}, result)

    def test_copy_page_allows_empty_editorial_wrapper_before_body(self) -> None:
        article = wrap_first_divider_in_structural_section(valid_article())
        result = HTML_VALIDATOR.validate_html(PAGE_BUILDER.build_page(TITLE, article))
        self.assertEqual(result["status"], "pass", result)


class ImageHostSetupTests(unittest.TestCase):
    def test_macos_setup_uses_the_managed_vercel_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            managed = root / "state" / "goldhand-clinic-blog" / "bin" / "vercel"
            managed.parent.mkdir(parents=True)
            managed.write_text("#!/bin/sh\n", encoding="ascii")
            managed.chmod(0o755)
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(root)}), mock.patch.object(
                IMAGE_HOST_SETUP.shutil,
                "which",
                return_value=None,
            ):
                actual = IMAGE_HOST_SETUP.resolve_vercel_cli(platform_name="posix")
        self.assertEqual(Path(actual).resolve(), managed.resolve())

    def test_windows_setup_uses_the_vercel_cmd_shim(self) -> None:
        with mock.patch.object(
            IMAGE_HOST_SETUP.shutil,
            "which",
            side_effect=lambda name: r"C:\Users\tester\AppData\Roaming\npm\vercel.cmd"
            if name == "vercel.cmd"
            else None,
        ):
            command = IMAGE_HOST_SETUP.vercel_command(["whoami", "--format", "json"], platform_name="nt")
        self.assertEqual(
            command,
            [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                r"C:\Users\tester\AppData\Roaming\npm\vercel.cmd",
                "whoami",
                "--format",
                "json",
            ],
        )

    def test_first_setup_logs_in_creates_project_deploys_and_writes_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_dir = root / "image-host-project"
            config_path = root / "state" / "image-host.json"
            calls: list[tuple[str, ...]] = []
            whoami_count = 0

            def fake_run(arguments, cwd, **kwargs):
                nonlocal whoami_count
                calls.append(tuple(arguments))
                if arguments[:1] == ["whoami"]:
                    whoami_count += 1
                    return subprocess.CompletedProcess(arguments, 1 if whoami_count == 1 else 0, "{}", "")
                if arguments == ["login"]:
                    self.assertTrue(kwargs.get("interactive"))
                    return subprocess.CompletedProcess(arguments, 0, "", "")
                if arguments[:2] == ["project", "inspect"]:
                    return subprocess.CompletedProcess(arguments, 1, "", "missing")
                if arguments[:2] == ["project", "add"]:
                    return subprocess.CompletedProcess(arguments, 0, "", "")
                if arguments[:1] == ["link"]:
                    link_dir = Path(cwd) / ".vercel"
                    link_dir.mkdir(parents=True, exist_ok=True)
                    (link_dir / "project.json").write_text(
                        json.dumps(
                            {
                                "projectId": "prj_test",
                                "orgId": "team_test",
                                "projectName": "goldhand-blog-images",
                            }
                        ),
                        encoding="utf-8",
                    )
                    return subprocess.CompletedProcess(arguments, 0, "", "")
                if arguments[:1] == ["deploy"]:
                    return subprocess.CompletedProcess(
                        arguments,
                        0,
                        json.dumps({"url": "goldhand-blog-images-random-owner.vercel.app"}),
                        "",
                    )
                if arguments[:1] == ["inspect"]:
                    return subprocess.CompletedProcess(
                        arguments,
                        0,
                        json.dumps(
                            {
                                "aliases": [
                                    "goldhand-blog-images.vercel.app",
                                    "goldhand-blog-images-owner.vercel.app",
                                ]
                            }
                        ),
                        "",
                    )
                raise AssertionError(f"unexpected Vercel command: {arguments}")

            with mock.patch.object(IMAGE_HOST_SETUP, "run_vercel", side_effect=fake_run), mock.patch.object(
                IMAGE_HOST_SETUP,
                "verify_public_base_url",
            ) as verify:
                payload = IMAGE_HOST_SETUP.setup_image_host(
                    config_path,
                    project_dir,
                    "goldhand-blog-images",
                )

            self.assertEqual(payload["publicBaseUrl"], "https://goldhand-blog-images.vercel.app")
            self.assertEqual(json.loads(config_path.read_text(encoding="utf-8")), payload)
            self.assertTrue((project_dir / "vercel.json").is_file())
            self.assertTrue((project_dir / ".vercel" / "project.json").is_file())
            self.assertIn(("login",), calls)
            self.assertIn(("project", "add", "goldhand-blog-images"), calls)
            self.assertIn(("link", "--yes", "--project", "goldhand-blog-images"), calls)
            self.assertIn(("deploy", "--prod", "--yes", "--format", "json"), calls)
            verify.assert_called_once_with("https://goldhand-blog-images.vercel.app")

    def test_existing_valid_setup_is_reused_without_redeploy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_dir = root / "project"
            config_path = root / "image-host.json"
            IMAGE_HOST_SETUP.write_host_template(project_dir)
            link_dir = project_dir / ".vercel"
            link_dir.mkdir(parents=True)
            (link_dir / "project.json").write_text(
                json.dumps({"projectId": "prj_test", "projectName": "goldhand-blog-images"}),
                encoding="utf-8",
            )
            expected = {
                "projectDir": str(project_dir.resolve()),
                "publicBaseUrl": "https://goldhand-blog-images.example",
                "projectName": "goldhand-blog-images",
            }
            config_path.write_text(json.dumps(expected), encoding="utf-8")
            with mock.patch.object(
                IMAGE_HOST_SETUP,
                "run_vercel",
                return_value=subprocess.CompletedProcess([], 0, "{}", ""),
            ) as run_vercel, mock.patch.object(IMAGE_HOST_SETUP, "verify_public_base_url") as verify:
                actual = IMAGE_HOST_SETUP.setup_image_host(
                    config_path,
                    project_dir,
                    "goldhand-blog-images",
                )
            self.assertEqual(actual, expected)
            self.assertEqual(run_vercel.call_count, 1)
            verify.assert_called_once_with(expected["publicBaseUrl"])


class StateAndMediaTests(unittest.TestCase):
    def test_media_history_skips_current_article_during_revalidation(self) -> None:
        state = {
            "entries": [
                {
                    "title": "현재 글",
                    "realMediaIds": ["CURRENT"],
                    "realMediaHashes": ["current-hash"],
                    "trustMediaIds": ["CURRENT-TRUST"],
                    "trustMediaHashes": ["current-trust-hash"],
                },
                {
                    "title": "직전 글",
                    "realMediaIds": ["PREVIOUS"],
                    "realMediaHashes": ["previous-hash"],
                    "trustMediaIds": ["PREVIOUS-TRUST"],
                    "trustMediaHashes": ["previous-trust-hash"],
                },
            ]
        }
        ids, hashes = MEDIA_RECOMMENDER.recent_media(state, current_title="현재 글")
        self.assertEqual(ids, {"PREVIOUS"})
        self.assertEqual(hashes, {"previous-hash"})
        validator_ids, validator_hashes, _, _ = ARTICLE_VALIDATOR.recent_media_policy(
            state,
            current_title="현재 글",
        )
        self.assertEqual(validator_ids, {"PREVIOUS"})
        self.assertEqual(validator_hashes, {"previous-hash"})
        trust_ids, trust_hashes = ARTICLE_VALIDATOR.recent_trust_media_policy(
            state,
            current_title="현재 글",
        )
        self.assertEqual(trust_ids, {"PREVIOUS-TRUST"})
        self.assertEqual(trust_hashes, {"previous-trust-hash"})

    def test_state_keeps_only_latest_three_without_body(self) -> None:
        state: dict[str, object] = {}
        for index in range(4):
            state = STATE_RECORDER.record(
                state,
                {
                    "title": f"제목{index}",
                    "mainKeyword": f"키워드{index}",
                    "ideaReferenceId": f"WP{index}",
                    "ideaReferenceTitle": f"참고 제목{index}",
                    "ideaReferenceUrl": f"https://blog.naver.com/wi-parkclinic/{index}",
                    "ideaType": "symptom-cause",
                    "titlePatternId": "reason-explained",
                    "writingMasterId": "INFO03",
                    "writingReferenceUrl": "https://blog.naver.com/wi-parkclinic/224337414108",
                    "type": "정보전달형",
                    "writtenAt": f"2026-08-{index + 1:02d}",
                },
            )
        self.assertEqual(len(state["entries"]), 3)
        self.assertNotIn("body", json.dumps(state, ensure_ascii=False))

    def test_state_keeps_editorial_master_provenance(self) -> None:
        entry = {
            "title": "광주 한의원 추천, 운동하는데 왜 살이 잘 안 빠질까요?",
            "mainKeyword": "광주 한의원 추천",
            "ideaReferenceId": "BTI028",
            "ideaReferenceTitle": "운동해도 살이 빠지지 않을 때 생활 점검",
            "ideaReferenceUrl": "https://blog.naver.com/beomeo_sm/224231647991",
            "ideaType": "weight-management",
            "titlePatternId": "natural-question",
            "writingMasterId": "INFO06",
            "writingReferenceUrl": "https://blog.naver.com/wi-parkclinic/224205420099",
            "editorialMasterId": "BM224231647991",
            "editorialReferenceTitle": "대구 린다이어트, 운동을 해도 살이 안 빠지는 이유!",
            "editorialReferenceUrl": "https://blog.naver.com/beomeo_sm/224231647991",
            "editorialSourceRole": "title-tone-content-sequence-only",
            "editorialProfileStatus": "ready",
            "type": "정보전달형",
            "writtenAt": "2026-08-21",
        }
        state = STATE_RECORDER.record({}, entry)
        saved = state["entries"][0]
        self.assertEqual(saved["editorialMasterId"], "BM224231647991")
        self.assertEqual(saved["editorialReferenceUrl"], entry["editorialReferenceUrl"])
        self.assertEqual(saved["editorialSourceRole"], "title-tone-content-sequence-only")

    def test_state_rejects_unreviewed_editorial_candidate(self) -> None:
        entry = {
            "title": "감사 전 후보 글",
            "mainKeyword": "광주 한의원 추천",
            "ideaReferenceId": "BTI011",
            "ideaReferenceTitle": "소화불량 주제",
            "ideaReferenceUrl": "https://blog.naver.com/beomeo_sm/224338019561",
            "ideaType": "symptom-cause",
            "titlePatternId": "natural-question",
            "writingMasterId": "INFO10",
            "writingReferenceUrl": "https://blog.naver.com/wi-parkclinic/224287906098",
            "editorialProfileStatus": "live-source-audit-required",
            "type": "정보전달형",
            "writtenAt": "2026-08-21",
        }
        with self.assertRaisesRegex(ValueError, "감사가 완료되지 않은"):
            STATE_RECORDER.record({}, entry)

    def test_state_removes_legacy_non_information_entries(self) -> None:
        legacy = {
            "entries": [
                {"title": "예전 업체소개형", "type": "업체소개형"},
                {"title": "예전 사례공유형", "type": "사례공유형"},
            ]
        }
        entry = {
            "title": "현재 정보글",
            "mainKeyword": "광주 한의원",
            "ideaReferenceId": "WP224320052203",
            "ideaReferenceTitle": "일자목 거북목",
            "ideaReferenceUrl": "https://blog.naver.com/wi-parkclinic/224320052203",
            "ideaType": "risk-warning",
            "titlePatternId": "reader-commonality-numbered",
            "writingMasterId": "INFO01",
            "writingReferenceUrl": "https://blog.naver.com/wi-parkclinic/224320052203",
            "type": "정보전달형",
            "writtenAt": "2026-08-20",
        }
        result = STATE_RECORDER.record(legacy, entry)
        self.assertEqual([item["type"] for item in result["entries"]], ["정보전달형"])

    def test_state_v5_round_trips_semantic_topic_and_media_fields(self) -> None:
        entry = {
            "title": "광주 한의원 추천, 추나요법을 고려하기 전 확인할 기준",
            "mainKeyword": "광주 한의원 추천",
            "ideaReferenceId": "WP224320052203",
            "ideaReferenceTitle": "일자목 거북목",
            "ideaReferenceUrl": "https://blog.naver.com/wi-parkclinic/224320052203",
            "ideaType": "treatment-decision",
            "titlePatternId": "reader-commonality-numbered",
            "writingMasterId": "INFO01",
            "writingReferenceUrl": "https://blog.naver.com/wi-parkclinic/224320052203",
            "type": "정보전달형",
            "writtenAt": "2026-08-20",
            "topicSourceId": "BTI001",
            "topicSourceTitle": "만촌동 한의원, 목·허리 통증, 추나치료가 필요한 경우는 언제일까요?",
            "topicSourceUrl": "https://blog.naver.com/beomeo_sm/224202473239",
            "topicSourceRole": "topic-idea-and-coverage-questions-only",
            "semanticTopicId": "chuna.neck-back-pain.when-to-consider",
            "topicCluster": "chuna",
            "primarySubjectId": "chuna-decision",
            "subjectIds": ["chuna-manual-therapy", "neck-back-pain"],
            "topicIntent": "treatment-decision",
            "dedupeKeys": ["추나요법", "치료선택기준"],
            "realMediaIds": ["GH0001", "GHLABC123"],
            "realMediaHashes": ["abc123"],
            "trustMediaIds": ["GH0042"],
            "trustMediaHashes": ["trust123"],
        }
        result = STATE_RECORDER.record({}, entry)
        self.assertEqual(result["schemaVersion"], 5)
        self.assertEqual(result["entries"][0]["semanticTopicId"], entry["semanticTopicId"])
        self.assertEqual(result["entries"][0]["subjectIds"], entry["subjectIds"])
        self.assertEqual(result["entries"][0]["realMediaIds"], entry["realMediaIds"])
        self.assertEqual(result["entries"][0]["realMediaHashes"], entry["realMediaHashes"])
        self.assertEqual(result["entries"][0]["trustMediaIds"], entry["trustMediaIds"])
        self.assertEqual(result["entries"][0]["trustMediaHashes"], entry["trustMediaHashes"])

    def test_media_never_fills_with_objects_or_duplicate_group(self) -> None:
        library = {
            "assets": [
                {"id": "A", "safeAuto": True, "requiresReview": False, "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": "a", "url": "https://example.com/a.jpg", "sourceTitle": "교통사고 통증", "caption": "ICT 물리치료", "filename": "ICT.jpg", "context": "교통사고", "tokens": ["교통사고"], "tags": ["traffic-accident"], "postOrder": 1, "imageOrder": 1, "sourceLogNo": "1", "duplicateGroup": "same"},
                {"id": "B", "safeAuto": True, "requiresReview": False, "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": "b", "url": "https://example.com/b.jpg", "sourceTitle": "교통사고 통증", "caption": "ICT 물리치료", "filename": "ICT2.jpg", "context": "교통사고", "tokens": ["교통사고"], "tags": ["traffic-accident"], "postOrder": 2, "imageOrder": 1, "sourceLogNo": "2", "duplicateGroup": "same"},
                {"id": "C", "safeAuto": True, "requiresReview": False, "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": "c", "url": "https://example.com/c.jpg", "sourceTitle": "비염", "caption": "보험한약", "filename": "한약.jpg", "context": "비염", "tokens": ["비염"], "tags": ["respiratory"], "postOrder": 3, "imageOrder": 1, "sourceLogNo": "3", "duplicateGroup": ""},
            ]
        }
        result = MEDIA_RECOMMENDER.recommend(
            library,
            topic="교통사고 통증",
            keyword="광주 교통사고 한의원",
            article_type="정보전달형",
            count=1,
            recent_ids=set(),
            placement_mode="before-credential",
        )
        self.assertEqual(result["selectedCount"], 0, result)
        self.assertEqual(result["status"], "decision-required")

    def test_media_excludes_immediately_previous_photos_but_allows_older_ones(self) -> None:
        assets = [
            {
                "id": f"T{index}", "safeAuto": True, "requiresReview": False,
                "url": f"https://example.com/trust-{index}.jpg", "sourceTitle": f"원내 신뢰 사진 {index}",
                "caption": f"금손 신뢰 장면 {index}", "filename": f"trust-{index}.jpg", "context": "",
                "tokens": [], "tags": ["clinic-space"], "postOrder": index,
                "imageOrder": 1, "sourceLogNo": str(index), "duplicateGroup": "",
                "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": f"trust-{index}",
                "sceneType": "director-patient-consultation", "personInteraction": True,
                "directorVisible": True, "trustPriority": 100,
                "placementTerms": ["갱년기 상담"],
                "approvedAlt": f"박준희 원장이 갱년기 환자와 상담하는 장면 {index}",
            }
            for index in range(1, 4)
        ]
        result = MEDIA_RECOMMENDER.recommend(
            {"assets": assets}, topic="갱년기 증상", keyword="광주 한의원 추천",
            article_type="정보전달형", count=2, recent_ids={"T1"},
            placement_mode="closing-trust",
        )
        self.assertEqual(result["selectedCount"], 2, result)
        self.assertEqual(result["freshCount"], 2, result)
        self.assertEqual(result["blockedImmediatelyPreviousCount"], 1, result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual({item["id"] for item in result["selected"]}, {"T2", "T3"})
        self.assertTrue(all(item["figureAttributes"]["data-real-photo-slot"] == "closing-trust" for item in result["selected"]))

    def test_closing_trust_selector_uses_reviewed_pool_and_rotates_previous_photo(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        first = CLOSING_TRUST_RECOMMENDER.recommend(
            library,
            recent_ids=set(),
            recent_hashes=set(),
        )
        self.assertEqual(first["status"], "complete", first)
        self.assertEqual(first["eligibleCount"], 7)
        self.assertEqual(first["selectedCount"], 1)
        self.assertEqual(first["selected"][0]["id"], "GH0042")
        self.assertEqual(first["selected"][0]["figureAttributes"]["data-trust-photo-slot"], "closing-credential-trust")
        rotated = CLOSING_TRUST_RECOMMENDER.recommend(
            library,
            recent_ids={first["selected"][0]["id"]},
            recent_hashes={first["selected"][0]["sha256"]},
        )
        self.assertEqual(rotated["status"], "complete", rotated)
        self.assertNotEqual(rotated["selected"][0]["id"], first["selected"][0]["id"])
        self.assertEqual(rotated["blockedImmediatelyPreviousCount"], 1)

    def test_media_does_not_reuse_immediately_previous_photo(self) -> None:
        assets = [
            {
                "id": f"F{index}", "safeAuto": True, "requiresReview": False,
                "url": f"https://example.com/fresh-{index}.jpg", "sourceTitle": f"진료 공간 {index}",
                "caption": f"금손 진료 공간 {index}", "filename": f"fresh-{index}.jpg", "context": "",
                "tokens": [], "tags": ["clinic-space"], "postOrder": index,
                "imageOrder": 1, "sourceLogNo": str(index), "duplicateGroup": "",
                "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": f"fresh-{index}",
                "sceneType": "director-patient-treatment", "personInteraction": True,
                "directorVisible": True, "trustPriority": 100,
                "placementTerms": ["수면 상담"],
                "approvedAlt": f"박준희 원장이 수면 문제를 진찰하는 장면 {index}",
            }
            for index in range(1, 9)
        ]
        result = MEDIA_RECOMMENDER.recommend(
            {"assets": assets}, topic="수면 관리", keyword="광주 한의원",
            article_type="정보전달형", count=1, recent_ids={"F1", "F2"},
            placement_mode="before-credential",
        )
        self.assertEqual(result["selectedCount"], 1, result)
        self.assertEqual(result["fallbackRecentTrustCount"], 0, result)
        self.assertFalse({"F1", "F2"} & {item["id"] for item in result["selected"]})

    def test_media_prioritizes_director_patient_scenes_over_objects(self) -> None:
        people = [
            {
                "id": f"P{index}", "safeAuto": True, "requiresReview": False,
                "url": f"https://example.com/person-{index}.jpg", "sourceTitle": "방문 진료",
                "caption": "", "filename": f"person-{index}.jpg", "context": "",
                "tokens": [], "tags": ["home-visit"], "postOrder": index,
                "imageOrder": 1, "sourceLogNo": str(index), "duplicateGroup": "",
                "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": f"person-{index}",
                "sceneType": "director-patient-treatment", "personInteraction": True,
                "directorVisible": True, "trustPriority": 100,
                "placementTerms": ["목통증 진찰"],
                "approvedAlt": f"박준희 원장이 환자의 목을 진찰하는 장면 {index}",
            }
            for index in range(1, 7)
        ]
        objects = [
            {
                "id": f"O{index}", "safeAuto": True, "requiresReview": False,
                "url": f"https://example.com/object-{index}.jpg", "sourceTitle": "목 통증 치료",
                "caption": "목 통증 장비", "filename": f"object-{index}.jpg", "context": "목 통증",
                "tokens": ["통증"], "tags": ["physical-therapy"], "postOrder": index + 10,
                "imageOrder": 1, "sourceLogNo": str(index + 10), "duplicateGroup": "",
                "bundledPath": "assets/gpt-image-test-fixture.png", "sha256": f"object-{index}",
            }
            for index in range(1, 7)
        ]
        result = MEDIA_RECOMMENDER.recommend(
            {"assets": people + objects}, topic="목 통증", keyword="광주 한의원 추천",
            article_type="정보전달형", count=2, recent_ids=set(),
            placement_mode="closing-trust",
        )
        self.assertEqual([item["id"][0] for item in result["selected"]], ["P"] * 2, result)

    def test_all_official_media_is_bundled_inside_plugin(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        self.assertEqual(library["schemaVersion"], 3)
        self.assertEqual(library["assetCount"], 113)
        self.assertEqual(library["bundledAssetCount"], 113)
        self.assertEqual(library["safeAutoCount"], 6)
        self.assertEqual(library["closingTrustCount"], 7)
        self.assertEqual(OFFICIAL_MEDIA_SYNC.validate_library(library), [])
        self.assertTrue(all(str(item["bundledPath"]).startswith("assets/official-media/") for item in library["assets"]))
        approved = [item for item in library["assets"] if item.get("safeAuto")]
        self.assertTrue(all(item.get("personInteraction") is True for item in approved))
        self.assertTrue(all(item.get("directorVisible") is True for item in approved))
        self.assertTrue(all(str(item.get("sceneType", "")).startswith("director-patient-") for item in approved))
        self.assertTrue(all(item.get("placementTerms") for item in approved))
        self.assertTrue(all(item.get("approvedAlt") for item in approved))
        self.assertFalse(any(re.search(r"(?:로고|logo)", str(item.get("filename", "")), re.I) for item in approved))
        closing_trust = [item for item in library["assets"] if item.get("closingTrustEligible")]
        self.assertEqual(len(closing_trust), 7)
        self.assertTrue(all(item.get("closingTrustReviewed") is True for item in closing_trust))
        self.assertTrue(all(item.get("closingTrustPlacementTerms") for item in closing_trust))
        self.assertTrue(all(item.get("closingTrustApprovedAlt") for item in closing_trust))
        self.assertTrue(all(item.get("closingTrustContextText") for item in closing_trust))

    def test_unrelated_topic_reports_exact_context_photo_shortage(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        approved_ids = {item["id"] for item in library["assets"] if item.get("safeAuto")}
        result = MEDIA_RECOMMENDER.recommend(
            library,
            topic="갱년기 홍조 불면",
            keyword="광주 한의원 추천",
            article_type="정보전달형",
            count=1,
            recent_ids=approved_ids,
            placement_mode="before-credential",
        )
        self.assertEqual(result["status"], "decision-required", result)
        self.assertEqual(result["freshEligibleCount"], 0, result)
        self.assertEqual(result["immediatelyPreviousContextEligibleCount"], 0, result)
        self.assertEqual(result["reusedRecentCount"], 0, result)
        self.assertEqual(result["missingToMinimum"], 1, result)

    def test_closing_trust_uses_actual_treatment_photos_without_topic_context(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        result = MEDIA_RECOMMENDER.recommend(
            library,
            topic="갱년기 홍조 불면",
            keyword="광주 한의원 추천",
            article_type="정보전달형",
            count=2,
            recent_ids=set(),
            placement_mode="closing-trust",
        )
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual([item["id"] for item in result["selected"]], ["GH0016", "GH0017"])
        self.assertTrue(all(not item["matchedPlacementTerms"] for item in result["selected"]))
        self.assertTrue(
            all(
                item["figureAttributes"]["data-image-placement"] == "closing-clinical-gallery"
                for item in result["selected"]
            )
        )

    def test_closing_trust_reuses_previous_approved_treatment_photos_when_needed(self) -> None:
        library = json.loads((SKILL_DIR / "assets" / "media-library.json").read_text(encoding="utf-8"))
        approved_ids = {item["id"] for item in library["assets"] if item.get("safeAuto")}
        result = MEDIA_RECOMMENDER.recommend(
            library,
            topic="갱년기 홍조 불면",
            keyword="광주 한의원 추천",
            article_type="정보전달형",
            count=2,
            recent_ids=approved_ids,
            placement_mode="closing-trust",
        )
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["selectedCount"], 2, result)
        self.assertEqual(result["freshCount"], 0, result)
        self.assertEqual(result["reusedRecentCount"], 2, result)
        self.assertTrue(all(item["reusedFromRecent"] for item in result["selected"]))


class TopicSourceBoundaryTests(unittest.TestCase):
    def topic_library(self) -> dict[str, object]:
        return json.loads((SKILL_DIR / "assets" / "beomeo-topic-idea-library.json").read_text(encoding="utf-8"))

    def wipark_library(self) -> dict[str, object]:
        return json.loads((SKILL_DIR / "assets" / "topic-idea-library.json").read_text(encoding="utf-8"))

    def editorial_profiles(self) -> dict[str, object]:
        return json.loads((SKILL_DIR / "assets" / "beomeo-editorial-master-profiles.json").read_text(encoding="utf-8"))

    def test_all_69_posts_and_topic_only_boundary_validate(self) -> None:
        library = self.topic_library()
        inventory = TOPIC_SOURCE_VALIDATOR.parse_inventory(SKILL_DIR / "references" / "beomeo-source-inventory.md")
        self.assertEqual(TOPIC_SOURCE_VALIDATOR.validate_library(library, inventory), [])
        self.assertEqual(len(library["sourcePosts"]), 69)
        self.assertEqual(len(library["topicIdeas"]), 29)
        self.assertEqual(
            {item["topicCluster"] for item in library["topicIdeas"]},
            {"chuna", "traffic-accident", "pain", "digestive", "respiratory", "tonic", "growth", "weight-management"},
        )

    def test_topic_source_rejects_structure_fact_and_body_payloads(self) -> None:
        inventory = TOPIC_SOURCE_VALIDATOR.parse_inventory(SKILL_DIR / "references" / "beomeo-source-inventory.md")
        for forbidden_key in ("titlePatternId", "writingMasterId", "bodyText", "claims", "cases", "media"):
            mutated = json.loads(json.dumps(self.topic_library(), ensure_ascii=False))
            mutated["topicIdeas"][0][forbidden_key] = "금지 payload"
            errors = TOPIC_SOURCE_VALIDATOR.validate_library(mutated, inventory)
            self.assertTrue(any(forbidden_key in error for error in errors), (forbidden_key, errors))

    def test_selector_keeps_beomeo_topic_and_wipark_structure_separate(self) -> None:
        result = TOPIC_SELECTOR.select_ideas(
            self.wipark_library(),
            {"entries": []},
            "광주 한의원 추천",
            topic="다이어트 정체기 체성분",
            count=1,
            seed="beomeo-boundary",
            topic_source_library=self.topic_library(),
        )[0]
        self.assertEqual(result["topicSourceBlogId"], "beomeo_sm", result)
        self.assertTrue(result["topicSourceUrl"].startswith("https://blog.naver.com/beomeo_sm/"), result)
        self.assertTrue(result["ideaReferenceUrl"].startswith("https://blog.naver.com/wi-parkclinic/"), result)
        self.assertTrue(result["writingReferenceUrl"].startswith("https://blog.naver.com/wi-parkclinic/"), result)
        self.assertFalse(result["topicSourceControlsTitlePattern"])
        self.assertFalse(result["topicSourceControlsStructure"])

    def test_every_beomeo_topic_is_ready_or_has_one_live_audit_candidate(self) -> None:
        candidates = TOPIC_SELECTOR.external_topic_candidates(self.topic_library())
        statuses = {"ready": 0, "live-source-audit-required": 0}
        for candidate in candidates:
            status = candidate["editorialProfileStatus"]
            self.assertIn(status, statuses)
            statuses[status] += 1
            if status == "ready":
                self.assertTrue(all(candidate[field] for field in (
                    "editorialMasterId",
                    "editorialReferenceTitle",
                    "editorialReferenceUrl",
                    "editorialSourceRole",
                )))
            else:
                self.assertFalse(any(candidate[field] for field in (
                    "editorialMasterId",
                    "editorialReferenceTitle",
                    "editorialReferenceUrl",
                    "editorialSourceRole",
                )))
                self.assertTrue(all(candidate[field] for field in (
                    "editorialCandidateId",
                    "editorialCandidateTitle",
                    "editorialCandidateUrl",
                )))
                self.assertIn(candidate["editorialCandidateId"], candidate["topicSourcePostIds"])
        self.assertEqual(statuses, {"ready": 1, "live-source-audit-required": 28})

    def test_wipark_topic_uses_its_own_same_source_editorial_master(self) -> None:
        library = self.wipark_library()
        source = library["articles"][0]
        candidate = TOPIC_SELECTOR.wipark_topic_candidate(source, library)
        self.assertEqual(candidate["editorialProfileStatus"], "ready")
        self.assertEqual(candidate["editorialMasterId"], source["id"])
        self.assertEqual(candidate["editorialReferenceUrl"], source["sourceUrl"])

    def test_valid_body_reviewed_runtime_profile_promotes_candidate_to_ready(self) -> None:
        topic_library = self.topic_library()
        profiles = self.editorial_profiles()
        runtime = json.loads(json.dumps(profiles, ensure_ascii=False))
        base = json.loads(json.dumps(runtime["profiles"]["BM224231647991"], ensure_ascii=False))
        source = next(item for item in topic_library["sourcePosts"] if item["id"] == "BM224338019561")
        base.update({
            "id": source["id"],
            "sourcePostId": source["sourcePostId"],
            "sourceTitle": source["sourceTitle"],
            "sourceUrl": source["sourceUrl"],
            "appliesToTopicIdeaIds": ["BTI011"],
            "sourceAuditStatus": "body-reviewed",
        })
        runtime["profiles"][source["id"]] = base
        runtime["topicIdeaAssignments"]["BTI011"] = {
            "primaryEditorialSource": source["id"],
            "selectionReason": "실제 본문을 읽고 소화불량 질문과 전개를 확인한 실행용 프로필",
        }
        self.assertEqual(EDITORIAL_PROFILE_VALIDATOR.validate_profiles(runtime, topic_library), [])
        candidate = next(
            item for item in TOPIC_SELECTOR.external_topic_candidates(topic_library, runtime)
            if item["topicSourceId"] == "BTI011"
        )
        self.assertEqual(candidate["editorialProfileStatus"], "ready")
        self.assertEqual(candidate["editorialMasterId"], source["id"])

    def test_profile_without_body_review_status_cannot_promote(self) -> None:
        topic_library = self.topic_library()
        runtime = self.editorial_profiles()
        runtime["profiles"]["BM224231647991"]["sourceAuditStatus"] = "title-only"
        errors = EDITORIAL_PROFILE_VALIDATOR.validate_profiles(runtime, topic_library)
        self.assertTrue(any("sourceAuditStatus=body-reviewed" in error for error in errors), errors)

    def test_legacy_chuna_alias_blocks_chuna_topic(self) -> None:
        candidate = next(
            item
            for item in TOPIC_SELECTOR.external_topic_candidates(self.topic_library())
            if item["topicSourceId"] == "BTI001"
        )
        legacy = {
            "entries": [
                {
                    "title": "광주 한의원 추나 치료를 받아도 다시 아픈 이유",
                    "mainKeyword": "광주 한의원",
                    "topic": "추나 적용과 생활조건",
                    "type": "정보전달형",
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "no-semantic-fresh-topic"):
            TOPIC_SELECTOR.choose_topic_candidates([candidate], legacy, "광주 한의원", "추나요법", 1, "alias")

    def test_count_three_is_pairwise_semantically_distinct(self) -> None:
        results = TOPIC_SELECTOR.select_ideas(
            self.wipark_library(),
            {"entries": []},
            "광주 한의원 추천",
            count=3,
            seed="semantic-pairwise",
            topic_source_library=self.topic_library(),
        )
        self.assertEqual(len(results), 3)
        for index, left in enumerate(results):
            for right in results[index + 1 :]:
                self.assertFalse(TOPIC_SELECTOR.semantic_overlap(left, right), (left, right))

    def test_same_cluster_different_subject_can_remain_fresh(self) -> None:
        candidates = TOPIC_SELECTOR.external_topic_candidates(self.topic_library())
        left = next(item for item in candidates if item["topicSourceId"] == "BTI021")
        right = next(item for item in candidates if item["topicSourceId"] == "BTI024")
        self.assertEqual(left["topicCluster"], right["topicCluster"])
        self.assertFalse(TOPIC_SELECTOR.semantic_overlap(left, right))


class ReferenceCorpusTests(unittest.TestCase):
    def corpus(self) -> dict[str, object]:
        return json.loads((SKILL_DIR / "assets" / "wipark-reference-corpus.json").read_text(encoding="utf-8"))

    def ideas(self) -> dict[str, object]:
        return json.loads((SKILL_DIR / "assets" / "topic-idea-library.json").read_text(encoding="utf-8"))

    def test_cutoff_audit_is_complete_and_daily_posts_are_excluded(self) -> None:
        corpus = self.corpus()
        self.assertEqual(corpus["sourceBlogId"], "wi-parkclinic")
        self.assertEqual(corpus["cutoffInclusive"], "2024-10-04")
        self.assertEqual(corpus["sourceTotalCount"], 196)
        self.assertEqual(corpus["includedCount"], 130)
        self.assertEqual(corpus["fetchSuccessCount"], 130)
        self.assertEqual(corpus["fetchFailureCount"], 0)
        articles = corpus["articles"]
        self.assertEqual(min(item["publishedAt"] for item in articles), "2024-10-04")
        counts: dict[str, int] = {}
        for item in articles:
            counts[item["contentType"]] = counts.get(item["contentType"], 0) + 1
            self.assertNotIn("bodyText", item)
            self.assertNotIn("sourceHtml", item)
            if item["contentType"] == "제외":
                self.assertFalse(item["eligible"])
        self.assertEqual(
            counts,
            {"정보전달형": 88, "업체소개형": 4, "사례공유형": 4, "스토리텔링형": 2, "제외": 32},
        )

    def test_idea_and_writing_master_roles_are_separate(self) -> None:
        library = self.ideas()
        self.assertEqual(library["sourceArticleCount"], 130)
        self.assertEqual(library["articleCount"], 11)
        self.assertEqual(library["excludedCount"], 119)
        self.assertEqual(library["sourceExcludedCount"], 32)
        self.assertEqual(library["familyFilteredOutCount"], 119)
        self.assertTrue(
            all(
                item["sourceFactsBlocked"]
                and item["sourceSentencesBlocked"]
                and item["sourceMediaBlocked"]
                and item["sourceContentType"] == "정보전달형"
                and item["referenceFamilyId"] == "two-or-three-reader-concern-hooks-solution-preview-info"
                and item["minimumReaderHookCount"] == 2
                and item["maximumReaderHookCount"] == 3
                and item["allowedReaderHookCounts"] == [2, 3]
                and item["requiresSolutionPreviewBeforeBody"]
                for item in library["articles"]
            )
        )
        selections = TOPIC_SELECTOR.select_ideas(
            library,
            {"entries": []},
            "광주 한의원",
            topic="목 통증",
            count=3,
            seed="contract-test",
        )
        self.assertEqual(len(selections), 3)
        self.assertTrue(all(item["sourceContentType"] == "정보전달형" for item in selections))
        self.assertTrue(all(item["ideaReferenceUrl"].startswith("https://blog.naver.com/wi-parkclinic/") for item in selections))
        self.assertTrue(all(item["writingReferenceUrl"].startswith("https://blog.naver.com/wi-parkclinic/") for item in selections))
        self.assertTrue(all("금손한의원 사실" in item["factPolicy"] for item in selections))
        broad = TOPIC_SELECTOR.select_ideas(
            library,
            {"entries": []},
            "광주 한의원",
            count=1,
            seed="broad-clinic-contract",
        )[0]
        self.assertEqual(broad["ideaReferenceId"], "WP224320052203", broad)
        self.assertEqual(broad["writingMasterId"], "INFO01", broad)
        legacy_state = {
            "schemaVersion": 1,
            "entries": [
                {
                    "mainKeyword": "광주 한의원",
                    "ideaReferenceUrl": "https://blog.naver.com/wi-parkclinic/224320052203",
                    "writingMasterId": "INFO01",
                    "topic": "치료받아도 반복되는 생활 조건",
                    "title": "광주 한의원 통증이 반복되는 생활 조건 2가지",
                    "titlePattern": "특징 2가지",
                    "type": "정보전달형",
                }
            ],
        }
        rotated = TOPIC_SELECTOR.select_ideas(
            library,
            legacy_state,
            "광주 한의원",
            count=1,
            seed="legacy-state-contract",
        )[0]
        self.assertNotEqual(rotated["ideaReferenceId"], "WP224320052203", rotated)
        self.assertNotEqual(rotated["writingMasterId"], "INFO01", rotated)

    def test_master_profiles_are_exactly_the_eleven_allowed_information_posts(self) -> None:
        data = json.loads((SKILL_DIR / "assets" / "reference-master-profiles.json").read_text(encoding="utf-8"))
        profiles = data["profiles"]
        self.assertEqual(len(profiles), 11)
        counts: dict[str, int] = {}
        for profile in profiles.values():
            counts[profile["type"]] = counts.get(profile["type"], 0) + 1
            self.assertTrue(profile["sourceUrl"].startswith("https://blog.naver.com/wi-parkclinic/"))
            self.assertIn("maximumCenterRatio", profile["renderContract"])
            self.assertEqual(profile["renderContract"]["nativeDesignSystemId"], "goldhand-naver-native-v4")
            self.assertFalse(profile["renderContract"]["referenceControlsDecoration"])
            self.assertEqual(profile["renderContract"]["minimumCenterRatio"], 1.0)
            self.assertEqual(profile["renderContract"]["maximumCenterRatio"], 1.0)
            self.assertEqual(profile["renderContract"]["requiredUnderlineMinimum"], 2)
            self.assertEqual(profile["referenceFamilyId"], "two-or-three-reader-concern-hooks-solution-preview-info")
            self.assertEqual(profile["renderContract"]["requiredRoleMinimums"]["reader-question"], 2)
            self.assertEqual(profile["renderContract"]["requiredRoleMaximums"]["reader-question"], 3)
            self.assertEqual(profile["renderContract"]["requiredRoleMinimums"]["solution-preview"], 1)
            self.assertTrue(profile["writingContract"]["referenceExpressionLearningEnabled"])
            self.assertTrue(profile["toneContract"]["referenceRhetoricalReasoningEnabled"])
            self.assertTrue(profile["editorialReasoningContract"]["adaptationDecisionRequired"])
            self.assertNotIn("sourceToneBlocked", json.dumps(profile, ensure_ascii=False))
        self.assertEqual(counts, {"정보전달형": 11})
        self.assertNotIn("INFO02", profiles)

    def test_reference_writing_intelligence_contains_eleven_valid_profiles(self) -> None:
        intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(encoding="utf-8")
        )
        family = json.loads(
            (SKILL_DIR / "assets" / "two-reader-hooks-reference-family.json").read_text(encoding="utf-8")
        )
        errors = REFERENCE_LEARNING_VALIDATOR.validate_intelligence(intelligence, family)
        self.assertEqual(errors, [])
        self.assertEqual(len(intelligence["profiles"]), 11)
        self.assertEqual(
            intelligence["profiles"]["INFO06"]["openingMechanism"]["numericPrincipleChain"],
            [
                "specific-number",
                "perceived-concreteness",
                "low-effort",
                "attention",
                "topic-specific-payoff",
            ],
        )
        self.assertEqual(
            intelligence["profiles"]["INFO08"]["openingMechanism"]["primaryDeviceId"],
            "specific-number-low-friction-topic-payoff",
        )


class SkillPackageTests(unittest.TestCase):
    def test_required_contract_files_exist(self) -> None:
        for relative in (
            "SKILL.md",
            "agents/openai.yaml",
            "references/clinic-facts.md",
            "references/content-formulas.md",
            "references/two-reader-hooks-reference-audit.md",
            "references/reference-master-library.md",
            "references/reference-exact-reconstruction.md",
            "references/reference-editorial-reasoning.md",
            "references/official-blog-inventory.md",
            "references/topic-idea-types.md",
            "references/beomeo-source-inventory.md",
            "references/beomeo-topic-source-policy.md",
            "references/wipark-reference-inventory.md",
            "references/wipark-content-source-policy.md",
            "references/goldhand-official-voice.md",
            "references/natural-speech-rewrite-protocol.md",
            "references/final-writing-voice-review.md",
            "assets/media-library.json",
            "assets/topic-idea-library.json",
            "assets/beomeo-topic-idea-library.json",
            "assets/wipark-reference-corpus.json",
            "assets/reference-master-profiles.json",
            "assets/reference-writing-intelligence.json",
            "assets/goldhand-naver-native-design-system.json",
            "assets/goldhand-closing-links.json",
            "assets/callilife-ogq-media-library.json",
            "assets/gpt-image-test-fixture.png",
            "assets/goldhand-value-proof-library.json",
            "assets/two-reader-hooks-reference-family.json",
            "assets/wipark-content-briefs.json",
            "assets/goldhand-official-voice-profile.json",
            "assets/writing-voice-final-review-contract.json",
            "scripts/select_topic_idea.py",
            "scripts/validate_topic_source_library.py",
            "scripts/select_reference_master.py",
            "scripts/validate_reference_reconstruction.py",
            "scripts/select_wipark_content_reference.py",
            "scripts/validate_reference_learning.py",
            "scripts/validate_goldhand_voice.py",
            "scripts/validate_natural_speech_suite.py",
            "scripts/validate_final_voice_review.py",
            "scripts/sync_official_media_assets.py",
            "scripts/recommend_media.py",
            "scripts/recommend_closing_trust_media.py",
            "scripts/setup_image_host.py",
            "../writing-voice/SKILL.md",
        ):
            self.assertTrue((SKILL_DIR / relative).is_file(), relative)
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        proof = json.loads((SKILL_DIR / "assets" / "goldhand-value-proof-library.json").read_text(encoding="utf-8"))
        design = json.loads((SKILL_DIR / "assets" / "goldhand-naver-native-design-system.json").read_text(encoding="utf-8"))
        openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertFalse(proof["selectionAllowed"])
        self.assertEqual(len(proof["fixedRows"]), 6)
        self.assertEqual(design["layout"]["bodyTextAlign"], "center")
        self.assertEqual(design["textEmphasis"]["minimumTotalCount"], 6)
        self.assertEqual(design["textEmphasis"]["highlight"]["minimumCount"], 3)
        self.assertFalse(design["retentionHooks"]["titleRequiresNumericAnswerPromise"])
        self.assertFalse(design["retentionHooks"]["readingTime"]["requiredForEveryArticle"])
        self.assertEqual(design["retentionHooks"]["readingTime"]["minimumMinutes"], 1)
        self.assertEqual(design["retentionHooks"]["readingTime"]["maximumMinutes"], 5)
        self.assertTrue(design["retentionHooks"]["readingTime"]["topicSpecificPayoffRequired"])
        self.assertEqual(design["generatedReferenceMedia"]["creator"], "callilife")
        self.assertEqual(design["generatedReferenceMedia"]["minimumCount"], 3)
        self.assertEqual(design["generatedReferenceMedia"]["maximumCount"], 4)
        self.assertEqual(design["realGoldhandMedia"]["minimumCount"], 1)
        self.assertEqual(design["realGoldhandMedia"]["maximumCount"], 2)
        self.assertEqual(design["realGoldhandMedia"]["recentArticleWindow"], 1)
        self.assertFalse(design["realGoldhandMedia"]["recentReuseAllowedWhenFreshBelowTarget"])
        self.assertEqual(design["realGoldhandMedia"]["recentReuseMaximumPerArticle"], 0)
        self.assertEqual(design["realGoldhandMedia"]["allowedLayouts"], {"before-credential": 1, "closing-trust": 2})
        self.assertTrue(design["realGoldhandMedia"]["placementTermsRequired"])
        self.assertEqual(
            design["realGoldhandMedia"]["contextMatchRequiredByLayout"],
            {"before-credential": True, "closing-trust": False},
        )
        self.assertEqual(
            design["realGoldhandMedia"]["requiredFigurePlacementByLayout"],
            {"before-credential": "after-related-paragraph", "closing-trust": "closing-clinical-gallery"},
        )
        self.assertTrue(design["realGoldhandMedia"]["closingTrustRecentReuseAllowedWhenFreshBelowTarget"])
        self.assertEqual(design["realGoldhandMedia"]["closingTrustRecentReuseMaximumPerArticle"], 2)
        self.assertTrue(design["realGoldhandMedia"]["approvedAltRequired"])
        self.assertTrue(design["realGoldhandMedia"]["personInteractionRequired"])
        self.assertTrue(design["realGoldhandMedia"]["directorVisibleRequired"])
        self.assertEqual(design["closingCredentialTrustMedia"]["exactCount"], 1)
        self.assertTrue(design["closingCredentialTrustMedia"]["separateFromClinicalMedia"])
        self.assertFalse(design["closingCredentialTrustMedia"]["countsTowardRealGoldhandMedia"])
        self.assertEqual(design["closingCredentialTrustMedia"]["requiredSlot"], "closing-credential-trust")
        self.assertTrue(design["closingCredentialTrustMedia"]["mustBeLastImageBeforeClinicHours"])
        self.assertFalse(design["closingCredentialTrustMedia"]["immediatelyPreviousArticleReuseAllowed"])
        self.assertFalse(design["fixedClosingLinks"]["enabled"])
        self.assertFalse(design["fixedClosingLinks"]["requiredOnEveryArticle"])
        self.assertEqual(design["fixedClosingLinks"]["articleEndsWith"], "clinic-info")
        self.assertTrue(design["finalWritingVoiceReview"]["requiredOnEveryArticle"])
        self.assertFalse(design["finalWritingVoiceReview"]["allowForcedEdit"])
        self.assertEqual(
            design["finalWritingVoiceReview"]["contractId"],
            "writing-voice-final-rehear-v1",
        )
        self.assertEqual(design["generatedReferenceMedia"]["contentPreservation"], "medical-information-layout")
        self.assertEqual(
            design["generatedReferenceMedia"]["allowedVariationModes"],
            ["person-identity-subtle-variation", "nonperson-style-subtle-variation"],
        )
        self.assertEqual(design["tablePurposes"]["clinic-hours"]["columnWidths"], ["24%", "38%", "38%"])
        self.assertEqual(design["tablePurposes"]["clinic-hours"]["minimumRows"], 4)
        self.assertEqual(design["tablePurposes"]["clinic-hours"]["maximumRows"], 4)
        self.assertEqual(design["tablePurposes"]["clinic-info"]["minimumColumns"], 1)
        self.assertEqual(design["tablePurposes"]["clinic-info"]["maximumColumns"], 1)
        self.assertEqual(design["tablePurposes"]["clinic-info"]["columnWidth"], "100%")
        self.assertEqual(design["tablePurposes"]["clinic-info"]["minimumRows"], 4)
        self.assertEqual(design["tablePurposes"]["clinic-info"]["maximumRows"], 4)
        self.assertEqual(design["textEmphasis"]["red"]["minimumCount"], 1)
        credential_placement = design["editorialCloseOverrides"]["credentialPlacement"]
        self.assertTrue(credential_placement["appliesToEveryArticle"])
        self.assertEqual(credential_placement["requiredAfterCompletedRole"], "solution-preview")
        self.assertEqual(credential_placement["allowedInterveningContentRoles"], ["evidence-media:before-credential"])
        self.assertEqual(
            credential_placement["requiredImmediatelyBeforeFirstInformationBodyRole"],
            ["divider", "section-heading"],
        )
        self.assertIn("실제 고민을 금손 내용으로 바꿔 2~3개", skill)
        self.assertIn("일상글", skill)
        self.assertIn("fallback 어디에도 넣지 않는다", skill)
        self.assertIn("wipark-content-briefs.json", skill)
        self.assertIn("최근 3개", skill)
        self.assertIn("goldhand-official-voice-v1", skill)
        self.assertIn("위석 원문의 완성 문장", skill)
        self.assertIn("referenceWritingIntelligence", skill)
        self.assertIn("validate_goldhand_voice.py", skill)
        self.assertIn("validate_natural_speech_suite.py", skill)
        self.assertIn("validate_final_voice_review.py", skill)
        self.assertIn("final-writing-voice-review.md", skill)
        self.assertIn("writing-voice-final-rehear-v1", skill)
        self.assertIn("`before-credential`은 해결 방향 예고 뒤", skill)
        self.assertIn("`closing-trust`는 다른 사진을 우선하되", skill)
        self.assertIn("질환·부위·본문 문맥과 맞지 않아도", skill)
        self.assertIn("GPT Image 3~4장", skill)
        self.assertIn("placementTerms", skill)
        self.assertIn("approvedAlt", skill)
        self.assertIn("assets/official-media", skill)
        self.assertIn("clinic-info 운영정보 표에서 끝", skill)
        self.assertIn("`clinic-hours` 진료시간 3열 표", skill)
        self.assertNotIn("goldhand-naver-editor-finisher", skill)
        self.assertIn("로고·간판·건물 외부·약·환제·탕약·장비·제품·빈 원내 공간", skill)
        self.assertNotIn("Desktop/" + "금손한의원 사진", skill)
        self.assertIn("진료실 발화 가능성 검사", skill)
        self.assertIn("natural-speech-rewrite-protocol.md", skill)
        self.assertIn("orderedContentAtoms", skill)
        self.assertIn("sourceProseWithheld=true", skill)
        self.assertIn("별도 발화 편집", skill)
        self.assertIn("질문의 기능·구체성·리듬·설득 심리", skill)
        self.assertIn("data-question-source", skill)
        self.assertIn("solution-preview", skill)
        self.assertIn("goldhand-naver-native-v4", skill)
        self.assertIn("첫 정보 본문의 구분선·소제목·설명보다 앞", skill)
        self.assertIn("reference-editorial-reasoning.md", openai_yaml)
        self.assertIn("specific number -> perceived concreteness -> low effort -> attention -> topic-specific payoff", openai_yaml)
        self.assertIn("Preserve the fixed Goldhand credential table after the complete introduction", openai_yaml)
        self.assertIn("Never use a logo, sign, building", openai_yaml)
        self.assertNotIn("Naver Place map block", openai_yaml)
        self.assertNotIn("clickable Goldhand director-consultation photo", openai_yaml)
        self.assertIn("Keep the fixed clinic information table unchanged as the final article component", openai_yaml)
        self.assertIn("Do not append a related-reading label", openai_yaml)
        self.assertIn("Use orderedContentAtoms as the factual skeleton and flowBeats as the editorial sequence", openai_yaml)
        self.assertIn("naturalize the adapted reasoning without erasing it", openai_yaml)
        self.assertIn("separate spoken-editor pass", openai_yaml)
        self.assertIn("final writing-voice rehear pass", openai_yaml)
        self.assertIn("$writing-voice", openai_yaml)
        self.assertIn("data-mobile-group", skill)
        self.assertNotIn("Notion TOP 5", skill)

    def test_writing_voice_skill_is_bundled_exactly(self) -> None:
        bundled = SKILL_DIR.parent / "writing-voice" / "SKILL.md"
        self.assertTrue(bundled.is_file())
        self.assertEqual(
            hashlib.sha256(bundled.read_bytes()).hexdigest(),
            "4dcbc094c3c129f7c33d012ceff4b327a7c0084cfed3459ffdee8122d81e0fbd",
        )
        text = bundled.read_text(encoding="utf-8")
        self.assertIn("name: writing-voice", text)
        self.assertIn("Make the writer easier to hear", text)
        self.assertIn("Do not add, remove, reorder, promote, or demote material", text)

    def test_shared_skill_package_has_no_owner_machine_paths(self) -> None:
        owner_machine_prefix = "/Users/" + "seojun"
        for path in SKILL_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".py", ".yaml", ".yml"}:
                continue
            self.assertNotIn(owner_machine_prefix, path.read_text(encoding="utf-8"), str(path))

    def test_windows_requirements_cover_network_parsing_and_timezone(self) -> None:
        from zoneinfo import ZoneInfo

        requirements = (SKILL_DIR.parents[1] / "requirements-windows.txt").read_text(encoding="utf-8").splitlines()
        self.assertIn("beautifulsoup4==4.13.5", requirements)
        self.assertIn("requests==2.32.5", requirements)
        self.assertIn("tzdata==2026.3", requirements)
        self.assertEqual(ZoneInfo("Asia/Seoul").key, "Asia/Seoul")

    def test_official_goldhand_voice_is_required_and_emoticons_fail(self) -> None:
        profile = json.loads((SKILL_DIR / "assets" / "goldhand-official-voice-profile.json").read_text(encoding="utf-8"))
        example = (SKILL_DIR / "examples" / "광주-한의원-네이버-순정-원고.html").read_text(encoding="utf-8")
        passed = GOLDHAND_VOICE_VALIDATOR.validate(example, profile)
        self.assertEqual(passed["status"], "pass", passed)
        failed = GOLDHAND_VOICE_VALIDATOR.validate(example.replace("그런데", "ㅎㅎ 그런데", 1), profile)
        self.assertEqual(failed["status"], "fail", failed)
        self.assertIn("emoticon", {item["code"] for item in failed["issues"]})

    def test_spoken_clinic_gate_rejects_ai_register_not_only_exact_examples(self) -> None:
        profile = json.loads((SKILL_DIR / "assets" / "goldhand-official-voice-profile.json").read_text(encoding="utf-8"))
        example = (SKILL_DIR / "examples" / "광주-한의원-네이버-순정-원고.html").read_text(encoding="utf-8")
        direct = GOLDHAND_VOICE_VALIDATOR.validate(example, profile)
        self.assertEqual(direct["status"], "pass", direct)

        translated = example.replace(
            "혼자 판단해서 운동을 계속하시면 안 됩니다.",
            "혼자 스트레칭을 지속하지 마세요.",
            1,
        )
        translated_result = GOLDHAND_VOICE_VALIDATOR.validate(translated, profile)
        self.assertIn(
            "translated-indirect-safety-command",
            {item["code"] for item in translated_result["issues"]},
        )

        homework = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "그때의 몸 변화를 기록해 보세요.",
            1,
        )
        homework_result = GOLDHAND_VOICE_VALIDATOR.validate(homework, profile)
        self.assertIn("reader-homework-imperative", {item["code"] for item in homework_result["issues"]})

        poetic = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "이것이 회복의 첫걸음이 됩니다.",
            1,
        )
        poetic_result = GOLDHAND_VOICE_VALIDATOR.validate(poetic, profile)
        self.assertIn("poetic-abstract-payoff", {item["code"] for item in poetic_result["issues"]})

        softened = example.replace(
            "혼자 판단해서 운동을 계속하시면 안 됩니다.",
            "저림이 있으면 운동을 쉬어 보는 편이 좋습니다.",
            1,
        )
        softened_result = GOLDHAND_VOICE_VALIDATOR.validate(softened, profile)
        self.assertIn("over-softened-medical-guidance", {item["code"] for item in softened_result["issues"]})

    def test_voice_gate_rejects_user_reported_parallel_hooks_and_abstract_transition(self) -> None:
        profile = json.loads((SKILL_DIR / "assets" / "goldhand-official-voice-profile.json").read_text(encoding="utf-8"))
        example = (SKILL_DIR / "examples" / "광주-한의원-네이버-순정-원고.html").read_text(encoding="utf-8")
        bad_hooks = example.replace(
            "치료받은 날은 편했는데, 왜 며칠 지나면 통증이 다시 나타날까요?",
            "홍조 때문에 얼굴이 달아오르고 땀이 나서 사람 만나는 게 불편해졌나요?",
            1,
        ).replace(
            "아픈 곳만 치료하면 되는 건지, 자세와 움직임도 함께 봐야 할까요?",
            "불면 때문에 새벽에 깨고, 다음 날 피로와 가라앉은 기분도 이어지나요?",
            1,
        )
        hook_result = GOLDHAND_VOICE_VALIDATOR.validate(bad_hooks, profile)
        hook_codes = {item["code"] for item in hook_result["issues"]}
        self.assertIn("parallel-because-hook-template", hook_codes, hook_result)
        self.assertIn("stacked-symptom-summary-question", hook_codes, hook_result)

        abstract_transition = example.replace(
            "자주 겪는 장면 하나면 충분합니다.",
            "어느 불편이 하루를 가장 많이 흔드는지 알면 설명도 이어집니다.",
            1,
        )
        transition_result = GOLDHAND_VOICE_VALIDATOR.validate(abstract_transition, profile)
        self.assertIn(
            "abstract-symptom-ranking-transition",
            {item["code"] for item in transition_result["issues"]},
            transition_result,
        )

    def test_all_reference_profiles_force_hooks_before_greeting(self) -> None:
        family = json.loads(
            (SKILL_DIR / "assets" / "two-reader-hooks-reference-family.json").read_text(encoding="utf-8")
        )
        self.assertTrue(family["articles"])
        self.assertTrue(all(item["questionPlacement"] == "before-greeting" for item in family["articles"]))
        self.assertTrue(
            all(item["openingMode"] == "two-quotation-components-then-greeting" for item in family["articles"])
        )

    def test_spoken_clinic_gate_rejects_additional_ai_registers(self) -> None:
        profile = json.loads((SKILL_DIR / "assets" / "goldhand-official-voice-profile.json").read_text(encoding="utf-8"))
        example = (SKILL_DIR / "examples" / "광주-한의원-네이버-순정-원고.html").read_text(encoding="utf-8")
        meta = example.replace(
            "제가 진료할 때 여쭙는 건",
            "이번 글에서는 함께 살펴보겠습니다",
            1,
        )
        meta_result = GOLDHAND_VOICE_VALIDATOR.validate(meta, profile)
        self.assertIn("blog-meta-framing", {item["code"] for item in meta_result["issues"]})

        afterglow = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "이 내용이 작은 도움이 되었으면 합니다.",
            1,
        )
        afterglow_result = GOLDHAND_VOICE_VALIDATOR.validate(afterglow, profile)
        self.assertIn("lesson-afterglow-ending", {item["code"] for item in afterglow_result["issues"]})

        literary_location = example.replace(
            "아픈 곳만 말씀하지 마시고",
            "아픈 자리만 말씀하지 마시고",
            1,
        )
        literary_location_result = GOLDHAND_VOICE_VALIDATOR.validate(literary_location, profile)
        self.assertIn(
            "literary-body-location",
            {item["code"] for item in literary_location_result["issues"]},
        )

        abstract_gait = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "걷기가 달라지면 진료할 때 말씀해 주세요.",
            1,
        )
        abstract_gait_result = GOLDHAND_VOICE_VALIDATOR.validate(abstract_gait, profile)
        self.assertIn(
            "abstract-gait-description",
            {item["code"] for item in abstract_gait_result["issues"]},
        )

        abstract_predicate = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "이 내용이 치료 방향에 차이를 만듭니다.",
            1,
        )
        abstract_predicate_result = GOLDHAND_VOICE_VALIDATOR.validate(abstract_predicate, profile)
        self.assertIn(
            "abstract-editorial-predicate",
            {item["code"] for item in abstract_predicate_result["issues"]},
        )

        natural_gait = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "평소보다 걷기 힘들다면 진료할 때 말씀해 주세요.",
            1,
        )
        natural_gait_result = GOLDHAND_VOICE_VALIDATOR.validate(natural_gait, profile)
        self.assertEqual(natural_gait_result["status"], "pass", natural_gait_result)

        symmetric = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "하루 편했다고 다 나았다고 말할 수는 없습니다. 반대로 다음 날 아팠다고 치료가 소용없었다고 볼 수도 없습니다.",
            1,
        )
        symmetric_result = GOLDHAND_VOICE_VALIDATOR.validate(symmetric, profile)
        self.assertIn(
            "symmetric-caveat-chain",
            {item["code"] for item in symmetric_result["issues"]},
        )

        possibility = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "아플 수 있습니다. 저릴 수 있습니다. 뻐근할 수 있습니다. 힘들 수 있습니다. 달라질 수 있습니다. 불편할 수 있습니다.",
            1,
        )
        possibility_result = GOLDHAND_VOICE_VALIDATOR.validate(possibility, profile)
        self.assertIn(
            "possibility-ending-overuse",
            {item["code"] for item in possibility_result["issues"]},
        )

        treatment_catalogue = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "침, 약침, 추나, 물리치료, 한약을 차례로 고려합니다.",
            1,
        )
        treatment_catalogue_result = GOLDHAND_VOICE_VALIDATOR.validate(treatment_catalogue, profile)
        self.assertIn(
            "treatment-catalogue",
            {item["code"] for item in treatment_catalogue_result["issues"]},
        )

        priority = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "먼저 시작을 묻고 먼저 잠을 묻고 먼저 식사를 묻고 먼저 걷기를 묻고 먼저 약을 묻고 먼저 검사를 묻습니다.",
            1,
        )
        priority_result = GOLDHAND_VOICE_VALIDATOR.validate(priority, profile)
        self.assertIn(
            "priority-transition-overuse",
            {item["code"] for item in priority_result["issues"]},
        )

        contrast = example.replace(
            "진료할 때 같이 말씀해 주세요.",
            "반대로 아침에는 괜찮습니다. 반대로 오후에는 아픕니다. 반대로 밤에는 잠을 설칩니다.",
            1,
        )
        contrast_result = GOLDHAND_VOICE_VALIDATOR.validate(contrast, profile)
        self.assertIn(
            "binary-contrast-overuse",
            {item["code"] for item in contrast_result["issues"]},
        )

    def test_mobile_br_is_not_a_sentence_boundary_for_voice_cadence(self) -> None:
        fragment = "<article><p>모니터를 오래 내려다보면<br>오후에 목이 뻐근해집니다.</p><p>다음 문장입니다.</p></article>"
        text = GOLDHAND_VOICE_VALIDATOR.prose_text(fragment)
        self.assertEqual(
            GOLDHAND_VOICE_VALIDATOR.prose_sentences(text),
            ["모니터를 오래 내려다보면 오후에 목이 뻐근해집니다.", "다음 문장입니다."],
        )

    def test_final_writing_voice_review_accepts_accounted_local_revision(self) -> None:
        contract = json.loads(
            (SKILL_DIR / "assets" / "writing-voice-final-review-contract.json").read_text(encoding="utf-8")
        )
        title = "광주 한의원 팔을 들 때 아픈 이유"
        before = [
            "현재의 불편 양상을 종합적으로 살펴볼 필요가 있습니다.",
            "통증이 심해지면 운동을 멈추셔야 합니다.",
        ]
        final = [
            "팔을 들 때 어디가 어떻게 아픈지 먼저 봐야 합니다.",
            "통증이 심해지면 운동을 멈추셔야 합니다.",
        ]
        case = {
            "title": title,
            "finalBody": final,
            "writingVoiceReview": writing_voice_review(
                title,
                before,
                final,
                expressive_jobs={
                    1: "환자가 팔을 드는 장면과 아픈 곳을 바로 떠올리도록 추상적인 말을 직접적인 설명으로 바꿈"
                },
            ),
        }
        result = FINAL_WRITING_VOICE_VALIDATOR.validate_case(case, contract)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["changedParagraphs"], 1)

    def test_final_writing_voice_review_allows_no_change_when_voice_already_holds(self) -> None:
        contract = json.loads(
            (SKILL_DIR / "assets" / "writing-voice-final-review-contract.json").read_text(encoding="utf-8")
        )
        title = "광주 한의원 목이 다시 뻐근한 이유"
        body = ["모니터를 오래 내려다보면 오후에 목이 다시 뻐근해집니다."]
        case = {
            "title": title,
            "finalBody": body,
            "writingVoiceReview": writing_voice_review(title, body, body),
        }
        result = FINAL_WRITING_VOICE_VALIDATOR.validate_case(case, contract)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["changedParagraphs"], 0)

    def test_final_writing_voice_review_rejects_generic_or_unaccounted_change(self) -> None:
        contract = json.loads(
            (SKILL_DIR / "assets" / "writing-voice-final-review-contract.json").read_text(encoding="utf-8")
        )
        title = "광주 한의원 어깨 통증"
        before = ["어깨의 불편 양상을 확인합니다."]
        final = ["팔을 들 때 어깨 앞쪽이 아픈지 봅니다."]
        review = writing_voice_review(title, before, final)
        review["revisions"][0]["expressiveJob"] = "더 자연스럽게"
        review["frozenMaterial"]["claimStrengthPreserved"] = False
        case = {"title": title, "finalBody": final, "writingVoiceReview": review}
        result = FINAL_WRITING_VOICE_VALIDATOR.validate_case(case, contract)
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("writing-voice-expressive-job-missing", codes, result)
        self.assertIn("writing-voice-frozen-material-failed", codes, result)

    def test_final_writing_voice_review_is_required(self) -> None:
        contract = json.loads(
            (SKILL_DIR / "assets" / "writing-voice-final-review-contract.json").read_text(encoding="utf-8")
        )
        result = FINAL_WRITING_VOICE_VALIDATOR.validate_case(
            {"title": "광주 한의원 목 통증", "finalBody": ["오후에 목이 뻐근합니다."]},
            contract,
        )
        self.assertIn("writing-voice-review-missing", {item["code"] for item in result["issues"]})

    def test_plain_draft_suite_rejects_three_sentence_paragraph_template(self) -> None:
        profile = json.loads((SKILL_DIR / "assets" / "goldhand-official-voice-profile.json").read_text(encoding="utf-8"))
        briefs = json.loads((SKILL_DIR / "assets" / "wipark-content-briefs.json").read_text(encoding="utf-8"))
        atom_ids = [atom["id"] for atom in briefs["briefs"]["INFO01"]["orderedContentAtoms"]]
        paragraph = "광주 한의원에서 모니터를 봅니다. 오후에는 목이 뻐근합니다. 어깨도 같이 올라가죠."
        final_body = [
            "모니터를 오래 보고 나면 오후마다 목이 뻐근해지나요?",
            "고개를 돌릴 때 어깨까지 같이 당기시나요?",
            "안녕하세요, 금손한의원 박준희 원장입니다.",
            *[paragraph for _ in range(10)],
        ]
        case = {
            "iteration": 1,
            "briefId": "INFO01",
            "keyword": "광주 한의원",
            "title": "광주 한의원 목 통증을 볼 2가지",
            "finalBody": final_body,
            "atomCoverage": {atom_id: "모니터를 봅니다" for atom_id in atom_ids},
            "manualReview": {
                "soundsSpoken": True,
                "onePassMeaning": True,
                "sceneIsVisible": True,
                "noTemplateFlow": True,
                "finalStatus": "pass",
                "revisionHistory": ["검수"],
            },
            "writingVoiceReview": writing_voice_review(
                "광주 한의원 목 통증을 볼 2가지",
                final_body,
                final_body,
            ),
        }
        result = NATURAL_SPEECH_SUITE_VALIDATOR.validate_suite(
            {"cases": [case]},
            profile,
            briefs,
            expected_count=1,
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("paragraph-cadence-single-template", codes)
        self.assertIn("paragraph-cadence-dominance", codes)
        self.assertIn("paragraph-cadence-run", codes)
        self.assertFalse(any(code.startswith("writing-voice:") for code in codes), result)

    def test_plain_draft_suite_rejects_cross_draft_eight_word_copy(self) -> None:
        repeated = NATURAL_SPEECH_SUITE_VALIDATOR.repeated_cross_case_phrases(
            [
                {"iteration": 1, "finalBody": ["하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉"]},
                {"iteration": 2, "finalBody": ["다른 시작 하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉"]},
            ]
        )
        self.assertTrue(repeated, repeated)

    def test_wipark_selector_emits_editorial_reasoning_and_goldhand_adaptation(self) -> None:
        briefs = json.loads((SKILL_DIR / "assets" / "wipark-content-briefs.json").read_text(encoding="utf-8"))
        profiles = json.loads((SKILL_DIR / "assets" / "reference-master-profiles.json").read_text(encoding="utf-8"))
        selected = WIPARK_CONTENT_SELECTOR.select(
            "광주 한의원", "", briefs, profiles, {"entries": []}, count=1, seed="content-voice-contract"
        )[0]
        self.assertTrue(selected["orderedContentAtoms"])
        self.assertNotIn("orderedGeneralInformation", selected)
        self.assertTrue(selected["sourceProseWithheld"])
        self.assertTrue(selected["contentAtomCoverageRequired"])
        self.assertTrue(selected["sourceSentenceImitationBlocked"])
        self.assertTrue(selected["referenceExpressionLearningEnabled"])
        self.assertTrue(selected["referenceEditorialReasoningEnabled"])
        self.assertTrue(selected["goldhandFactReplacementRequired"])
        self.assertTrue(selected["adaptationDecisionRequired"])
        self.assertNotIn("sourceToneBlocked", selected)
        self.assertTrue(selected["finalVoiceReviewRequired"])
        self.assertEqual(selected["finalVoiceReviewerSkill"], "writing-voice")
        self.assertEqual(selected["finalVoiceReviewContractId"], "writing-voice-final-rehear-v1")
        self.assertTrue(selected["referenceWritingIntelligence"]["flowBeats"])
        self.assertTrue(selected["referenceWritingIntelligence"]["microExpressionPatterns"])
        self.assertEqual(selected["voiceProfileId"], "goldhand-official-voice-v1")
        self.assertEqual(selected["voiceProtocolId"], "natural-speech-rewrite-protocol-v1")
        self.assertEqual(selected["contentAtomIds"], [atom["id"] for atom in selected["orderedContentAtoms"]])

    def test_two_active_tasks_reserve_different_references_for_same_keyword(self) -> None:
        selector = SCRIPTS / "select_wipark_content_reference.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / "recent.json"
            reservations = root / "reservations"
            common = [
                sys.executable,
                str(selector),
                "--keyword",
                "광주 한의원 추천",
                "--seed",
                "parallel-contract",
                "--state",
                str(state),
                "--reservation-dir",
                str(reservations),
            ]
            first = subprocess.Popen(
                [*common, "--run-id", "parallel-run-one"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            second = subprocess.Popen(
                [*common, "--run-id", "parallel-run-two"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            first_stdout, first_stderr = first.communicate(timeout=10)
            second_stdout, second_stderr = second.communicate(timeout=10)
            self.assertEqual(first.returncode, 0, first_stderr)
            self.assertEqual(second.returncode, 0, second_stderr)
            first_payload = json.loads(first_stdout)
            second_payload = json.loads(second_stdout)
            self.assertNotEqual(first_payload["masterId"], second_payload["masterId"])
            self.assertEqual(first_payload["reservation"]["runId"], "parallel-run-one")
            self.assertEqual(second_payload["reservation"]["runId"], "parallel-run-two")

    def test_all_wipark_briefs_have_ordered_nonprose_content_atoms(self) -> None:
        briefs = json.loads((SKILL_DIR / "assets" / "wipark-content-briefs.json").read_text(encoding="utf-8"))
        self.assertEqual(briefs["schemaVersion"], 2)
        seen: set[str] = set()
        for master_id, brief in briefs["briefs"].items():
            atoms = WIPARK_CONTENT_SELECTOR.content_atoms(brief, master_id)
            self.assertEqual(len(atoms), 4)
            for atom in atoms:
                self.assertNotIn(atom["id"], seen)
                seen.add(atom["id"])
                for value in [*atom["observables"], *atom["meaning"]]:
                    self.assertNotRegex(value, r"(?:습니다|합니다|입니다|됩니다|다)\s*[.!?]$")


if __name__ == "__main__":
    unittest.main()
