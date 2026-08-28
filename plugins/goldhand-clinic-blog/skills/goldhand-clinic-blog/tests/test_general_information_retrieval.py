from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
ASSETS = SKILL_DIR / "assets"


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"goldhand_{name}_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECT = load_module("select_general_information")
SEARCH = load_module("search_naver_background")
FETCH = load_module("fetch_naver_post_text")
VALIDATE_LIBRARY = load_module("validate_general_information_library")
VALIDATE_SOURCES = load_module("validate_information_sources")


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, text: str) -> None:
        self.text = text

    def get(self, *args, **kwargs):
        return FakeResponse(self.text)


class GeneralInformationSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.briefs = json.loads((ASSETS / "wipark-content-briefs.json").read_text(encoding="utf-8"))
        cls.profiles = json.loads((ASSETS / "reference-master-profiles.json").read_text(encoding="utf-8"))
        cls.empty_library = json.loads(
            (ASSETS / "user-general-information-references.json").read_text(encoding="utf-8")
        )

    def select(self, topic: str, title: str, keyword: str = "동천동 한의원"):
        return SELECT.select_information(
            topic,
            title,
            keyword,
            self.briefs,
            self.profiles,
            self.empty_library,
        )

    def test_insomnia_uses_only_sleep_atoms_from_info04(self) -> None:
        result = self.select("불면증", "동천동 한의원 불면증 원인 2가지")
        self.assertEqual(result["status"], "stored-sufficient")
        self.assertEqual([source["id"] for source in result["storedSources"]], ["INFO04"])
        atom_ids = {
            atom_id
            for atom in result["mergedInformationAtoms"]
            for atom_id in atom["sourceAtomIds"]
        }
        self.assertEqual(atom_ids, {"INFO04-A1", "INFO04-A3"})

    def test_unknown_topic_never_forces_unrelated_reference(self) -> None:
        result = self.select("이명", "동천동 한의원 이명 원인 3가지")
        self.assertEqual(result["status"], "web-required")
        self.assertEqual(result["storedSources"], [])
        self.assertTrue(result["webSearch"]["required"])
        self.assertTrue(all(SELECT.HANGUL.search(query) for query in result["webSearch"]["queries"]))
        self.assertTrue(all("동천동 한의원" not in query for query in result["webSearch"]["queries"]))

    def test_numbered_title_requires_enough_distinct_atoms(self) -> None:
        result = self.select("불면증", "동천동 한의원 불면증 원인 3가지")
        self.assertEqual(result["status"], "stored-plus-web-required")
        self.assertEqual(result["titleContract"]["promisedAnswerCount"], 3)
        self.assertEqual(result["coverage"]["minimumAtomCount"], 3)

    def test_sensitive_context_atoms_stay_closed(self) -> None:
        insomnia = self.select("불면증", "동천동 한의원 불면증 원인 2가지")
        insomnia_ids = {
            atom_id
            for atom in insomnia["mergedInformationAtoms"]
            for atom_id in atom["sourceAtomIds"]
        }
        self.assertNotIn("INFO04-A2", insomnia_ids)
        self.assertNotIn("INFO04-A4", insomnia_ids)

        panic = self.select("공황장애와 불면증", "동천동 한의원 공황 불면 주의 3가지")
        panic_ids = {
            atom_id
            for atom in panic["mergedInformationAtoms"]
            for atom_id in atom["sourceAtomIds"]
        }
        self.assertIn("INFO04-A2", panic_ids)
        self.assertIn("INFO04-A4", panic_ids)

        unrelated = self.select("회복", "동천동 한의원 회복 원칙 2가지")
        unrelated_sources = {source["id"] for source in unrelated["storedSources"]}
        self.assertNotIn("INFO11", unrelated_sources)

    def test_multiple_user_references_are_merged_and_deduplicated(self) -> None:
        def source(source_id: str, publisher: str) -> dict[str, object]:
            return {
                "id": source_id,
                "sourceTitle": f"발바닥 통증 정보 {publisher}",
                "sourceUrl": f"https://example.com/{source_id}",
                "sourceType": "clinic-blog",
                "sourceClinicName": publisher,
                "topic": "발바닥 통증",
                "topicTags": ["발바닥 통증", "족저 통증"],
                "reviewStatus": "general-information-only-reviewed",
                "generalInformationOnly": True,
                "sourceClinicFactsBlocked": True,
                "sourceSentencesBlocked": True,
                "sourceCasesAndResultsBlocked": True,
                "blockedEntities": [publisher],
                "generalInformationAtoms": [
                    {
                        "id": f"{source_id}-A1",
                        "role": "morning-pain",
                        "observables": ["아침 첫발을 디딜 때 발바닥 통증"],
                        "meaning": ["첫걸음 통증 양상 확인"],
                        "generalInformationOnly": True,
                    }
                ],
            }

        library = copy.deepcopy(self.empty_library)
        library["sources"] = [source("USER01", "가나다한의원"), source("USER02", "라마바한의원")]
        result = SELECT.select_information(
            "발바닥 통증",
            "동천동 한의원 발바닥 통증 원인 1가지",
            "동천동 한의원",
            {"briefs": {}},
            {"profiles": {}},
            library,
        )
        self.assertEqual({item["id"] for item in result["storedSources"]}, {"USER01", "USER02"})
        self.assertEqual(len(result["mergedInformationAtoms"]), 1)
        self.assertEqual(set(result["mergedInformationAtoms"][0]["sourceIds"]), {"USER01", "USER02"})


class BackgroundNaverTests(unittest.TestCase):
    def test_search_parser_skips_navigation_and_keeps_actual_results(self) -> None:
        page = """
        <html><body>
          <a href="https://www.naver.com">NAVER</a>
          <a href="https://map.naver.com/v5/search/test">지도</a>
          <a href="https://blog.naver.com/sleepdoctor/224123456789">불면증 정보 글</a>
          <a href="https://health.kdca.go.kr/healthinfo/biz/health/main/mainPage/main.do">국가건강정보포털</a>
        </body></html>
        """
        result = SEARCH.search_one(FakeSession(page), "불면증 원인", 10)
        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(
            {item["kind"] for item in result["candidates"]},
            {"naver-blog-post", "official-korean-medical"},
        )

    def test_fetch_parser_stops_before_contact_section(self) -> None:
        page = """
        <html><head>
          <meta property="og:title" content="불면증 일반 정보">
          <meta property="og:site_name" content="예시 블로그">
        </head><body><div class="se-main-container">
          <div class="se-component"><p class="se-text-paragraph">잠드는 시간과 깨는 시간을 함께 봅니다.</p></div>
          <div class="se-component"><p class="se-text-paragraph">네이버 예약 및 전화 문의</p></div>
          <div class="se-component"><p class="se-text-paragraph">업체 주소</p></div>
        </div></body></html>
        """
        result = FETCH.fetch_one(
            FakeSession(page), "https://blog.naver.com/sleepdoctor/224123456789"
        )
        self.assertEqual(result["paragraphs"], ["잠드는 시간과 깨는 시간을 함께 봅니다."])
        self.assertTrue(result["sourceUsePolicy"]["sourceClinicFactsBlocked"])


class SourceBoundaryValidationTests(unittest.TestCase):
    def valid_manifest(self) -> dict[str, object]:
        source_base = {
            "generalInformationOnly": True,
            "sourceClinicFactsBlocked": True,
            "sourceCasesResultsProgramsMediaBlocked": True,
            "sourceSentenceCopyBlocked": True,
        }
        return {
            "schemaVersion": 1,
            "topic": "불면증",
            "title": "동천동 한의원 불면증 원인 2가지",
            "mainKeyword": "동천동 한의원",
            "numberedAnswerCount": 2,
            "structureContract": "existing-goldhand-structure-unchanged",
            "medicalClaimsIncludeTreatmentOrSafety": True,
            "contentSources": [
                {
                    **source_base,
                    "id": "WEB01",
                    "title": "불면증 일반 정보",
                    "url": "https://blog.naver.com/sleepdoctor/224123456789",
                    "kind": "naver-blog-post",
                    "publisher": "수면정보블로그",
                    "retrievedBy": "naver",
                    "blockedEntities": ["서울잠한의원", "김수면 원장"],
                },
                {
                    **source_base,
                    "id": "WEB02",
                    "title": "국가건강정보포털 불면증",
                    "url": "https://health.kdca.go.kr/example/insomnia",
                    "kind": "official-korean-medical",
                    "publisher": "질병관리청 국가건강정보포털",
                    "retrievedBy": "naver",
                    "blockedEntities": [],
                },
            ],
            "mergedInformationAtoms": [
                {"id": "A1", "role": "원인", "sourceIds": ["WEB01"], "generalInformationOnly": True},
                {"id": "A2", "role": "치료 주의", "sourceIds": ["WEB02"], "generalInformationOnly": True},
            ],
            "goldhandFacts": [
                {"fact": "금손한의원 사실", "source": "references/clinic-facts.md"}
            ],
            "webSearch": {
                "used": True,
                "engine": "naver",
                "language": "ko-KR",
                "execution": "background-http-no-gui",
                "requiresBrowser": False,
                "requiresLogin": False,
                "queries": ["불면증 원인", "불면증 국가건강정보포털"],
            },
        }

    def test_empty_curated_library_is_valid(self) -> None:
        library = json.loads(
            (ASSETS / "user-general-information-references.json").read_text(encoding="utf-8")
        )
        self.assertEqual(VALIDATE_LIBRARY.validate_library(library)["status"], "pass")

    def test_library_rejects_source_clinic_name_inside_atom(self) -> None:
        library = json.loads(
            (ASSETS / "user-general-information-references.json").read_text(encoding="utf-8")
        )
        library["sources"] = [
            {
                "id": "USER01",
                "sourceTitle": "불면증 정보",
                "sourceUrl": "https://example.com/post",
                "sourceType": "clinic-blog",
                "sourceClinicName": "서울잠한의원",
                "topicTags": ["불면증"],
                "reviewStatus": "general-information-only-reviewed",
                "generalInformationOnly": True,
                "sourceClinicFactsBlocked": True,
                "sourceSentencesBlocked": True,
                "sourceCasesAndResultsBlocked": True,
                "blockedEntities": ["서울잠한의원"],
                "generalInformationAtoms": [
                    {
                        "id": "USER01-A1",
                        "role": "원인",
                        "observables": ["서울잠한의원에서 보는 수면 시간"],
                        "meaning": ["수면 양상"],
                        "generalInformationOnly": True,
                    }
                ],
            }
        ]
        result = VALIDATE_LIBRARY.validate_library(library)
        self.assertEqual(result["status"], "fail")
        self.assertIn("source-entity-in-atom", {issue["code"] for issue in result["issues"]})

    def test_valid_web_manifest_passes(self) -> None:
        result = VALIDATE_SOURCES.validate_manifest(
            self.valid_manifest(),
            '<article><h2 data-reference-role="section-heading">1. 첫째</h2>'
            '<h2 data-reference-role="section-heading">2. 둘째</h2>'
            "<p>금손한의원 일반 정보입니다.</p></article>",
        )
        self.assertEqual(result["status"], "pass", result["issues"])

    def test_manifest_blocks_source_clinic_leak(self) -> None:
        result = VALIDATE_SOURCES.validate_manifest(
            self.valid_manifest(),
            '<article><h2 data-reference-role="section-heading">1. 첫째</h2>'
            '<h2 data-reference-role="section-heading">2. 둘째</h2>'
            "서울잠한의원 김수면 원장의 설명입니다.</article>",
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("source-entity-leak", {issue["code"] for issue in result["issues"]})

    def test_manifest_requires_two_publishers_and_korean_queries(self) -> None:
        manifest = self.valid_manifest()
        manifest["contentSources"][1]["publisher"] = "수면정보블로그"
        manifest["webSearch"]["queries"] = ["insomnia causes"]
        result = VALIDATE_SOURCES.validate_manifest(manifest)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("web-independent-sources", codes)
        self.assertIn("web-query-korean", codes)

    def test_manifest_requires_exact_count_and_goldhand_fact_authority(self) -> None:
        manifest = self.valid_manifest()
        manifest["numberedAnswerCount"] = 3
        manifest["goldhandFacts"][0]["source"] = "다른한의원 글"
        result = VALIDATE_SOURCES.validate_manifest(manifest)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("numbered-answer-mismatch", codes)
        self.assertIn("goldhand-fact-authority", codes)

    def test_manifest_checks_actual_numbered_headings(self) -> None:
        result = VALIDATE_SOURCES.validate_manifest(
            self.valid_manifest(),
            '<article><h2 data-reference-role="section-heading">1. 첫째</h2></article>',
        )
        self.assertIn(
            "article-numbered-answer-mismatch",
            {issue["code"] for issue in result["issues"]},
        )


if __name__ == "__main__":
    unittest.main()
