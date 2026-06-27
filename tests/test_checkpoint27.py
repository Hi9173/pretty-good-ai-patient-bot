import asyncio
import json
import tempfile
import unittest

from pgai_patient_bot.artifacts import AudioArtifactRecorder
from pgai_patient_bot.audio import REAL_PCMU_SILENCE
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_realtime_media_websocket


class DelayedRealtimeConnection:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.append_count = 0
        self.ready = asyncio.Event()
        self.recv_count = 0

    async def send(self, message):
        self.sent.append(message)
        if json.loads(message).get("type") == "input_audio_buffer.append":
            self.append_count += 1
            if self.append_count == 2:
                self.ready.set()

    async def recv(self):
        await self.ready.wait()
        self.recv_count += 1
        if self.recv_count == 1:
            return json.dumps({"type": "input_audio_buffer.speech_stopped"})
        if self.recv_count == 2:
            return json.dumps(
                {
                    "type": "response.output_audio.delta",
                    "delta": REAL_PCMU_SILENCE,
                }
            )
        await asyncio.Event().wait()

    async def close(self):
        self.closed = True


class Checkpoint27Tests(unittest.TestCase):
    def test_realtime_bridge_keeps_forwarding_audio_while_waiting_for_output(self):
        twilio = FakeWebSocket(
            twilio_mock_call(
                [REAL_PCMU_SILENCE, REAL_PCMU_SILENCE],
                stream_sid="MZDELAYED",
            )
        )
        realtime = DelayedRealtimeConnection()

        with tempfile.TemporaryDirectory() as tmp:
            recorder = AudioArtifactRecorder(tmp, "call-live-001")
            sent_count = asyncio.run(
                asyncio.wait_for(
                    handle_realtime_media_websocket(
                        twilio,
                        realtime,
                        "Act like a patient.",
                        audio_recorder=recorder,
                    ),
                    timeout=0.5,
                )
            )

            self.assertEqual(sent_count, 1)
            self.assertEqual(
                [json.loads(message)["type"] for message in realtime.sent],
                [
                    "session.update",
                    "input_audio_buffer.append",
                    "input_audio_buffer.append",
                ],
            )
            self.assertEqual(
                json.loads(twilio.sent[0])["media"]["payload"],
                REAL_PCMU_SILENCE,
            )

            manifest = json.loads((recorder.call_dir / "audio_manifest.json").read_text())
            self.assertEqual(
                [chunk["direction"] for chunk in manifest["chunks"]],
                ["inbound", "inbound", "outbound"],
            )
            self.assertTrue(realtime.closed)

    def test_realtime_bridge_closes_realtime_when_twilio_disconnects_early(self):
        class ClosingTwilio:
            sent = []

            def __aiter__(self):
                self.index = 0
                self.messages = twilio_mock_call([REAL_PCMU_SILENCE], stream_sid="MZBYE")
                return self

            async def __anext__(self):
                if self.index == 2:
                    raise ConnectionError("twilio disconnected")
                message = self.messages[self.index]
                self.index += 1
                return message

        class BlockingRealtime(DelayedRealtimeConnection):
            def __init__(self):
                super().__init__()
                self.recv_cancelled = False
                self.closed_before_recv_cancel = False

            async def recv(self):
                try:
                    await asyncio.Event().wait()
                finally:
                    self.recv_cancelled = True

            async def close(self):
                self.closed_before_recv_cancel = not self.recv_cancelled
                await super().close()

        realtime = BlockingRealtime()

        with self.assertRaises(ConnectionError):
            asyncio.run(
                handle_realtime_media_websocket(
                    ClosingTwilio(),
                    realtime,
                    "Act like a patient.",
                )
            )

        self.assertTrue(realtime.closed)
        self.assertFalse(realtime.closed_before_recv_cancel)


if __name__ == "__main__":
    unittest.main()
