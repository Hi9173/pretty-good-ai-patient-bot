import asyncio
import io
import unittest

from pgai_patient_bot.cli import main
from pgai_patient_bot import media_server


class PathWebSocket:
    def __init__(self, path="/media"):
        self.request = type("Request", (), {"path": path})()
        self.closed = None

    async def close(self, code=None, reason=None):
        self.closed = {"code": code, "reason": reason}


class Checkpoint16Tests(unittest.TestCase):
    def test_media_handler_accepts_media_path_and_delegates_to_bridge(self):
        calls = []
        websocket = PathWebSocket("/media")

        async def bridge(websocket_arg, api_key, instructions):
            calls.append((websocket_arg, api_key, instructions))
            return 3

        sent_count = asyncio.run(
            media_server.media_handler(
                websocket,
                "secret-key",
                "Act like a patient.",
                bridge=bridge,
            )
        )

        self.assertEqual(sent_count, 3)
        self.assertEqual(calls, [(websocket, "secret-key", "Act like a patient.")])
        self.assertIsNone(websocket.closed)

    def test_media_handler_rejects_non_media_path(self):
        websocket = PathWebSocket("/wrong")

        async def bridge(*args):
            raise AssertionError("bridge should not run")

        sent_count = asyncio.run(
            media_server.media_handler(
                websocket,
                "secret-key",
                "Act like a patient.",
                bridge=bridge,
            )
        )

        self.assertEqual(sent_count, 0)
        self.assertEqual(websocket.closed["code"], 1008)

    def test_serve_media_websocket_uses_injected_server_factory(self):
        calls = []

        async def server_factory(handler, host, port):
            calls.append((handler, host, port))
            return "server"

        server = asyncio.run(
            media_server.serve_media_websocket(
                "127.0.0.1",
                8765,
                "secret-key",
                "Act like a patient.",
                server_factory=server_factory,
            )
        )

        self.assertEqual(server, "server")
        self.assertEqual(calls[0][1:], ("127.0.0.1", 8765))
        self.assertTrue(callable(calls[0][0]))

    def test_main_serve_media_requires_live_flag_and_api_key(self):
        output = io.StringIO()

        missing_flag = main(["serve-media"], env={}, output=output)
        missing_key = main(["serve-media", "--live"], env={}, output=output)

        self.assertEqual(missing_flag, 2)
        self.assertEqual(missing_key, 2)
        self.assertIn("serve-media --live", output.getvalue())
        self.assertIn("OPENAI_API_KEY is required", output.getvalue())

    def test_main_serve_media_delegates_without_printing_key(self):
        output = io.StringIO()
        calls = []

        def runner(env, output_arg):
            calls.append((env["OPENAI_API_KEY"], output_arg))
            return 0

        exit_code = main(
            ["serve-media", "--live"],
            env={"OPENAI_API_KEY": "secret-key"},
            output=output,
            media_server_runner=runner,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("secret-key", output)])
        self.assertNotIn("secret-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
