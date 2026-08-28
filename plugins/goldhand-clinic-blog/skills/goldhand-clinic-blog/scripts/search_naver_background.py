#!/usr/bin/env python3
"""Search Naver in Korean without browser UI, login, or OS-specific automation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


SEARCH_URL = "https://search.naver.com/search.naver"
USER_AGENT = "Mozilla/5.0 GoldhandGeneralInformationSearch/1.0"
HANGUL = re.compile(r"[가-힣]")
QUERY_TOKEN = re.compile(r"[0-9A-Za-z가-힣]{2,}")
QUERY_STOP = {
    "원인",
    "증상",
    "치료",
    "주의",
    "검사",
    "필요한",
    "경우",
    "생활관리",
    "정보",
    "국가건강정보포털",
}
NAVER_POST = re.compile(
    r"https?://(?:(?:m|blog)\.)?blog\.naver\.com/(?P<blog_id>[A-Za-z0-9_.-]+)/(?P<log_no>\d{6,})",
    re.I,
)


def canonical_url(raw: str) -> str:
    raw = raw.strip()
    match = NAVER_POST.search(raw)
    if match:
        return f"https://blog.naver.com/{match.group('blog_id')}/{match.group('log_no')}"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc.endswith("search.naver.com"):
        return ""
    query = parse_qs(parsed.query)
    for key in ("url", "u"):
        target = query.get(key, [""])[0]
        if target.startswith("http"):
            return canonical_url(target)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", parsed.query, ""))


def candidate_kind(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if NAVER_POST.fullmatch(url):
        return "naver-blog-post"
    if host.endswith("terms.naver.com"):
        return "naver-knowledge"
    if any(
        host == domain or host.endswith("." + domain)
        for domain in (
            "health.kdca.go.kr",
            "kdca.go.kr",
            "mohw.go.kr",
            "nhis.or.kr",
            "hira.or.kr",
            "health.korea.kr",
            "mentalhealth.go.kr",
        )
    ):
        return "official-korean-medical"
    if host.endswith("naver.com"):
        return "naver-content"
    return "external-result"


def meaningful_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("새 창 열림", " ")).strip()
    if len(value) < 4 or value.isdigit():
        return ""
    return value[:180]


def publisher_key(url: str) -> str:
    match = NAVER_POST.fullmatch(url)
    if match:
        return f"naver-blog:{match.group('blog_id').lower()}"
    return urlparse(url).netloc.lower()


def relevance_terms(query: str) -> set[str]:
    return {token.lower() for token in QUERY_TOKEN.findall(query) if token not in QUERY_STOP}


def search_one(session: requests.Session, query: str, maximum: int) -> dict[str, Any]:
    response = session.get(SEARCH_URL, params={"query": query}, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_publishers: set[str] = set()
    subject_terms = relevance_terms(query)
    for anchor in soup.select("a[href]"):
        url = canonical_url(str(anchor.get("href", "")))
        if not url or url in seen:
            continue
        kind = candidate_kind(url)
        # Search navigation, shopping, maps, dictionaries, and profile links are
        # not article evidence. Keep only actual posts, knowledge pages, official
        # medical pages, and titled external organic results.
        if kind == "naver-content":
            continue
        title = meaningful_title(anchor.get_text(" ", strip=True))
        if not title:
            continue
        title_compact = re.sub(r"[^0-9A-Za-z가-힣]+", "", title).lower()
        if kind != "official-korean-medical" and subject_terms and not any(
            term in title_compact for term in subject_terms
        ):
            continue
        source_publisher_key = publisher_key(url)
        if source_publisher_key in seen_publishers:
            continue
        seen.add(url)
        seen_publishers.add(source_publisher_key)
        candidates.append(
            {
                "url": url,
                "title": title,
                "host": urlparse(url).netloc.lower(),
                "kind": kind,
                "publisherKey": source_publisher_key,
            }
        )
        if len(candidates) >= maximum:
            break
    return {
        "query": query,
        "searchUrl": f"{SEARCH_URL}?{urlencode({'query': query})}",
        "candidateCount": len(candidates),
        "candidates": candidates,
    }


def search(queries: list[str], maximum: int = 10) -> dict[str, Any]:
    cleaned: list[str] = []
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query not in cleaned:
            cleaned.append(query)
    if not cleaned:
        raise ValueError("검색어가 비어 있습니다.")
    if any(HANGUL.search(query) is None for query in cleaned):
        raise ValueError("네이버 보충 검색어는 한국어를 포함해야 합니다.")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = [search_one(session, query, maximum) for query in cleaned]
    return {
        "status": "pass" if any(item["candidateCount"] for item in results) else "no-results",
        "engine": "naver",
        "language": "ko-KR",
        "execution": "background-http-no-gui",
        "requiresBrowser": False,
        "requiresLogin": False,
        "osIndependent": True,
        "queries": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = search(args.query, max(2, min(args.max_results, 20)))
    except (ValueError, requests.RequestException) as exc:
        print(f"네이버 백그라운드 검색 실패: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    if args.json or not args.output:
        print(payload, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
