import io
import unittest
from types import SimpleNamespace

from pgai_patient_bot import public_server
from pgai_patient_bot.checkpoint import Config
from pgai_patient_bot.cli import main


class Checkpoint23Tests(unittest.IsolatedAsyncioTestCase):
    async def test_public_process_request_serves_twiml_on_websocket_port(self):
        config = Config(
            account_sid="ACLOCALTEST",
            auth_token="secret-token",
            from_number="+15555550123",
            public_base_url="https://public.example.test",
        )
        process_request = public_server.make_process_request(config)

        response = process_request(None, SimpleNamespace(path="/twiml"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/xml")
        self.assertIn(
            'Stream url="wss://public.example.test/media"',
            response.body.decode(),
        )

    async def test_public_process_request_allows_media_websocket_handshake(self):
        config = Config(
            account_sid="ACLOCALTEST",
            auth_token="secret-token",
            from_number="+15555550123",
            public_base_url="https://public.example.test",
        )
        process_request = public_server.make_process_request(config)

        self.assertIsNone(process_request(None, SimpleNamespace(path="/media?probe=1")))


class Checkpoint23CliTests(unittest.TestCase):
    def test_main_serve_public_requires_live_flag_and_api_key(self):
        output = io.StringIO()

        missing_flag = main(["serve-public"], env={}, output=output)
        missing_key = main(["serve-public", "--live"], env={}, output=output)

        self.assertEqual(missing_flag, 2)
        self.assertEqual(missing_key, 2)
        self.assertIn("serve-public --live", output.getvalue())
        self.assertIn("OPENAI_API_KEY is required", output.getvalue())

    def test_main_serve_public_delegates_without_printing_key(self):
        output = io.StringIO()
        calls = []

        def runner(env, output_arg):
            calls.append((env["OPENAI_API_KEY"], output_arg))
            return 0

        exit_code = main(
            ["serve-public", "--live"],
            env={"OPENAI_API_KEY": "secret-key"},
            output=output,
            public_server_runner=runner,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("secret-key", output)])
        self.assertNotIn("secret-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
