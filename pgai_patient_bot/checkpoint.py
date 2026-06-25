from dataclasses import dataclass
from base64 import b64encode
from urllib.parse import urlencode
from urllib.request import Request
from xml.etree import ElementTree


# Safety rail: every real Twilio call request must target the challenge number.
TEST_NUMBER = "+18054398008"
REQUIRED_ENV = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "PUBLIC_BASE_URL",
)


@dataclass(frozen=True)
class Config:
    account_sid: str
    auth_token: str
    from_number: str
    public_base_url: str
    public_media_base_url: str | None = None


def load_config(env):
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        raise ValueError("Missing required environment variables: " + ", ".join(missing))

    return Config(
        account_sid=env["TWILIO_ACCOUNT_SID"],
        auth_token=env["TWILIO_AUTH_TOKEN"],
        from_number=env["TWILIO_FROM_NUMBER"],
        public_base_url=env["PUBLIC_BASE_URL"].rstrip("/"),
        public_media_base_url=env.get("PUBLIC_MEDIA_BASE_URL", "").rstrip("/") or None,
    )


def twiml_for_stream(media_url):
    response = ElementTree.Element("Response")
    connect = ElementTree.SubElement(response, "Connect")
    ElementTree.SubElement(connect, "Stream", {"url": media_url})
    return ElementTree.tostring(response, encoding="unicode")


def build_call_request(config):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}/Calls.json"
    body = urlencode(
        {
            "To": TEST_NUMBER,
            "From": config.from_number,
            "Url": f"{config.public_base_url}/twiml",
        }
    ).encode()
    token = f"{config.account_sid}:{config.auth_token}".encode()

    return Request(
        url,
        data=body,
        headers={
            "Authorization": "Basic " + b64encode(token).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
