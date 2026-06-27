import io
import unittest

from pgai_patient_bot.checkpoint import TEST_NUMBER
from pgai_patient_bot.cli import main


class Checkpoint24Tests(unittest.TestCase):
    def test_twilio_check_prints_call_readiness_without_auth_secrets(self):
        output = io.StringIO()

        exit_code = main(
            ["twilio-check"],
            env={
                "TWILIO_ACCOUNT_SID": "account-sid-placeholder",
                "TWILIO_AUTH_TOKEN": "auth-token-placeholder",
                "TWILIO_FROM_NUMBER": "+15555550123",
                "PUBLIC_BASE_URL": "https://public.example.test",
            },
            output=output,
        )

        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Twilio config: ok", text)
        self.assertIn(f"To: {TEST_NUMBER}", text)
        self.assertIn("From: +15555550123", text)
        self.assertIn("TwiML URL: https://public.example.test/twiml", text)
        self.assertIn("Media URL: wss://public.example.test/media", text)
        self.assertNotIn("auth-token-placeholder", text)
        self.assertNotIn("account-sid-placeholder", text)

    def test_twilio_check_reports_missing_config_without_traceback(self):
        output = io.StringIO()

        exit_code = main(["twilio-check"], env={}, output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("Missing required environment variables", output.getvalue())


if __name__ == "__main__":
    unittest.main()
