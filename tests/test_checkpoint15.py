import asyncio
import contextlib
import io
import json
import unittest

from pgai_patient_bot.audio import symbolic_audio
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.openai_realtime import FakeRealtimeConnection
from pgai_patient_bot import websocket_adapter
from pgai_patient_bot.websocket_adapter import FakeWebSocket


class OrderedWebSocket:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []
        self.events = []

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.incoming):
            raise StopAsyncIteration
        message = self.incoming[self._index]
        self._index += 1
        self.events.append(f"recv:{json.loads(message)['event']}")
        return message

    async def send(self, message):
        self.events.append(f"send:{json.loads(message)['event']}")
        self.sent.append(message)


class Checkpoint15Tests(unittest.TestCase):
    def test_default_bot_silence_timeout_waits_thirty_seconds(self):
        self.assertEqual(websocket_adapter.DEFAULT_BOT_SILENCE_TIMEOUT_SECONDS, 30)

    def test_realtime_media_bridge_configures_realtime_and_returns_audio_to_twilio(self):
        caller_audio = symbolic_audio("caller-live")
        model_audio = symbolic_audio("patient-live")
        twilio = FakeWebSocket(twilio_mock_call([caller_audio], stream_sid="MZBRIDGE"))
        realtime = FakeRealtimeConnection({caller_audio: model_audio})

        self.assertTrue(hasattr(websocket_adapter, "handle_realtime_media_websocket"))

        sent_count = asyncio.run(
            websocket_adapter.handle_realtime_media_websocket(
                twilio,
                realtime,
                "Act like a patient.",
            )
        )

        self.assertEqual(sent_count, 1)
        self.assertEqual(
            [json.loads(message)["type"] for message in realtime.sent],
            ["session.update", "input_audio_buffer.append"],
        )
        session = json.loads(realtime.sent[0])["session"]
        self.assertIn("You are the patient", session["instructions"])
        self.assertIn("Act like a patient.", session["instructions"])
        self.assertEqual(json.loads(twilio.sent[0])["media"]["payload"], model_audio)
        self.assertTrue(realtime.closed)

    def test_media_websocket_sends_model_audio_before_waiting_for_stop(self):
        caller_audio = symbolic_audio("caller-stream")
        model_audio = symbolic_audio("patient-stream")
        twilio = OrderedWebSocket(twilio_mock_call([caller_audio], stream_sid="MZORDER"))
        realtime = FakeRealtimeConnection({caller_audio: model_audio})

        self.assertTrue(hasattr(websocket_adapter, "handle_realtime_media_websocket"))

        asyncio.run(
            websocket_adapter.handle_realtime_media_websocket(
                twilio,
                realtime,
                "Stream responses.",
            )
        )

        self.assertEqual(
            twilio.events,
            ["recv:start", "recv:media", "send:media", "recv:stop"],
        )

    def test_live_media_bridge_opens_realtime_without_exposing_api_key(self):
        caller_audio = symbolic_audio("caller-live-open")
        model_audio = symbolic_audio("patient-live-open")
        twilio = FakeWebSocket(twilio_mock_call([caller_audio], stream_sid="MZLIVE"))
        realtime = FakeRealtimeConnection({caller_audio: model_audio})
        opened = {}

        async def opener(api_key, safety_identifier=None):
            opened["api_key"] = api_key
            opened["safety_identifier"] = safety_identifier
            return realtime

        self.assertTrue(hasattr(websocket_adapter, "handle_live_media_websocket"))

        sent_count = asyncio.run(
            websocket_adapter.handle_live_media_websocket(
                twilio,
                "secret-key",
                "Act like a patient.",
                opener=opener,
                safety_identifier="patient-bot-local",
            )
        )

        self.assertEqual(sent_count, 1)
        self.assertEqual(opened, {
            "api_key": "secret-key",
            "safety_identifier": "patient-bot-local",
        })
        self.assertNotIn("secret-key", "".join(twilio.sent + realtime.sent))

    def test_realtime_media_bridge_ends_after_other_bot_silence(self):
        caller_audio = symbolic_audio("caller-silence")
        model_audio = symbolic_audio("patient-silence")

        class SilentAfterFirstMedia:
            sent = []

            def __aiter__(self):
                self.index = 0
                self.messages = twilio_mock_call(
                    [caller_audio],
                    stream_sid="MZSILENCE",
                )[:2]
                return self

            async def __anext__(self):
                if self.index >= len(self.messages):
                    await asyncio.Event().wait()
                message = self.messages[self.index]
                self.index += 1
                return message

            async def send(self, message):
                self.sent.append(message)

        twilio = SilentAfterFirstMedia()
        realtime = FakeRealtimeConnection({caller_audio: model_audio})

        sent_count = asyncio.run(
            websocket_adapter.handle_realtime_media_websocket(
                twilio,
                realtime,
                "Act like a patient.",
                bot_silence_timeout=0.01,
            )
        )

        self.assertEqual(sent_count, 1)
        self.assertTrue(realtime.closed)

    def test_realtime_media_bridge_logs_timeout_close_reason(self):
        caller_audio = symbolic_audio("caller-silence-log")
        model_audio = symbolic_audio("patient-silence-log")

        class SilentAfterFirstMedia:
            sent = []

            def __aiter__(self):
                self.index = 0
                self.messages = twilio_mock_call(
                    [caller_audio],
                    stream_sid="MZSILENCELOG",
                )[:2]
                return self

            async def __anext__(self):
                if self.index >= len(self.messages):
                    await asyncio.Event().wait()
                message = self.messages[self.index]
                self.index += 1
                return message

            async def send(self, message):
                self.sent.append(message)

        twilio = SilentAfterFirstMedia()
        realtime = FakeRealtimeConnection({caller_audio: model_audio})
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            sent_count = asyncio.run(
                websocket_adapter.handle_realtime_media_websocket(
                    twilio,
                    realtime,
                    "Act like a patient.",
                    bot_silence_timeout=0.01,
                )
            )

        self.assertEqual(sent_count, 1)
        self.assertIn("[bridge] close reason=bot_silence_timeout", output.getvalue())
        self.assertIn(
            "[bridge] cleanup reason=bot_silence_timeout sent_count=1",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
