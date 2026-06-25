import io
import unittest

from pgai_patient_bot.cli import main
from pgai_patient_bot.openai_realtime import live_realtime_smoke


class FakeConnection:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send(self, message):
        self.sent.append(message)

    async def recv(self):
        return '{"type":"session.updated"}'

    async def close(self):
        self.closed = True


class Checkpoint13Tests(unittest.TestCase):
    def test_live_realtime_smoke_sends_session_update_and_closes(self):
        connection = FakeConnection()

        async def opener(api_key, safety_identifier=None):
            self.assertEqual(api_key, "test-key")
            self.assertEqual(safety_identifier, "patient-bot-local")
            return connection

        event = live_realtime_smoke(
            "test-key",
            opener=opener,
            safety_identifier="patient-bot-local",
        )

        self.assertEqual(event["type"], "session.updated")
        self.assertIn('"type": "session.update"', connection.sent[0])
        self.assertTrue(connection.closed)

    def test_main_realtime_smoke_requires_live_flag(self):
        output = io.StringIO()

        exit_code = main(["realtime-smoke"], env={}, output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("--live", output.getvalue())

    def test_main_realtime_smoke_requires_api_key(self):
        output = io.StringIO()

        exit_code = main(["realtime-smoke", "--live"], env={}, output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("OPENAI_API_KEY is required", output.getvalue())

    def test_main_realtime_smoke_does_not_print_api_key(self):
        output = io.StringIO()

        def smoke(api_key):
            self.assertEqual(api_key, "secret-key")
            return {"type": "session.updated"}

        exit_code = main(
            ["realtime-smoke", "--live"],
            env={"OPENAI_API_KEY": "secret-key"},
            output=output,
            realtime_smoke=smoke,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("Realtime smoke event: session.updated", output.getvalue())
        self.assertNotIn("secret-key", output.getvalue())

    def test_main_realtime_smoke_returns_failure_on_error_event(self):
        output = io.StringIO()

        def smoke(api_key):
            self.assertEqual(api_key, "secret-key")
            return {
                "type": "error",
                "error": {
                    "code": "insufficient_quota",
                    "message": "quota exhausted",
                },
            }

        exit_code = main(
            ["realtime-smoke", "--live"],
            env={"OPENAI_API_KEY": "secret-key"},
            output=output,
            realtime_smoke=smoke,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("Realtime smoke error: insufficient_quota", output.getvalue())
        self.assertNotIn("secret-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
