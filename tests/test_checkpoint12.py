import asyncio
import unittest

from pgai_patient_bot.openai_realtime import (
    RealtimeWebSocketConnection,
    open_realtime_connection,
    realtime_headers,
    realtime_websocket_url,
)


class DummySocket:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def recv(self):
        return '{"type":"response.done"}'

    def close(self):
        self.closed = True


class DummyWebSocketModule:
    def __init__(self):
        self.socket = DummySocket()
        self.url = None
        self.header = None

    def create_connection(self, url, header):
        self.url = url
        self.header = header
        return self.socket


class Checkpoint12Tests(unittest.TestCase):
    def test_realtime_url_and_headers_match_openai_websocket_shape(self):
        self.assertEqual(
            realtime_websocket_url(),
            "wss://api.openai.com/v1/realtime?model=gpt-realtime-2",
        )
        self.assertEqual(
            realtime_headers("test-api-key", safety_identifier="patient-bot-local"),
            [
                "Authorization: Bearer test-api-key",
                "OpenAI-Safety-Identifier: patient-bot-local",
            ],
        )

    def test_realtime_headers_reject_missing_api_key(self):
        with self.assertRaises(ValueError):
            realtime_headers("")

    def test_open_realtime_connection_wraps_websocket_send_recv(self):
        websocket_module = DummyWebSocketModule()

        connection = open_realtime_connection(
            "test-api-key",
            safety_identifier="patient-bot-local",
            websocket_module=websocket_module,
        )

        self.assertIsInstance(connection, RealtimeWebSocketConnection)
        self.assertEqual(
            websocket_module.url,
            "wss://api.openai.com/v1/realtime?model=gpt-realtime-2",
        )
        self.assertIn("Authorization: Bearer test-api-key", websocket_module.header)

        async def run():
            await connection.send("hello")
            return await connection.recv()

        self.assertEqual(asyncio.run(run()), '{"type":"response.done"}')
        self.assertEqual(websocket_module.socket.sent, ["hello"])


if __name__ == "__main__":
    unittest.main()
