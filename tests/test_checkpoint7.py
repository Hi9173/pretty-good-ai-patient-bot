import json
import unittest

from pgai_patient_bot.media import run_media_loop
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.openai_realtime import (
    fake_realtime_audio,
    input_audio_event,
    output_audio_delta,
)


class Checkpoint7Test(unittest.IsolatedAsyncioTestCase):
    def test_input_audio_event_wraps_twilio_payload_for_realtime(self):
        event = json.loads(input_audio_event("caller-audio"))

        self.assertEqual(
            event,
            {
                "type": "input_audio_buffer.append",
                "audio": "caller-audio",
            },
        )

    def test_output_audio_delta_extracts_model_audio_payload(self):
        payload = output_audio_delta(
            json.dumps(
                {
                    "type": "response.output_audio.delta",
                    "delta": "model-audio",
                }
            )
        )

        self.assertEqual(payload, "model-audio")

    def test_output_audio_delta_ignores_non_audio_events(self):
        self.assertIsNone(output_audio_delta(json.dumps({"type": "response.done"})))

    async def test_fake_realtime_audio_drives_media_loop(self):
        outbound = await run_media_loop(
            twilio_mock_call(["caller-audio"], stream_sid="MZOPENAI"),
            fake_realtime_audio({"caller-audio": "model-audio"}),
        )

        self.assertEqual(
            [json.loads(message) for message in outbound],
            [
                {
                    "event": "media",
                    "streamSid": "MZOPENAI",
                    "media": {"payload": "model-audio"},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
