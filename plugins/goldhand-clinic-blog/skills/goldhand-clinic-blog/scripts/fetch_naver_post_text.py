#!/usr/bin/env python3
"""Fetch Naver blog post text for internal general-information separation only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


POST_URL = re.compile(
    r"https?://(?:(?:m|blog)\.)?blog\.naver\.com/(?P<blog_id>[A-Za-z0-9_.-]+)/(?P<log_no>\d{6,})",
    re.I,
)
USER_AGENT = "Mozilla/5.0 GoldhandGeneralInformationFetch/1.0"
CONTACT_BOUNDARY = re.compile(
    r"(?:전화\s*문의|네이버\s*(?:톡톡|예약)|오시는\s*길|진료\s*시간|상담\s*문의|예약\s*문의)",
    re.I,
)


def canonical_parts(url: str) -> tuple[str, str]:
    match = POST_URL.fullmatch(url.strip())
    if match is None:
        raise ValueError(f"지원하지 않는 네이버 블로그 글 URL입니다: {url}")
    return match.group("blog_id"), match.group("log_no")


def compact_text(node: Any) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\u200b", " ")).strip()


def fetch_one(session: requests.Session, url: str) -> dict[str, Any]:
    blog_id, log_no = canonical_parts(url)
    mobile_url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    response = session.get(mobile_url, timeout=35)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    root = soup.select_one(".se-main-container") or soup.select_one(".se_component_wrap")
    if root is None:
        raise ValueError(f"네이버 스마트에디터 본문을 찾지 못했습니다: {url}")
    paragraphs: list[str] = []
    for component in root.select(":scope > .se-component") or root.select(".se-component"):
        classes = set(component.get("class", []))
        if any(value in classes for value in ("se-image", "se-imageGroup", "se-video", "se-placesMap", "se-oglink")):
            continue
        candidates = [compact_text(node) for node in component.select(".se-text-paragraph")]
        candidates = [value for value in candidates if value]
        if not candidates:
            fallback = compact_text(component)
            candidates = [fallback] if fallback else []
        for paragraph in candidates:
            if CONTACT_BOUNDARY.search(paragraph):
                break
            if paragraph not in paragraphs:
                paragraphs.append(paragraph)
        if candidates and CONTACT_BOUNDARY.search(candidates[-1]):
            break
    title_meta = soup.select_one('meta[property="og:title"]')
    site_meta = soup.select_one('meta[property="og:site_name"]')
    title = str(title_meta.get("content", "")).strip() if title_meta else ""
    site_name = str(site_meta.get("content", "")).strip() if site_meta else ""
    return {
        "sourceTitle": title,
        "sourceUrl": f"https://blog.naver.com/{blog_id}/{log_no}",
        "sourceBlogId": blog_id,
        "sourceSiteName": site_name,
        "paragraphs": paragraphs,
        "sourceUsePolicy": {
            "generalInformationOnly": True,
            "sourceClinicFactsBlocked": True,
            "sourceCasesResultsProgramsMediaBlocked": True,
            "sourceSentenceCopyBlocked": True,
            "mustCreateParaphrasedInformationAtomsBeforeDrafting": True,
            "mustIdentifySourceClinicDoctorLocationAndContactAsBlockedEntities": True,
        },
    }


def fetch(urls: list[str]) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    posts = [fetch_one(session, url) for url in urls]
    return {
        "status": "pass",
        "temporaryInternalUseOnly": True,
        "posts": posts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = fetch(args.url)
    except (ValueError, requests.RequestException) as exc:
        print(f"네이버 글 읽기 실패: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
