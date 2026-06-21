import json
import unittest

from pgai_patient_bot.media import run_media_loop
from pgai_patient_bot.mock_data import fake_model_audio, twilio_mock_call


class Checkpoint5Test(unittest.IsolatedAsyncioTestCase):
    def test_twilio_mock_call_builds_start_media_stop_messages(self):
        messages = twilio_mock_call(["hello", "need-appointment"], stream_sid="MZTEST")

        decoded = [json.loads(message) for message in messages]

        self.assertEqual(decoded[0], {"event": "start", "start": {"streamSid": "MZTEST"}})
        self.assertEqual(decoded[1], {"event": "media", "media": {"payload": "hello"}})
        self.assertEqual(
            decoded[2],
            {"event": "media", "media": {"payload": "need-appointment"}},
        )
        self.assertEqual(decoded[3], {"event": "stop"})

    async def test_mock_call_drives_media_loop_end_to_end(self):
        outbound = await run_media_loop(
            twilio_mock_call(["hello", "need-appointment"], stream_sid="MZTEST"),
            fake_model_audio(
                {
                    "hello": "hi-there",
                    "need-appointment": "what-day-works",
                }
            ),
        )

        self.assertEqual(
            [json.loads(message) for message in outbound],
            [
                {
                    "event": "media",
                    "streamSid": "MZTEST",
                    "media": {"payload": "hi-there"},
                },
                {
                    "event": "media",
                    "streamSid": "MZTEST",
                    "media": {"payload": "what-day-works"},
                },
            ],
        )

    async def test_fake_model_audio_returns_none_for_unknown_payload(self):
        model = fake_model_audio({"hello": "hi-there"})

        self.assertIsNone(await model("unknown"))


if __name__ == "__main__":
    unittest.main()
