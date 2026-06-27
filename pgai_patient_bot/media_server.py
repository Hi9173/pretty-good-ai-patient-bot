import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from pgai_patient_bot.artifacts import AudioArtifactRecorder
from pgai_patient_bot.scenarios import scenario_instructions
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
    audio_recorder_factory=None,
):
    path = websocket_path(websocket)
    if is_media_probe(path):
        await websocket.close(code=1000, reason="probe ok")
        return 0
    if urlsplit(path or "").path != MEDIA_PATH:
        await websocket.close(code=1008, reason="unsupported path")
        return 0
    if audio_recorder_factory:
        return await bridge(
            websocket,
            api_key,
            instructions,
            audio_recorder=audio_recorder_factory(),
        )
    return await bridge(websocket, api_key, instructions)


async def serve_media_websocket(
    host,
    port,
    api_key,
    instructions=DEFAULT_PATIENT_INSTRUCTIONS,
    server_factory=None,
    audio_recorder_factory=None,
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
            audio_recorder_factory=audio_recorder_factory,
        )

    return await server_factory(handler, host, port)


def run_media_server(env, output):
    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    host = env.get("MEDIA_SERVER_HOST", DEFAULT_MEDIA_HOST)
    port = int(env.get("MEDIA_SERVER_PORT", DEFAULT_MEDIA_PORT))
    recorder_factory = audio_recorder_factory_from_env(env)
    instructions = patient_instructions_from_env(env)
    print(f"Media WebSocket server listening on ws://{host}:{port}{MEDIA_PATH}", file=output)

    async def run_forever():
        server = await serve_media_websocket(
            host,
            port,
            api_key,
            instructions,
            audio_recorder_factory=recorder_factory,
        )
        async with server:
            await asyncio.Future()

    asyncio.run(run_forever())
    return 0


def audio_recorder_factory_from_env(env):
    root = env.get("CALL_ARTIFACT_ROOT")
    if not root:
        return None

    def make_recorder():
        if env.get("CALL_ARTIFACT_ID"):
            return AudioArtifactRecorder(root, env["CALL_ARTIFACT_ID"])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = uuid4().hex[:8]
        return AudioArtifactRecorder(root, f"call-{timestamp}-{suffix}")

    return make_recorder


def patient_instructions_from_env(env):
    scenario_id = env.get("PATIENT_SCENARIO_ID")
    if scenario_id:
        return scenario_instructions(scenario_id)
    return env.get("PATIENT_INSTRUCTIONS", DEFAULT_PATIENT_INSTRUCTIONS)


def _load_websockets_serve():
    try:
        from websockets.asyncio.server import serve
    except ImportError:
        from websockets import serve
    return serve
