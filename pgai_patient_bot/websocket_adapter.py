import json

from pgai_patient_bot.media import MediaBridge
from pgai_patient_bot.openai_realtime import (
    configure_realtime_connection,
    open_realtime_connection,
    realtime_audio_from_connection,
)


class FakeWebSocket:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.incoming):
            raise StopAsyncIteration
        message = self.incoming[self._index]
        self._index += 1
        return message

    async def send(self, message):
        self.sent.append(message)


async def handle_media_websocket(websocket, model_audio_for):
    bridge = MediaBridge()
    sent_count = 0

    async for message in websocket:
        event = json.loads(message)
        bridge.receive_twilio(message)

        if bridge.closed:
            break
        if event.get("event") != "media":
            continue

        model_payload = await model_audio_for(event["media"]["payload"])
        if model_payload:
            await websocket.send(bridge.twilio_audio(model_payload))
            sent_count += 1

    return sent_count


async def handle_realtime_media_websocket(websocket, realtime, instructions):
    try:
        await configure_realtime_connection(realtime, instructions)
        return await handle_media_websocket(
            websocket,
            lambda payload: realtime_audio_from_connection(realtime, payload),
        )
    finally:
        close = getattr(realtime, "close", None)
        if close:
            await close()


async def handle_live_media_websocket(
    websocket,
    api_key,
    instructions,
    opener=open_realtime_connection,
    safety_identifier="patient-bot-local",
):
    realtime = await _maybe_await(
        opener(api_key, safety_identifier=safety_identifier)
    )
    return await handle_realtime_media_websocket(websocket, realtime, instructions)


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value
