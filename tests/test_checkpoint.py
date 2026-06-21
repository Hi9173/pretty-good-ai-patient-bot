from urllib.parse import parse_qs
from xml.etree import ElementTree

import unittest

from pgai_patient_bot.checkpoint import (
    TEST_NUMBER,
    build_call_request,
    load_config,
    twiml_for_stream,
)


class CheckpointTest(unittest.TestCase):
    def test_load_config_reads_required_values_and_normalizes_public_url(self):
        config = load_config(
            {
                "TWILIO_ACCOUNT_SID": "AC123",
                "TWILIO_AUTH_TOKEN": "secret",
                "TWILIO_FROM_NUMBER": "+15551234567",
                "PUBLIC_BASE_URL": "https://example.ngrok-free.app/",
            }
        )

        self.assertEqual(config.account_sid, "AC123")
        self.assertEqual(config.auth_token, "secret")
        self.assertEqual(config.from_number, "+15551234567")
        self.assertEqual(config.public_base_url, "https://example.ngrok-free.app")

    def test_load_config_reports_missing_environment_names(self):
        with self.assertRaisesRegex(ValueError, "TWILIO_AUTH_TOKEN, PUBLIC_BASE_URL"):
            load_config(
                {
                    "TWILIO_ACCOUNT_SID": "AC123",
                    "TWILIO_FROM_NUMBER": "+15551234567",
                }
            )

    def test_twiml_for_stream_connects_to_media_websocket(self):
        xml = twiml_for_stream("wss://example.ngrok-free.app/media")

        root = ElementTree.fromstring(xml)
        stream = root.find("./Connect/Stream")

        self.assertEqual(root.tag, "Response")
        self.assertIsNotNone(stream)
        self.assertEqual(stream.attrib["url"], "wss://example.ngrok-free.app/media")

    def test_build_call_request_targets_only_the_assessment_number(self):
        config = load_config(
            {
                "TWILIO_ACCOUNT_SID": "AC123",
                "TWILIO_AUTH_TOKEN": "secret",
                "TWILIO_FROM_NUMBER": "+15551234567",
                "PUBLIC_BASE_URL": "https://example.ngrok-free.app",
            }
        )

        request = build_call_request(config)
        body = parse_qs(request.data.decode())

        self.assertEqual(
            request.full_url,
            "https://api.twilio.com/2010-04-01/Accounts/AC123/Calls.json",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(body["To"], [TEST_NUMBER])
        self.assertEqual(body["From"], ["+15551234567"])
        self.assertEqual(body["Url"], ["https://example.ngrok-free.app/twiml"])


if __name__ == "__main__":
    unittest.main()
