import json
import unittest

from pgai_patient_bot.media import run_media_loop


class Checkpoint4Test(unittest.IsolatedAsyncioTestCase):
    async def test_media_loop_returns_model_audio_as_twilio_frames(self):
        async def fake_model(payload):
            return "model-" + payload

        outbound = await run_media_loop(
            [
                json.dumps({"event": "start", "start": {"streamSid": "MZ123"}}),
                json.dumps({"event": "media", "media": {"payload": "caller-audio"}}),
            ],
            fake_model,
        )

        self.assertEqual(
            [json.loads(message) for message in outbound],
            [
                {
                    "event": "media",
                    "streamSid": "MZ123",
                    "media": {"payload": "model-caller-audio"},
                }
            ],
        )

    async def test_media_loop_stops_after_stop_event(self):
        seen = []

        async def fake_model(payload):
            seen.append(payload)
            return "model-" + payload

        outbound = await run_media_loop(
            [
                json.dumps({"event": "start", "start": {"streamSid": "MZ123"}}),
                json.dumps({"event": "stop"}),
                json.dumps({"event": "media", "media": {"payload": "ignored"}}),
            ],
            fake_model,
        )

        self.assertEqual(outbound, [])
        self.assertEqual(seen, [])

    async def test_media_loop_ignores_model_when_it_returns_no_audio(self):
        async def fake_model(payload):
            return None

        outbound = await run_media_loop(
            [
                json.dumps({"event": "start", "start": {"streamSid": "MZ123"}}),
                json.dumps({"event": "media", "media": {"payload": "caller-audio"}}),
            ],
            fake_model,
        )

        self.assertEqual(outbound, [])


if __name__ == "__main__":
    unittest.main()
