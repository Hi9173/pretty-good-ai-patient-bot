import json


class MediaBridge:
    def __init__(self):
        self.stream_sid = None
        self.inbound_audio = []
        self.closed = False

    def receive_twilio(self, text):
        message = json.loads(text)
        event = message.get("event")

        if event == "start":
            self.stream_sid = message["start"]["streamSid"]
        elif event == "media":
            self.inbound_audio.append(message["media"]["payload"])
        elif event == "stop":
            self.closed = True

    def twilio_audio(self, payload):
        if not self.stream_sid:
            raise ValueError("cannot send audio before Twilio stream SID is known")

        return json.dumps(
            {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": payload},
            }
        )


async def run_media_loop(twilio_messages, model_audio_for):
    bridge = MediaBridge()
    outbound = []

    for text in twilio_messages:
        message = json.loads(text)
        bridge.receive_twilio(text)

        if bridge.closed:
            break
        if message.get("event") != "media":
            continue

        # The model callback is the only seam between Twilio media and Realtime audio.
        model_payload = await model_audio_for(message["media"]["payload"])
        if model_payload:
            outbound.append(bridge.twilio_audio(model_payload))

    return outbound
