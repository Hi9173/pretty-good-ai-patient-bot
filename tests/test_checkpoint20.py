import io
import unittest

from pgai_patient_bot import endpoint_check
from pgai_patient_bot.cli import main


class Checkpoint20Tests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_endpoints_local_mode_fetches_and_probes_local_urls(self):
        calls = []

        def fetch_text(url):
            calls.append(("twiml", url))
            return (
                '<Response><Connect><Stream url="wss://public.example.test/media" />'
                "</Connect></Response>"
            )

        async def probe_media(url):
            calls.append(("media", url))

        report = await endpoint_check.verify_endpoints(
            {"PUBLIC_BASE_URL": "https://public.example.test"},
            fetch_text=fetch_text,
            probe_media=probe_media,
            local=True,
        )

        self.assertEqual(report["twiml"], "ok")
        self.assertEqual(report["media"], "ok")
        self.assertEqual(report["stream_url"], "wss://public.example.test/media")
        self.assertEqual(
            calls,
            [
                ("twiml", "http://127.0.0.1:8000/twiml"),
                ("media", "ws://127.0.0.1:8765/media?probe=1"),
            ],
        )


class Checkpoint20CliTests(unittest.TestCase):
    def test_main_endpoint_check_local_delegates_with_flag(self):
        output = io.StringIO()
        calls = []

        def endpoint_checker(env, output_arg):
            calls.append((env["argv"], output_arg))
            return 0

        exit_code = main(
            ["endpoint-check", "--local"],
            env={"PUBLIC_BASE_URL": "https://public.example.test"},
            output=output,
            endpoint_checker=endpoint_checker,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [(["endpoint-check", "--local"], output)])


if __name__ == "__main__":
    unittest.main()
