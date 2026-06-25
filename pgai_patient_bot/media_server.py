import asyncio
from urllib.parse import parse_qs, urlsplit

from pgai_patient_bot.websocket_adapter import handle_live_media_websocket


MEDIA_PATH = "/media"
MEDIA_PROBE_QUERY = "probe"
DEFAULT_MEDIA_HOST = "127.0.0.1"
DEFAULT_MEDIA_PORT = 8765
DEFAULT_PATIENT_INSTRUCTIONS = "Act like a patient calling a healthcare office."


def websocket_path(websocket):
    request = getattr(websocket, "request", None)
    if request is not None and getattr(request, "path", None):
        return request.path
    return getattr(websocket, "path", None)


def is_media_probe(path):
    parsed = urlsplit(path or "")
    return parsed.path == MEDIA_PATH and parse_qs(parsed.query).get(MEDIA_PROBE_QUERY) == ["1"]


async def media_handler(
    websocket,
    api_key,
    instructions=DEFAULT_PATIENT_INSTRUCTIONS,
    bridge=handle_live_media_websocket,
):
    path = websocket_path(websocket)
    if is_media_probe(path):
        await websocket.close(code=1000, reason="probe ok")
        return 0
    if urlsplit(path or "").path != MEDIA_PATH:
        await websocket.close(code=1008, reason="unsupported path")
        return 0
    return await bridge(websocket, api_key, instructions)


async def serve_media_websocket(
    host,
    port,
    api_key,
    instructions=DEFAULT_PATIENT_INSTRUCTIONS,
    server_factory=None,
):
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    if server_factory is None:
        server_factory = _load_websockets_serve()

    async def handler(websocket):
        return await media_handler(websocket, api_key, instructions)

    return await server_factory(handler, host, port)


def run_media_server(env, output):
    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    host = env.get("MEDIA_SERVER_HOST", DEFAULT_MEDIA_HOST)
    port = int(env.get("MEDIA_SERVER_PORT", DEFAULT_MEDIA_PORT))
    print(f"Media WebSocket server listening on ws://{host}:{port}{MEDIA_PATH}", file=output)

    async def run_forever():
        server = await serve_media_websocket(host, port, api_key)
        async with server:
            await asyncio.Future()

    asyncio.run(run_forever())
    return 0


def _load_websockets_serve():
    try:
        from websockets.asyncio.server import serve
    except ImportError:
        from websockets import serve
    return serve
