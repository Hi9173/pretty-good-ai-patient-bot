import json
import unittest

from pgai_patient_bot.openai_realtime import realtime_session_update


class Checkpoint8Test(unittest.TestCase):
    def test_realtime_session_update_uses_telephony_audio_formats(self):
        event = json.loads(
            realtime_session_update(
                instructions="Act like a realistic patient.",
                model="gpt-realtime-2",
                voice="marin",
            )
        )

        self.assertEqual(event["type"], "session.update")
        self.assertEqual(event["session"]["type"], "realtime")
        self.assertEqual(event["session"]["model"], "gpt-realtime-2")
        self.assertEqual(event["session"]["instructions"], "Act like a realistic patient.")
        self.assertEqual(
            event["session"]["audio"]["input"]["format"],
            {"type": "audio/pcmu"},
        )
        self.assertEqual(
            event["session"]["audio"]["output"]["format"],
            {"type": "audio/pcmu"},
        )
        self.assertEqual(event["session"]["audio"]["output"]["voice"], "marin")

    def test_realtime_session_update_enables_server_vad(self):
        event = json.loads(realtime_session_update(instructions="Test."))

        self.assertEqual(
            event["session"]["audio"]["input"]["turn_detection"],
            {
                "type": "server_vad",
                "create_response": True,
                "interrupt_response": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
