#!/usr/bin/env python3
"""Validate Beomeo editorial-master assignments and their reuse boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = SKILL_DIR / "assets" / "beomeo-editorial-master-profiles.json"
DEFAULT_TOPIC_LIBRARY = SKILL_DIR / "assets" / "beomeo-topic-idea-library.json"
EXPECTED_SOURCE_BLOG_ID = "beomeo_sm"
EXPECTED_SOURCE_BLOG_URL = "https://blog.naver.com/beomeo_sm"
EXPECTED_SOURCE_ROLE = "title-tone-content-sequence-only"
REQUIRED_ALLOWED_REUSE = {
    "title-device",
    "reader-question-shape",
    "problem-framing",
    "content-sequence",
    "sentence-rhythm",
    "everyday-reader-vocabulary",
}
REQUIRED_BLOCKED_REUSE = {
    "clinic-fact",
    "named-program",
    "case",
    "number",
    "medical-claim",
    "source-sentence",
    "media",
}
REQUIRED_PROFILE_BLOCKS = {
    "clinicFact",
    "namedProgram",
    "case",
    "number",
    "medicalClaim",
    "sourceSentence",
    "media",
}
REQUIRED_BLOCK_FLAGS = {
    "sourceFactsBlocked",
    "sourceProgramsBlocked",
    "sourceCasesBlocked",
    "sourceNumbersBlocked",
    "sourceMedicalClaimsBlocked",
    "sourceSentencesBlocked",
    "sourceMediaBlocked",
}
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", "--library", dest="profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--topic-source-library", type=Path, default=DEFAULT_TOPIC_LIBRARY)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"파일을 찾을 수 없습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 형식이 올바르지 않습니다: {path}:{exc.lineno}:{exc.colno}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"최상위 값은 객체여야 합니다: {path}")
    return value


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def require_string(item: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"비어 있지 않은 문자열이 필요합니다: {path}.{key}")
        return ""
    return value.strip()


def validate_profiles(
    library: dict[str, Any],
    topic_library: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if library.get("schemaVersion") != 1:
        errors.append("schemaVersion은 1이어야 합니다.")
    if library.get("sourceBlogId") != EXPECTED_SOURCE_BLOG_ID:
        errors.append(f"sourceBlogId는 {EXPECTED_SOURCE_BLOG_ID}여야 합니다.")
    if library.get("sourceBlogUrl") != EXPECTED_SOURCE_BLOG_URL:
        errors.append(f"sourceBlogUrl은 {EXPECTED_SOURCE_BLOG_URL}이어야 합니다.")
    if library.get("sourceRole") != EXPECTED_SOURCE_ROLE:
        errors.append(f"sourceRole은 {EXPECTED_SOURCE_ROLE}이어야 합니다.")

    selection_policy = library.get("selectionPolicy")
    if not isinstance(selection_policy, dict):
        errors.append("selectionPolicy 객체가 필요합니다.")
    else:
        for key, expected in {
            "onePrimaryEditorialSourcePerTopicIdea": True,
            "primaryEditorialSourceMustBelongToTopicSourcePostIds": True,
            "fallbackToFirstSourcePost": False,
            "unassignedTopicIdeasRemainWithoutEditorialMaster": True,
            "unassignedTopicIdeasRequireLiveSourceAudit": True,
            "promotionRequiresValidatedProfile": True,
            "emitOneLiveAuditCandidateForUnassignedTopic": True,
            "candidateCannotBecomeMasterBeforeSourceAudit": True,
        }.items():
            if selection_policy.get(key) is not expected:
                errors.append(f"selectionPolicy.{key}는 {str(expected).lower()}여야 합니다.")

    boundary = library.get("reuseBoundary")
    if not isinstance(boundary, dict):
        errors.append("reuseBoundary 객체가 필요합니다.")
    else:
        allowed = set(string_list(boundary.get("mayInform")))
        blocked = set(string_list(boundary.get("mustNeverInform")))
        if not REQUIRED_ALLOWED_REUSE.issubset(allowed):
            errors.append("reuseBoundary.mayInform에 제목·질문·전개·말투의 허용 역할이 모두 필요합니다.")
        if not REQUIRED_BLOCKED_REUSE.issubset(blocked):
            errors.append("reuseBoundary.mustNeverInform에 업체사실·프로그램·사례·수치·의료주장·문장·미디어 금지가 모두 필요합니다.")
        for key in ("medicalInformationRule", "goldhandCompatibilityRule", "antiCopyRule"):
            require_string(boundary, key, "$.reuseBoundary", errors)

    topic_posts = {
        str(post.get("id", "")): post
        for post in topic_library.get("sourcePosts", [])
        if isinstance(post, dict) and str(post.get("id", ""))
    }
    topic_ideas = {
        str(idea.get("id", "")): idea
        for idea in topic_library.get("topicIdeas", [])
        if isinstance(idea, dict) and str(idea.get("id", ""))
    }
    if topic_library.get("sourceBlogId") != EXPECTED_SOURCE_BLOG_ID:
        errors.append("주제 소스 라이브러리의 sourceBlogId가 범어 설명한의원이 아닙니다.")

    assignments = library.get("topicIdeaAssignments")
    candidate_assignments = library.get("liveAuditCandidateAssignments")
    profiles = library.get("profiles")
    if not isinstance(assignments, dict) or not assignments:
        errors.append("topicIdeaAssignments 객체가 비어 있습니다.")
        assignments = {}
    if not isinstance(profiles, dict) or not profiles:
        errors.append("profiles 객체가 비어 있습니다.")
        profiles = {}
    if not isinstance(candidate_assignments, dict):
        errors.append("liveAuditCandidateAssignments 객체가 필요합니다.")
        candidate_assignments = {}

    for topic_id, idea in topic_ideas.items():
        if topic_id in assignments:
            continue
        source_ids = string_list(idea.get("sourcePostIds"))
        candidate_assignment = candidate_assignments.get(topic_id)
        if len(source_ids) <= 1:
            if candidate_assignment is not None:
                errors.append(f"단일 sourcePost 주제에는 별도 live audit 후보 배정이 필요하지 않습니다: {topic_id}")
            continue
        path = f"$.liveAuditCandidateAssignments.{topic_id}"
        if not isinstance(candidate_assignment, dict):
            errors.append(f"복수 sourcePost 주제에는 명시적인 live audit 후보 배정이 필요합니다: {topic_id}")
            continue
        candidate_id = require_string(candidate_assignment, "primaryEditorialCandidate", path, errors)
        require_string(candidate_assignment, "selectionReason", path, errors)
        if candidate_id and candidate_id not in source_ids:
            errors.append(f"primaryEditorialCandidate는 해당 topic idea의 sourcePostIds 중 한 편이어야 합니다: {topic_id} -> {candidate_id}")

    assigned_masters: dict[str, str] = {}
    for topic_id, assignment in assignments.items():
        path = f"$.topicIdeaAssignments.{topic_id}"
        if topic_id not in topic_ideas:
            errors.append(f"존재하지 않는 topic idea 배정입니다: {topic_id}")
            continue
        if not isinstance(assignment, dict):
            errors.append(f"객체가 필요합니다: {path}")
            continue
        primary = require_string(assignment, "primaryEditorialSource", path, errors)
        require_string(assignment, "selectionReason", path, errors)
        if not primary:
            continue
        if primary not in string_list(topic_ideas[topic_id].get("sourcePostIds")):
            errors.append(f"primaryEditorialSource는 해당 topic idea의 sourcePostIds 중 한 편이어야 합니다: {topic_id} -> {primary}")
        if primary not in profiles:
            errors.append(f"profiles에 없는 primaryEditorialSource입니다: {primary}")
        assigned_masters[topic_id] = primary

    for master_id, profile in profiles.items():
        path = f"$.profiles.{master_id}"
        if not isinstance(profile, dict):
            errors.append(f"객체가 필요합니다: {path}")
            continue
        if require_string(profile, "id", path, errors) != master_id:
            errors.append(f"프로필 키와 id가 다릅니다: {master_id}")
        source_post_id = require_string(profile, "sourcePostId", path, errors)
        if require_string(profile, "sourceBlogId", path, errors) != EXPECTED_SOURCE_BLOG_ID:
            errors.append(f"프로필 sourceBlogId가 올바르지 않습니다: {master_id}")
        source_title = require_string(profile, "sourceTitle", path, errors)
        source_url = require_string(profile, "sourceUrl", path, errors)
        if require_string(profile, "sourceRole", path, errors) != EXPECTED_SOURCE_ROLE:
            errors.append(f"프로필 sourceRole이 올바르지 않습니다: {master_id}")
        if profile.get("sourceAuditStatus") != "body-reviewed":
            errors.append(f"sourceAuditStatus=body-reviewed가 필요합니다: {master_id}")
        if profile.get("autoEligible") is not True:
            errors.append(f"편집 마스터는 autoEligible=true여야 합니다: {master_id}")

        source_post = topic_posts.get(master_id)
        if source_post is None:
            errors.append(f"주제 소스 라이브러리에 없는 편집 마스터입니다: {master_id}")
        else:
            for key, actual, expected in (
                ("sourcePostId", source_post_id, str(source_post.get("sourcePostId", ""))),
                ("sourceTitle", source_title, str(source_post.get("sourceTitle", ""))),
                ("sourceUrl", source_url, str(source_post.get("sourceUrl", ""))),
            ):
                if actual != expected:
                    errors.append(f"주제 소스와 {key}가 다릅니다: {master_id}")

        applies_to = string_list(profile.get("appliesToTopicIdeaIds"))
        if not applies_to:
            errors.append(f"appliesToTopicIdeaIds가 비어 있습니다: {master_id}")
        for topic_id in applies_to:
            if topic_id not in topic_ideas:
                errors.append(f"존재하지 않는 appliesToTopicIdeaIds 참조입니다: {master_id} -> {topic_id}")
            elif master_id not in string_list(topic_ideas[topic_id].get("sourcePostIds")):
                errors.append(f"편집 마스터가 주제의 sourcePostIds에 없습니다: {master_id} -> {topic_id}")
            if assigned_masters.get(topic_id) != master_id:
                errors.append(f"프로필 적용 주제가 이 마스터를 primary로 배정하지 않았습니다: {master_id} -> {topic_id}")

        for contract_key in ("titleContract", "toneContract", "contentSequenceContract"):
            if not isinstance(profile.get(contract_key), dict) or not profile[contract_key]:
                errors.append(f"비어 있지 않은 객체가 필요합니다: {path}.{contract_key}")
        beats = string_list(profile.get("requiredContentBeats"))
        if not beats or len(beats) != len(set(beats)):
            errors.append(f"requiredContentBeats는 중복 없는 문자열 배열이어야 합니다: {master_id}")
        guidance = profile.get("contentBeatGuidance")
        if not isinstance(guidance, dict) or set(guidance) != set(beats):
            errors.append(f"contentBeatGuidance는 requiredContentBeats와 정확히 대응해야 합니다: {master_id}")
        elif any(not isinstance(guidance[beat], str) or not guidance[beat].strip() for beat in beats):
            errors.append(f"contentBeatGuidance 설명은 비어 있지 않아야 합니다: {master_id}")

        blocked_reuse = set(string_list(profile.get("blockedReuse")))
        if not REQUIRED_PROFILE_BLOCKS.issubset(blocked_reuse):
            errors.append(f"blockedReuse에 모든 업체·내용·문장·미디어 금지가 필요합니다: {master_id}")
        for flag in REQUIRED_BLOCK_FLAGS:
            if profile.get(flag) is not True:
                errors.append(f"{flag}=true가 필요합니다: {master_id}")

    return errors


def validate_library(library: dict[str, Any], topic_library: dict[str, Any]) -> list[str]:
    """Compatibility alias for other package validators."""
    return validate_profiles(library, topic_library)


def main() -> int:
    args = parse_args()
    try:
        library = load_json(args.profiles)
        topic_library = load_json(args.topic_source_library)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate_profiles(library, topic_library)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(
            "Beomeo editorial master profiles are valid: "
            f"{len(library['profiles'])} profile, "
            f"{len(library['topicIdeaAssignments'])} topic assignment."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
