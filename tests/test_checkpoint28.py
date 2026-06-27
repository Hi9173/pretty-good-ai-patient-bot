import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from pgai_patient_bot.artifacts import AudioArtifactRecorder, export_call_mp3
from pgai_patient_bot.cli import main


def payload(raw):
    return base64.b64encode(raw).decode("ascii")


class Checkpoint28Tests(unittest.TestCase):
    def test_export_call_mp3_combines_manifest_order_and_invokes_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = AudioArtifactRecorder(tmp, "call-live-001")
            recorder.record("inbound", payload(b"in"))
            recorder.record("outbound", payload(b"out"))
            calls = []

            def runner(command, check):
                calls.append((command, check))
                input_path = Path(command[command.index("-i") + 1])
                self.assertEqual(input_path.read_bytes(), b"inout")
                Path(command[-1]).write_bytes(b"fake mp3")

            mp3_path = export_call_mp3(recorder.call_dir, runner=runner)

            self.assertEqual(mp3_path, recorder.call_dir / "recording.mp3")
            self.assertEqual(mp3_path.read_bytes(), b"fake mp3")
            command, check = calls[0]
            self.assertTrue(check)
            self.assertEqual(command[:7], ["ffmpeg", "-y", "-f", "mulaw", "-ar", "8000", "-ac"])
            self.assertEqual(command[-1], str(mp3_path))
            self.assertFalse((recorder.call_dir / "recording.pcmu").exists())

            manifest = json.loads((recorder.call_dir / "audio_manifest.json").read_text())
            self.assertEqual(manifest["recording"], "recording.mp3")

    def test_export_call_mp3_cli_requires_call_dir(self):
        output = io.StringIO()

        exit_code = main(["export-mp3"], env={}, output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("export-mp3 <call_dir>", output.getvalue())

    def test_export_call_mp3_cli_prints_path(self):
        output = io.StringIO()

        def exporter(call_dir):
            self.assertEqual(call_dir, "calls/call-live-001")
            return Path("calls/call-live-001/recording.mp3")

        exit_code = main(
            ["export-mp3", "calls/call-live-001"],
            env={},
            output=output,
            mp3_exporter=exporter,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("MP3: calls/call-live-001/recording.mp3", output.getvalue())


if __name__ == "__main__":
    unittest.main()
