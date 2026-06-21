import asyncio
import base64
import json
import tempfile
import unittest

from pgai_patient_bot.artifacts import write_bug_report, write_call_artifacts
from pgai_patient_bot.audio import (
    TELEPHONY_AUDIO_MIME_TYPE,
    is_real_audio_payload,
    is_symbolic_audio,
    symbolic_audio,
)
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.openai_realtime import (
    FakeRealtimeConnection,
    configure_realtime_connection,
    realtime_audio_from_connection,
)
from pgai_patient_bot.scenarios import patient_scenarios
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_media_websocket


class Checkpoint9Through13Tests(unittest.TestCase):
    def test_fake_realtime_connection_records_session_and_audio_events(self):
        caller_audio = symbolic_audio("caller-hello")
        model_audio = symbolic_audio("model-hello")
        connection = FakeRealtimeConnection({caller_audio: model_audio})

        async def run():
            await configure_realtime_connection(connection, "Act like a patient.")
            return await realtime_audio_from_connection(connection, caller_audio)

        self.assertEqual(asyncio.run(run()), model_audio)
        self.assertEqual(
            [json.loads(message)["type"] for message in connection.sent],
            ["session.update", "input_audio_buffer.append"],
        )

    def test_fake_realtime_connection_drives_twilio_websocket_loop(self):
        caller_audio = symbolic_audio("caller-appointment")
        model_audio = symbolic_audio("patient-reply")
        twilio = FakeWebSocket(twilio_mock_call([caller_audio], stream_sid="MZFULL"))
        realtime = FakeRealtimeConnection({caller_audio: model_audio})

        async def run():
            await configure_realtime_connection(realtime, "Schedule an appointment.")
            return await handle_media_websocket(
                twilio,
                lambda payload: realtime_audio_from_connection(realtime, payload),
            )

        self.assertEqual(asyncio.run(run()), 1)
        self.assertEqual(json.loads(twilio.sent[0])["media"]["payload"], model_audio)
        self.assertEqual(
            [json.loads(message)["type"] for message in realtime.sent],
            ["session.update", "input_audio_buffer.append"],
        )

    def test_audio_helpers_keep_real_payloads_and_symbolic_mocks_separate(self):
        real_payload = base64.b64encode(b"\xff\x00\x7f").decode()
        mock_payload = symbolic_audio("not-real-audio")

        self.assertEqual(TELEPHONY_AUDIO_MIME_TYPE, "audio/pcmu")
        self.assertTrue(is_real_audio_payload(real_payload))
        self.assertFalse(is_real_audio_payload(mock_payload))
        self.assertTrue(is_symbolic_audio(mock_payload))
        self.assertFalse(is_symbolic_audio(real_payload))

    def test_patient_scenarios_cover_expected_call_types(self):
        scenarios = patient_scenarios()

        self.assertEqual(
            {scenario["id"] for scenario in scenarios},
            {
                "appointment_scheduling",
                "reschedule",
                "refill",
                "office_hours",
                "edge_case",
            },
        )
        for scenario in scenarios:
            self.assertIsInstance(scenario["goal"], str)
            self.assertTrue(scenario["caller_payloads"])
            self.assertTrue(all(is_symbolic_audio(p) for p in scenario["caller_payloads"]))

    def test_call_artifacts_and_bug_report_shape(self):
        issue = {
            "title": "Bot accepts unavailable weekend appointment",
            "severity": "High",
            "call": "call-001",
            "evidence": "AGENT: Saturday at 9 works.",
            "expected": "The bot should offer office-hour appointments only.",
        }

        with tempfile.TemporaryDirectory() as tmp:
            call_dir = write_call_artifacts(
                tmp,
                "call-001",
                {"scenario_id": "appointment_scheduling", "duration_seconds": 62},
                "PATIENT: I need an appointment.\nAGENT: Saturday at 9 works.\n",
                "Potential scheduling-policy bug.\n",
            )
            report_path = write_bug_report(tmp, [issue])

            self.assertEqual(call_dir.name, "call-001")
            self.assertTrue((call_dir / "metadata.json").exists())
            self.assertTrue((call_dir / "transcript.txt").exists())
            self.assertTrue((call_dir / "analysis.md").exists())
            self.assertEqual(
                json.loads((call_dir / "metadata.json").read_text())["scenario_id"],
                "appointment_scheduling",
            )

            report = report_path.read_text()
            self.assertIn("## High - Bot accepts unavailable weekend appointment", report)
            self.assertIn("Call: call-001", report)
            self.assertIn("Evidence: AGENT: Saturday at 9 works.", report)
            self.assertIn(
                "Expected: The bot should offer office-hour appointments only.",
                report,
            )


if __name__ == "__main__":
    unittest.main()
