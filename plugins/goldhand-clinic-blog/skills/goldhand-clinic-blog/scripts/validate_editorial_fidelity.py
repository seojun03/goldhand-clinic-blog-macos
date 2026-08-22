#!/usr/bin/env python3
"""Validate one Beomeo editorial master and its required content-beat order."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = SKILL_DIR / "assets" / "beomeo-editorial-master-profiles.json"
BEOMEO_URL = re.compile(
    r"https?://(?:m\.|blog\.)?naver\.com/(?:PostView\.naver\?[^\"'<>\s]*blogId=beomeo_sm|beomeo_sm(?:/|\b))",
    re.I,
)


def article_fragment(raw: str) -> str:
    matches = re.findall(r"<article\b[^>]*>.*?</article>", raw, flags=re.I | re.S)
    if len(matches) != 1:
        raise ValueError(f"<article>이 {len(matches)}개입니다. 하나만 있어야 합니다.")
    return matches[0]


def attr_values(fragment: str, attribute: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(attribute)}\s*=\s*(['\"])(.*?)\1", re.I | re.S)
    return [html.unescape(match.group(2)).strip() for match in pattern.finditer(fragment)]


def visible_text(fragment: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", fragment, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def without_allowed_editorial_source(fragment: str) -> str:
    return re.sub(
        r"(\bdata-editorial-reference-source\s*=\s*['\"])(.*?)(['\"])",
        r"\1EDITORIAL_REFERENCE_SOURCE\3",
        fragment,
        flags=re.I | re.S,
    )


def load_profiles(path: Path) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict):
        raise ValueError("편집 마스터 파일의 profiles mapping을 찾지 못했습니다.")
    return {
        str(profile_id): profile
        for profile_id, profile in profiles.items()
        if isinstance(profile, dict)
    }


def validate(
    raw: str,
    profiles: dict[str, dict[str, object]],
    expected_profile: str = "",
) -> dict[str, object]:
    article = article_fragment(raw)
    issues: list[str] = []
    tag_match = re.search(r"<article\b[^>]*>", article, re.I | re.S)
    tag = tag_match.group(0) if tag_match else ""

    master_values = attr_values(tag, "data-editorial-master-id")
    source_values = attr_values(tag, "data-editorial-reference-source")
    source_role_values = attr_values(tag, "data-editorial-source-role")
    status_values = attr_values(tag, "data-editorial-profile-status")
    layout_source_values = attr_values(tag, "data-reference-source")
    for attribute, tag_values in (
        ("data-editorial-master-id", master_values),
        ("data-editorial-reference-source", source_values),
        ("data-editorial-source-role", source_role_values),
        ("data-editorial-profile-status", status_values),
    ):
        if len(attr_values(article, attribute)) != len(tag_values):
            issues.append(f"{attribute}는 <article> 시작 태그에만 선언해야 합니다.")

    if len(master_values) != 1:
        issues.append(f"data-editorial-master-id가 {len(master_values)}개입니다. 정확히 1개여야 합니다.")
    master_id = master_values[0] if len(master_values) == 1 else ""
    if expected_profile and master_id != expected_profile:
        issues.append(f"편집 마스터는 {master_id or '없음'}이며 요구값은 {expected_profile}입니다.")

    profile = profiles.get(master_id)
    if profile is None:
        issues.append(f"등록되지 않은 편집 마스터 ID입니다: {master_id or '없음'}")
        profile = {}

    if len(source_values) != 1:
        issues.append(f"data-editorial-reference-source가 {len(source_values)}개입니다. 정확히 1개여야 합니다.")
    source_url = source_values[0] if len(source_values) == 1 else ""
    expected_source = str(profile.get("sourceUrl", ""))
    if profile and source_url != expected_source:
        issues.append("data-editorial-reference-source가 선택한 편집 원문 URL과 정확히 일치하지 않습니다.")

    expected_source_role = str(profile.get("sourceRole", "title-tone-content-sequence-only"))
    if len(source_role_values) > 1:
        issues.append("data-editorial-source-role은 최대 1개만 선언할 수 있습니다.")
    elif source_role_values and source_role_values[0] != expected_source_role:
        issues.append(
            f"data-editorial-source-role은 {expected_source_role}여야 합니다."
        )
    if status_values != ["ready"]:
        issues.append("data-editorial-profile-status는 원문 본문 감사와 프로필 검증을 마친 ready여야 합니다.")

    if any(BEOMEO_URL.search(value) for value in layout_source_values):
        issues.append("data-reference-source에는 Beomeo 편집 원문이 아니라 기존 순정 레이아웃 마스터를 둡니다.")
    leaked_source = BEOMEO_URL.search(without_allowed_editorial_source(article))
    if leaked_source:
        issues.append(
            "Beomeo URL은 data-editorial-reference-source에서만 허용하며 본문·미디어·레이아웃 출처로 넣지 않습니다."
        )

    required_raw = profile.get("requiredContentBeats", []) if isinstance(profile, dict) else []
    required_beats = [str(value) for value in required_raw] if isinstance(required_raw, list) else []
    if not required_beats:
        issues.append("편집 마스터에 requiredContentBeats가 없습니다.")

    beat_matches = list(
        re.finditer(
            r"<(?P<tag>[a-z][\w:-]*)\b(?P<attrs>(?=[^>]*\bdata-editorial-beat\s*=\s*['\"](?P<beat>[^'\"]+)['\"])[^>]*)>",
            article,
            re.I | re.S,
        )
    )
    actual_beats = [html.unescape(match.group("beat")).strip() for match in beat_matches]
    counts = Counter(actual_beats)
    for beat in required_beats:
        if counts[beat] == 0:
            issues.append(f"필수 편집 비트가 없습니다: {beat}")
        elif counts[beat] > 1:
            issues.append(f"필수 편집 비트가 {counts[beat]}번 선언되었습니다: {beat}")
    unknown_beats = [beat for beat in actual_beats if beat not in set(required_beats)]
    if unknown_beats:
        issues.append(f"선택한 한 편의 프로필에 없는 편집 비트가 섞였습니다: {', '.join(unknown_beats)}")
    if actual_beats != required_beats:
        issues.append(f"편집 비트 순서가 다릅니다: 실제 {actual_beats}, 필수 {required_beats}")

    for index, match in enumerate(beat_matches):
        closing = re.search(
            rf"</{re.escape(match.group('tag'))}\s*>",
            article[match.end():],
            re.I,
        )
        region = article[match.end():match.end() + closing.start()] if closing else ""
        if not visible_text(region):
            issues.append(f"편집 비트에 실제 본문이 없습니다: {actual_beats[index]}")

    return {
        "status": "pass" if not issues else "fail",
        "metrics": {
            "editorialMasterId": master_id,
            "editorialReferenceSource": source_url,
            "editorialSourceRole": source_role_values[0] if len(source_role_values) == 1 else "",
            "editorialProfileStatus": status_values[0] if len(status_values) == 1 else "",
            "requiredContentBeats": required_beats,
            "actualContentBeats": actual_beats,
            "beatCount": len(actual_beats),
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", default="")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = args.input.read_text(encoding="utf-8")
        result = validate(raw, load_profiles(args.profiles), args.profile)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"편집 충실도 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"editorial master: {result['metrics']['editorialMasterId']}")
        for issue in result["issues"]:
            print(f"[ERROR] {issue}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
