import io
import unittest
from xml.etree import ElementTree

from pgai_patient_bot.app import make_server, media_websocket_url, response_for_path
from pgai_patient_bot.checkpoint import TEST_NUMBER, load_config
from pgai_patient_bot.cli import dry_run_call, main


def sample_config():
    return load_config(sample_config_env())


def sample_config_env():
    return {
        "TWILIO_ACCOUNT_SID": "AC123",
        "TWILIO_AUTH_TOKEN": "secret",
        "TWILIO_FROM_NUMBER": "+15551234567",
        "PUBLIC_BASE_URL": "https://example.ngrok-free.app/",
    }


class Checkpoint2Test(unittest.TestCase):
    def test_media_websocket_url_rewrites_https_public_url(self):
        self.assertEqual(
            media_websocket_url(sample_config()),
            "wss://example.ngrok-free.app/media",
        )

    def test_twiml_path_returns_stream_response(self):
        status, headers, body = response_for_path("/twiml", sample_config())

        root = ElementTree.fromstring(body)
        stream = root.find("./Connect/Stream")

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/xml")
        self.assertIsNotNone(stream)
        self.assertEqual(stream.attrib["url"], "wss://example.ngrok-free.app/media")

    def test_twiml_path_uses_separate_public_media_base_when_present(self):
        env = sample_config_env()
        env["PUBLIC_MEDIA_BASE_URL"] = "https://media.ngrok-free.app/"

        status, headers, body = response_for_path("/twiml", load_config(env))
        stream = ElementTree.fromstring(body).find("./Connect/Stream")

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/xml")
        self.assertEqual(stream.attrib["url"], "wss://media.ngrok-free.app/media")

    def test_unknown_path_returns_404(self):
        status, headers, body = response_for_path("/nope", sample_config())

        self.assertEqual(status, 404)
        self.assertEqual(headers["Content-Type"], "text/plain")
        self.assertEqual(body, "not found\n")

    def test_dry_run_call_prints_request_without_auth_token(self):
        output = io.StringIO()

        exit_code = dry_run_call(sample_config(), output)
        text = output.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("POST https://api.twilio.com/2010-04-01/Accounts/AC123/Calls.json", text)
        self.assertIn(f"To: {TEST_NUMBER}", text)
        self.assertIn("From: +15551234567", text)
        self.assertIn("Url: https://example.ngrok-free.app/twiml", text)
        self.assertNotIn("secret", text)

    def test_make_server_serves_twiml_over_http(self):
        class FakeServer:
            def __init__(self, address, handler):
                self.address = address
                self.handler = handler

        server = make_server(sample_config_env(), port=0, server_class=FakeServer)

        self.assertEqual(server.address, ("127.0.0.1", 0))
        self.assertTrue(callable(server.handler))

    def test_main_dry_run_reads_environment(self):
        output = io.StringIO()

        exit_code = main(["dry-run-call"], env=sample_config_env(), output=output)

        self.assertEqual(exit_code, 0)
        self.assertIn(f"To: {TEST_NUMBER}", output.getvalue())

    def test_main_unknown_command_prints_usage(self):
        output = io.StringIO()

        exit_code = main(["wat"], env=sample_config_env(), output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("usage:", output.getvalue())

    def test_main_serve_delegates_to_server_factory(self):
        output = io.StringIO()
        calls = []

        class FakeServer:
            def serve_forever(self):
                calls.append("served")

        def fake_server_factory(env):
            calls.append(env["TWILIO_ACCOUNT_SID"])
            return FakeServer()

        exit_code = main(
            ["serve"],
            env=sample_config_env(),
            output=output,
            server_factory=fake_server_factory,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["AC123", "served"])


if __name__ == "__main__":
    unittest.main()
