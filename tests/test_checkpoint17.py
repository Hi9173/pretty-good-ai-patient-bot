import io
import unittest

from pgai_patient_bot.cli import main
from pgai_patient_bot import tunnel


class Checkpoint17Tests(unittest.TestCase):
    def test_tunnel_urls_use_public_https_base(self):
        urls = tunnel.tunnel_urls(
            {
                "PUBLIC_BASE_URL": "https://example.ngrok-free.app/",
            }
        )

        self.assertEqual(urls["twiml"], "https://example.ngrok-free.app/twiml")
        self.assertEqual(urls["media"], "wss://example.ngrok-free.app/media")
        self.assertEqual(urls["local_twiml"], "http://127.0.0.1:8000/twiml")
        self.assertEqual(urls["local_media"], "ws://127.0.0.1:8765/media")

    def test_tunnel_urls_can_use_separate_public_media_base(self):
        urls = tunnel.tunnel_urls(
            {
                "PUBLIC_BASE_URL": "https://twiml.ngrok-free.app",
                "PUBLIC_MEDIA_BASE_URL": "https://media.ngrok-free.app/",
            }
        )

        self.assertEqual(urls["twiml"], "https://twiml.ngrok-free.app/twiml")
        self.assertEqual(urls["media"], "wss://media.ngrok-free.app/media")

    def test_tunnel_urls_require_https_public_base(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_BASE_URL must start with https://"):
            tunnel.tunnel_urls({"PUBLIC_BASE_URL": "http://example.test"})

    def test_tunnel_urls_require_https_public_media_base(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_MEDIA_BASE_URL must start with https://"):
            tunnel.tunnel_urls(
                {
                    "PUBLIC_BASE_URL": "https://twiml.example.test",
                    "PUBLIC_MEDIA_BASE_URL": "http://media.example.test",
                }
            )

    def test_main_tunnel_check_prints_urls_without_twilio_secrets(self):
        output = io.StringIO()

        exit_code = main(
            ["tunnel-check"],
            env={
                "PUBLIC_BASE_URL": "https://example.ngrok-free.app",
                "TWILIO_AUTH_TOKEN": "twilio-secret",
            },
            output=output,
        )

        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Public TwiML: https://example.ngrok-free.app/twiml", text)
        self.assertIn("Public media: wss://example.ngrok-free.app/media", text)
        self.assertIn("Local TwiML: http://127.0.0.1:8000/twiml", text)
        self.assertIn("Local media: ws://127.0.0.1:8765/media", text)
        self.assertNotIn("twilio-secret", text)

    def test_main_tunnel_check_reports_missing_public_base(self):
        output = io.StringIO()

        exit_code = main(["tunnel-check"], env={}, output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("PUBLIC_BASE_URL is required", output.getvalue())


if __name__ == "__main__":
    unittest.main()
