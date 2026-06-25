import asyncio
import importlib
import json
from urllib.parse import urlencode

from pgai_patient_bot.audio import TELEPHONY_AUDIO_FORMAT


REALTIME_MODEL = "gpt-realtime-2"
REALTIME_WEBSOCKET_BASE_URL = "wss://api.openai.com/v1/realtime"


class FakeRealtimeConnection:
    # Test double for the WebSocket shape used by the future live Realtime adapter.
    def __init__(self, responses):
        self.responses = dict(responses)
        self.sent = []
        self._incoming = []

    async def send(self, message):
        self.sent.append(message)
        event = json.loads(message)
        if event.get("type") == "input_audio_buffer.append":
            response = self.responses.get(event["audio"])
            if response is not None:
                self._incoming.append(
                    json.dumps(
                        {
                            "type": "response.output_audio.delta",
                            "delta": response,
                        }
                    )
                )

    async def recv(self):
        if self._incoming:
            return self._incoming.pop(0)
        return json.dumps({"type": "response.done"})


class RealtimeWebSocketConnection:
    def __init__(self, websocket):
        self.websocket = websocket

    async def send(self, message):
        await asyncio.to_thread(self.websocket.send, message)

    async def recv(self):
        return await asyncio.to_thread(self.websocket.recv)

    async def close(self):
        await asyncio.to_thread(self.websocket.close)


def realtime_websocket_url(model=REALTIME_MODEL):
    return f"{REALTIME_WEBSOCKET_BASE_URL}?{urlencode({'model': model})}"


def realtime_headers(api_key, safety_identifier=None):
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")

    headers = [f"Authorization: Bearer {api_key}"]
    if safety_identifier:
        headers.append(f"OpenAI-Safety-Identifier: {safety_identifier}")
    return headers


def open_realtime_connection(
    api_key,
    model=REALTIME_MODEL,
    safety_identifier=None,
    websocket_module=None,
):
    if websocket_module is None:
        websocket_module = importlib.import_module("websocket")

    websocket = websocket_module.create_connection(
        realtime_websocket_url(model),
        header=realtime_headers(api_key, safety_identifier),
    )
    return RealtimeWebSocketConnection(websocket)


def realtime_session_update(
    instructions,
    model="gpt-realtime-2",
    voice="marin",
):
    return json.dumps(
        {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": model,
                "instructions": instructions,
                "audio": {
                    "input": {
                        "format": TELEPHONY_AUDIO_FORMAT,
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "format": TELEPHONY_AUDIO_FORMAT,
                        "voice": voice,
                    },
                },
            },
        }
    )


async def configure_realtime_connection(connection, instructions):
    await connection.send(realtime_session_update(instructions))


async def realtime_audio_from_connection(connection, payload):
    # One caller audio frame maps to the next mocked output audio delta.
    await connection.send(input_audio_event(payload))
    return output_audio_delta(await connection.recv())


def input_audio_event(payload):
    return json.dumps(
        {
            "type": "input_audio_buffer.append",
            "audio": payload,
        }
    )


def output_audio_delta(text):
    event = json.loads(text)
    if event.get("type") == "response.output_audio.delta":
        return event["delta"]
    return None


def fake_realtime_audio(responses):
    async def model(payload):
        input_audio_event(payload)
        response = responses.get(payload)
        if response is None:
            return None
        return output_audio_delta(
            json.dumps(
                {
                    "type": "response.output_audio.delta",
                    "delta": response,
                }
            )
        )

    return model
