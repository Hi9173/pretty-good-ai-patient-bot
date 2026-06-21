from pgai_patient_bot.media import run_media_loop


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
    inbound = []
    async for message in websocket:
        inbound.append(message)

    outbound = await run_media_loop(inbound, model_audio_for)
    for message in outbound:
        await websocket.send(message)
    return len(outbound)
