import asyncio
import importlib
import json
from urllib.parse import urlencode

from pgai_patient_bot.audio import TELEPHONY_AUDIO_FORMAT, pcmu_silence_payload


REALTIME_MODEL = "gpt-realtime-2"
REALTIME_WEBSOCKET_BASE_URL = "wss://api.openai.com/v1/realtime"
DEFAULT_TURN_DETECTION = object()


class FakeRealtimeConnection:
    # Test double for the WebSocket shape used by the future live Realtime adapter.
    def __init__(self, responses):
        self.responses = dict(responses)
        self.sent = []
        self._incoming = []
        self.closed = False

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

    async def close(self):
        self.closed = True


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


async def async_live_realtime_smoke(
    api_key,
    opener=None,
    safety_identifier="patient-bot-local",
):
    opener = open_realtime_connection if opener is None else opener
    connection = await _maybe_await(opener(api_key, safety_identifier=safety_identifier))
    try:
        await configure_realtime_connection(connection, "Realtime smoke test.")
        return await _next_session_result(connection)
    finally:
        await connection.close()


def live_realtime_smoke(api_key, opener=None, safety_identifier="patient-bot-local"):
    return asyncio.run(
        async_live_realtime_smoke(
            api_key,
            opener=opener,
            safety_identifier=safety_identifier,
        )
    )


async def async_live_realtime_audio_smoke(
    api_key,
    opener=None,
    safety_identifier="patient-bot-local",
    payload=None,
):
    opener = open_realtime_connection if opener is None else opener
    connection = await _maybe_await(opener(api_key, safety_identifier=safety_identifier))
    try:
        await configure_realtime_connection(
            connection,
            "Realtime audio append smoke test.",
            turn_detection=None,
        )
        event = await _next_session_result(connection)
        if event.get("type") == "error":
            return event

        await connection.send(input_audio_event(payload or pcmu_silence_payload(200)))
        await connection.send(input_audio_commit_event())
        return json.loads(await connection.recv())
    finally:
        await connection.close()


def live_realtime_audio_smoke(
    api_key,
    opener=None,
    safety_identifier="patient-bot-local",
):
    return asyncio.run(
        async_live_realtime_audio_smoke(
            api_key,
            opener=opener,
            safety_identifier=safety_identifier,
        )
    )


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value


async def _next_session_result(connection):
    event = json.loads(await connection.recv())
    if event.get("type") == "session.created":
        event = json.loads(await connection.recv())
    return event


def realtime_session_update(
    instructions,
    model="gpt-realtime-2",
    voice="marin",
    turn_detection=DEFAULT_TURN_DETECTION,
):
    if turn_detection is DEFAULT_TURN_DETECTION:
        turn_detection = {
            "type": "server_vad",
            "create_response": True,
            "interrupt_response": True,
        }

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
                        "turn_detection": turn_detection,
                    },
                    "output": {
                        "format": TELEPHONY_AUDIO_FORMAT,
                        "voice": voice,
                    },
                },
            },
        }
    )


async def configure_realtime_connection(
    connection,
    instructions,
    turn_detection=DEFAULT_TURN_DETECTION,
):
    await connection.send(
        realtime_session_update(instructions, turn_detection=turn_detection)
    )


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


def input_audio_commit_event():
    return json.dumps({"type": "input_audio_buffer.commit"})


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
