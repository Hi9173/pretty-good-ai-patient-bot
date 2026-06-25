import asyncio

from websockets.datastructures import Headers
from websockets.http11 import Response

from pgai_patient_bot.app import media_websocket_url
from pgai_patient_bot.checkpoint import load_config, twiml_for_stream
from pgai_patient_bot.media_server import (
    DEFAULT_MEDIA_HOST,
    DEFAULT_PATIENT_INSTRUCTIONS,
    media_handler,
)


DEFAULT_PUBLIC_PORT = 8000


def make_process_request(config):
    def process_request(_connection, request):
        if request.path != "/twiml":
            return None

        body = twiml_for_stream(media_websocket_url(config)).encode()
        return Response(
            200,
            "OK",
            Headers(
                [
                    ("Content-Type", "text/xml"),
                    ("Content-Length", str(len(body))),
                ]
            ),
            body,
        )

    return process_request


async def serve_public_websocket(
    host,
    port,
    api_key,
    config,
    instructions=DEFAULT_PATIENT_INSTRUCTIONS,
    server_factory=None,
):
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    if server_factory is None:
        server_factory = _load_websockets_serve()

    async def handler(websocket):
        return await media_handler(websocket, api_key, instructions)

    return await server_factory(
        handler,
        host,
        port,
        process_request=make_process_request(config),
    )


def run_public_server(env, output):
    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    config = load_config(env)
    host = env.get("PUBLIC_SERVER_HOST", DEFAULT_MEDIA_HOST)
    port = int(env.get("PUBLIC_SERVER_PORT", DEFAULT_PUBLIC_PORT))
    print(f"Public server listening on http/ws://{host}:{port}", file=output)

    async def run_forever():
        server = await serve_public_websocket(host, port, api_key, config)
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
