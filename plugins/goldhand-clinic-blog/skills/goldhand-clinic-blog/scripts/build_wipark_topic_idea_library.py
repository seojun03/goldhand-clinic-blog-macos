#!/usr/bin/env python3
"""Create a fact-blocked title/topic idea library from the audited corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = SKILL_DIR / "assets" / "wipark-reference-corpus.json"
DEFAULT_MASTERS = SKILL_DIR / "assets" / "reference-master-profiles.json"
DEFAULT_FAMILY = SKILL_DIR / "assets" / "two-reader-hooks-reference-family.json"
DEFAULT_OUTPUT = SKILL_DIR / "assets" / "topic-idea-library.json"
DEFAULT_GUIDE = SKILL_DIR / "references" / "topic-idea-types.md"

IDEA_LABELS = {
    "risk-warning": "방치·주의·피해야 할 조건",
    "self-care": "생활관리·예방",
    "treatment-decision": "치료 선택·적용 기준",
    "symptom-cause": "증상 원인·구분",
    "clinic-trust": "한의원 선택·진료 강점",
    "case-journey": "사례 과정·공통점",
    "doctor-philosophy": "원장 서사·진료 철학",
}


def guide_markdown(library: dict[str, object]) -> str:
    articles = library["articles"]
    counts = Counter(str(article["primaryType"]) for article in articles)
    lines = [
        "# 정보 주제와 독자 고민 2~3개형 글쓰기 마스터 라이브러리",
        "",
        "## 네 역할 분리",
        "",
        "1. `beomeo-topic-idea-library.json`: 범어 설명한의원 공개 글 69편에서 정보성 주제와 독자 질문 범위만 고른다.",
        "2. `topic-idea-library.json`: 사용자가 승인한 위석부부한의원 11편의 정보 주제를 후보로 보태며, 별도로 제목 장치를 고르는 레지스트리다.",
        "3. `reference-master-profiles.json`: 위석부부한의원 11편 중 선택한 한 편의 제목 장치·질문 위치·문단 구조·논리 배치를 재구성한다.",
        "4. `clinic-facts.md`: 제목과 본문에 들어갈 업체·진료·사례·이미지 사실은 금손한의원 자료만 사용한다.",
        "",
        "주제 출처와 글쓰기 마스터는 서로 독립이다. 범어 설명한의원 원문은 제목 패턴·질문 문구·문단 구조·정보 순서·문장 호흡·꾸밈을 통제할 수 없다. 위석부부한의원 글쓰기 마스터 한 편만 제목 장치·질문 위치·정보 순서·문장 호흡을 통제한다. 꾸밈은 네이버 순정 goldhand-naver-native-v4로 고정하며, 어느 원문이든 업체 이름·지역·연차·환자 수·치료 결과·후기·문장·사진을 금손한의원 글로 옮기지 않는다.",
        "",
        "## 수집 범위",
        "",
        f"- 기준일 포함 이후: `{library['cutoffInclusive']}`",
        f"- 전체 본문 분석: {library['sourceArticleCount']}편",
        f"- 동일 형식으로 직접 확인해 허용한 글: {library['articleCount']}편",
        f"- 같은 기간 전체 글 중 이 형식이 아니어서 제외: {library['familyFilteredOutCount']}편",
        "",
        "## 위석부부한의원 글쓰기 마스터의 제목 장치 유형",
        "",
        "| ID | 의미 | 등록 수 | 제목에서 가져올 것 |",
        "|---|---|---:|---|",
    ]
    for idea_id, label in IDEA_LABELS.items():
        lines.append(f"| `{idea_id}` | {label} | {counts.get(idea_id, 0)} | 제목 장치, 독자 질문, 답변 의제 |")
    lines.extend(
        [
            "",
            "## 실행 규칙",
            "",
            "- 자동모드는 `scripts/select_topic_idea.py`가 최근 3개의 의미 주제와 겹치는 후보를 먼저 제외하고, 남은 주제에 맞는 위석부부한의원 글쓰기 마스터를 별도로 고른다.",
            "- 정밀작성모드는 같은 선택기로 서로 의미가 다른 최대 3개 주제와 각 글쓰기 마스터를 제시한다.",
            "- 모든 결과는 `정보전달형`이며 업체소개형·사례공유형·스토리텔링형·일상글로 전환하지 않는다.",
            "- 범어 설명한의원 글은 주제 아이디어와 설명할 질문만 제공한다. 제목 문구·제목 패턴·본문 순서·말투·꾸밈·의학 답·사례·이미지는 제공하지 않는다.",
            "- 선택된 위석부부한의원 한 편을 제목 장치와 글쓰기 흐름 마스터로 사용하고, 꾸밈은 네이버 순정 인용구·구분선·표1을 적용한다.",
            "- 원문 제목의 연차·환자 수·효과 수치·전문 표현은 제목 슬롯으로 보지 않고 폐기한다.",
            "- 최종 제목은 금손한의원 사실로 다시 설계하고 `validate_title.py`를 통과시킨다.",
            "- 글을 쓸 때는 선택된 글쓰기 마스터 원문 한 편만 구조 재현용으로 읽는다. 주제 출처 본문은 확인할 개념·질문 범위를 파악할 수 있지만, 그 답은 금손 사실과 필요한 권위 자료에서 새로 구성한다.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--masters", type=Path, default=DEFAULT_MASTERS)
    parser.add_argument("--family", type=Path, default=DEFAULT_FAMILY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        master_data = json.loads(args.masters.read_text(encoding="utf-8"))
        family = json.loads(args.family.read_text(encoding="utf-8"))
        profiles = master_data["profiles"]
        family_articles = {str(item["id"]): item for item in family["articles"]}
        registry = {
            master_id: {
                "label": profile["sourceTitle"],
                "type": profile["type"],
                "sourceUrl": profile["sourceUrl"],
                "autoEligible": profile["autoEligible"],
                "bestFor": profile["bestFor"],
                "selectionTags": profile.get("selectionTags", []),
            }
            for master_id, profile in profiles.items()
        }
        masters_by_type: dict[str, list[str]] = {}
        for master_id, profile in profiles.items():
            if profile.get("autoEligible") is True:
                masters_by_type.setdefault(str(profile["type"]), []).append(master_id)
        articles = []
        for source in corpus["articles"]:
            source_id = str(source["id"])
            if source_id not in family_articles:
                continue
            family_article = family_articles[source_id]
            content_type = "정보전달형"
            compatible = [str(family_article["masterId"])]
            articles.append(
                {
                    "id": source["id"],
                    "sourceTitle": source["sourceTitle"],
                    "sourceUrl": source["sourceUrl"],
                    "publishedAt": source["publishedAt"],
                    "sourceContentType": content_type,
                    "primaryType": source["primaryIdeaType"],
                    "primaryTypeLabel": IDEA_LABELS[source["primaryIdeaType"]],
                    "titlePatternId": source["titlePatternId"],
                    "titlePatternDescription": source["titlePatternDescription"],
                    "topicTerms": source["topicTerms"],
                    "readerQuestion": source["readerQuestion"],
                    "answerAgenda": source["answerAgenda"],
                    "compatibleWritingMasterIds": compatible,
                    "referenceFamilyId": family["familyId"],
                    "minimumReaderHookCount": family["minimumReaderHookCount"],
                    "maximumReaderHookCount": family["maximumReaderHookCount"],
                    "allowedReaderHookCounts": family["allowedReaderHookCounts"],
                    "requiresSolutionPreviewBeforeBody": family["requiresSolutionPreviewBeforeBody"],
                    "questionPlacement": family_article["questionPlacement"],
                    "openingMode": family_article["openingMode"],
                    "solutionPreviewMode": family_article["solutionPreviewMode"],
                    "broadKeywordPriority": family_article["broadKeywordPriority"],
                    "sourceFactsBlocked": True,
                    "sourceSentencesBlocked": True,
                    "sourceMediaBlocked": True,
                }
            )
        library = {
            "schemaVersion": 2,
            "sourceBlogId": corpus["sourceBlogId"],
            "sourceBlogUrl": corpus["sourceBlogUrl"],
            "cutoffInclusive": corpus["cutoffInclusive"],
            "referenceFamilyId": family["familyId"],
            "allowedReferenceIds": family["allowedReferenceIds"],
            "allowedMasterIds": family["allowedMasterIds"],
            "sourceArticleCount": corpus["includedCount"],
            "articleCount": len(articles),
            "excludedCount": corpus["includedCount"] - len(articles),
            "sourceExcludedCount": corpus["includedCount"] - sum(item.get("eligible") is True for item in corpus["articles"]),
            "familyFilteredOutCount": corpus["includedCount"] - len(articles),
            "factPolicy": "Use only Goldhand Clinic facts. Never transfer source facts, claims, cases, sentences or media.",
            "writingMasterRegistry": registry,
            "articles": articles,
        }
        args.output.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.guide.write_text(guide_markdown(library), encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        print(f"주제 아이디어 라이브러리 생성 실패: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "pass", "articles": len(articles), "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
