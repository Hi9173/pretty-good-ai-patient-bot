import io
import unittest

from pgai_patient_bot import endpoint_check
from pgai_patient_bot.cli import main


class Checkpoint19Tests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_endpoints_fetches_twiml_and_probes_media(self):
        calls = []

        def fetch_text(url):
            calls.append(("twiml", url))
            return (
                '<Response><Connect><Stream url="wss://media.example.test/media" />'
                "</Connect></Response>"
            )

        async def probe_media(url):
            calls.append(("media", url))

        report = await endpoint_check.verify_endpoints(
            {
                "PUBLIC_BASE_URL": "https://twiml.example.test",
                "PUBLIC_MEDIA_BASE_URL": "https://media.example.test",
            },
            fetch_text=fetch_text,
            probe_media=probe_media,
        )

        self.assertEqual(report["twiml"], "ok")
        self.assertEqual(report["media"], "ok")
        self.assertEqual(report["stream_url"], "wss://media.example.test/media")
        self.assertEqual(
            calls,
            [
                ("twiml", "https://twiml.example.test/twiml"),
                ("media", "wss://media.example.test/media?probe=1"),
            ],
        )

    async def test_verify_endpoints_rejects_wrong_stream_url(self):
        def fetch_text(_url):
            return (
                '<Response><Connect><Stream url="wss://wrong.example.test/media" />'
                "</Connect></Response>"
            )

        async def probe_media(_url):
            raise AssertionError("media should not be probed after a TwiML mismatch")

        with self.assertRaisesRegex(ValueError, "TwiML stream URL mismatch"):
            await endpoint_check.verify_endpoints(
                {
                    "PUBLIC_BASE_URL": "https://twiml.example.test",
                    "PUBLIC_MEDIA_BASE_URL": "https://media.example.test",
                },
                fetch_text=fetch_text,
                probe_media=probe_media,
            )


class Checkpoint19CliTests(unittest.TestCase):
    def test_main_endpoint_check_delegates_without_printing_secrets(self):
        output = io.StringIO()
        calls = []

        def endpoint_checker(env, output_arg):
            calls.append((env["PUBLIC_BASE_URL"], output_arg))
            print("TwiML: ok", file=output_arg)
            print("Media: ok", file=output_arg)
            return 0

        exit_code = main(
            ["endpoint-check"],
            env={
                "PUBLIC_BASE_URL": "https://twiml.example.test",
                "OPENAI_API_KEY": "secret-key",
            },
            output=output,
            endpoint_checker=endpoint_checker,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("https://twiml.example.test", output)])
        self.assertIn("TwiML: ok", output.getvalue())
        self.assertIn("Media: ok", output.getvalue())
        self.assertNotIn("secret-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
