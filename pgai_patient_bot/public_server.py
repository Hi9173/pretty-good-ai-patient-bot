import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from websockets.datastructures import Headers
    from websockets.http11 import Response
except ImportError:
    Headers = dict

    class Response:
        def __init__(self, status_code, reason_phrase, headers, body):
            self.status_code = status_code
            self.reason_phrase = reason_phrase
            self.headers = headers
            self.body = body

from pgai_patient_bot.app import media_websocket_url
from pgai_patient_bot.checkpoint import load_config, twiml_for_stream
from pgai_patient_bot.media_server import (
    DEFAULT_MEDIA_HOST,
    DEFAULT_PATIENT_INSTRUCTIONS,
    audio_recorder_factory_from_env,
    media_handler,
    patient_instructions_from_env,
)
from pgai_patient_bot.websocket_adapter import handle_live_media_websocket


DEFAULT_PUBLIC_PORT = 8000


def stream_status_callback_url(config):
    return f"{config.public_base_url}/stream-status"


def make_process_request(config, stream_status_path=None):
    def process_request(_connection, request):
        parsed = urlsplit(request.path)
        if parsed.path == "/stream-status":
            record_stream_status(parsed.query, stream_status_path)
            return Response(
                204,
                "No Content",
                Headers([("Content-Length", "0")]),
                b"",
            )
        if parsed.path != "/twiml":
            return None

        body = twiml_for_stream(
            media_websocket_url(config),
            status_callback_url=stream_status_callback_url(config),
        ).encode()
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


def record_stream_status(query, path):
    if not path:
        return
    fields = {
        key: values[-1]
        for key, values in parse_qs(query, keep_blank_values=True).items()
    }
    fields["received_at"] = datetime.now(timezone.utc).isoformat()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(fields, sort_keys=True) + "\n")


async def serve_public_websocket(
    host,
    port,
    api_key,
    config,
    instructions=DEFAULT_PATIENT_INSTRUCTIONS,
    server_factory=None,
    bridge=handle_live_media_websocket,
    audio_recorder_factory=None,
    stream_status_path=None,
):
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    if server_factory is None:
        server_factory = _load_websockets_serve()

    async def handler(websocket):
        return await media_handler(
            websocket,
            api_key,
            instructions,
            bridge=bridge,
            audio_recorder_factory=audio_recorder_factory,
        )

    return await server_factory(
        handler,
        host,
        port,
        process_request=make_process_request(config, stream_status_path=stream_status_path),
        ping_interval=None,
    )


def stream_status_path_from_env(env):
    root = env.get("CALL_ARTIFACT_ROOT")
    call_id = env.get("CALL_ARTIFACT_ID")
    if not root or not call_id:
        return None
    return Path(root) / "calls" / call_id / "stream_status.jsonl"


def run_public_server(env, output):
    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    config = load_config(env)
    host = env.get("PUBLIC_SERVER_HOST", DEFAULT_MEDIA_HOST)
    port = int(env.get("PUBLIC_SERVER_PORT", DEFAULT_PUBLIC_PORT))
    recorder_factory = audio_recorder_factory_from_env(env)
    stream_status_path = stream_status_path_from_env(env)
    instructions = patient_instructions_from_env(env)
    print(f"Public server listening on http/ws://{host}:{port}", file=output, flush=True)

    async def run_forever():
        server = await serve_public_websocket(
            host,
            port,
            api_key,
            config,
            instructions,
            audio_recorder_factory=recorder_factory,
            stream_status_path=stream_status_path,
        )
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
