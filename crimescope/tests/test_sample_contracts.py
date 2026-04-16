import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_SAMPLES = REPO_ROOT / "data_samples"


class SampleContractsTest(unittest.TestCase):
    def test_tract_risk_contract_has_required_keys(self) -> None:
        payload = json.loads((DATA_SAMPLES / "tract_risk_package.sample.json").read_text())
        required = {
            "regionId",
            "regionType",
            "scores",
            "drivers",
            "trustPassport",
            "liveDisagreement",
            "whatChanged",
        }
        self.assertTrue(required.issubset(payload.keys()))

    def test_live_event_contract_has_banner_and_events(self) -> None:
        payload = json.loads((DATA_SAMPLES / "live_event_package.sample.json").read_text())
        self.assertIn("banner", payload)
        self.assertGreaterEqual(len(payload["events"]), 1)

    def test_persona_decision_contract_has_next_step(self) -> None:
        payload = json.loads(
            (DATA_SAMPLES / "persona_decision_package.sample.json").read_text()
        )
        self.assertIn("nextStep", payload)
        self.assertIn("decision", payload)

    def test_compare_contract_has_both_regions(self) -> None:
        payload = json.loads((DATA_SAMPLES / "compare_package.sample.json").read_text())
        self.assertIn("left", payload)
        self.assertIn("right", payload)
        self.assertIn("summary", payload)
        self.assertNotEqual(payload["left"]["regionId"], payload["right"]["regionId"])

    def test_report_summary_has_trust_notes(self) -> None:
        payload = json.loads((DATA_SAMPLES / "report_summary_package.sample.json").read_text())
        self.assertTrue(payload["trustNotes"])


if __name__ == "__main__":
    unittest.main()
