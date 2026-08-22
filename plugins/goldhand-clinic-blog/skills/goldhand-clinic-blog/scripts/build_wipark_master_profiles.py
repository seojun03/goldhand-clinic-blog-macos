#!/usr/bin/env python3
"""Build Goldhand one-master profiles from the audited wi-parkclinic corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = SKILL_DIR / "assets" / "wipark-reference-corpus.json"
DEFAULT_FAMILY = SKILL_DIR / "assets" / "two-reader-hooks-reference-family.json"
DEFAULT_OUTPUT = SKILL_DIR / "assets" / "reference-master-profiles.json"
DEFAULT_LIBRARY = SKILL_DIR / "references" / "reference-master-library.md"
DEFAULT_CONTENT_BRIEFS = SKILL_DIR / "assets" / "wipark-content-briefs.json"
DEFAULT_VOICE_PROFILE = SKILL_DIR / "assets" / "goldhand-official-voice-profile.json"
DEFAULT_WRITING_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"

MASTER_CONFIG: dict[str, dict[str, Any]] = {
    "INFO01": {
        "logNo": "224320052203",
        "type": "정보전달형",
        "selectionTags": ["치료받아도 소용없는 특징", "생활습관", "치료 지속", "직장인", "2가지"],
        "bestFor": "치료만 반복해도 변화가 더딘 이유와 생활 조건 두 가지를 설명할 때",
        "hook": "독자가 품을 수 있는 치료 효과 질문 두 개를 연속 인용",
        "voice": "솔직한 한계를 먼저 인정한 뒤 특징·생활 조건·치료 선택을 구체적으로 설명",
        "close": "두 특징을 다시 확인시키고 치료와 생활관리의 공동 역할로 마무리",
    },
    "INFO02": {
        "logNo": "224355735689",
        "type": "정보전달형",
        "selectionTags": ["방치하면 안 되는 이유", "교통사고", "후유증", "증상 목록", "초기 대응"],
        "bestFor": "증상이 늦게 나타나는 이유, 살필 신호, 가능한 관리 순서를 차례로 설명할 때",
        "hook": "괜찮다고 넘긴 뒤 뒤늦게 불편해지는 상황으로 시작",
        "voice": "전문용어를 쉬운 말로 풀고 증상·접근·행동을 질문형 소제목으로 전개",
        "close": "초기 판단의 중요성을 짧게 회수하고 중립적인 진찰 안내로 끝냄",
    },
    "INFO03": {
        "logNo": "224337414108",
        "type": "정보전달형",
        "selectionTags": ["질문 2가지", "갑작스러운 증상", "언제 검사", "치료 병행", "안전 기준"],
        "bestFor": "환자의 두 가지 핵심 질문에 각각 직접 답하고 다른 검사·기관이 먼저인 경우를 밝힐 때",
        "hook": "긴급성과 치료 가능성에 관한 질문 두 개를 글 맨 앞에 배치",
        "voice": "결론부터 답한 뒤 이유·예외·병행 판단을 한 질문씩 깊게 설명",
        "close": "두 답을 다시 정리하고 불안한 독자에게 다음 판단을 건넴",
    },
    "INFO04": {
        "logNo": "224291545650",
        "type": "정보전달형",
        "selectionTags": ["효과 보는 사람", "못 보는 사람", "비교", "공통점", "자가 점검"],
        "bestFor": "같은 관리에도 반응이 다른 조건을 비교하고 자신에게 맞는지 구분하게 할 때",
        "hook": "치료 가능성과 중단 후 재발 걱정을 연속 질문으로 제시",
        "voice": "반응 차이의 공통 조건을 설명하고 자가 점검 항목과 적용 한계를 함께 제시",
        "close": "누구에게나 같은 결과가 아님을 밝히고 상태 파악의 필요성을 회수",
    },
    "INFO05": {
        "logNo": "224280621821",
        "type": "정보전달형",
        "selectionTags": ["건강보험", "적용 기준", "비용", "횟수", "많이 묻는 질문"],
        "bestFor": "보험·제도·적용 조건처럼 정확한 기준과 예외를 두 갈래로 설명할 때",
        "hook": "환자가 반복해서 묻는 적용 여부와 부담 질문을 도입 안에 포함",
        "voice": "기준을 먼저 공개하고 적용 대상·예외·치료 의미를 순서대로 구체화",
        "close": "일반 기준과 개인별 차이를 구분하고 현재 상태 확인으로 연결",
    },
    "INFO06": {
        "logNo": "224205420099",
        "type": "정보전달형",
        "selectionTags": ["회복 원칙", "움직임 분석", "구조적 원인", "2가지", "통증 반복"],
        "bestFor": "아픈 부위만 보지 않고 움직임과 주변 구조를 함께 살피는 두 원칙을 설명할 때",
        "hook": "일상 동작의 불편과 검사상 이상 없음이라는 답답함을 인용",
        "voice": "첫 원칙·근거·확인 장면, 둘째 원칙·근거·재점검 순으로 단호하게 전개",
        "close": "두 원칙을 실제 명사로 다시 묶고 반복 통증의 판단 기준으로 끝냄",
    },
    "INFO07": {
        "logNo": "224134818728",
        "type": "정보전달형",
        "selectionTags": ["치료방법 핵심", "관절 움직임", "염증", "일상 불편", "단계별 설명"],
        "bestFor": "한 증상의 치료 원리를 두세 단계로 나누고 각 단계의 이유를 설명할 때",
        "hook": "옷 입기·물건 꺼내기처럼 구체적인 일상 불편 질문으로 시작",
        "voice": "먼저 풀 문제, 다음에 살필 문제, 개인별 차이를 짧은 소제목으로 전개",
        "close": "증상 이름보다 현재 제한과 원인을 확인해야 한다는 답으로 회수",
    },
    "INFO08": {
        "logNo": "224307070715",
        "type": "정보전달형",
        "selectionTags": ["시기 2가지", "보약", "예방", "회복", "체질 차이"],
        "bestFor": "같은 관리도 시작 시점과 몸 상태에 따라 달라지는 두 경우를 비교할 때",
        "hook": "언제 시작해야 하는지에 관한 상반된 질문 두 개를 제시",
        "voice": "첫 시기와 둘째 시기를 각각 대상·이유·차이로 설명하고 예외를 덧붙임",
        "close": "두 시기는 일반 기준일 뿐이라는 한계를 밝히고 개인 상태 확인으로 끝냄",
    },
    "INFO09": {
        "logNo": "224314708696",
        "type": "정보전달형",
        "selectionTags": ["주의사항 2가지", "중단 이후", "요요", "생활 변화", "유지 조건"],
        "bestFor": "치료·관리 중단 뒤 생길 수 있는 변화와 이후 유지 조건 두 가지를 설명할 때",
        "hook": "중단 뒤 다시 문제가 생길지와 유지 방법에 관한 질문 두 개를 연속 인용",
        "voice": "독자의 불안을 구체화한 뒤 변화가 생기는 이유와 두 가지 주의점을 차례로 설명",
        "close": "두 주의점을 다시 묶고 개인 상태와 생활 조건을 함께 확인하라는 판단으로 끝냄",
    },
    "INFO10": {
        "logNo": "224287906098",
        "type": "정보전달형",
        "selectionTags": ["증상 원인", "일반 치료의 한계", "치료 원리", "오래가는 불편", "두 고민"],
        "bestFor": "오래 이어지는 증상의 원인, 흔한 접근의 한계, 고려할 치료 원리를 순서대로 설명할 때",
        "hook": "일상·수면을 흔드는 서로 다른 두 불편을 인용",
        "voice": "왜 선택이 어려운지 짚은 뒤 원인·기존 접근의 한계·선택 기준을 정보 중심으로 전개",
        "close": "증상 이름만으로 치료를 고르지 말고 현재 양상과 한계를 확인하라는 판단으로 끝냄",
    },
    "INFO11": {
        "logNo": "224221217878",
        "type": "정보전달형",
        "selectionTags": ["극복 방법 2가지", "오래된 불편", "몸과 마음", "치료 가능성", "두 질문"],
        "bestFor": "오래된 불편을 한 면으로만 보지 않고 두 갈래의 회복 기준을 설명할 때",
        "hook": "오래 안고 가야 하는지와 기존 관리로도 달라지지 않는다는 질문 두 개를 인용",
        "voice": "막막함의 이유를 풀고 서로 다른 두 관리 축을 원리·적용 범위·한계와 함께 설명",
        "close": "두 축을 함께 보되 현재 상태에 맞게 순서를 정해야 한다는 판단으로 끝냄",
    },
    "INFO12": {
        "logNo": "224212833691",
        "type": "정보전달형",
        "selectionTags": ["성공 조건", "같은 노력 다른 결과", "몸의 변화", "조건 3가지", "두 고민"],
        "bestFor": "같은 노력을 해도 결과가 다른 이유와 성공을 좌우하는 여러 조건을 설명할 때",
        "hook": "노력해도 달라지지 않는다는 독자의 현실적인 고민 두 개를 연속 인용",
        "voice": "반응 차이에 대한 질문을 던진 뒤 원인과 성공 조건을 번호가 있는 정보 절로 전개",
        "close": "조건의 우선순위는 사람마다 다르며 현재 상태부터 구분해야 한다고 끝냄",
    },
    "COMP01": {
        "logNo": "223708852851",
        "type": "업체소개형",
        "selectionTags": ["한의원 선택 기준", "3가지", "비교", "경험", "진료 시스템"],
        "bestFor": "한의원을 비교할 때 환자가 확인할 세 가지 진료 기준을 설명할 때",
        "hook": "어디를 선택할지 모르겠다는 독자 질문 세 개를 연속 제시",
        "voice": "원장 배경과 기준 세 개를 각각 이유·예시·확인 행동으로 길게 설명",
        "close": "세 기준을 다시 묶어 독자가 다른 곳에도 적용할 비교 기준으로 건넴",
    },
    "COMP02": {
        "logNo": "223618743964",
        "type": "업체소개형",
        "selectionTags": ["맞춤 진료", "장점", "가족", "협진", "원인 분석"],
        "bestFor": "금손한의원의 맞춤 진료가 환자에게 어떤 차이를 만드는지 세 강점으로 설명할 때",
        "hook": "한의학 진찰의 낯섦을 먼저 설명한 뒤 독자의 선택 고민 세 개를 인용",
        "voice": "강점 이름을 먼저 공개하고 실제 진료 기준·대상·한계를 사례형 설명으로 확장",
        "close": "자기 홍보만이 아니라 한의원 선택에 쓸 기준이라는 태도로 마무리",
    },
    "COMP03": {
        "logNo": "223832005988",
        "type": "업체소개형",
        "selectionTags": ["통합적 접근", "몸 전체", "원인", "협력", "만성 불편"],
        "bestFor": "한 부위만 보지 않는 통합적 확인 과정과 그 이유를 설명할 때",
        "hook": "한의원의 지향점을 밝힌 뒤 오래된 불편을 가진 독자의 절망을 구체화",
        "voice": "접근 원칙·확인 과정·협력 방식·환자에게 돌아오는 의미를 순서대로 설명",
        "close": "여러 치료를 나열하기보다 개인 상태를 함께 보는 의미로 회수",
    },
    "COMP04": {
        "logNo": "224232356093",
        "type": "업체소개형",
        "selectionTags": ["검사상 이상 없음", "몸과 마음", "설명 과정", "심리", "숨은 원인"],
        "bestFor": "검사로 설명되지 않는 불편을 어떻게 듣고 설명하는지 진료 과정을 소개할 때",
        "hook": "원인을 찾지 못한 독자의 두 질문을 원장 인사 안에 녹여 제시",
        "voice": "진단 질문·설명 도구·치료 선택·협력 원칙을 짧은 제목과 구분선으로 전개",
        "close": "글의 한계를 인정하고 현재 불편을 구체적으로 상의할 수 있다는 정도로 끝냄",
    },
    "CASE01": {
        "logNo": "224157334525",
        "type": "사례공유형",
        "selectionTags": ["환자 공통점", "생활 습관", "꾸준한 관리", "비염", "보험 한약"],
        "bestFor": "공개된 여러 사례에서 확인된 공통 조건을 묶어 설명할 때",
        "hook": "치료 효과에 관한 환자의 대표 질문과 원장의 솔직한 첫 판단으로 시작",
        "voice": "치료 전 특징·함께 실천한 생활·지속 관리의 의미를 공통점 중심으로 설명",
        "close": "완치 단정 대신 관리와 개인별 진찰 필요성을 밝힘",
    },
    "CASE02": {
        "logNo": "224152237859",
        "type": "사례공유형",
        "autoEligible": False,
        "selectionTags": ["실제 후기", "당사자 기록", "재발", "치료 병행", "감정과 신체"],
        "bestFor": "사용 허락을 받은 실제 당사자 기록이나 긴 직접 인용이 있을 때만",
        "hook": "원장이 발견한 문제를 제시한 뒤 공개 동의를 받은 당사자 기록을 길게 배치",
        "voice": "당사자 서술을 먼저 보여 주고 치료 개념·적용 대상·한계를 설명",
        "close": "한 사례의 의미와 다른 상태에는 같은 접근이 필수가 아님을 밝힘",
    },
    "CASE03": {
        "logNo": "223844045863",
        "type": "사례공유형",
        "selectionTags": ["공통점 2가지", "검사상 이상 없음", "원인", "생활 관리", "재점검"],
        "bestFor": "확인된 둘 이상의 사례에서 서로 다른 공통점 두 가지를 설명할 때",
        "hook": "검사로 설명되지 않는 구체적인 일상 불편과 제목의 두 공통점을 예고",
        "voice": "첫 공통점과 사례, 둘째 공통점과 사례를 같은 무게로 전개",
        "close": "사례 결과를 보장하지 않고 원인 확인과 생활 조건을 함께 보라는 판단으로 끝냄",
    },
    "CASE04": {
        "logNo": "223796925860",
        "type": "사례공유형",
        "autoEligible": False,
        "selectionTags": ["부모 고민", "수치 경과", "청소년", "한약", "실제 사례"],
        "bestFor": "사용 가능한 전후 수치와 보호자 고민이 모두 확인된 사례에만",
        "hook": "보호자의 걱정 세 문장을 인용한 뒤 제도 변화와 공개 이유를 설명",
        "voice": "제도·사례 전 상태·선택 이유·관찰된 변화·치료 원리를 순서대로 전개",
        "close": "경과를 일반화하지 않고 개인별 처방과 다른 원인을 밝힘",
    },
    "STORY01": {
        "logNo": "224242818123",
        "type": "스토리텔링형",
        "selectionTags": ["한 자리를 지킨 이유", "개원", "지역", "원장 이야기", "현재 원칙"],
        "bestFor": "개원부터 지금까지 이어 온 선택과 지역에서 지켜 온 원칙을 이야기할 때",
        "hook": "현재의 장소와 반복되는 풍경을 짧게 보여 준 뒤 원장이 인사",
        "voice": "왜 남았는지·환자에게 배운 것·함께 진료하는 방식·현재 목표 순서로 담담하게 전개",
        "close": "거대한 선언 대신 앞으로도 지키려는 소박한 진료 태도로 끝냄",
    },
    "STORY02": {
        "logNo": "223922695931",
        "type": "스토리텔링형",
        "selectionTags": ["한의사가 된 이유", "전환점", "공부", "진료 철학", "가족 경험"],
        "bestFor": "원장의 확인된 개인 경험과 공부가 현재 진료 철학으로 이어진 과정을 설명할 때",
        "hook": "환자의 실제 고민을 먼저 보여 준 뒤 왜 이 이야기를 공개하는지 밝힘",
        "voice": "시작점·개인적 전환점·오랜 공부·현재의 네 가지 철학을 긴 호흡으로 연결",
        "close": "의료의 한계를 인정하면서도 지키려는 구체적인 태도와 감사로 끝냄",
    },
}


def trim_blueprint(blueprint: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in blueprint:
        kind = str(item.get("kind", ""))
        role = str(item.get("role", ""))
        if kind == "placesMap":
            break
        if kind == "oglink" or role == "related-link":
            continue
        result.append(dict(item))
    while result and result[-1].get("kind") in {"horizontalLine", "table"}:
        result.pop()
    return result


def rewrite_roles(blueprint: list[dict[str, Any]]) -> None:
    text_indexes = [index for index, item in enumerate(blueprint) if item.get("kind") == "text" and item.get("charCount", 0)]
    last_two = set(text_indexes[-2:])
    first_text = text_indexes[0] if text_indexes else -1
    for index, item in enumerate(blueprint):
        kind = str(item.get("kind", ""))
        if kind == "quotation" and index < first_text:
            role = "reader-question"
        elif kind == "table" and index <= 6:
            role = "credential-proof"
        elif kind in {"image", "imageGroup", "video"}:
            role = "evidence-media"
        elif kind == "horizontalLine":
            role = "divider"
        elif index == first_text:
            role = "greeting-authority"
        elif kind == "text" and int(item.get("charCount", 0)) <= 90 and (
            int(item.get("boldCount", 0)) or int(item.get("questionCount", 0)) or int(item.get("paragraphCount", 0)) <= 2
        ):
            role = "section-heading"
        elif kind == "text" and index in last_two:
            role = "recap" if index == min(last_two) else "neutral-close"
        elif kind == "text":
            role = "explanation"
        elif kind == "table":
            role = "supporting-table"
        else:
            role = kind
        item["role"] = role
        item["sentenceCount"] = int(item.get("sentenceCount", 0))


def merge_counter(blueprint: list[dict[str, Any]], key: str) -> dict[str, int]:
    total: Counter[str] = Counter()
    for item in blueprint:
        values = item.get(key, {})
        if isinstance(values, dict):
            total.update({str(name): int(count) for name, count in values.items()})
    return dict(total)


def make_profile(
    article: dict[str, Any],
    config: dict[str, Any],
    family_article: dict[str, Any],
    family_id: str,
    content_brief: dict[str, Any],
    voice_profile_id: str,
    learning_profile: dict[str, Any],
) -> dict[str, Any]:
    blueprint = trim_blueprint(article.get("componentBlueprint", []))
    rewrite_roles(blueprint)
    writing_roles = [
        str(item["role"])
        for item in blueprint
        if item.get("kind") in {"text", "quotation", "table"} and item.get("charCount", 0)
    ]
    writing_roles.append("contact")
    role_counts = Counter(writing_roles)
    alignment_counts = Counter(str(item.get("alignment", "default")) for item in blueprint)
    auto_eligible = bool(config.get("autoEligible", True))
    profile = {
        "type": config["type"],
        "referenceFamilyId": family_id,
        "sourceBlogId": "wi-parkclinic",
        "sourceUrl": article["sourceUrl"],
        "sourceTitle": article["sourceTitle"],
        "publishedAt": article["publishedAt"],
        "autoEligible": auto_eligible,
        "selectionTags": config["selectionTags"],
        "bestFor": config["bestFor"],
        "writingContract": {
            "hook": config["hook"],
            "contentProgress": config["voice"],
            "close": config["close"],
            "sourceFactsBlocked": True,
            "sourceSentencesBlocked": True,
            "sourceMediaBlocked": True,
            "referenceExpressionLearningEnabled": True,
            "sourceSentenceImitationBlocked": True,
        },
        "contentContract": {
            "topic": content_brief["topic"],
            "readerConcerns": content_brief["readerConcerns"],
            "orderedContentAtoms": content_brief["orderedContentAtoms"],
            "blockedFromSource": content_brief["blockedFromSource"],
            "sourceProseWithheld": True,
            "contentAtomCoverageRequired": True,
            "instruction": "내용 원자는 사실 골격으로 유지하고, 선택 레퍼런스의 편집 판단 프로필로 독자 심리·전환·강조·마무리 기능을 함께 재구성한다.",
        },
        "toneContract": {
            "voiceAuthority": voice_profile_id,
            "voiceProtocolId": "natural-speech-rewrite-protocol-v1",
            "referenceRhetoricalReasoningEnabled": True,
            "sourceSentenceImitationBlocked": True,
            "sourceRhythmAndExpressionObservation": {
                "textStats": article.get("textStats", {}),
            },
            "instruction": "위석 문장을 복사하지 않되 설득 장치·전환 방식·미세 표현 기능은 분석해 옮긴다. 금손 공식 말투는 이 기능을 지우지 않고 실제 진료실 생활어로 자연화한다.",
        },
        "editorialReasoningContract": {
            "intelligenceId": "goldhand-reference-writing-intelligence-v1",
            "profileId": str(article.get("masterId", "")) or str(content_brief.get("masterId", "")),
            "titleMechanism": learning_profile["titleMechanism"],
            "openingMechanism": learning_profile["openingMechanism"],
            "flowBeats": learning_profile["flowBeats"],
            "microExpressionPatterns": learning_profile["microExpressionPatterns"],
            "trustMechanism": learning_profile["trustMechanism"],
            "closingMechanism": learning_profile["closingMechanism"],
            "adaptationDecisionRequired": True,
        },
        "observedStyle": {
            "textColors": merge_counter(blueprint, "textColors"),
            "backgroundColors": merge_counter(blueprint, "backgroundColors"),
            "alignmentCounts": dict(alignment_counts),
            "componentCounts": dict(Counter(str(item.get("kind", "unknown")) for item in blueprint)),
            "fontSizeClasses": merge_counter(blueprint, "fontSizeClasses"),
            "boldCount": sum(int(item.get("boldCount", 0)) for item in blueprint),
            "underlineCount": sum(int(item.get("underlineCount", 0)) for item in blueprint),
        },
        "componentBlueprint": blueprint,
        "renderContract": {
            "nativeDesignSystemId": "goldhand-naver-native-v4",
            "referenceControlsDecoration": False,
            "allowedArticleHexColors": [
                "#C99F75",
                "#7A5434",
                "#4D4D4D",
                "#6C6B6D",
                "#FBF8F4",
                "#F3E8DD",
                "#FFF2A8",
                "#E53935",
                "#D6D6D6",
                "#FFFFFF",
            ],
            "requiredOrderedRoles": [
                "reader-question",
                "reader-question",
                "solution-preview",
                "explanation",
                "neutral-close",
                "contact",
            ],
            "requiredRoleMinimums": {
                "reader-question": 2,
                "solution-preview": 1,
                "explanation": 1,
                "neutral-close": 1,
                "contact": 1,
            },
            "requiredRoleMaximums": {
                "reader-question": 3,
                "solution-preview": 1,
            },
            "minimumCenterRatio": 1.0,
            "maximumCenterRatio": 1.0,
            "requiredUnderlineMinimum": 2,
            "maxConsecutiveBodyParagraphs": 3,
            "titleMechanismControlledByReferenceReasoning": True,
            "introductionDeviceControlledByReferenceReasoning": True,
            "closingMechanismControlledByReferenceReasoning": True,
            "mediaPlacementPolicy": "같은 위치를 우선하되 금손 공식 안전 이미지가 부족하면 관련 없는 사진으로 채우지 않는다.",
        },
    }
    profile["familyContract"] = {
        "label": "독자 고민 2~3개·해결 방향 예고·정보 본문형",
        "minimumReaderHookCount": 2,
        "maximumReaderHookCount": 3,
        "allowedReaderHookCounts": [2, 3],
        "questionPlacement": family_article["questionPlacement"],
        "openingMode": family_article["openingMode"],
        "solutionPreviewMode": family_article["solutionPreviewMode"],
        "requiresSolutionPreviewBeforeBody": True,
        "sameReferenceForIdeaAndContentFlow": True,
        "referenceControlsDecoration": False,
        "nativeDesignSystemId": "goldhand-naver-native-v4",
    }
    return profile


def library_markdown(profiles: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# 독자 고민 2~3개·해결 방향 예고·정보 본문형 레퍼런스",
        "",
        "## 역할",
        "",
        "이 11편은 주제·독자 고민·핵심 일반 정보뿐 아니라 제목 장치의 심리, 도입 설득, 정보 공개 순서, 전환 방식, 미세 표현 기능, 마무리 감정을 통제한다. 한 글에서는 한 편을 콘텐츠·편집 레퍼런스로 고정한다. 원문 완성 문장과 업체의 경력·수치·치료 주장·사례·사진은 옮기지 않고, 각 기능을 확인된 금손 사실과 박준희 원장의 생활어로 재구성한다. 꾸밈은 `goldhand-naver-native-v4`로 고정한다.",
        "",
        "주제와 일반 정보 출처는 `wipark-content-briefs.json`, 편집 판단 출처는 `reference-writing-intelligence.json`, 최종 생활어 출처는 `goldhand-official-voice-profile.json`, 금손 사실 출처는 `clinic-facts.md`, 꾸밈 출처는 `goldhand-naver-native-design-system.json`이다. 역할을 서로 바꾸지 않는다.",
        "",
    ]
    lines.extend(["## 허용 레퍼런스 11편", ""])
    for profile_id, profile in profiles.items():
        lines.extend(
            [
                f"### `{profile_id}` — {profile['sourceTitle']}",
                "",
                f"- 원문: <{profile['sourceUrl']}>",
                f"- 발행일: {profile['publishedAt']}",
                "- 상태: 자동·정밀작성 모두 선택 가능",
                f"- 질문 위치: {profile['familyContract']['questionPlacement']}",
                f"- 적합한 글: {profile['bestFor']}",
                f"- 도입: {profile['writingContract']['hook']}",
                f"- 내용 전개: {profile['writingContract']['contentProgress']}",
                f"- 제목 심리: {profile['editorialReasoningContract']['titleMechanism']['readerPsychology']}",
                f"- 도입 설득: {profile['editorialReasoningContract']['openingMechanism']['attentionLogic']}",
                f"- 말투: 레퍼런스의 설득 기능을 유지한 채 `{profile['toneContract']['voiceAuthority']}`로 생활어 자연화; 원문 문장 복사 금지",
                f"- 마무리: {profile['writingContract']['close']}",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--family", type=Path, default=DEFAULT_FAMILY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--content-briefs", type=Path, default=DEFAULT_CONTENT_BRIEFS)
    parser.add_argument("--voice-profile", type=Path, default=DEFAULT_VOICE_PROFILE)
    parser.add_argument("--writing-intelligence", type=Path, default=DEFAULT_WRITING_INTELLIGENCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        family = json.loads(args.family.read_text(encoding="utf-8"))
        content_briefs = json.loads(args.content_briefs.read_text(encoding="utf-8"))
        voice_profile = json.loads(args.voice_profile.read_text(encoding="utf-8"))
        writing_intelligence = json.loads(args.writing_intelligence.read_text(encoding="utf-8"))
        articles = {str(item["logNo"]): item for item in corpus["articles"]}
        profiles = {}
        for family_article in family["articles"]:
            profile_id = str(family_article["masterId"])
            config = MASTER_CONFIG[profile_id]
            profiles[profile_id] = make_profile(
                articles[str(family_article["logNo"])],
                config,
                family_article,
                str(family["familyId"]),
                content_briefs["briefs"][profile_id],
                str(voice_profile["profileId"]),
                writing_intelligence["profiles"][profile_id],
            )
            profiles[profile_id]["editorialReasoningContract"]["profileId"] = profile_id
        output = {
            "schemaVersion": 5,
            "sourceBlogId": "wi-parkclinic",
            "cutoffInclusive": corpus["cutoffInclusive"],
            "referenceFamilyId": family["familyId"],
            "allowedMasterIds": family["allowedMasterIds"],
            "sourceFactsBlocked": True,
            "referenceExpressionLearningEnabled": True,
            "sourceSentenceImitationBlocked": True,
            "topicAndContentAuthority": "wi-parkclinic-reviewed-11-posts",
            "editorialReasoningAuthority": "goldhand-reference-writing-intelligence-v1",
            "voiceAuthority": str(voice_profile["profileId"]),
            "voiceProtocolId": "natural-speech-rewrite-protocol-v1",
            "profiles": profiles,
        }
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.library.write_text(library_markdown(profiles), encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        print(f"마스터 프로필 생성 실패: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "pass", "profiles": len(profiles), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
