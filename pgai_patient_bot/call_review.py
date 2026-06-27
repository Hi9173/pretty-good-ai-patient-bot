import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
RESPONSES_URL = "https://api.openai.com/v1/responses"
TRANSCRIPTION_MODEL = "gpt-4o-transcribe-diarize"
ANALYSIS_MODEL = "gpt-5-mini"


def review_call(
    call_dir,
    api_key,
    transcriber=None,
    analyzer=None,
    transcribe_model=TRANSCRIPTION_MODEL,
    analysis_model=ANALYSIS_MODEL,
):
    call_dir = Path(call_dir)
    mp3_path = call_dir / "recording.mp3"
    if transcriber is None:
        transcriber = lambda mp3_path, key: openai_transcribe_mp3(
            mp3_path, key, model=transcribe_model
        )
    if analyzer is None:
        analyzer = lambda transcript, key: openai_analyze_transcript(
            transcript, key, model=analysis_model
        )

    transcription = transcriber(mp3_path, api_key)
    transcript = format_transcript(transcription)
    analysis = analyzer(transcript, api_key)

    transcript_path = call_dir / "transcript.txt"
    analysis_path = call_dir / "analysis.md"
    transcript_path.write_text(transcript)
    analysis_path.write_text(analysis)
    return {
        "transcript_path": transcript_path,
        "analysis_path": analysis_path,
        "transcribe_model": transcribe_model,
        "analysis_model": analysis_model,
    }


def openai_transcribe_mp3(
    mp3_path,
    api_key,
    opener=urlopen,
    model=TRANSCRIPTION_MODEL,
):
    mp3_path = Path(mp3_path)
    body, content_type = multipart_form(
        {
            "model": model,
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
        },
        {"file": (mp3_path.name, "audio/mpeg", mp3_path.read_bytes())},
    )
    request = Request(
        TRANSCRIPTION_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    with opener(request, timeout=120) as response:
        return json.loads(response.read().decode())


def openai_analyze_transcript(
    transcript,
    api_key,
    opener=urlopen,
    model=ANALYSIS_MODEL,
):
    prompt = (
        "Analyze this Pretty Good AI patient-bot call transcript for a QA submission. "
        "Return concise Markdown with these sections: Summary, Potential Bugs, "
        "Evidence, Expected Behavior, and Next Follow-up. If no bug is confirmed, "
        "say so and identify what would need another call.\n\n"
        f"Transcript:\n{transcript}"
    )
    request = Request(
        RESPONSES_URL,
        data=json.dumps({"model": model, "input": prompt}).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with opener(request, timeout=120) as response:
        payload = json.loads(response.read().decode())

    text = response_output_text(payload)
    return text if text.endswith("\n") else text + "\n"


def format_transcript(payload):
    if isinstance(payload, str):
        return payload if payload.endswith("\n") else payload + "\n"

    segments = payload.get("segments") or []
    if segments:
        lines = []
        for segment in segments:
            text = segment.get("text", "").strip()
            if not text:
                continue
            speaker = segment.get("speaker", "speaker").upper()
            lines.append(f"{timestamp_range(segment)} {speaker}: {text}")
        return "\n".join(lines) + "\n"

    text = payload.get("text", "")
    return text if text.endswith("\n") else text + "\n"


def multipart_form(fields, files):
    boundary = f"----pgai-{uuid.uuid4().hex}"
    chunks = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    for name, (filename, content_type, data) in files.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        chunks.append(data)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def timestamp_range(segment):
    start = format_seconds(segment.get("start"))
    end = segment.get("end")
    if end is None:
        return f"[{start}]"
    return f"[{start}-{format_seconds(end)}]"


def format_seconds(value):
    seconds = float(value or 0)
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:05.2f}"


def response_output_text(payload):
    if payload.get("output_text"):
        return payload["output_text"].strip()

    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip() or json.dumps(payload, indent=2)
