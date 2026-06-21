import json
import unittest

from pgai_patient_bot.mock_data import fake_model_audio, twilio_mock_call
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_media_websocket


class Checkpoint6Test(unittest.IsolatedAsyncioTestCase):
    async def test_fake_websocket_adapter_sends_model_audio_frames(self):
        websocket = FakeWebSocket(
            twilio_mock_call(["hello", "need-appointment"], stream_sid="MZWS")
        )

        sent_count = await handle_media_websocket(
            websocket,
            fake_model_audio(
                {
                    "hello": "hi-there",
                    "need-appointment": "what-day-works",
                }
            ),
        )

        self.assertEqual(sent_count, 2)
        self.assertEqual(
            [json.loads(message) for message in websocket.sent],
            [
                {
                    "event": "media",
                    "streamSid": "MZWS",
                    "media": {"payload": "hi-there"},
                },
                {
                    "event": "media",
                    "streamSid": "MZWS",
                    "media": {"payload": "what-day-works"},
                },
            ],
        )

    async def test_fake_websocket_adapter_stops_on_stop_event(self):
        websocket = FakeWebSocket(
            [
                *twilio_mock_call([], stream_sid="MZWS"),
                json.dumps({"event": "media", "media": {"payload": "ignored"}}),
            ]
        )

        sent_count = await handle_media_websocket(
            websocket,
            fake_model_audio({"ignored": "should-not-send"}),
        )

        self.assertEqual(sent_count, 0)
        self.assertEqual(websocket.sent, [])


if __name__ == "__main__":
    unittest.main()
