#!/usr/bin/env python3
"""Validate source separation, Naver fallback, and source-clinic leakage for one draft."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup


HANGUL = re.compile(r"[가-힣]")
NUMBERED_PROMISE = re.compile(r"(?P<count>\d+)\s*(?:가지|단계|기준|이유|방법|원칙|포인트)")
NUMBERED_HEADING = re.compile(r"^\s*(?P<count>\d+)\s*[.．)\]]")
GLOBAL_BLOCKED_ENTITIES = (
    "위석부부한의원",
    "위석 원장",
    "박경화",
    "송정동",
    "광산구",
    "광주송정역",
)
ALLOWED_EXECUTION = {"background-http-no-gui", "background-http-or-system-web-no-gui"}
SOURCE_FLAGS = (
    "generalInformationOnly",
    "sourceClinicFactsBlocked",
    "sourceCasesResultsProgramsMediaBlocked",
    "sourceSentenceCopyBlocked",
)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def compact(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", clean(value)).lower()


def article_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def add(issues: list[dict[str, str]], code: str, detail: str) -> None:
    issues.append({"severity": "error", "code": code, "detail": detail})


def validate_manifest(data: dict[str, Any], article: str = "") -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if data.get("schemaVersion") != 1:
        add(issues, "schema-version", "schemaVersion은 1이어야 합니다.")
    if data.get("structureContract") != "existing-goldhand-structure-unchanged":
        add(issues, "structure-contract", "기존 금손 글 구조 고정 계약이 필요합니다.")
    for field in ("topic", "title", "mainKeyword"):
        if not clean(data.get(field, "")):
            add(issues, f"{field}-missing", f"{field}가 필요합니다.")

    title = clean(data.get("title", ""))
    promises = [int(match.group("count")) for match in NUMBERED_PROMISE.finditer(title)]
    answer_count = data.get("numberedAnswerCount")
    if promises:
        if not isinstance(answer_count, int):
            add(issues, "numbered-answer-count", "숫자 약속 제목에는 numberedAnswerCount 정수가 필요합니다.")
        elif any(value != answer_count for value in promises):
            add(issues, "numbered-answer-mismatch", f"제목 약속 {promises}와 본문 답 {answer_count}개가 다릅니다.")

    sources = data.get("contentSources")
    if not isinstance(sources, list) or not sources:
        add(issues, "content-sources", "contentSources가 하나 이상 필요합니다.")
        sources = []
    blocked_entities = {compact(value): value for value in GLOBAL_BLOCKED_ENTITIES}
    source_urls: set[str] = set()
    declared_source_ids: set[str] = set()
    for index, source in enumerate(sources):
        label = f"contentSources[{index}]"
        if not isinstance(source, dict):
            add(issues, "source-type", f"{label}는 객체여야 합니다.")
            continue
        for field in ("id", "title", "url", "kind", "publisher"):
            if not clean(source.get(field, "")):
                add(issues, f"source-{field}", f"{label}.{field}가 필요합니다.")
        source_id = clean(source.get("id", ""))
        if source_id in declared_source_ids:
            add(issues, "source-id-duplicate", f"중복 출처 ID: {source_id}")
        if source_id:
            declared_source_ids.add(source_id)
        url = clean(source.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            add(issues, "source-url", f"{label}.url은 HTTP(S) 주소여야 합니다.")
        if url in source_urls:
            add(issues, "source-url-duplicate", f"중복 출처 URL: {url}")
        source_urls.add(url)
        for flag in SOURCE_FLAGS:
            if source.get(flag) is not True:
                add(issues, f"source-{flag}", f"{label}.{flag}는 true여야 합니다.")
        blocked = source.get("blockedEntities", [])
        if not isinstance(blocked, list):
            add(issues, "source-blocked-entities", f"{label}.blockedEntities는 배열이어야 합니다.")
            blocked = []
        if source.get("kind") in {"naver-blog-post", "stored-reference", "clinic-blog"} and not any(
            clean(value) for value in blocked
        ):
            add(issues, "source-blocked-entities-empty", f"{label}의 업체명·인명 차단 목록이 비어 있습니다.")
        publisher_signature = compact(source.get("publisher", ""))
        if publisher_signature:
            blocked_entities[publisher_signature] = clean(source.get("publisher", ""))
        for value in blocked:
            signature = compact(value)
            if signature:
                blocked_entities[signature] = clean(value)

    atoms = data.get("mergedInformationAtoms")
    if not isinstance(atoms, list) or not atoms:
        add(issues, "merged-atoms", "mergedInformationAtoms가 하나 이상 필요합니다.")
        atoms = []
    for index, atom in enumerate(atoms):
        label = f"mergedInformationAtoms[{index}]"
        if not isinstance(atom, dict):
            add(issues, "atom-type", f"{label}은 객체여야 합니다.")
            continue
        if atom.get("generalInformationOnly") is not True:
            add(issues, "atom-general-only", f"{label}.generalInformationOnly는 true여야 합니다.")
        source_ids = atom.get("sourceIds")
        if not isinstance(source_ids, list) or not source_ids:
            add(issues, "atom-source-ids", f"{label}.sourceIds가 필요합니다.")
        else:
            unknown = [clean(value) for value in source_ids if clean(value) not in declared_source_ids]
            if unknown:
                add(issues, "atom-source-id-unknown", f"{label}의 등록되지 않은 출처 ID: {unknown}")

    facts = data.get("goldhandFacts", [])
    if not isinstance(facts, list):
        add(issues, "goldhand-facts", "goldhandFacts는 배열이어야 합니다.")
        facts = []
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict) or fact.get("source") != "references/clinic-facts.md":
            add(issues, "goldhand-fact-authority", f"goldhandFacts[{index}]는 clinic-facts.md만 출처로 써야 합니다.")

    web = data.get("webSearch")
    if not isinstance(web, dict):
        add(issues, "web-search", "webSearch 객체가 필요합니다.")
        web = {}
    used = web.get("used") is True
    if used:
        if web.get("engine") != "naver":
            add(issues, "web-engine", "보충 검색 엔진은 naver여야 합니다.")
        if web.get("language") != "ko-KR":
            add(issues, "web-language", "보충 검색 언어는 ko-KR이어야 합니다.")
        if web.get("execution") not in ALLOWED_EXECUTION:
            add(issues, "web-execution", "브라우저 UI·로그인 없는 백그라운드 실행이어야 합니다.")
        if web.get("requiresBrowser") is not False or web.get("requiresLogin") is not False:
            add(issues, "web-ui-login", "보충 검색은 브라우저와 로그인을 요구하면 안 됩니다.")
        queries = web.get("queries")
        if not isinstance(queries, list) or not queries:
            add(issues, "web-queries", "한국어 네이버 검색어가 필요합니다.")
            queries = []
        keyword_signature = compact(data.get("mainKeyword", ""))
        for query in queries:
            if HANGUL.search(clean(query)) is None:
                add(issues, "web-query-korean", f"한국어가 없는 검색어: {query}")
            if keyword_signature and keyword_signature in compact(query):
                add(issues, "web-query-seo-keyword", f"정보 검색어에 메인키워드를 넣지 않습니다: {query}")
        web_sources = [source for source in sources if isinstance(source, dict) and source.get("retrievedBy") == "naver"]
        publishers = {compact(source.get("publisher", "")) for source in web_sources if compact(source.get("publisher", ""))}
        if len(web_sources) < 2 or len(publishers) < 2:
            add(issues, "web-independent-sources", "네이버 보충 정보는 서로 다른 발행자 2곳 이상이 필요합니다.")
        treatment_or_safety = data.get("medicalClaimsIncludeTreatmentOrSafety") is True or any(
            re.search(r"치료|주의|검사|응급|안전", clean(value))
            for value in [title, *[atom.get("role", "") for atom in atoms if isinstance(atom, dict)]]
        )
        if treatment_or_safety and not any(
            source.get("kind") == "official-korean-medical" for source in web_sources
        ):
            add(issues, "official-medical-source", "치료·안전 정보에는 한국 공식 의료 출처가 하나 이상 필요합니다.")

    if article:
        if promises:
            soup = BeautifulSoup(article, "html.parser")
            numbered = []
            for node in soup.select('[data-reference-role="section-heading"]'):
                match = NUMBERED_HEADING.search(node.get_text(" ", strip=True))
                if match:
                    numbered.append(int(match.group("count")))
            expected = list(range(1, promises[0] + 1))
            if numbered != expected:
                add(
                    issues,
                    "article-numbered-answer-mismatch",
                    f"제목 약속은 {promises[0]}개인데 본문 번호 소제목은 {numbered}입니다.",
                )
        normalized_article = compact(article_text(article))
        for signature, display in blocked_entities.items():
            if signature and signature in normalized_article:
                add(issues, "source-entity-leak", f"완성 본문에 출처 업체 정보가 남아 있습니다: {display}")

    errors = len(issues)
    return {
        "status": "fail" if errors else "pass",
        "metrics": {
            "contentSourceCount": len(sources),
            "mergedAtomCount": len(atoms),
            "webSearchUsed": used,
            "blockedEntityCount": len(blocked_entities),
            "errors": errors,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--article", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("최상위 값은 JSON 객체여야 합니다.")
        article = args.article.read_text(encoding="utf-8") if args.article else ""
        result = validate_manifest(data, article)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"정보 출처 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        for issue in result["issues"]:
            print(f"- {issue['code']}: {issue['detail']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
