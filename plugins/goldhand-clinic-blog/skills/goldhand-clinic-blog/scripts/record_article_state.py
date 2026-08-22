#!/usr/bin/env python3
"""Record one Goldhand article and retain the newest three semantic topics."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import sys
import time
from datetime import date
from pathlib import Path


ALLOWED_TYPES = {"정보전달형"}


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


REQUIRED_ENTRY_FIELDS = (
    "title",
    "mainKeyword",
    "ideaReferenceId",
    "ideaReferenceTitle",
    "ideaReferenceUrl",
    "ideaType",
    "titlePatternId",
    "writingMasterId",
    "writingReferenceUrl",
    "type",
    "writtenAt",
)

OPTIONAL_SCALAR_FIELDS = (
    "topicSourceId",
    "topicSourceTitle",
    "topicSourceUrl",
    "topicSourceBlogId",
    "topicSourceRole",
    "topicSourcePublishedAt",
    "semanticTopicId",
    "topicCluster",
    "primarySubjectId",
    "topicIntent",
    "topicIdea",
    "editorialMasterId",
    "editorialReferenceTitle",
    "editorialReferenceUrl",
    "editorialSourceRole",
    "editorialProfileStatus",
    "referenceWritingIntelligenceId",
    "titleMechanismId",
    "introPersuasionDeviceId",
    "closingMechanismId",
)

OPTIONAL_LIST_FIELDS = (
    "topicSourcePostIds",
    "subjectIds",
    "dedupeKeys",
    "coverageQuestions",
    "realMediaIds",
    "realMediaHashes",
    "trustMediaIds",
    "trustMediaHashes",
)


def string_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def clean_entry(entry: dict[str, object]) -> dict[str, object]:
    allowed_fields = set(REQUIRED_ENTRY_FIELDS) | set(OPTIONAL_SCALAR_FIELDS) | set(OPTIONAL_LIST_FIELDS)
    cleaned = {field: value for field, value in entry.items() if field in allowed_fields}
    for field in OPTIONAL_SCALAR_FIELDS:
        value = str(cleaned.get(field, "")).strip()
        if value:
            cleaned[field] = value
        else:
            cleaned.pop(field, None)
    for field in OPTIONAL_LIST_FIELDS:
        values = string_list(cleaned.get(field))
        if values:
            cleaned[field] = values
        else:
            cleaned.pop(field, None)
    return cleaned


def record(state: dict[str, object], entry: dict[str, object]) -> dict[str, object]:
    normalized_entry = clean_entry(entry)
    missing = [field for field in REQUIRED_ENTRY_FIELDS if not str(normalized_entry.get(field, "")).strip()]
    if missing:
        raise ValueError(f"이력 필드가 비어 있습니다: {', '.join(missing)}")
    if normalized_entry["type"] not in ALLOWED_TYPES:
        raise ValueError(f"허용되지 않은 글 유형: {normalized_entry['type']}")
    editorial_status = str(normalized_entry.get("editorialProfileStatus", "")).strip()
    if editorial_status:
        if editorial_status != "ready":
            raise ValueError("편집 원문 감사가 완료되지 않은 글은 최근 이력에 기록할 수 없습니다.")
        required_editorial = (
            "editorialMasterId",
            "editorialReferenceTitle",
            "editorialReferenceUrl",
            "editorialSourceRole",
        )
        missing_editorial = [
            field for field in required_editorial
            if not str(normalized_entry.get(field, "")).strip()
        ]
        if missing_editorial:
            raise ValueError(f"ready 편집 이력 필드가 비어 있습니다: {', '.join(missing_editorial)}")
        if normalized_entry["editorialSourceRole"] not in {
            "title-tone-content-sequence-only",
            "topic-reader-concerns-general-information-sequence-only",
            "editorial-reasoning-content-flow-and-expression-principles",
        }:
            raise ValueError("ready 편집 이력의 source role이 올바르지 않습니다.")
    entries = state.get("entries", [])
    current = (
        [
            item
            for item in entries
            if isinstance(item, dict) and str(item.get("type", "")).strip() in ALLOWED_TYPES
        ]
        if isinstance(entries, list)
        else []
    )
    identity = (
        str(normalized_entry["title"]),
        str(normalized_entry.get("editorialReferenceUrl") or normalized_entry["ideaReferenceUrl"]),
        str(normalized_entry.get("editorialMasterId") or normalized_entry["writingMasterId"]),
    )
    current = [
        item
        for item in current
        if (
            str(item.get("title")),
            str(item.get("editorialReferenceUrl") or item.get("ideaReferenceUrl")),
            str(item.get("editorialMasterId") or item.get("writingMasterId")),
        )
        != identity
    ]
    current.insert(0, normalized_entry)
    return {"schemaVersion": 5, "maxEntries": 3, "entries": current[:3]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--title", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--idea-reference-id", required=True)
    parser.add_argument("--idea-reference-title", required=True)
    parser.add_argument("--idea-reference-url", required=True)
    parser.add_argument("--idea-type", required=True)
    parser.add_argument("--title-pattern-id", required=True)
    parser.add_argument("--writing-master-id", required=True)
    parser.add_argument("--writing-reference-url", required=True)
    parser.add_argument("--type", required=True, dest="article_type")
    parser.add_argument("--written-at", default=date.today().isoformat())
    parser.add_argument("--topic-source-id", default="")
    parser.add_argument("--topic-source-title", default="")
    parser.add_argument("--topic-source-url", default="")
    parser.add_argument("--topic-source-blog-id", default="")
    parser.add_argument("--topic-source-role", default="")
    parser.add_argument("--topic-source-published-at", default="")
    parser.add_argument("--topic-source-post-id", "--topic-source-post-ids", action="append", dest="topic_source_post_ids", default=[])
    parser.add_argument("--semantic-topic-id", default="")
    parser.add_argument("--topic-cluster", default="")
    parser.add_argument("--primary-subject-id", default="")
    parser.add_argument("--subject-id", "--subject-ids", action="append", dest="subject_ids", default=[])
    parser.add_argument("--topic-intent", default="")
    parser.add_argument("--dedupe-key", "--dedupe-keys", action="append", dest="dedupe_keys", default=[])
    parser.add_argument("--topic-idea", default="")
    parser.add_argument("--coverage-question", "--coverage-questions", action="append", dest="coverage_questions", default=[])
    parser.add_argument("--editorial-master-id", default="")
    parser.add_argument("--editorial-reference-title", default="")
    parser.add_argument("--editorial-reference-url", default="")
    parser.add_argument("--editorial-source-role", default="")
    parser.add_argument("--editorial-profile-status", default="")
    parser.add_argument("--reference-writing-intelligence-id", default="")
    parser.add_argument("--title-mechanism-id", default="")
    parser.add_argument("--intro-persuasion-device-id", default="")
    parser.add_argument("--closing-mechanism-id", default="")
    parser.add_argument("--reservation-master-id", default="")
    parser.add_argument("--reservation-run-id", default="")
    parser.add_argument("--reservation-dir", type=Path)
    parser.add_argument("--real-media-id", action="append", dest="real_media_ids", default=[])
    parser.add_argument("--real-media-hash", action="append", dest="real_media_hashes", default=[])
    parser.add_argument("--trust-media-id", action="append", dest="trust_media_ids", default=[])
    parser.add_argument("--trust-media-hash", action="append", dest="trust_media_hashes", default=[])
    return parser.parse_args()


def add_optional(entry: dict[str, object], field: str, value: object) -> None:
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(string_list(item))
        if values:
            entry[field] = values
        return
    normalized = str(value).strip()
    if normalized:
        entry[field] = normalized


def default_reservation_dir(state_path: Path) -> Path:
    override = os.environ.get("GOLDHAND_RESERVATION_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return state_path.parent / "reservations"


def release_reservation(reservation_dir: Path, master_id: str, run_id: str) -> bool:
    path = reservation_dir / f"{master_id}.json"
    if not path.exists():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or str(payload.get("runId", "")) != run_id:
        return False
    path.unlink()
    return True


@contextmanager
def state_write_lock(state_path: Path, *, timeout_seconds: float = 10.0):
    """Serialize concurrent completions so one task cannot erase another."""

    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 30:
                    lock_path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("최근 글 이력 잠금을 10초 안에 확보하지 못했습니다.")
            time.sleep(0.05)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    args = parse_args()
    if args.article_type not in ALLOWED_TYPES:
        print(f"허용되지 않은 글 유형: {args.article_type}", file=sys.stderr)
        return 1
    entry: dict[str, object] = {
        "title": args.title.strip(),
        "mainKeyword": args.keyword.strip(),
        "ideaReferenceId": args.idea_reference_id.strip(),
        "ideaReferenceTitle": args.idea_reference_title.strip(),
        "ideaReferenceUrl": args.idea_reference_url.strip(),
        "ideaType": args.idea_type.strip(),
        "titlePatternId": args.title_pattern_id.strip(),
        "writingMasterId": args.writing_master_id.strip(),
        "writingReferenceUrl": args.writing_reference_url.strip(),
        "type": args.article_type,
        "writtenAt": args.written_at,
    }
    optional_values = {
        "topicSourceId": args.topic_source_id,
        "topicSourceTitle": args.topic_source_title,
        "topicSourceUrl": args.topic_source_url,
        "topicSourceBlogId": args.topic_source_blog_id,
        "topicSourceRole": args.topic_source_role,
        "topicSourcePublishedAt": args.topic_source_published_at,
        "topicSourcePostIds": args.topic_source_post_ids,
        "semanticTopicId": args.semantic_topic_id,
        "topicCluster": args.topic_cluster,
        "primarySubjectId": args.primary_subject_id,
        "subjectIds": args.subject_ids,
        "topicIntent": args.topic_intent,
        "dedupeKeys": args.dedupe_keys,
        "topicIdea": args.topic_idea,
        "coverageQuestions": args.coverage_questions,
        "editorialMasterId": args.editorial_master_id,
        "editorialReferenceTitle": args.editorial_reference_title,
        "editorialReferenceUrl": args.editorial_reference_url,
        "editorialSourceRole": args.editorial_source_role,
        "editorialProfileStatus": args.editorial_profile_status,
        "referenceWritingIntelligenceId": args.reference_writing_intelligence_id,
        "titleMechanismId": args.title_mechanism_id,
        "introPersuasionDeviceId": args.intro_persuasion_device_id,
        "closingMechanismId": args.closing_mechanism_id,
        "realMediaIds": args.real_media_ids,
        "realMediaHashes": args.real_media_hashes,
        "trustMediaIds": args.trust_media_ids,
        "trustMediaHashes": args.trust_media_hashes,
    }
    for field, value in optional_values.items():
        add_optional(entry, field, value)
    if not all(str(entry.get(field, "")).strip() for field in REQUIRED_ENTRY_FIELDS):
        print("이력 필드는 비워 둘 수 없습니다.", file=sys.stderr)
        return 1
    try:
        if bool(args.reservation_master_id) != bool(args.reservation_run_id):
            raise ValueError("예약 해제에는 reservation master ID와 run ID가 모두 필요합니다.")
        with state_write_lock(args.state):
            state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {}
            updated = record(state if isinstance(state, dict) else {}, entry)
            temp_path = args.state.with_name(f"{args.state.name}.{os.getpid()}.tmp")
            temp_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temp_path, args.state)
        if args.reservation_master_id:
            reservation_dir = (args.reservation_dir or default_reservation_dir(args.state)).expanduser().resolve()
            if not release_reservation(
                reservation_dir,
                args.reservation_master_id.strip(),
                args.reservation_run_id.strip(),
            ):
                raise ValueError("완료된 글의 레퍼런스 예약을 해제하지 못했습니다.")
    except (OSError, UnicodeError, json.JSONDecodeError, TimeoutError, ValueError) as exc:
        print(f"이력 저장 실패: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(updated, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
