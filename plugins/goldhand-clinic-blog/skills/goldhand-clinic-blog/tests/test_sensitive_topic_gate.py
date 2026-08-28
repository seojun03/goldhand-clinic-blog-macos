from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SELECTOR_PATH = SKILL_DIR / "scripts" / "select_wipark_content_reference.py"


def load_selector():
    spec = importlib.util.spec_from_file_location("goldhand_sensitive_selector", SELECTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("민감 주제 선택기를 불러오지 못했습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECTOR = load_selector()


class SensitiveTopicGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.briefs = json.loads(
            (SKILL_DIR / "assets" / "wipark-content-briefs.json").read_text(encoding="utf-8")
        )
        cls.profiles = json.loads(
            (SKILL_DIR / "assets" / "reference-master-profiles.json").read_text(encoding="utf-8")
        )
        cls.intelligence = json.loads(
            (SKILL_DIR / "assets" / "reference-writing-intelligence.json").read_text(encoding="utf-8")
        )

    def select(
        self,
        keyword: str,
        topic: str = "",
        *,
        count: int = 20,
        preferred_master_id: str = "",
        allow_sensitive_manual: bool = False,
        excluded_master_ids: set[str] | None = None,
    ) -> list[dict[str, object]]:
        return SELECTOR.select(
            keyword,
            topic,
            self.briefs,
            self.profiles,
            {"entries": []},
            count=count,
            seed="sensitive-topic-gate-test",
            intelligence=self.intelligence,
            excluded_master_ids=excluded_master_ids,
            preferred_master_id=preferred_master_id,
            allow_sensitive_manual=allow_sensitive_manual,
        )

    def test_generated_assets_keep_eleven_reviewed_but_only_nine_automatic(self) -> None:
        sensitive_ids = {"INFO04", "INFO11"}
        self.assertEqual(len(self.profiles["allowedMasterIds"]), 11)
        self.assertEqual(len(self.profiles["automaticMasterIds"]), 9)
        self.assertEqual(set(self.profiles["sensitiveTopicMasterIds"]), sensitive_ids)
        self.assertTrue(sensitive_ids.isdisjoint(self.profiles["automaticMasterIds"]))
        for master_id in sensitive_ids:
            profile = self.profiles["profiles"][master_id]
            self.assertIs(profile["autoEligible"], False)
            self.assertIs(profile["sensitiveTopicPolicy"]["automaticSelectionBlocked"], True)
            self.assertIs(profile["sensitiveTopicPolicy"]["explicitRequestRequired"], True)

        topic_library = json.loads(
            (SKILL_DIR / "assets" / "topic-idea-library.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(topic_library["allowedMasterIds"]), 11)
        self.assertEqual(len(topic_library["automaticMasterIds"]), 9)
        self.assertEqual(set(topic_library["sensitiveTopicMasterIds"]), sensitive_ids)
        for master_id in sensitive_ids:
            self.assertIs(topic_library["writingMasterRegistry"][master_id]["autoEligible"], False)

    def test_broad_and_nonmatching_queries_never_return_sensitive_masters(self) -> None:
        sensitive_ids = {"INFO04", "INFO11"}
        queries = (
            ("동천동 한의원", ""),
            ("금손 한의원", ""),
            ("광주 통증 한의원", ""),
            ("광주 잘하는 곳 한의원", ""),
            ("정신건강 상담", ""),
            ("심리상담", ""),
            ("광주 한의원", "생활 관리"),
        )
        for keyword, topic in queries:
            with self.subTest(keyword=keyword, topic=topic):
                selected_ids = {item["masterId"] for item in self.select(keyword, topic)}
                self.assertTrue(sensitive_ids.isdisjoint(selected_ids), selected_ids)

    def test_sensitive_masters_are_not_used_as_fallback(self) -> None:
        automatic_ids = set(self.profiles["automaticMasterIds"])
        self.assertEqual(
            self.select("광주 한의원 추천", excluded_master_ids=automatic_ids),
            [],
        )

    def test_explicit_trauma_terms_select_info11(self) -> None:
        for keyword, topic in (
            ("광주 트라우마치료", ""),
            ("광주 한의원", "외상 후 스트레스 회복"),
            ("광주 한의원", "PTSD 관리"),
        ):
            with self.subTest(keyword=keyword, topic=topic):
                selected = self.select(keyword, topic, count=1)[0]
                self.assertEqual(selected["masterId"], "INFO11")
                self.assertEqual(selected["sensitiveSelectionMode"], "explicit-request")
                self.assertIs(selected["automaticSelectionEligible"], False)

    def test_explicit_panic_or_insomnia_selects_info04(self) -> None:
        for keyword, topic in (
            ("광주 공황장애 한의원", ""),
            ("광주 한의원", "공황 발작 관리"),
            ("광주 한의원", "불면"),
            ("광주 한의원", "불면증"),
            ("광주 한의원", "불면과 불안이 함께 있는 경우"),
            ("광주 한의원", "정신건강 상담이 필요한 불면증"),
            ("광주 한의원", "우울감과 불면"),
        ):
            with self.subTest(keyword=keyword, topic=topic):
                selected = self.select(keyword, topic, count=1)[0]
                self.assertEqual(selected["masterId"], "INFO04")
                self.assertEqual(selected["sensitiveSelectionMode"], "explicit-request")
                self.assertIs(selected["automaticSelectionEligible"], False)

    def test_explicit_insomnia_is_not_displaced_by_recent_master_rotation(self) -> None:
        selected = SELECTOR.select(
            "동천동 한의원",
            "불면증",
            self.briefs,
            self.profiles,
            {"entries": [{"editorialMasterId": "INFO04"}]},
            count=1,
            seed="recent-sensitive-master-test",
            intelligence=self.intelligence,
        )[0]
        self.assertEqual(selected["masterId"], "INFO04")
        self.assertEqual(selected["sensitiveSelectionMode"], "explicit-request")

    def test_menopausal_insomnia_does_not_unlock_info04(self) -> None:
        for topic in (
            "갱년기 불면",
            "폐경 후 불면과 우울감",
            "완경 이후 불면과 불안",
            "안면홍조 불면 심리 상담",
        ):
            with self.subTest(topic=topic):
                selected_ids = {item["masterId"] for item in self.select("광주 한의원", topic)}
                self.assertNotIn("INFO04", selected_ids)

    def test_preferred_sensitive_id_does_not_bypass_explicit_request_gate(self) -> None:
        self.assertEqual(
            self.select("광주 한의원", preferred_master_id="INFO11"),
            [],
        )
        self.assertEqual(
            self.select("정신건강 상담", preferred_master_id="INFO04"),
            [],
        )
        selected = self.select(
            "광주 트라우마치료",
            preferred_master_id="INFO11",
            count=1,
        )[0]
        self.assertEqual(selected["masterId"], "INFO11")
        self.assertEqual(selected["sensitiveSelectionMode"], "explicit-request")

    def test_manual_override_requires_exact_preferred_sensitive_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "preferred-master-id"):
            self.select("광주 한의원", allow_sensitive_manual=True)
        with self.assertRaisesRegex(ValueError, "preferred-master-id"):
            self.select(
                "광주 한의원",
                preferred_master_id="INFO01",
                allow_sensitive_manual=True,
            )

        for master_id, topic in (("INFO04", "갱년기 불면"), ("INFO11", "일반 건강 정보")):
            with self.subTest(master_id=master_id):
                selected = self.select(
                    "광주 한의원",
                    topic,
                    preferred_master_id=master_id,
                    allow_sensitive_manual=True,
                    count=1,
                )[0]
                self.assertEqual(selected["masterId"], master_id)
                self.assertEqual(selected["sensitiveSelectionMode"], "manual-override")

    def test_cli_manual_override_is_wired_without_reservation(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SELECTOR_PATH),
                "--keyword",
                "광주 한의원",
                "--topic",
                "일반 건강 정보",
                "--preferred-master-id",
                "INFO11",
                "--allow-sensitive-manual",
                "--no-reserve",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["masterId"], "INFO11")
        self.assertEqual(payload["sensitiveSelectionMode"], "manual-override")


if __name__ == "__main__":
    unittest.main()
