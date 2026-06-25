import base64
import binascii


TELEPHONY_AUDIO_MIME_TYPE = "audio/pcmu"
TELEPHONY_AUDIO_FORMAT = {"type": TELEPHONY_AUDIO_MIME_TYPE}
SYMBOLIC_AUDIO_PREFIX = "mock:"
REAL_PCMU_SILENCE = "/////w=="
PCMU_SAMPLE_RATE_HZ = 8000


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


def pcmu_silence_payload(milliseconds=100):
    if milliseconds <= 0:
        raise ValueError("milliseconds must be positive")
    byte_count = PCMU_SAMPLE_RATE_HZ * milliseconds // 1000
    return base64.b64encode(b"\xff" * byte_count).decode("ascii")
