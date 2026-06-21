import json
import unittest

from pgai_patient_bot.media import MediaBridge


class Checkpoint3Test(unittest.TestCase):
    def test_start_event_records_stream_sid(self):
        bridge = MediaBridge()

        bridge.receive_twilio(
            json.dumps(
                {
                    "event": "start",
                    "start": {"streamSid": "MZ123"},
                }
            )
        )

        self.assertEqual(bridge.stream_sid, "MZ123")

    def test_media_event_records_inbound_audio_payload(self):
        bridge = MediaBridge()

        bridge.receive_twilio(
            json.dumps(
                {
                    "event": "media",
                    "media": {"payload": "dGVzdA=="},
                }
            )
        )

        self.assertEqual(bridge.inbound_audio, ["dGVzdA=="])

    def test_stop_event_marks_session_closed(self):
        bridge = MediaBridge()

        bridge.receive_twilio(json.dumps({"event": "stop"}))

        self.assertTrue(bridge.closed)

    def test_outbound_audio_uses_recorded_stream_sid(self):
        bridge = MediaBridge()
        bridge.receive_twilio(
            json.dumps(
                {
                    "event": "start",
                    "start": {"streamSid": "MZ123"},
                }
            )
        )

        message = json.loads(bridge.twilio_audio("bW9kZWwtYXVkaW8="))

        self.assertEqual(
            message,
            {
                "event": "media",
                "streamSid": "MZ123",
                "media": {"payload": "bW9kZWwtYXVkaW8="},
            },
        )

    def test_outbound_audio_before_start_is_rejected(self):
        bridge = MediaBridge()

        with self.assertRaisesRegex(ValueError, "stream SID"):
            bridge.twilio_audio("bW9kZWwtYXVkaW8=")


if __name__ == "__main__":
    unittest.main()
