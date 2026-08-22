#!/usr/bin/env python3
"""Select and optionally reserve one reviewed Wipark editorial reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BRIEFS = SKILL_DIR / "assets" / "wipark-content-briefs.json"
DEFAULT_PROFILES = SKILL_DIR / "assets" / "reference-master-profiles.json"
DEFAULT_INTELLIGENCE = SKILL_DIR / "assets" / "reference-writing-intelligence.json"
VOICE_PROFILE_ID = "goldhand-official-voice-v1"
VOICE_PROTOCOL = "natural-speech-rewrite-protocol-v1"
FINAL_VOICE_REVIEW_ID = "writing-voice-final-rehear-v1"
SOURCE_ROLE = "editorial-reasoning-content-flow-and-expression-principles"


def content_atoms(brief: dict[str, Any], master_id: str) -> list[dict[str, Any]]:
    atoms = brief.get("orderedContentAtoms")
    if not isinstance(atoms, list) or not atoms:
        raise ValueError(f"{master_id}에 orderedContentAtoms가 없습니다.")
    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, atom in enumerate(atoms, start=1):
        if not isinstance(atom, dict):
            raise ValueError(f"{master_id} orderedContentAtoms[{index}]는 객체여야 합니다.")
        atom_id = str(atom.get("id", "")).strip()
        role = str(atom.get("role", "")).strip()
        observables = atom.get("observables")
        meaning = atom.get("meaning")
        if not atom_id or atom_id in seen_ids:
            raise ValueError(f"{master_id} 내용 원자 ID가 비었거나 중복입니다: {atom_id}")
        if not role:
            raise ValueError(f"{atom_id}에 role이 없습니다.")
        for key, values in (("observables", observables), ("meaning", meaning)):
            if (
                not isinstance(values, list)
                or not values
                or any(not isinstance(value, str) or not value.strip() for value in values)
            ):
                raise ValueError(f"{atom_id}.{key}는 비어 있지 않은 문자열 배열이어야 합니다.")
            if any(re.search(r"(?:습니다|합니다|입니다|됩니다|다)\s*[.!?]?$", value.strip()) for value in values):
                raise ValueError(f"{atom_id}.{key}에는 완성 문장을 넣지 않습니다: {values}")
        seen_ids.add(atom_id)
        validated.append(
            {
                "id": atom_id,
                "role": role,
                "observables": [str(value).strip() for value in observables],
                "meaning": [str(value).strip() for value in meaning],
            }
        )
    return validated


def default_state_path() -> Path:
    override = os.environ.get("GOLDHAND_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    return root / "state" / "goldhand-clinic-blog" / "recent-articles.json"


def default_reservation_dir(state_path: Path | None = None) -> Path:
    override = os.environ.get("GOLDHAND_RESERVATION_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    state = state_path or default_state_path()
    return state.parent / "reservations"


def tokens(value: str) -> set[str]:
    stop = {"광주", "한의원", "금손한의원", "추천", "정보", "관련", "가지"}
    return {
        item
        for item in re.findall(r"[0-9A-Za-z가-힣]{2,}", value.lower())
        if item not in stop
    }


def recent_master_ids(state: dict[str, Any]) -> set[str]:
    entries = state.get("entries", [])
    if not isinstance(entries, list):
        return set()
    result: set[str] = set()
    for item in entries[:3]:
        if not isinstance(item, dict):
            continue
        for key in ("editorialMasterId", "writingMasterId", "topicSourceId"):
            value = str(item.get(key, ""))
            match = re.search(r"(?:INFO\d+|WP\d{12})", value)
            if not match:
                continue
            found = match.group(0)
            result.add(found.replace("WP", "INFO", 1) if found.startswith("WP") else found)
    return result


def load_intelligence(path: Path = DEFAULT_INTELLIGENCE) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("profiles"), dict):
        raise ValueError("레퍼런스 편집 판단 자산을 읽지 못했습니다.")
    return value


def relevant_lessons(intelligence: dict[str, Any], master_id: str) -> list[dict[str, Any]]:
    lessons = intelligence.get("approvedLessons", [])
    if not isinstance(lessons, list):
        return []
    return [
        lesson
        for lesson in lessons
        if isinstance(lesson, dict) and master_id in lesson.get("observedIn", [])
    ]


def select(
    keyword: str,
    topic: str,
    briefs: dict[str, Any],
    profiles: dict[str, Any],
    state: dict[str, Any],
    *,
    count: int = 1,
    seed: str = "",
    intelligence: dict[str, Any] | None = None,
    excluded_master_ids: set[str] | None = None,
    preferred_master_id: str = "",
) -> list[dict[str, Any]]:
    intelligence = intelligence or load_intelligence()
    learning_profiles = intelligence.get("profiles", {})
    if not isinstance(learning_profiles, dict):
        raise ValueError("레퍼런스 편집 판단 프로필이 없습니다.")
    query_tokens = tokens(f"{keyword} {topic}")
    recent = recent_master_ids(state)
    excluded = excluded_master_ids or set()
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for master_id, brief in briefs.get("briefs", {}).items():
        if preferred_master_id and master_id != preferred_master_id:
            continue
        if (
            master_id in recent
            or master_id in excluded
            or master_id not in profiles.get("profiles", {})
            or master_id not in learning_profiles
        ):
            continue
        profile = profiles["profiles"][master_id]
        learning_profile = learning_profiles[master_id]
        haystack = " ".join(
            [
                str(brief.get("topic", "")),
                *[str(value) for value in brief.get("readerConcerns", [])],
                *[str(value) for value in brief.get("orderedGeneralInformation", [])],
                *[str(value) for value in profile.get("selectionTags", [])],
                str(learning_profile.get("readerState", "")),
                str(learning_profile.get("openingMechanism", {}).get("topicPayoff", "")),
            ]
        )
        overlap = len(query_tokens & tokens(haystack))
        broad_bonus = 2 if not query_tokens and master_id == "INFO01" else 0
        stable = int(hashlib.sha256(f"{seed}|{keyword}|{topic}|{master_id}".encode()).hexdigest(), 16)
        candidates.append((overlap + broad_bonus, -stable, master_id, brief))
    candidates.sort(reverse=True)

    selected: list[dict[str, Any]] = []
    global_contract = intelligence.get("globalDecisionContract", {})
    for _, _, master_id, brief in candidates[: max(0, count)]:
        profile = profiles["profiles"][master_id]
        learning_profile = learning_profiles[master_id]
        atoms = content_atoms(brief, master_id)
        post_id = re.search(r"/(\d{12})$", str(brief["sourceUrl"]))
        selected.append(
            {
                "masterId": master_id,
                "editorialMasterId": f"WP{post_id.group(1)}" if post_id else "",
                "sourceTitle": profile["sourceTitle"],
                "sourceUrl": brief["sourceUrl"],
                "sourceBlogId": "wi-parkclinic",
                "sourceRole": SOURCE_ROLE,
                "topic": brief["topic"],
                "readerConcerns": brief["readerConcerns"],
                "orderedContentAtoms": atoms,
                "contentAtomIds": [atom["id"] for atom in atoms],
                "blockedFromSource": brief["blockedFromSource"],
                "sourceProseWithheld": True,
                "contentAtomCoverageRequired": True,
                "sourceSentenceImitationBlocked": True,
                "sourceFactsBlocked": True,
                "referenceExpressionLearningEnabled": True,
                "referenceEditorialReasoningEnabled": True,
                "goldhandFactReplacementRequired": True,
                "adaptationDecisionRequired": True,
                "referenceWritingIntelligenceId": intelligence.get("id", ""),
                "referenceWritingIntelligence": learning_profile,
                "approvedWritingLessons": relevant_lessons(intelligence, master_id),
                "adaptationDecisionFields": global_contract.get("decisionRecordFields", []),
                "maximumConsecutiveSourceWords": global_contract.get("maximumConsecutiveSourceWords", 6),
                "voiceProfileId": VOICE_PROFILE_ID,
                "voiceProtocolId": VOICE_PROTOCOL,
                "voiceAuthority": "goldhand7582_ official 74-post voice corpus",
                "voiceFunction": "naturalize-the-adapted-reference-reasoning-without-erasing-it",
                "finalVoiceReviewRequired": True,
                "finalVoiceReviewerSkill": "writing-voice",
                "finalVoiceReviewContractId": FINAL_VOICE_REVIEW_ID,
                "finalVoiceReviewStage": "after-complete-visible-prose-and-seo-before-production-assembly",
                "finalVoiceReviewScope": "sentence-expression-only-no-content-or-structure-changes",
                "designSystemId": "goldhand-naver-native-v4",
            }
        )
    return selected


def reservation_path(reservation_dir: Path, master_id: str) -> Path:
    if not re.fullmatch(r"INFO\d+", master_id):
        raise ValueError(f"예약할 수 없는 마스터 ID입니다: {master_id}")
    return reservation_dir / f"{master_id}.json"


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def cleanup_stale_reservations(reservation_dir: Path, *, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    removed: list[str] = []
    if not reservation_dir.exists():
        return removed
    for path in reservation_dir.glob("INFO*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            expires_at = parse_timestamp(payload.get("expiresAt")) if isinstance(payload, dict) else None
            if expires_at is not None and expires_at > now:
                continue
            path.unlink()
            removed.append(path.stem)
        except (OSError, UnicodeError, json.JSONDecodeError):
            try:
                path.unlink()
                removed.append(path.stem)
            except OSError:
                continue
    return removed


def active_reserved_master_ids(reservation_dir: Path) -> set[str]:
    cleanup_stale_reservations(reservation_dir)
    if not reservation_dir.exists():
        return set()
    return {path.stem for path in reservation_dir.glob("INFO*.json") if re.fullmatch(r"INFO\d+", path.stem)}


def reserve_master(
    reservation_dir: Path,
    master_id: str,
    run_id: str,
    *,
    keyword: str,
    topic: str,
    ttl_minutes: int = 120,
) -> dict[str, Any] | None:
    reservation_dir.mkdir(parents=True, exist_ok=True)
    path = reservation_path(reservation_dir, master_id)
    now = datetime.now(timezone.utc)
    payload = {
        "schemaVersion": 1,
        "masterId": master_id,
        "runId": run_id,
        "keyword": keyword,
        "topic": topic,
        "reservedAt": now.isoformat(),
        "expiresAt": (now + timedelta(minutes=max(5, ttl_minutes))).isoformat(),
        "releaseRequired": True,
    }
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return payload


def release_reservation(reservation_dir: Path, master_id: str, run_id: str) -> bool:
    path = reservation_path(reservation_dir, master_id)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or str(payload.get("runId", "")) != run_id:
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyword", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--seed", default="")
    parser.add_argument("--preferred-master-id", default="")
    parser.add_argument("--briefs", type=Path, default=DEFAULT_BRIEFS)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--intelligence", type=Path, default=DEFAULT_INTELLIGENCE)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--reservation-dir", type=Path)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--reservation-ttl-minutes", type=int, default=120)
    parser.add_argument("--release-master-id", default="")
    parser.add_argument("--release-run-id", default="")
    reservation_group = parser.add_mutually_exclusive_group()
    reservation_group.add_argument("--reserve", dest="reserve", action="store_true")
    reservation_group.add_argument("--no-reserve", dest="reserve", action="store_false")
    parser.set_defaults(reserve=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reservation_dir = (args.reservation_dir or default_reservation_dir(args.state)).expanduser().resolve()
    if args.release_master_id or args.release_run_id:
        if not args.release_master_id or not args.release_run_id:
            print("예약 해제에는 --release-master-id와 --release-run-id가 모두 필요합니다.", file=sys.stderr)
            return 2
        released = release_reservation(reservation_dir, args.release_master_id, args.release_run_id)
        print(json.dumps({"status": "released" if released else "not-released"}, ensure_ascii=False, indent=2))
        return 0 if released else 1
    if not args.keyword.strip():
        print("메인키워드를 입력해 주세요.", file=sys.stderr)
        return 2

    try:
        briefs = json.loads(args.briefs.read_text(encoding="utf-8"))
        profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
        intelligence = load_intelligence(args.intelligence)
        state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {"entries": []}
        requested = max(1, min(args.count, 3))
        if args.reserve:
            active = active_reserved_master_ids(reservation_dir)
            candidates = select(
                args.keyword,
                args.topic,
                briefs,
                profiles,
                state,
                count=len(profiles.get("profiles", {})),
                seed=args.seed,
                intelligence=intelligence,
                excluded_master_ids=active,
                preferred_master_id=args.preferred_master_id.strip(),
            )
            run_id = args.run_id.strip() or str(uuid.uuid4())
            results: list[dict[str, Any]] = []
            for candidate in candidates:
                reservation = reserve_master(
                    reservation_dir,
                    candidate["masterId"],
                    run_id,
                    keyword=args.keyword.strip(),
                    topic=args.topic.strip(),
                    ttl_minutes=args.reservation_ttl_minutes,
                )
                if reservation is None:
                    continue
                candidate["reservation"] = reservation
                results.append(candidate)
                if len(results) >= requested:
                    break
        else:
            results = select(
                args.keyword,
                args.topic,
                briefs,
                profiles,
                state,
                count=requested,
                seed=args.seed,
                intelligence=intelligence,
                preferred_master_id=args.preferred_master_id.strip(),
            )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"레퍼런스 선택 실패: {exc}", file=sys.stderr)
        return 2
    if not results:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "최근 3개 또는 다른 진행 중 작업과 겹치지 않는 검토 완료 정보글이 없습니다.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(results[0] if len(results) == 1 else results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
