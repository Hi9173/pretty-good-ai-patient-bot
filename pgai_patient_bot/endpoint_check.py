import asyncio
from urllib.request import urlopen
from xml.etree import ElementTree

from pgai_patient_bot.tunnel import tunnel_urls


MEDIA_PROBE_SUFFIX = "probe=1"


def fetch_text(url, timeout=10):
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode()


async def probe_media(url):
    try:
        from websockets.asyncio.client import connect
    except ImportError:
        from websockets import connect

    async with connect(url):
        return None


def stream_url_from_twiml(body):
    root = ElementTree.fromstring(body)
    stream = root.find(".//Stream")
    if stream is None or not stream.get("url"):
        raise ValueError("TwiML Stream url is required")
    return stream.get("url")


def media_probe_url(url):
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{MEDIA_PROBE_SUFFIX}"


async def verify_endpoints(env, fetch_text=fetch_text, probe_media=probe_media, local=False):
    urls = tunnel_urls(env)
    twiml_url = urls["local_twiml"] if local else urls["twiml"]
    media_url = urls["local_media"] if local else urls["media"]

    stream_url = stream_url_from_twiml(fetch_text(twiml_url))
    if stream_url != urls["media"]:
        raise ValueError(
            f"TwiML stream URL mismatch: expected {urls['media']}, got {stream_url}"
        )

    await probe_media(media_probe_url(media_url))
    return {"twiml": "ok", "media": "ok", "stream_url": stream_url}


def run_endpoint_check(env, output, verifier=verify_endpoints):
    try:
        report = asyncio.run(verifier(env, local="--local" in env.get("argv", [])))
    except Exception as error:
        print(f"Endpoint check failed: {error}", file=output)
        return 1

    print(f"TwiML: {report['twiml']}", file=output)
    print(f"Media: {report['media']}", file=output)
    print(f"Stream URL: {report['stream_url']}", file=output)
    return 0
