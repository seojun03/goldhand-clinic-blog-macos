#!/usr/bin/env python3
"""Build a compact, fact-blocked reference corpus from wi-parkclinic posts."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

import requests
from bs4 import BeautifulSoup, Tag


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = SKILL_DIR / "assets" / "wipark-reference-corpus.json"
DEFAULT_INVENTORY = SKILL_DIR / "references" / "wipark-reference-inventory.md"
BLOG_ID = "wi-parkclinic"
BLOG_NAME = "위석부부한의원"
DEFAULT_CUTOFF = date(2024, 10, 4)
LIST_URL = "https://blog.naver.com/PostTitleListAsync.naver"
POST_URL = "https://m.blog.naver.com/{blog_id}/{log_no}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GoldhandReferenceAudit/1.0"
ALLOWED_TYPES = ("정보전달형", "업체소개형", "사례공유형", "스토리텔링형")

NOTICE_PATTERNS = (
    r"(?:^|\s)\d{1,2}월\s*진료\s*안내",
    r"20\d{2}년\s*\d{1,2}월\s*진료\s*안내",
    r"진료시간\s*(?:변경|안내)",
    r"휴진\s*안내",
    r"오리엔테이션",
    r"체험교실",
    r"워크숍",
    r"다녀왔습니다",
    r"행사\s*안내",
    r"^\[공유\]\s*QR$",
)
CASE_PATTERNS = (
    r"실례", r"사례", r"치료된", r"완화한", r"호전된", r"회복한",
    r"환자(?:들)?의\s*공통점", r"경험했어요", r"전후", r"후기",
)
STORY_PATTERNS = (
    r"원장\s*이야기", r"한\s*자리를\s*지킨\s*이유", r"개원.*이유", r"걸어온",
    r"진료\s*철학", r"부부\s*한의사.*이야기", r"한의사가\s*된\s*이유",
)
COMPANY_PATTERNS = (
    r"위석부부\s*한의원(?:의)?\s*장점", r"위석부부\s*한의원.*(?:소개|이유)",
    r"한의원.*(?:선택|고르는).*기준", r"왜\s*위석부부한의원",
)

STOP_TERMS = {
    "광주", "광산구", "송정동", "광주송정역", "전남광주", "위석부부한의원", "한의원", "한의사",
    "원장", "원장이", "원장님", "경력", "년차", "진료", "치료", "알려주는", "말하는", "답하는", "가지",
    "방법", "이유", "핵심", "주의사항", "완벽", "가이드", "이야기", "건강", "되는", "어떤",
    "알아두면", "좋은", "필요할까", "필요한", "발생하며", "생기고", "해야", "할까", "보는",
    "하는", "알아보는", "찾는", "관련", "당신", "공개하는", "공개한", "밝히는", "어떻게",
    "관리해야", "관리하는", "관리가", "기준과", "상담", "상담전", "포인트", "제대로", "계신가요",
}


def parse_date(value: str) -> date:
    parts = [int(part) for part in re.findall(r"\d+", value)[:3]]
    if len(parts) != 3:
        raise ValueError(f"Invalid date: {value}")
    return date(*parts)


def fetch_text(session: requests.Session, url: str, *, params: dict[str, Any] | None = None) -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = session.get(url, params=params, timeout=35)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(0.35 * (attempt + 1))
    raise RuntimeError(f"Fetch failed: {url}: {last_error}")


def load_post_list(session: requests.Session, blog_id: str, cutoff: date) -> tuple[list[dict[str, Any]], int]:
    selected: list[dict[str, Any]] = []
    total_count = 0
    page = 1
    while True:
        raw = fetch_text(
            session,
            LIST_URL,
            params={
                "blogId": blog_id,
                "viewdate": "",
                "currentPage": page,
                "categoryNo": 0,
                "parentCategoryNo": "",
                "countPerPage": 30,
            },
        )
        data = json.loads(raw.replace("\\'", "'"))
        total_count = int(data.get("totalCount", total_count or 0))
        posts = data.get("postList", [])
        if not posts:
            break
        reached_older = False
        for post in posts:
            published = parse_date(str(post.get("addDate", "")))
            if published >= cutoff:
                selected.append(post)
            else:
                reached_older = True
        if reached_older or len(selected) >= total_count:
            break
        page += 1
    return selected, total_count


def component_kind(component: Tag) -> str:
    classes = set(component.get("class", []))
    for kind in (
        "quotation", "text", "table", "imageGroup", "image", "horizontalLine", "oglink",
        "placesMap", "video", "file", "code", "schedule",
    ):
        if f"se-{kind}" in classes:
            return kind
    for class_name in classes:
        if class_name.startswith("se-") and class_name not in {"se-component", "se-l-default"}:
            return class_name.removeprefix("se-")
    return "unknown"


def layout_name(component: Tag) -> str:
    for class_name in component.get("class", []):
        if class_name.startswith("se-l-"):
            return class_name.removeprefix("se-l-")
    return "default"


def compact_text(node: Tag | BeautifulSoup) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\u200b", " ")).strip()


def alignment_of(component: Tag) -> str:
    haystack = " ".join(component.get("class", [])) + " " + " ".join(
        str(tag.get("style", "")) + " " + " ".join(tag.get("class", []))
        for tag in component.select("[style], [class]")[:50]
    )
    for value in ("center", "right", "left", "justify"):
        if re.search(rf"(?:align[-_: ]|text-align\s*:\s*){value}", haystack, re.I):
            return value
    return "default"


def style_signals(component: Tag) -> dict[str, Any]:
    styles = " ".join(str(tag.get("style", "")) for tag in component.select("[style]"))
    classes = " ".join(" ".join(tag.get("class", [])) for tag in component.select("[class]"))
    colors = re.findall(r"(?<!background-)color\s*:\s*(#[0-9a-fA-F]{6})", styles)
    backgrounds = re.findall(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6})", styles)
    font_sizes = re.findall(r"\bse-fs-([a-zA-Z0-9_-]+)", classes)
    return {
        "alignment": alignment_of(component),
        "textColors": dict(Counter(value.lower() for value in colors)),
        "backgroundColors": dict(Counter(value.lower() for value in backgrounds)),
        "fontSizeClasses": dict(Counter(font_sizes)),
        "boldCount": len(component.select("b, strong, .se-style-bold")),
        "underlineCount": len(component.select("u, .se-style-underline")),
    }


def sentence_count(text: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?。！？])\s+|\n+", text) if part.strip()]) or int(bool(text))


def classify_title(title: str, category_no: str) -> tuple[str, str]:
    if category_no in {"14", "17"} or any(re.search(pattern, title, re.I) for pattern in NOTICE_PATTERNS):
        return "제외", "진료공지·일상·행사 기록"
    if any(re.search(pattern, title, re.I) for pattern in CASE_PATTERNS):
        return "사례공유형", ""
    if any(re.search(pattern, title, re.I) for pattern in STORY_PATTERNS):
        return "스토리텔링형", ""
    if any(re.search(pattern, title, re.I) for pattern in COMPANY_PATTERNS):
        return "업체소개형", ""
    return "정보전달형", ""


def idea_type(title: str, content_type: str) -> str:
    if content_type == "사례공유형":
        return "case-journey"
    if content_type == "스토리텔링형":
        return "doctor-philosophy"
    if content_type == "업체소개형":
        return "clinic-trust"
    if re.search(r"주의|방치|소용없|모르면|위험|절대|안\s*되는", title):
        return "risk-warning"
    if re.search(r"생활습관|음식|관리|예방|건강하게|운동|스트레칭|나는\s*법", title):
        return "self-care"
    if re.search(r"치료|추나|약침|침|한약|보험|복용|보약", title):
        return "treatment-decision"
    return "symptom-cause"


def title_pattern(title: str, primary_idea: str) -> tuple[str, str]:
    numbered = bool(re.search(r"(?:\d+|두|세)\s*가지", title))
    if " vs " in title.lower() or "대" in title and "비교" in title:
        return "versus-comparison", "서로 다른 두 상태·선택을 대비해 차이를 설명"
    if re.search(r"공통점|특징", title):
        suffix = "-numbered" if numbered else ""
        return f"reader-commonality{suffix}", "특정 결과를 보인 사람들의 공통 조건을 공개"
    if re.search(r"모르면|소용없|방치|주의", title):
        suffix = "-numbered" if numbered else ""
        return f"warning-consequence{suffix}", "놓치기 쉬운 조건과 그 결과를 경고"
    if re.search(r"왜|이유", title):
        return "reason-explained", "익숙한 현상의 이유를 원인과 판단 기준으로 설명"
    if re.search(r"실례|사례|치료된|호전|완화한|경험했어요", title):
        return "case-outcome-journey", "한 사람의 고민·확인·관리·경과를 시간순으로 설명"
    if re.search(r"장점|한\s*자리|원장\s*이야기|철학", title):
        return "clinic-principle-story", "의료기관 또는 원장의 선택이 생긴 배경과 현재 원칙을 설명"
    if numbered:
        return "expert-answer-numbered", "전문가가 독자의 질문에 서로 다른 답을 정해진 개수로 설명"
    if re.search(r"방법|가이드|원칙|핵심", title):
        return "how-to-principle", "상태를 구분하고 행동으로 옮길 수 있는 방법을 설명"
    return f"{primary_idea}-direct-answer", "증상·치료 질문에 핵심 답과 예외를 직접 설명"


def topic_terms(title: str) -> list[str]:
    cleaned = re.sub(r"\d+[,.]?\d*|20\d{2}년|\([^)]*\)|[—_:?·,*]", " ", title)
    tokens = re.findall(r"[가-힣A-Za-z]{2,}", cleaned)
    result: list[str] = []
    for token in tokens:
        if token in STOP_TERMS or token.lower() in {"vs", "eft"}:
            continue
        if token not in result:
            result.append(token)
    return result[:8]


def idea_contract(primary_idea: str, terms: list[str]) -> tuple[str, list[str]]:
    subject = "·".join(terms[:2]) or "현재 불편"
    contracts = {
        "risk-warning": (
            f"{subject} 관련 불편을 그대로 두거나 한 가지 치료만 반복할 때 무엇을 놓칠 수 있는가?",
            ["놓치기 쉬운 악화 조건", "상태를 다시 구분할 신호", "의료진과 상의할 다음 판단"],
        ),
        "self-care": (
            f"{subject} 관련 불편을 일상에서 관리하려면 무엇을 먼저 바꿔야 하는가?",
            ["생활에서 반복되는 부담", "실천 가능한 관리 방법", "자가관리만으로 미루지 말아야 할 경우"],
        ),
        "treatment-decision": (
            f"{subject}과 관련해 어떤 치료가 필요한지 무엇으로 구분할 수 있는가?",
            ["치료 전 확인할 상태", "치료를 선택하는 이유와 한계", "함께 살필 생활 조건과 재점검"],
        ),
        "symptom-cause": (
            f"{subject} 관련 증상이 반복될 때 어떤 원인과 동반 신호를 나누어 봐야 하는가?",
            ["흔한 원인과 숨은 연결", "증상·움직임·생활 조건 구분", "검사나 진찰을 먼저 생각할 예외"],
        ),
        "clinic-trust": (
            "한의원을 비교할 때 광고 문구가 아니라 어떤 진료 과정을 확인해야 하는가?",
            ["환자가 실제로 겪는 불편", "금손한의원의 확인된 운영 원칙", "과장 없이 비교할 수 있는 질문"],
        ),
        "case-journey": (
            f"{subject} 관련 한 사람의 과정에서 어떤 판단 기준을 배울 수 있는가?",
            ["처음 고민과 일상 불편", "상태 확인과 치료·관리 선택 이유", "관찰된 경과와 개인차"],
        ),
        "doctor-philosophy": (
            "원장의 경험과 선택이 현재의 진료 태도에 어떻게 이어졌는가?",
            ["확인된 시작점과 전환점", "지금까지 이어 온 구체적인 노력", "환자에게 돌아오는 현재 진료 원칙"],
        ),
    }
    return contracts[primary_idea]


def refresh_article_metadata(article: dict[str, Any]) -> None:
    title = str(article.get("sourceTitle", ""))
    content_type, exclusion_reason = classify_title(title, str(article.get("categoryNo", "")))
    primary_idea = idea_type(title, content_type) if content_type in ALLOWED_TYPES else "excluded"
    pattern_id, pattern_description = title_pattern(title, primary_idea)
    terms = topic_terms(title)
    if content_type in ALLOWED_TYPES:
        reader_question, answer_agenda = idea_contract(primary_idea, terms)
    else:
        reader_question, answer_agenda = "", []
    article.update(
        {
            "contentType": content_type,
            "eligible": content_type in ALLOWED_TYPES,
            "exclusionReason": exclusion_reason,
            "primaryIdeaType": primary_idea,
            "titlePatternId": pattern_id,
            "titlePatternDescription": pattern_description,
            "topicTerms": terms,
            "readerQuestion": reader_question,
            "answerAgenda": answer_agenda,
            "compatibleWritingTypes": [content_type] if content_type in ALLOWED_TYPES else [],
            "sourceFactsBlocked": True,
            "sourceSentencesBlocked": True,
            "sourceMediaBlocked": True,
        }
    )
    blueprint = article.get("componentBlueprint", [])
    if isinstance(blueprint, list):
        for item in blueprint:
            if not isinstance(item, dict):
                continue
            for field in (
                "paragraphCount",
                "charCount",
                "sentenceCount",
                "questionCount",
                "boldCount",
                "underlineCount",
            ):
                item[field] = int(item.get(field, 0))


def role_blueprint(components: list[dict[str, Any]]) -> list[str]:
    roles: list[str] = []
    text_positions = [index for index, item in enumerate(components) if item["kind"] == "text"]
    last_texts = set(text_positions[-2:])
    seen_explanation = False
    for index, item in enumerate(components):
        kind = item["kind"]
        if kind == "quotation" and not seen_explanation:
            role = "reader-question"
        elif kind == "table" and index <= 5:
            role = "credential-proof"
        elif kind in {"image", "imageGroup", "video"}:
            role = "evidence-media"
        elif kind == "horizontalLine":
            role = "divider"
        elif kind == "text" and index == text_positions[0] if text_positions else False:
            role = "greeting-authority"
            seen_explanation = True
        elif kind == "text" and item["charCount"] <= 80 and (
            item["boldCount"] or item["questionCount"] or item["paragraphCount"] <= 2
        ):
            role = "section-heading"
            seen_explanation = True
        elif kind == "text" and index in last_texts:
            role = "recap" if index == min(last_texts) else "neutral-close"
            seen_explanation = True
        elif kind == "text":
            role = "explanation"
            seen_explanation = True
        elif kind == "oglink":
            role = "related-link"
        else:
            role = kind
        roles.append(role)
    return roles


def parse_post(meta: dict[str, Any], blog_id: str) -> dict[str, Any]:
    log_no = str(meta["logNo"])
    title = html_lib.unescape(unquote_plus(str(meta.get("title", ""))))
    published = parse_date(str(meta.get("addDate", "")))
    source_url = f"https://blog.naver.com/{blog_id}/{log_no}"
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    html = fetch_text(session, POST_URL.format(blog_id=blog_id, log_no=log_no))
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one(".se-main-container") or soup.select_one(".se_component_wrap")
    if root is None:
        raise RuntimeError(f"SmartEditor body missing: {log_no}")
    raw_components = root.select(":scope > .se-component") or root.select(".se-component")
    components: list[dict[str, Any]] = []
    all_paragraph_lengths: list[int] = []
    all_body_text: list[str] = []
    contact_started = False
    for component in raw_components:
        text = compact_text(component)
        if re.search(r"talk\.naver\.com|네이버\s*톡톡|전화\s*문의", text, re.I):
            contact_started = True
        kind = component_kind(component)
        if contact_started or (kind == "text" and re.fullmatch(r"https?://\S+", text)):
            continue
        paragraphs = [compact_text(node) for node in component.select(".se-text-paragraph")]
        paragraphs = [value for value in paragraphs if value]
        if not paragraphs and text and kind in {"text", "quotation", "table"}:
            paragraphs = [text]
        all_paragraph_lengths.extend(len(re.sub(r"\s+", "", value)) for value in paragraphs)
        if kind in {"text", "quotation", "table"}:
            all_body_text.extend(paragraphs)
        signals = style_signals(component)
        item = {
            "kind": kind,
            "layout": layout_name(component),
            "paragraphCount": len(paragraphs),
            "charCount": len(re.sub(r"\s+", "", " ".join(paragraphs))),
            "sentenceCount": sentence_count(" ".join(paragraphs)),
            "questionCount": " ".join(paragraphs).count("?"),
            **signals,
        }
        components.append(item)
    roles = role_blueprint(components)
    for item, role in zip(components, roles):
        item["role"] = role
    body_text = " ".join(all_body_text)
    content_type, exclusion_reason = classify_title(title, str(meta.get("categoryNo", "")))
    primary_idea = idea_type(title, content_type) if content_type in ALLOWED_TYPES else "excluded"
    pattern_id, pattern_description = title_pattern(title, primary_idea)
    terms = topic_terms(title)
    if content_type in ALLOWED_TYPES:
        reader_question, answer_agenda = idea_contract(primary_idea, terms)
    else:
        reader_question, answer_agenda = "", []
    endings = Counter(
        match.group(1)
        for match in re.finditer(
            r"(습니다|입니다|합니다|됩니다|있습니다|없습니다|인데요|했고요|합니다만|해요|예요|죠|세요)(?=[.!?\s]|$)",
            body_text,
        )
    )
    style_totals = {
        "alignmentCounts": dict(Counter(item["alignment"] for item in components)),
        "componentCounts": dict(Counter(item["kind"] for item in components)),
        "textColors": dict(sum((Counter(item["textColors"]) for item in components), Counter())),
        "backgroundColors": dict(sum((Counter(item["backgroundColors"]) for item in components), Counter())),
        "fontSizeClasses": dict(sum((Counter(item["fontSizeClasses"]) for item in components), Counter())),
        "boldCount": sum(int(item["boldCount"]) for item in components),
        "underlineCount": sum(int(item["underlineCount"]) for item in components),
    }
    return {
        "id": f"WP{log_no}",
        "logNo": log_no,
        "sourceTitle": title,
        "sourceUrl": source_url,
        "publishedAt": published.isoformat(),
        "categoryNo": str(meta.get("categoryNo", "")),
        "contentType": content_type,
        "eligible": content_type in ALLOWED_TYPES,
        "exclusionReason": exclusion_reason,
        "primaryIdeaType": primary_idea,
        "titlePatternId": pattern_id,
        "titlePatternDescription": pattern_description,
        "topicTerms": terms,
        "readerQuestion": reader_question,
        "answerAgenda": answer_agenda,
        "compatibleWritingTypes": [content_type] if content_type in ALLOWED_TYPES else [],
        "sourceFactsBlocked": True,
        "sourceSentencesBlocked": True,
        "sourceMediaBlocked": True,
        "textStats": {
            "nonWhitespaceChars": len(re.sub(r"\s+", "", body_text)),
            "paragraphCount": len(all_paragraph_lengths),
            "medianParagraphChars": round(statistics.median(all_paragraph_lengths), 1) if all_paragraph_lengths else 0,
            "maxParagraphChars": max(all_paragraph_lengths, default=0),
            "sentenceCount": sentence_count(body_text),
            "questionCount": body_text.count("?"),
        },
        "toneSignals": {
            "sentenceEndings": dict(endings.most_common()),
            "firstPersonCount": len(re.findall(r"저희|저는|제가|저의", body_text)),
            "readerAddressCount": len(re.findall(r"환자분|분들|여러분|내원하시는", body_text)),
            "quotedSpanCount": len(re.findall(r"[\"“”']", body_text)) // 2,
        },
        "styleSignals": style_totals,
        "componentBlueprint": components,
    }


def inventory_markdown(corpus: dict[str, Any]) -> str:
    articles = corpus["articles"]
    type_counts = Counter(article["contentType"] for article in articles)
    lines = [
        "# 위석부부한의원 레퍼런스 전수 목록",
        "",
        f"- 기준일: `{corpus['cutoffInclusive']}` 포함 이후",
        f"- 블로그 전체 공개 글: {corpus['sourceTotalCount']}편",
        f"- 기준일 이후 수집·본문 분석: {corpus['includedCount']}편",
        f"- 본문 추출 성공: {corpus['fetchSuccessCount']}편",
        f"- 유형별: " + ", ".join(f"{key} {value}편" for key, value in sorted(type_counts.items())),
        "- `제외`는 진료 공지·일상·행사 기록이며 주제 아이디어·글쓰기 마스터 어느 쪽에도 사용하지 않는다.",
        "- 원문 업체의 사실·수치·사례·문장·사진은 금손한의원 글에 옮기지 않는다.",
        "",
        "| 날짜 | 분류 | 제목 | 원문 |",
        "|---|---|---|---|",
    ]
    for article in articles:
        title = str(article["sourceTitle"]).replace("|", "\\|")
        lines.append(
            f"| {article['publishedAt']} | {article['contentType']} | {title} | [보기]({article['sourceUrl']}) |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blog-id", default=BLOG_ID)
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF.isoformat())
    parser.add_argument("--corpus-output", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--inventory-output", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--fresh", action="store_true", help="Ignore an existing partial corpus.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cutoff = date.fromisoformat(args.cutoff)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    try:
        posts, total_count = load_post_list(session, args.blog_id, cutoff)
        articles: list[dict[str, Any]] = []
        if args.corpus_output.exists() and not args.fresh:
            previous = json.loads(args.corpus_output.read_text(encoding="utf-8"))
            previous_articles = previous.get("articles", []) if isinstance(previous, dict) else []
            articles = [item for item in previous_articles if isinstance(item, dict)]
            post_by_log_no = {str(post.get("logNo", "")): post for post in posts}
            for article in articles:
                current_meta = post_by_log_no.get(str(article.get("logNo", "")))
                if current_meta:
                    article["sourceTitle"] = html_lib.unescape(
                        unquote_plus(str(current_meta.get("title", article.get("sourceTitle", ""))))
                    )
                    article["publishedAt"] = parse_date(str(current_meta.get("addDate", ""))).isoformat()
                    article["categoryNo"] = str(current_meta.get("categoryNo", article.get("categoryNo", "")))
                refresh_article_metadata(article)
        existing_log_nos = {str(article.get("logNo", "")) for article in articles}
        pending_posts = [post for post in posts if str(post.get("logNo", "")) not in existing_log_nos]
        failures: list[dict[str, str]] = []
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
            futures = {pool.submit(parse_post, post, args.blog_id): post for post in pending_posts}
            for future in as_completed(futures):
                post = futures[future]
                try:
                    articles.append(future.result())
                except Exception as exc:  # noqa: BLE001 - audit must report every failed source
                    failures.append({"logNo": str(post.get("logNo", "")), "error": str(exc)})
        articles.sort(key=lambda item: (item["publishedAt"], item["logNo"]), reverse=True)
        corpus = {
            "schemaVersion": 1,
            "sourceBlogId": args.blog_id,
            "sourceBlogName": BLOG_NAME,
            "sourceBlogUrl": f"https://blog.naver.com/{args.blog_id}",
            "cutoffInclusive": cutoff.isoformat(),
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sourceTotalCount": total_count,
            "includedCount": len(posts),
            "fetchSuccessCount": len(articles),
            "fetchFailureCount": len(failures),
            "failures": failures,
            "contentPolicy": "Ideas and one-master writing/decor patterns only; all source facts, claims, sentences and media are blocked.",
            "articles": articles,
        }
        args.corpus_output.parent.mkdir(parents=True, exist_ok=True)
        args.inventory_output.parent.mkdir(parents=True, exist_ok=True)
        args.corpus_output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.inventory_output.write_text(inventory_markdown(corpus), encoding="utf-8")
    except (OSError, ValueError, RuntimeError, requests.RequestException, json.JSONDecodeError) as exc:
        print(f"레퍼런스 수집 실패: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "pass" if not failures else "partial",
                "included": len(posts),
                "fetched": len(articles),
                "newlyFetched": len(pending_posts) - len(failures),
                "failed": len(failures),
                "corpus": str(args.corpus_output),
                "inventory": str(args.inventory_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
