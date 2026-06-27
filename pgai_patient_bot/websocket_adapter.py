import asyncio
from contextlib import suppress
import json

from pgai_patient_bot.media import MediaBridge
from pgai_patient_bot.openai_realtime import (
    configure_realtime_connection,
    input_audio_event,
    open_realtime_connection,
    output_audio_delta,
)


PATIENT_REALTIME_GUARD = (
    "You are the patient in this phone call. Keep acting as the patient until "
    "the other bot stops answering."
)
DEFAULT_BOT_SILENCE_TIMEOUT_SECONDS = 30


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


async def handle_media_websocket(websocket, model_audio_for, audio_recorder=None):
    bridge = MediaBridge()
    sent_count = 0

    async for message in websocket:
        event = json.loads(message)
        bridge.receive_twilio(message)

        if audio_recorder and event.get("event") == "start":
            start = event.get("start", {})
            audio_recorder.remember(
                twilio_call_sid=start.get("callSid"),
                twilio_stream_sid=start.get("streamSid"),
            )

        if bridge.closed:
            break
        if event.get("event") != "media":
            continue

        caller_payload = event["media"]["payload"]
        if audio_recorder:
            audio_recorder.record("inbound", caller_payload)

        model_payload = await model_audio_for(caller_payload)
        if model_payload:
            if audio_recorder:
                audio_recorder.record("outbound", model_payload)
            await websocket.send(bridge.twilio_audio(model_payload))
            sent_count += 1

    return sent_count


async def handle_realtime_media_websocket(
    websocket,
    realtime,
    instructions,
    audio_recorder=None,
    bot_silence_timeout=DEFAULT_BOT_SILENCE_TIMEOUT_SECONDS,
):
    bridge = MediaBridge()
    sent_count = 0
    receiver_task = None
    waiting_for_bot = False
    close_reason = "unknown"

    async def receive_realtime_audio():
        nonlocal sent_count, waiting_for_bot
        while True:
            text = await realtime.recv()
            event = json.loads(text)
            payload = output_audio_delta(text)
            if not payload:
                if event.get("type") == "response.done":
                    return
                continue
            if not bridge.stream_sid:
                continue
            if audio_recorder:
                audio_recorder.record("outbound", payload)
            await websocket.send(bridge.twilio_audio(payload))
            sent_count += 1
            waiting_for_bot = True

    async def start_receiver():
        nonlocal receiver_task
        if receiver_task is None or receiver_task.done():
            receiver_task = asyncio.create_task(receive_realtime_audio())

    try:
        bridge_log("start")
        await configure_realtime_connection(realtime, patient_realtime_instructions(instructions))
        messages = websocket.__aiter__()
        while True:
            try:
                message = await next_twilio_message(
                    messages,
                    waiting_for_bot,
                    bot_silence_timeout,
                )
            except StopAsyncIteration:
                close_reason = "twilio_iterator_stopped"
                break
            except asyncio.TimeoutError:
                close_reason = "bot_silence_timeout"
                bridge_log("close", reason=close_reason, sent_count=sent_count)
                break

            event = json.loads(message)
            bridge.receive_twilio(message)

            if audio_recorder and event.get("event") == "start":
                start = event.get("start", {})
                audio_recorder.remember(
                    twilio_call_sid=start.get("callSid"),
                    twilio_stream_sid=start.get("streamSid"),
                )

            if bridge.closed:
                close_reason = "twilio_stop"
                bridge_log("close", reason=close_reason, sent_count=sent_count)
                break
            if event.get("event") != "media":
                continue

            waiting_for_bot = False
            caller_payload = event["media"]["payload"]
            if audio_recorder:
                audio_recorder.record("inbound", caller_payload)
            await realtime.send(input_audio_event(caller_payload))
            await start_receiver()
            await asyncio.sleep(0)

        return sent_count
    except Exception as error:
        close_reason = f"exception:{type(error).__name__}"
        bridge_log("close", reason=close_reason, sent_count=sent_count)
        raise
    finally:
        if receiver_task:
            receiver_task.cancel()
            with suppress(asyncio.CancelledError):
                await receiver_task
        close = getattr(realtime, "close", None)
        if close:
            await close()
        bridge_log("cleanup", reason=close_reason, sent_count=sent_count)


async def handle_live_media_websocket(
    websocket,
    api_key,
    instructions,
    opener=open_realtime_connection,
    safety_identifier="patient-bot-local",
    audio_recorder=None,
):
    realtime = await _maybe_await(
        opener(api_key, safety_identifier=safety_identifier)
    )
    return await handle_realtime_media_websocket(
        websocket,
        realtime,
        instructions,
        audio_recorder=audio_recorder,
    )


async def next_twilio_message(messages, waiting_for_bot, bot_silence_timeout):
    if waiting_for_bot:
        return await asyncio.wait_for(messages.__anext__(), timeout=bot_silence_timeout)
    return await messages.__anext__()


def patient_realtime_instructions(instructions):
    return f"{PATIENT_REALTIME_GUARD}\n\n{instructions}"


def bridge_log(event, **fields):
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"[bridge] {event} {details}".rstrip(), flush=True)


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value
