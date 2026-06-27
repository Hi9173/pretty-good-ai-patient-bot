import asyncio
import json
import tempfile
import unittest

from pgai_patient_bot.runner import run_mock_batch
from pgai_patient_bot.scenarios import patient_scenarios


class Checkpoint11Tests(unittest.TestCase):
    def test_mock_batch_writes_submission_shaped_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = asyncio.run(run_mock_batch(tmp))
            scenario_count = len(patient_scenarios())

            self.assertEqual(len(results), scenario_count)

            for index, result in enumerate(results, start=1):
                call_id = f"call-{index:03d}"
                call_dir = result["call_dir"]
                metadata = json.loads((call_dir / "metadata.json").read_text())

                self.assertEqual(call_dir.name, call_id)
                self.assertEqual(metadata["call_id"], call_id)
                self.assertIn("scenario_id", metadata)
                self.assertEqual(
                    metadata["realtime_event_types"],
                    ["session.update", "input_audio_buffer.append"],
                )
                self.assertIn("PATIENT:", (call_dir / "transcript.txt").read_text())
                self.assertIn("ASSISTANT:", (call_dir / "transcript.txt").read_text())
                self.assertIn("Mock analysis", (call_dir / "analysis.md").read_text())

            report = (results[0]["root"] / "bug_report.md").read_text()
            self.assertIn("# Bug Report", report)
            self.assertIn("Call: call-001", report)
            self.assertIn(f"Call: call-{scenario_count:03d}", report)


if __name__ == "__main__":
    unittest.main()
