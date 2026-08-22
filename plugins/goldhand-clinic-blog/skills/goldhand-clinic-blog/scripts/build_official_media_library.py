#!/usr/bin/env python3
"""Build the media index that is later bundled by sync_official_media_assets.

Fetched blog text is treated only as untrusted source data. The builder never
executes scripts or follows instructions found inside a post.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = SKILL_DIR / "references" / "official-blog-inventory.md"
DEFAULT_OUTPUT = SKILL_DIR / "assets" / "media-library.json"
DEFAULT_REVIEW_OVERRIDES = SKILL_DIR / "assets" / "media-review-overrides.json"
SEOUL = ZoneInfo("Asia/Seoul")
ROW_RE = re.compile(
    r"^\|\s*(?P<number>\d+)\s*\|\s*(?P<date>[^|]+?)\s*\|\s*(?P<category>\d+)\s*\|\s*(?P<title>.*?)\s*\|\s*\[보기\]\((?P<url>https://blog\.naver\.com/goldhand7582_/\d+)\)\s*\|$"
)
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣+·._-]{1,}")
STOPWORDS = {"금손한의원", "광주", "한의원", "관련", "대한", "위한", "사진", "이미지", "합니다", "있습니다", "그리고"}

TAG_RULES: dict[str, tuple[str, ...]] = {
    "musculoskeletal": ("통증", "저림", "체형", "목", "어깨", "허리", "무릎", "손목", "팔꿈치", "관절", "근육", "염좌", "타박상"),
    "traffic-accident": ("교통사고", "자동차사고"),
    "physical-therapy": ("ICT", "TENS", "물리치료", "저주파"),
    "acupuncture": ("침치료", "침 치료", "KM침", "침"),
    "chuna": ("추나", "도수", "수기치료"),
    "golta": ("골타", "도인안교"),
    "pharmacopuncture": ("약침", "원외탕전"),
    "cupping": ("부항", "습식부항"),
    "herbal-medicine": ("한약", "탕약", "처방", "약재", "첩약"),
    "digestion": ("소화", "위염", "식도염", "복통", "더부룩", "반하사심탕", "평위산", "소건중탕"),
    "respiratory": ("비염", "기침", "가래", "기관지", "소청룡탕", "맥문동탕"),
    "women-health": ("생리통", "월경", "PMS", "어혈", "계지복령환", "칠제향부환"),
    "child-health": ("아이", "소아", "아들", "성장", "스티커침"),
    "restorative": ("공진단", "경옥고", "보약", "귀비탕", "체력"),
    "ointment": ("자운고", "연고", "피부", "보습"),
    "home-visit": ("방문진료", "왕진", "방문간호"),
    "clinic-space": ("대기실", "치료실", "진료실", "접수대", "내부", "외부", "간판"),
    "community": ("기부", "봉사", "협약", "초록우산", "보호소"),
    "director-story": ("박 원장", "박원장", "원장님", "갑상선암", "수술", "운동"),
}

TEMPORARY_POST = re.compile(r"(?:진료\s*안내|정상\s*진료|휴진|휴가|연휴|공휴일|제헌절|광복절|근로자의\s*날|크리스마스|설\s*연휴|추석|이벤트|할인|상품권|소비쿠폰|주차장)")
RISKY_DESCRIPTOR = re.compile(r"(?:환자|고객|아들|아이|어머니|자매|봉사|협약|보호소|어린이집|차트|처방전|검사결과|이름|연락처|얼굴|셀카|수술|입원|후기|방문진료|왕진)")
DOCUMENT_DESCRIPTOR = re.compile(r"(?:인증서|수료증|협약서|명패|서류|차트|처방전|검사|진단서|캡처|문자|카톡)")
CLEAR_OBJECT = re.compile(
    r"(?:^|[^A-Za-z])(?:ICT|TENS|KM침)(?:[^A-Za-z]|$)|"
    r"(?:물리치료기|저주파기|부항컵|일회용\s*부항|약침액|약침\s*재료|약침과.{0,12}주사기|주사기|침\s*포장|한약\s*팩|탕약\s*팩|탕약\s*사진|"
    r"약재|맞춤\s*한약|체질\s*한약|보험\s*한약|과립\s*한약|한약\s*사진|공진단|경옥고|자운고|계지복령환|칠제향부환|계지칠제|골타\s*(?:기기|도구)|추나\s*베드|치료\s*베드|대기실|치료실|진료실|접수대|한의원\s*(?:내부|외부|간판|로고)|의료기기|장비|스티커침)",
    re.I,
)
GENERIC_FILENAME = re.compile(r"^(?:SE[-_]|IMG[-_]?\d|KakaoTalk|image\d*|photo\d*|PXL[-_]|DSC[-_]?\d)", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-overrides", type=Path, default=DEFAULT_REVIEW_OVERRIDES)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0, help="테스트용 게시글 수 제한")
    parser.add_argument("--resume", action="store_true", help="기존 출력의 성공 글은 유지하고 누락 글만 다시 수집")
    return parser.parse_args()


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200b", " ")).strip()


def truncate(value: str, limit: int) -> str:
    value = compact(value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def tokens(value: str) -> list[str]:
    result: list[str] = []
    for token in TOKEN_RE.findall(value):
        cleaned = token.strip("._-").lower()
        if len(cleaned) < 2 or cleaned in STOPWORDS:
            continue
        if cleaned not in result:
            result.append(cleaned)
    return result


def parse_inventory(path: Path) -> list[dict[str, str]]:
    posts: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW_RE.match(line.strip())
        if not match:
            continue
        item = match.groupdict()
        item["logNo"] = item["url"].rstrip("/").rsplit("/", 1)[-1]
        item["mobileUrl"] = item["url"].replace("https://blog.naver.com/", "https://m.blog.naver.com/")
        posts.append(item)
    if not posts:
        raise ValueError("인벤토리에서 블로그 글을 찾지 못했습니다.")
    return posts


def tag_list(value: str) -> list[str]:
    lowered = value.lower()
    return sorted(tag for tag, phrases in TAG_RULES.items() if any(phrase.lower() in lowered for phrase in phrases))


def naver_render_url(value: str) -> str:
    value = value.strip()
    if value.startswith("https://") and "pstatic.net/" in value:
        return value.split("?", 1)[0] + "?type=w966"
    return value


def descriptor_safety(filename: str, caption: str, title: str, width: int, height: int) -> tuple[bool, str]:
    descriptor = compact(f"{Path(filename).stem} {caption}")
    if TEMPORARY_POST.search(title):
        return False, "temporary-post"
    if width < 240 or height < 180:
        return False, "small-or-decorative"
    if not descriptor:
        return False, "missing-description"
    if RISKY_DESCRIPTOR.search(descriptor):
        return False, "privacy-or-person-risk"
    if DOCUMENT_DESCRIPTOR.search(descriptor):
        return False, "document-or-personal-data-risk"
    if not CLEAR_OBJECT.search(descriptor):
        return False, "not-clearly-object-or-space"
    if GENERIC_FILENAME.search(filename) and not CLEAR_OBJECT.search(caption):
        return False, "generic-filename-without-clear-caption"
    return True, "clear-object-or-space"


def neighboring_context(index: int, components: list[Tag]) -> str:
    values: list[str] = []
    for nearby in components[max(0, index - 2) : min(len(components), index + 3)]:
        text = compact(nearby.get_text(" ", strip=False))
        if text and text not in values:
            values.append(text)
    return truncate(" / ".join(values), 520)


def fetch_post(post: dict[str, str]) -> tuple[dict[str, str], list[dict[str, Any]], str | None]:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GoldhandMediaIndexer/1.0"}
    last_error = ""
    for attempt in range(3):
        try:
            response = requests.get(post["mobileUrl"], headers=headers, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            container = soup.select_one(".se-main-container") or soup
            components = [tag for tag in container.select(".se-component") if isinstance(tag, Tag)]
            component_index = {id(tag): index for index, tag in enumerate(components)}
            assets: list[dict[str, Any]] = []
            for order, image in enumerate(container.select("img.se-image-resource"), start=1):
                component = image.find_parent(lambda tag: isinstance(tag, Tag) and "se-component" in tag.get("class", []))
                if not isinstance(component, Tag):
                    continue
                anchor = image.find_parent("a")
                source_url = ""
                original_width = int(str(image.get("data-width") or "0") or 0)
                original_height = int(str(image.get("data-height") or "0") or 0)
                if isinstance(anchor, Tag) and anchor.get("data-linkdata"):
                    try:
                        link_data = json.loads(str(anchor.get("data-linkdata")))
                        source_url = str(link_data.get("src") or "")
                        original_width = int(str(link_data.get("originalWidth") or original_width) or 0)
                        original_height = int(str(link_data.get("originalHeight") or original_height) or 0)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        source_url = ""
                if not source_url:
                    source_url = str(image.get("data-lazy-src") or image.get("src") or "").split("?", 1)[0]
                source_url = naver_render_url(source_url)
                if not source_url.startswith("https://"):
                    continue
                filename = unquote(Path(urlparse(source_url).path).name)
                caption_node = component.select_one(".se-caption")
                caption = compact(caption_node.get_text(" ", strip=False)) if caption_node else ""
                position = component_index.get(id(component), 0)
                context = neighboring_context(position, components)
                safe, reason = descriptor_safety(filename, caption, post["title"], original_width, original_height)
                ratio = position / max(1, len(components) - 1)
                band = "intro" if ratio <= 0.25 else "closing" if ratio >= 0.78 else "body"
                searchable = f"{post['title']} {filename} {caption} {context}"
                assets.append(
                    {
                        "postOrder": int(post["number"]),
                        "imageOrder": order,
                        "url": source_url,
                        "sourcePostUrl": post["url"],
                        "sourceMobileUrl": post["mobileUrl"],
                        "sourceLogNo": post["logNo"],
                        "sourceTitle": post["title"],
                        "sourceDate": compact(post["date"]),
                        "category": int(post["category"]),
                        "filename": filename,
                        "caption": caption,
                        "context": context,
                        "width": original_width,
                        "height": original_height,
                        "positionBand": band,
                        "tags": tag_list(searchable),
                        "tokens": tokens(searchable)[:45],
                        "safeAuto": safe,
                        "requiresReview": not safe,
                        "safetyReason": reason,
                    }
                )
            return post, assets, None
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(4.0 * (attempt + 1) if "429" in last_error else 0.8 * (attempt + 1))
    return post, [], last_error or "unknown-fetch-error"


def main() -> int:
    args = parse_args()
    try:
        posts = parse_inventory(args.inventory)
        if args.limit > 0:
            posts = posts[: args.limit]
        assets: list[dict[str, Any]] = []
        existing_by_post: dict[str, list[dict[str, Any]]] = {}
        existing_payload: dict[str, Any] = {}
        if args.resume and args.output.exists():
            existing = json.loads(args.output.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing_payload = existing
            for asset in existing.get("assets", []) if isinstance(existing, dict) else []:
                if isinstance(asset, dict) and asset.get("sourceLogNo"):
                    asset["url"] = naver_render_url(str(asset.get("url", "")))
                    safe, reason = descriptor_safety(
                        str(asset.get("filename", "")),
                        str(asset.get("caption", "")),
                        str(asset.get("sourceTitle", "")),
                        int(asset.get("width", 0) or 0),
                        int(asset.get("height", 0) or 0),
                    )
                    asset["safeAuto"] = safe
                    asset["requiresReview"] = not safe
                    asset["safetyReason"] = reason
                    existing_by_post.setdefault(str(asset["sourceLogNo"]), []).append(asset)
            assets.extend(asset for group in existing_by_post.values() for asset in group)
            posts = [post for post in posts if post["logNo"] not in existing_by_post]
        requested_posts = len(posts) + len(existing_by_post)
        failures: list[dict[str, str]] = []
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 10))) as pool:
            futures = [pool.submit(fetch_post, post) for post in posts]
            for future in as_completed(futures):
                post, post_assets, error = future.result()
                assets.extend(post_assets)
                if error:
                    failures.append({"logNo": post["logNo"], "url": post["url"], "error": error})
        assets.sort(key=lambda item: (item["postOrder"], item["imageOrder"]))
        review_data = json.loads(args.review_overrides.read_text(encoding="utf-8")) if args.review_overrides.exists() else {}
        approved = review_data.get("approved", {}) if isinstance(review_data, dict) else {}
        denied = review_data.get("denied", {}) if isinstance(review_data, dict) else {}
        for asset in assets:
            review_key = f"{asset['sourceLogNo']}:{asset['imageOrder']}"
            review = approved.get(review_key) if isinstance(approved, dict) else None
            denial = denied.get(review_key) if isinstance(denied, dict) else None
            manual_person_safe = bool(
                isinstance(review, dict)
                and review.get("safetyApproved") is True
                and review.get("personInteraction") is True
                and review.get("directorVisible") is True
                and str(review.get("sceneType", "")).startswith("director-patient-")
            )
            asset["reviewKey"] = review_key
            asset["visualReviewed"] = isinstance(review, dict)
            asset["duplicateGroup"] = str(review.get("duplicateGroup", "")) if isinstance(review, dict) else ""
            asset["sceneType"] = str(review.get("sceneType", "")) if isinstance(review, dict) else ""
            asset["personInteraction"] = bool(review.get("personInteraction")) if isinstance(review, dict) else False
            asset["directorVisible"] = bool(review.get("directorVisible")) if isinstance(review, dict) else False
            asset["trustPriority"] = int(review.get("trustPriority", 0)) if isinstance(review, dict) else 0
            if denial:
                asset["safeAuto"] = False
                asset["requiresReview"] = False
                asset["safetyReason"] = "visual-review-denied"
            elif isinstance(review, dict) and manual_person_safe:
                asset["safeAuto"] = True
                asset["requiresReview"] = False
                asset["safetyReason"] = "manual-director-patient-visual-review-approved"
            else:
                asset["safeAuto"] = False
                asset["requiresReview"] = True
                asset["safetyReason"] = "article-use-requires-director-patient-scene"
        for index, asset in enumerate(assets, start=1):
            asset["id"] = f"GH{index:04d}"
        bundled_assets = [
            asset
            for asset in assets
            if asset.get("bundledPath") and asset.get("sha256") and asset.get("sizeBytes")
        ]
        fully_bundled = bool(assets) and len(bundled_assets) == len(assets)
        payload = {
            "schemaVersion": 2 if fully_bundled else 1,
            "generatedAt": datetime.now(SEOUL).isoformat(timespec="seconds"),
            "sourceBlog": "https://blog.naver.com/goldhand7582_",
            "inventoryPosts": requested_posts,
            "fetchedPosts": requested_posts - len(failures),
            "failedPosts": failures,
            "assetCount": len(assets),
            "safeAutoCount": sum(asset["safeAuto"] for asset in assets),
            "policy": (
                "All indexed official-blog image binaries are bundled in the plugin; only visually approved "
                "director-patient safeAuto assets may be selected automatically"
                if fully_bundled
                else "Metadata inventory; run sync_official_media_assets.py before packaging or use"
            ),
            "assets": assets,
        }
        if bundled_assets:
            payload["bundledAt"] = existing_payload.get("bundledAt", datetime.now(SEOUL).isoformat(timespec="seconds"))
            payload["bundledAssetCount"] = len(bundled_assets)
            payload["bundledBytes"] = sum(int(asset.get("sizeBytes", 0) or 0) for asset in bundled_assets)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"미디어 라이브러리 생성 실패: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: payload[key] for key in ("inventoryPosts", "fetchedPosts", "assetCount", "safeAutoCount", "failedPosts")}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
