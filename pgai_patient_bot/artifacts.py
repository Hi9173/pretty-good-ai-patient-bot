import base64
import json
import subprocess
from pathlib import Path

from pgai_patient_bot.audio import TELEPHONY_AUDIO_MIME_TYPE


def write_call_artifacts(root, call_id, metadata, transcript, analysis):
    call_dir = Path(root) / "calls" / call_id
    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    (call_dir / "transcript.txt").write_text(transcript)
    (call_dir / "analysis.md").write_text(analysis)
    return call_dir


class AudioArtifactRecorder:
    def __init__(self, root, call_id):
        self.call_dir = Path(root) / "calls" / call_id
        self.audio_dir = self.call_dir / "audio"
        self.manifest_path = self.call_dir / "audio_manifest.json"
        self.counts = {"inbound": 0, "outbound": 0}
        self.chunks = []
        self.metadata = {}
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def remember(self, **metadata):
        self.metadata.update({key: value for key, value in metadata.items() if value})
        self._write_manifest()

    def record(self, direction, payload):
        self.counts[direction] += 1
        filename = f"{direction}-{self.counts[direction]:04d}.pcmu"
        audio = base64.b64decode(payload, validate=True)
        path = self.audio_dir / filename
        path.write_bytes(audio)
        self.chunks.append(
            {
                "direction": direction,
                "file": f"audio/{filename}",
                "mime_type": TELEPHONY_AUDIO_MIME_TYPE,
                "bytes": len(audio),
            }
        )
        self._write_manifest()
        return path

    def _write_manifest(self):
        self.manifest_path.write_text(
            json.dumps(
                {"metadata": self.metadata, "chunks": self.chunks},
                indent=2,
            )
            + "\n"
        )


def write_bug_report(root, issues):
    path = Path(root) / "bug_report.md"
    path.write_text(bug_report_markdown(issues))
    return path


def export_call_mp3(call_dir, runner=subprocess.run, ffmpeg="ffmpeg"):
    call_dir = Path(call_dir)
    manifest_path = call_dir / "audio_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    combined_path = call_dir / "recording.pcmu"
    mp3_path = call_dir / "recording.mp3"

    combined_path.write_bytes(
        b"".join((call_dir / chunk["file"]).read_bytes() for chunk in manifest["chunks"])
    )
    try:
        runner(
            [
                ffmpeg,
                "-y",
                "-f",
                "mulaw",
                "-ar",
                "8000",
                "-ac",
                "1",
                "-i",
                str(combined_path),
                str(mp3_path),
            ],
            check=True,
        )
    finally:
        combined_path.unlink(missing_ok=True)

    manifest["recording"] = mp3_path.name
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return mp3_path


def bug_report_markdown(issues):
    lines = ["# Bug Report", ""]
    for issue in issues:
        lines.extend(
            [
                f"## {issue['severity']} - {issue['title']}",
                "",
                f"Call: {issue['call']}",
                f"Evidence: {issue['evidence']}",
                f"Expected: {issue['expected']}",
                "",
            ]
        )
    return "\n".join(lines)
