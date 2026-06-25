from types import SimpleNamespace

from pgai_patient_bot.app import media_websocket_url


DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = "8000"
DEFAULT_MEDIA_HOST = "127.0.0.1"
DEFAULT_MEDIA_PORT = "8765"


def tunnel_urls(env):
    public_base = env.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not public_base:
        raise ValueError("PUBLIC_BASE_URL is required")
    if not public_base.startswith("https://"):
        raise ValueError("PUBLIC_BASE_URL must start with https://")

    public_media_base = env.get("PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
    if public_media_base and not public_media_base.startswith("https://"):
        raise ValueError("PUBLIC_MEDIA_BASE_URL must start with https://")

    return {
        "twiml": f"{public_base}/twiml",
        "media": media_websocket_url(
            SimpleNamespace(
                public_base_url=public_base,
                public_media_base_url=public_media_base or None,
            )
        ),
        "local_twiml": (
            f"http://{env.get('HTTP_SERVER_HOST', DEFAULT_HTTP_HOST)}:"
            f"{env.get('HTTP_SERVER_PORT', DEFAULT_HTTP_PORT)}/twiml"
        ),
        "local_media": (
            f"ws://{env.get('MEDIA_SERVER_HOST', DEFAULT_MEDIA_HOST)}:"
            f"{env.get('MEDIA_SERVER_PORT', DEFAULT_MEDIA_PORT)}/media"
        ),
    }


def print_tunnel_check(env, output):
    try:
        urls = tunnel_urls(env)
    except ValueError as error:
        print(str(error), file=output)
        return 2

    print(f"Public TwiML: {urls['twiml']}", file=output)
    print(f"Public media: {urls['media']}", file=output)
    print(f"Local TwiML: {urls['local_twiml']}", file=output)
    print(f"Local media: {urls['local_media']}", file=output)
    return 0
