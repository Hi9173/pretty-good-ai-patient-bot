import json
import tempfile
import unittest

from pgai_patient_bot.audio import REAL_PCMU_SILENCE, TELEPHONY_AUDIO_MIME_TYPE
from pgai_patient_bot.artifacts import AudioArtifactRecorder
from pgai_patient_bot import media_server, public_server
from pgai_patient_bot.checkpoint import Config
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_media_websocket


class Checkpoint26Tests(unittest.TestCase):
    def test_audio_recorder_writes_raw_pcmu_chunks_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = AudioArtifactRecorder(tmp, "call-live-001")

            inbound = recorder.record("inbound", REAL_PCMU_SILENCE)
            outbound = recorder.record("outbound", REAL_PCMU_SILENCE)

            self.assertEqual(inbound.name, "inbound-0001.pcmu")
            self.assertEqual(outbound.name, "outbound-0001.pcmu")
            self.assertEqual(inbound.read_bytes(), b"\xff\xff\xff\xff")
            self.assertEqual(outbound.read_bytes(), b"\xff\xff\xff\xff")

            manifest = json.loads(
                (inbound.parent.parent / "audio_manifest.json").read_text()
            )
            self.assertEqual(
                manifest["chunks"],
                [
                    {
                        "direction": "inbound",
                        "file": "audio/inbound-0001.pcmu",
                        "mime_type": TELEPHONY_AUDIO_MIME_TYPE,
                        "bytes": 4,
                    },
                    {
                        "direction": "outbound",
                        "file": "audio/outbound-0001.pcmu",
                        "mime_type": TELEPHONY_AUDIO_MIME_TYPE,
                        "bytes": 4,
                    },
                ],
            )

    def test_audio_recorder_factory_can_use_stable_artifact_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            factory = media_server.audio_recorder_factory_from_env(
                {
                    "CALL_ARTIFACT_ROOT": tmp,
                    "CALL_ARTIFACT_ID": "returning_patient_dob_verification",
                }
            )

            recorder = factory()

            self.assertEqual(
                recorder.call_dir.name,
                "returning_patient_dob_verification",
            )

    def test_media_bridge_records_inbound_and_outbound_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = AudioArtifactRecorder(tmp, "call-live-001")
            twilio = FakeWebSocket(
                twilio_mock_call([REAL_PCMU_SILENCE], stream_sid="MZREC")
            )

            async def model_audio_for(_payload):
                return REAL_PCMU_SILENCE

            sent_count = __import__("asyncio").run(
                handle_media_websocket(
                    twilio,
                    model_audio_for,
                    audio_recorder=recorder,
                )
            )

            self.assertEqual(sent_count, 1)
            self.assertEqual(
                sorted(path.name for path in (recorder.call_dir / "audio").iterdir()),
                ["inbound-0001.pcmu", "outbound-0001.pcmu"],
            )
            manifest = json.loads((recorder.call_dir / "audio_manifest.json").read_text())
            self.assertEqual(
                [chunk["direction"] for chunk in manifest["chunks"]],
                ["inbound", "outbound"],
            )

    def test_media_bridge_records_twilio_call_identifiers_in_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = AudioArtifactRecorder(tmp, "call-live-001")
            twilio = FakeWebSocket(
                [
                    json.dumps(
                        {
                            "event": "start",
                            "start": {"streamSid": "MZREC", "callSid": "CAREC"},
                        }
                    ),
                    json.dumps(
                        {"event": "media", "media": {"payload": REAL_PCMU_SILENCE}}
                    ),
                    json.dumps({"event": "stop"}),
                ]
            )

            async def model_audio_for(_payload):
                return None

            __import__("asyncio").run(
                handle_media_websocket(
                    twilio,
                    model_audio_for,
                    audio_recorder=recorder,
                )
            )

            manifest = json.loads((recorder.call_dir / "audio_manifest.json").read_text())
            self.assertEqual(
                manifest["metadata"],
                {"twilio_call_sid": "CAREC", "twilio_stream_sid": "MZREC"},
            )

    def test_media_handler_passes_optional_audio_recorder_to_bridge(self):
        calls = []
        recorder = object()
        websocket = type(
            "WebSocket",
            (),
            {"path": "/media"},
        )()

        async def bridge(websocket_arg, api_key, instructions, audio_recorder=None):
            calls.append((websocket_arg, api_key, instructions, audio_recorder))
            return 0

        sent_count = __import__("asyncio").run(
            media_server.media_handler(
                websocket,
                "secret-key",
                "Act like a patient.",
                bridge=bridge,
                audio_recorder_factory=lambda: recorder,
            )
        )

        self.assertEqual(sent_count, 0)
        self.assertEqual(
            calls,
            [(websocket, "secret-key", "Act like a patient.", recorder)],
        )

    def test_public_server_passes_audio_recorder_to_media_handler(self):
        calls = []
        recorder = object()
        websocket = type("WebSocket", (), {"path": "/media"})()
        config = Config(
            account_sid="ACLOCALTEST",
            auth_token="secret-token",
            from_number="+15555550123",
            public_base_url="https://public.example.test",
        )

        async def bridge(websocket_arg, api_key, instructions, audio_recorder=None):
            calls.append((websocket_arg, api_key, instructions, audio_recorder))
            return 0

        async def server_factory(handler, _host, _port, process_request=None, **_kwargs):
            await handler(websocket)
            return object()

        __import__("asyncio").run(
            public_server.serve_public_websocket(
                "127.0.0.1",
                8000,
                "secret-key",
                config,
                "Act like a patient.",
                server_factory=server_factory,
                bridge=bridge,
                audio_recorder_factory=lambda: recorder,
            )
        )

        self.assertEqual(
            calls,
            [(websocket, "secret-key", "Act like a patient.", recorder)],
        )


if __name__ == "__main__":
    unittest.main()
