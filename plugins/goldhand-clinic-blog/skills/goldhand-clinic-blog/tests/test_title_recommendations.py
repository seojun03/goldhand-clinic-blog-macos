from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "validate_title_recommendations.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "goldhand_title_recommendation_tests",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"제목 추천 검증기를 불러올 수 없습니다: {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


class TitleRecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (SKILL_DIR / "assets" / "title-recommendation-contract.json").read_text(
                encoding="utf-8"
            )
        )
        cls.evidence = (SKILL_DIR / "references" / "clinic-facts.md").read_text(
            encoding="utf-8"
        )
        cls.writing_intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(
                encoding="utf-8"
            )
        )

    def valid_payload(self) -> dict[str, object]:
        authority = "verified-authority-plus-two-urgent-answers"
        direct = "urgent-questions-with-direct-answer"
        return {
            "workflowStage": "master-aware",
            "topic": "수면을 방해하는 생활습관",
            "mainKeyword": "동천동 한의원",
            "referenceMasterId": "INFO03",
            "candidates": [
                {
                    "title": "동천동 한의원 11년차가 경고하는 최악의 수면습관 3가지",
                    "titleMechanismId": authority,
                    "readerStake": "loss-prevention",
                    "answerCount": 3,
                },
                {
                    "title": "동천동 한의원 놓치면 손해인 숙면 원칙 2가지",
                    "titleMechanismId": direct,
                    "readerStake": "loss-prevention",
                    "answerCount": 2,
                },
                {
                    "title": "동천동 한의원 반드시 알아야 할 수면 신호 3가지",
                    "titleMechanismId": direct,
                    "readerStake": "benefit",
                    "answerCount": 3,
                },
                {
                    "title": "동천동 한의원 잠을 망치는 최악의 야식 1가지",
                    "titleMechanismId": direct,
                    "readerStake": "loss-prevention",
                    "answerCount": 1,
                },
                {
                    "title": "동천동 한의원 11년차가 경고하는 불면 습관",
                    "titleMechanismId": authority,
                    "readerStake": "loss-prevention",
                },
            ],
        }

    def validate(self, payload: dict[str, object]) -> dict[str, object]:
        return VALIDATOR.validate_recommendations(
            payload,
            contract=self.contract,
            evidence=self.evidence,
            writing_intelligence=self.writing_intelligence,
        )

    def fast_payload(self) -> dict[str, object]:
        payload = self.valid_payload()
        payload["workflowStage"] = "title-first"
        payload.pop("referenceMasterId")
        for candidate in payload["candidates"]:
            candidate.pop("titleMechanismId")
        return payload

    def test_five_strong_numeric_topic_titles_pass(self) -> None:
        result = self.validate(self.valid_payload())
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["candidateCount"], 5)
        self.assertEqual(result["metrics"]["uniqueTitleCount"], 5)
        self.assertGreaterEqual(result["metrics"]["careerCandidateCount"], 1)
        self.assertGreaterEqual(result["metrics"]["numberedCandidateCount"], 3)

    def test_title_first_passes_without_research_or_reference_master(self) -> None:
        result = self.validate(self.fast_payload())
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["workflowStage"], "title-first")
        self.assertIs(result["metrics"]["researchDeferred"], True)
        self.assertIs(result["metrics"]["referenceMasterDeferred"], True)

    def test_contract_defaults_missing_workflow_stage_to_title_first(self) -> None:
        payload = self.fast_payload()
        payload.pop("workflowStage")
        result = self.validate(payload)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["workflowStage"], "title-first")

    def test_title_first_rejects_preselected_reference_metadata(self) -> None:
        payload = self.fast_payload()
        payload["referenceMasterId"] = "INFO03"
        payload["candidates"][0]["titleMechanismId"] = "urgent-questions-with-direct-answer"
        result = self.validate(payload)
        issue_codes = {item["code"] for item in result["issues"]}
        self.assertEqual(result["status"], "fail")
        self.assertIn("title-first-reference-master-preselected", issue_codes)
        self.assertIn("title-first-mechanism-preselected", issue_codes)

    def test_title_first_cli_does_not_load_writing_intelligence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload_path = Path(temporary) / "title-recommendations.json"
            payload_path.write_text(
                json.dumps(self.fast_payload(), ensure_ascii=False),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--input",
                    str(payload_path),
                    "--evidence",
                    str(Path(temporary) / "must-not-be-read-evidence.md"),
                    "--writing-intelligence",
                    str(Path(temporary) / "must-not-be-read.json"),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["metrics"]["workflowStage"], "title-first")

    def test_candidate_count_and_duplicate_titles_fail(self) -> None:
        payload = self.valid_payload()
        candidates = payload["candidates"]
        self.assertIsInstance(candidates, list)
        candidates[4] = dict(candidates[0])
        result = self.validate(payload)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertEqual(result["status"], "fail")
        self.assertIn("duplicate-title", codes)

        payload = self.valid_payload()
        payload["candidates"] = payload["candidates"][:4]
        result = self.validate(payload)
        self.assertIn("candidate-count", {issue["code"] for issue in result["issues"]})

    def test_weak_wording_or_missing_numeric_hook_fails(self) -> None:
        payload = self.valid_payload()
        payload["candidates"][0] = {
            "title": "동천동 한의원 나쁜 수면 습관",
            "titleMechanismId": "urgent-questions-with-direct-answer",
            "readerStake": "loss-prevention",
        }
        result = self.validate(payload)
        codes = {
            issue["code"]
            for issue in result["issues"]
            if issue.get("candidateIndex") == 1
        }
        self.assertIn("strong-wording-missing", codes)
        self.assertIn("weak-wording", codes)
        self.assertIn("numeric-hook-missing", codes)

    def test_core_title_rules_block_nonprefix_and_over_30_characters(self) -> None:
        payload = self.valid_payload()
        payload["candidates"][0]["title"] = (
            "수면습관 동천동 한의원 11년차가 경고하는 최악의 습관 3가지"
        )
        result = self.validate(payload)
        candidate_codes = {
            issue["code"]
            for issue in result["candidateResults"][0]["validation"]["issues"]
        }
        self.assertIn("title-keyword-prefix", candidate_codes)

        payload = self.valid_payload()
        payload["candidates"][0]["title"] = (
            "동천동 한의원 11년차가 경고하는 최악의 수면습관과 야간생활과 회복방해요인 3가지"
        )
        result = self.validate(payload)
        candidate_codes = {
            issue["code"]
            for issue in result["candidateResults"][0]["validation"]["issues"]
        }
        self.assertIn("title-too-long", candidate_codes)


if __name__ == "__main__":
    unittest.main()
