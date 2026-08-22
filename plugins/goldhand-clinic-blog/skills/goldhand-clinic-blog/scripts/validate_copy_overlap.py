#!/usr/bin/env python3
"""Block verbatim source reuse while allowing a small set of common search phrases."""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path


DEFAULT_ALLOWED_PHRASES = (
    "광주 한의원 추천",
    "운동을 해도 살이 안 빠지는 이유",
    "운동해도 살이 안 빠지는 이유",
    "운동을 해도 살이 잘 안 빠지는 이유",
    "운동하는데 왜 살이 잘 안 빠질까요",
)
TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", html.unescape(value))
    value = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", value)
    return value


def plain_text(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(
        r"</?(?:p|div|section|header|footer|article|h[1-6]|blockquote|li|tr|table|figure|figcaption|br|hr)\b[^>]*>",
        "\n",
        value,
        flags=re.I,
    )
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[\t\f\v ]+", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def tokens(value: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(normalize(value))]


def compact_tokens(values: list[str]) -> str:
    return "".join(values)


def sentence_units(value: str) -> list[str]:
    text = plain_text(value)
    units: list[str] = []
    for block in re.split(r"\n+", text):
        for sentence in re.split(r"(?<=[.!?。！？])\s+", block):
            sentence = re.sub(r"\s+", " ", sentence).strip()
            if sentence:
                units.append(sentence)
    return units


def contains_tokens(haystack: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(haystack[index:index + width] == needle for index in range(len(haystack) - width + 1))


def is_allowed_phrase(sequence: list[str], allowed: list[list[str]]) -> bool:
    return any(sequence == phrase for phrase in allowed)


def validate(
    source: str,
    draft: str,
    *,
    min_consecutive: int = 7,
    allowed_phrases: list[str] | None = None,
) -> dict[str, object]:
    if min_consecutive < 2:
        raise ValueError("min_consecutive는 2 이상이어야 합니다.")
    allowed_text = list(DEFAULT_ALLOWED_PHRASES)
    if allowed_phrases:
        allowed_text.extend(allowed_phrases)
    allowed = [tokens(value) for value in allowed_text if tokens(value)]

    source_tokens = tokens(plain_text(source))
    draft_tokens = tokens(plain_text(draft))
    matcher = difflib.SequenceMatcher(None, source_tokens, draft_tokens, autojunk=False)
    matching_blocks = [
        block for block in matcher.get_matching_blocks()
        if block.size >= min_consecutive
    ]

    issues: list[dict[str, object]] = []
    long_matches: list[dict[str, object]] = []
    blocked_source_ranges: list[tuple[int, int]] = []
    for block in matching_blocks:
        sequence = source_tokens[block.a:block.a + block.size]
        if is_allowed_phrase(sequence, allowed):
            continue
        phrase = " ".join(sequence)
        long_matches.append(
            {
                "wordCount": block.size,
                "phrase": phrase,
                "sourceWordIndex": block.a,
                "draftWordIndex": block.b,
            }
        )
        blocked_source_ranges.append((block.a, block.a + block.size))
        issues.append(
            {
                "severity": "error",
                "code": "consecutive-copy-overlap",
                "detail": f"원문과 {block.size}어절이 연속 일치합니다: {phrase}",
            }
        )

    unique_sentence_matches: list[dict[str, object]] = []
    for sentence in sentence_units(source):
        sentence_tokens = tokens(sentence)
        token_count = len(sentence_tokens)
        compact_chars = len(compact_tokens(sentence_tokens))
        # Seven-word sequences are already handled above. This catches shorter,
        # distinctive source sentences without treating a two- or three-word
        # search query as copied prose.
        if token_count < 3 or token_count >= min_consecutive or compact_chars < 22:
            continue
        if is_allowed_phrase(sentence_tokens, allowed):
            continue
        if not contains_tokens(draft_tokens, sentence_tokens):
            continue
        source_positions = [
            index
            for index in range(len(source_tokens) - token_count + 1)
            if source_tokens[index:index + token_count] == sentence_tokens
        ]
        already_reported = any(
            any(start <= position and position + token_count <= end for start, end in blocked_source_ranges)
            for position in source_positions
        )
        if already_reported:
            continue
        match = {
            "wordCount": token_count,
            "phrase": " ".join(sentence_tokens),
            "compactChars": compact_chars,
        }
        unique_sentence_matches.append(match)
        issues.append(
            {
                "severity": "error",
                "code": "source-sentence-copy",
                "detail": f"원문의 고유 문장이 그대로 남았습니다: {match['phrase']}",
            }
        )

    errors = sum(issue["severity"] == "error" for issue in issues)
    return {
        "status": "fail" if errors else "pass",
        "metrics": {
            "minimumConsecutiveWords": min_consecutive,
            "sourceWordCount": len(source_tokens),
            "draftWordCount": len(draft_tokens),
            "maximumConsecutiveMatch": max((block.size for block in matcher.get_matching_blocks()), default=0),
            "longMatchCount": len(long_matches),
            "uniqueSentenceMatchCount": len(unique_sentence_matches),
            "allowedPhraseCount": len(allowed),
            "errors": errors,
        },
        "matches": {
            "consecutive": long_matches,
            "uniqueSentences": unique_sentence_matches,
        },
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", type=Path, help="직접 확인한 레퍼런스 원문 txt")
    source_group.add_argument("--source-text", help="직접 확인한 레퍼런스 원문 텍스트")
    draft_group = parser.add_mutually_exclusive_group(required=True)
    draft_group.add_argument("--draft", type=Path, help="검사할 초안 txt 또는 HTML")
    draft_group.add_argument("--input", type=Path, help="--draft와 같은 초안 입력 별칭")
    parser.add_argument("--min-consecutive", type=int, default=7)
    parser.add_argument("--allow-phrase", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source = args.source.read_text(encoding="utf-8") if args.source else args.source_text
        draft_path = args.draft or args.input
        draft = draft_path.read_text(encoding="utf-8")
        result = validate(
            source,
            draft,
            min_consecutive=args.min_consecutive,
            allowed_phrases=args.allow_phrase,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"원문 복사 중복 검증 실패: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"최장 연속 일치: {result['metrics']['maximumConsecutiveMatch']}어절")
        for issue in result["issues"]:
            print(f"[{issue['severity'].upper()}] {issue['code']}: {issue['detail']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
