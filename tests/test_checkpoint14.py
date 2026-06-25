import base64
import inspect
import json
import io
import unittest

from pgai_patient_bot import audio
from pgai_patient_bot.cli import main
from pgai_patient_bot import openai_realtime


class AudioSmokeConnection:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.incoming = [
            '{"type":"session.created"}',
            '{"type":"session.updated"}',
            '{"type":"input_audio_buffer.committed"}',
        ]

    async def send(self, message):
        self.sent.append(message)

    async def recv(self):
        return self.incoming.pop(0)

    async def close(self):
        self.closed = True


class Checkpoint14Tests(unittest.TestCase):
    def test_pcmu_silence_payload_builds_real_audio_duration(self):
        self.assertTrue(hasattr(audio, "pcmu_silence_payload"))

        payload = audio.pcmu_silence_payload(milliseconds=100)

        self.assertTrue(audio.is_real_audio_payload(payload))
        self.assertEqual(base64.b64decode(payload, validate=True), b"\xff" * 800)

    def test_live_realtime_audio_smoke_appends_and_commits_audio(self):
        connection = AudioSmokeConnection()

        async def opener(api_key, safety_identifier=None):
            self.assertEqual(api_key, "test-key")
            self.assertEqual(safety_identifier, "patient-bot-local")
            return connection

        self.assertTrue(hasattr(openai_realtime, "live_realtime_audio_smoke"))

        event = openai_realtime.live_realtime_audio_smoke(
            "test-key",
            opener=opener,
            safety_identifier="patient-bot-local",
        )

        self.assertEqual(event["type"], "input_audio_buffer.committed")
        sent = [json.loads(message) for message in connection.sent]
        self.assertEqual(sent[0]["type"], "session.update")
        self.assertIsNone(sent[0]["session"]["audio"]["input"]["turn_detection"])
        self.assertEqual(sent[1]["type"], "input_audio_buffer.append")
        self.assertEqual(sent[2]["type"], "input_audio_buffer.commit")
        self.assertTrue(connection.closed)

    def test_main_realtime_audio_smoke_does_not_print_api_key(self):
        output = io.StringIO()

        def smoke(api_key):
            self.assertEqual(api_key, "secret-key")
            return {"type": "input_audio_buffer.committed"}

        self.assertIn("realtime_audio_smoke", inspect.signature(main).parameters)

        exit_code = main(
            ["realtime-audio-smoke", "--live"],
            env={"OPENAI_API_KEY": "secret-key"},
            output=output,
            realtime_audio_smoke=smoke,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "Realtime audio smoke event: input_audio_buffer.committed",
            output.getvalue(),
        )
        self.assertNotIn("secret-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
