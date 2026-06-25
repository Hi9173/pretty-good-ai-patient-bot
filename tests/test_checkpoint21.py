import asyncio
import unittest

from pgai_patient_bot import endpoint_check, media_server


class PathWebSocket:
    def __init__(self, path):
        self.request = type("Request", (), {"path": path})()
        self.closed = None

    async def close(self, code=None, reason=None):
        self.closed = {"code": code, "reason": reason}


class Checkpoint21Tests(unittest.IsolatedAsyncioTestCase):
    async def test_media_probe_path_closes_without_opening_bridge(self):
        websocket = PathWebSocket("/media?probe=1")

        async def bridge(*args):
            raise AssertionError("probe should not open the media bridge")

        sent_count = await media_server.media_handler(
            websocket,
            "secret-key",
            bridge=bridge,
        )

        self.assertEqual(sent_count, 0)
        self.assertEqual(websocket.closed["code"], 1000)
        self.assertEqual(websocket.closed["reason"], "probe ok")

    async def test_endpoint_check_probes_media_with_probe_query(self):
        calls = []

        def fetch_text(url):
            calls.append(("twiml", url))
            return (
                '<Response><Connect><Stream url="wss://public.example.test/media" />'
                "</Connect></Response>"
            )

        async def probe_media(url):
            calls.append(("media", url))

        await endpoint_check.verify_endpoints(
            {"PUBLIC_BASE_URL": "https://public.example.test"},
            fetch_text=fetch_text,
            probe_media=probe_media,
            local=True,
        )

        self.assertEqual(calls[-1], ("media", "ws://127.0.0.1:8765/media?probe=1"))


if __name__ == "__main__":
    unittest.main()
