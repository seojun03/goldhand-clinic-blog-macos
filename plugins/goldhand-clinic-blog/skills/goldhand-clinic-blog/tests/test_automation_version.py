from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = SKILL_DIR.parents[1]
REFRESH_PATH = PLUGIN_ROOT / "scripts" / "refresh_plugin.py"


def load_refresh_module():
    spec = importlib.util.spec_from_file_location(
        "goldhand_refresh_plugin_version_tests",
        REFRESH_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"새로고침 모듈을 불러올 수 없습니다: {REFRESH_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REFRESH = load_refresh_module()


class AutomationVersionTests(unittest.TestCase):
    def make_plugin(self, root: Path) -> tuple[Path, Path, Path]:
        manifest = root / ".codex-plugin" / "plugin.json"
        skill = root / "skills" / "goldhand-clinic-blog" / "SKILL.md"
        state = (
            root
            / "skills"
            / "goldhand-clinic-blog"
            / "assets"
            / "automation-version.json"
        )
        manifest.parent.mkdir(parents=True)
        skill.parent.mkdir(parents=True)
        state.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "name": "goldhand-clinic-blog",
                    "version": "1.0.0+codex.20260827000000",
                    "description": "test",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        skill.write_text(
            "# 금손한의원 블로그 자동화\n\n"
            "## 시작 브리핑과 자동화 버전\n\n"
            "- 현재 자동화 버전: `1.0`\n"
            "- 현재 버전 브리핑: 테스트 브리핑\n",
            encoding="utf-8",
        )
        state.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "automationVersion": "1.0",
                    "sourceFingerprint": "",
                    "packageVersion": "",
                    "updatedAt": "",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest, skill, state

    def test_initial_baseline_is_v1_0_without_an_extra_bump(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "plugin"
            manifest, skill, state = self.make_plugin(root)
            result = REFRESH.sync_automation_version(
                root,
                now="2026-08-27T00:00:00+00:00",
            )
            self.assertTrue(result["initialized"])
            self.assertFalse(result["contentChanged"])
            self.assertTrue(result["needsCachebuster"])
            self.assertEqual(result["currentVersion"], "1.0")
            self.assertIn("현재 자동화 버전: `1.0`", skill.read_text(encoding="utf-8"))
            self.assertTrue(
                json.loads(manifest.read_text(encoding="utf-8"))["version"].startswith(
                    "1.0.0+codex."
                )
            )
            self.assertTrue(
                json.loads(state.read_text(encoding="utf-8"))["sourceFingerprint"]
            )

    def test_crlf_skill_initializes_with_the_same_managed_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "plugin"
            manifest, skill, state = self.make_plugin(root)
            skill.write_bytes(
                skill.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8")
            )

            result = REFRESH.sync_automation_version(
                root,
                now="2026-08-27T00:00:00+00:00",
            )

            self.assertTrue(result["initialized"])
            self.assertFalse(result["contentChanged"])
            self.assertEqual(result["currentVersion"], "1.0")
            self.assertTrue(
                json.loads(state.read_text(encoding="utf-8"))["sourceFingerprint"]
            )

    def test_one_source_update_bumps_once_and_retry_keeps_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "plugin"
            manifest, skill, state = self.make_plugin(root)
            REFRESH.sync_automation_version(root, now="2026-08-27T00:00:00+00:00")
            REFRESH.mark_package_version(root, now="2026-08-27T00:00:01+00:00")

            runtime_file = root / "skills" / "goldhand-clinic-blog" / "scripts" / "runtime.py"
            runtime_file.parent.mkdir(parents=True)
            runtime_file.write_text("VALUE = 1\n", encoding="utf-8")
            changed = REFRESH.sync_automation_version(
                root,
                now="2026-08-27T00:01:00+00:00",
            )
            self.assertTrue(changed["contentChanged"])
            self.assertEqual(changed["previousVersion"], "1.0")
            self.assertEqual(changed["currentVersion"], "1.1")
            self.assertTrue(changed["needsCachebuster"])
            self.assertIn("현재 자동화 버전: `1.1`", skill.read_text(encoding="utf-8"))
            self.assertTrue(
                json.loads(manifest.read_text(encoding="utf-8"))["version"].startswith(
                    "1.1.0+codex."
                )
            )

            retry = REFRESH.sync_automation_version(
                root,
                now="2026-08-27T00:02:00+00:00",
            )
            self.assertFalse(retry["contentChanged"])
            self.assertEqual(retry["currentVersion"], "1.1")
            self.assertTrue(retry["needsCachebuster"])
            self.assertEqual(
                json.loads(state.read_text(encoding="utf-8"))["automationVersion"],
                "1.1",
            )

            REFRESH.mark_package_version(root, now="2026-08-27T00:02:01+00:00")
            installed_retry = REFRESH.sync_automation_version(
                root,
                now="2026-08-27T00:03:00+00:00",
            )
            self.assertFalse(installed_retry["contentChanged"])
            self.assertFalse(installed_retry["needsCachebuster"])
            self.assertEqual(installed_retry["currentVersion"], "1.1")

    def test_current_skill_starts_with_managed_version_briefing(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        state = json.loads(
            (SKILL_DIR / "assets" / "automation-version.json").read_text(
                encoding="utf-8"
            )
        )
        managed = REFRESH.managed_skill_version(SKILL_DIR / "SKILL.md")
        self.assertEqual(managed, state["automationVersion"])
        self.assertIn(
            "금손한의원 블로그 자동화 v{현재 자동화 버전}을 시작합니다.",
            skill_text,
        )
        self.assertIn("현재 버전: {현재 버전 브리핑}", skill_text)
        self.assertLess(
            skill_text.index("## 시작 브리핑과 자동화 버전"),
            skill_text.index("## 운영체제별 실행기"),
        )

    def test_current_skill_uses_topic_first_fixed_automatic_flow(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        readme_text = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        agent_text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        topic_question = "작성할 글의 주제를 입력해 주세요."
        keyword_question = "메인키워드를 입력해 주세요."
        title_question = "1~5번 중 사용할 제목을 선택하거나, 원하는 제목을 직접 입력해 주세요."

        self.assertIn(topic_question, skill_text)
        self.assertIn(keyword_question, skill_text)
        self.assertIn(title_question, skill_text)
        self.assertLess(skill_text.index(topic_question), skill_text.index(keyword_question))
        self.assertLess(skill_text.index(keyword_question), skill_text.index(title_question))
        self.assertIn('--topic "{사용자 입력 주제}"', skill_text)
        self.assertIn("사용자가 입력한 글 주제를 실제 글의 주제로 고정", skill_text)
        self.assertIn("제목 후보 5개", skill_text)
        self.assertIn("공백 제외 30자", skill_text)
        self.assertIn("select_general_information.py", skill_text)
        self.assertIn("search_naver_background.py", skill_text)
        self.assertIn("한국어 네이버", skill_text)
        self.assertIn("기존 글 구조", skill_text)
        self.assertIn("clinic-facts.md", skill_text)
        self.assertNotIn("현재 검토된 정보글 범위에서 연결할 수 없는 주제입니다", skill_text)
        self.assertNotIn("1. 자동모드  2. 정밀작성모드", skill_text)
        self.assertNotIn("정밀작성모드", skill_text)
        self.assertNotIn("정밀작성모드", readme_text)
        self.assertIn(topic_question, agent_text)
        self.assertIn(keyword_question, agent_text)
        self.assertIn(title_question, agent_text)
        self.assertIn("제목 5개", readme_text)
        self.assertTrue(
            all(
                "정밀작성모드" not in prompt
                for prompt in manifest["interface"]["defaultPrompt"]
            )
        )


if __name__ == "__main__":
    unittest.main()
