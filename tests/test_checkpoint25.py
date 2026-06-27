import io
import json
import unittest

from pgai_patient_bot.cli import main


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class Checkpoint25Tests(unittest.TestCase):
    def test_place_call_requires_live_flag_and_config(self):
        output = io.StringIO()

        missing_flag = main(["place-call"], env={}, output=output)
        missing_config = main(["place-call", "--live"], env={}, output=output)

        self.assertEqual(missing_flag, 2)
        self.assertEqual(missing_config, 2)
        self.assertIn("place-call --live", output.getvalue())
        self.assertIn("Missing required environment variables", output.getvalue())

    def test_place_call_posts_twilio_request_without_printing_secrets(self):
        output = io.StringIO()
        calls = []

        def opener(request, timeout=10):
            calls.append((request, timeout))
            return FakeResponse({"sid": "CA123", "status": "queued"})

        exit_code = main(
            ["place-call", "--live"],
            env={
                "TWILIO_ACCOUNT_SID": "account-sid-placeholder",
                "TWILIO_AUTH_TOKEN": "auth-token-placeholder",
                "TWILIO_FROM_NUMBER": "+15555550123",
                "PUBLIC_BASE_URL": "https://public.example.test",
            },
            output=output,
            twilio_call_opener=opener,
        )

        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("Twilio call: queued", text)
        self.assertIn("Call SID: CA123", text)
        self.assertNotIn("auth-token-placeholder", text)
        self.assertNotIn("account-sid-placeholder", text)


if __name__ == "__main__":
    unittest.main()
