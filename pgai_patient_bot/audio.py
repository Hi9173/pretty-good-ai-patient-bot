import base64
import binascii


TELEPHONY_AUDIO_MIME_TYPE = "audio/pcmu"
TELEPHONY_AUDIO_FORMAT = {"type": TELEPHONY_AUDIO_MIME_TYPE}
SYMBOLIC_AUDIO_PREFIX = "mock:"
REAL_PCMU_SILENCE = "/////w=="


def symbolic_audio(name):
    return f"{SYMBOLIC_AUDIO_PREFIX}{name}"


def is_symbolic_audio(payload):
    return isinstance(payload, str) and payload.startswith(SYMBOLIC_AUDIO_PREFIX)


def is_real_audio_payload(payload):
    if not isinstance(payload, str) or not payload or is_symbolic_audio(payload):
        return False
    try:
        base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True
