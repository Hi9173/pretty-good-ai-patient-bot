import json

from pgai_patient_bot.audio import TELEPHONY_AUDIO_FORMAT


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
