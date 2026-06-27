import io
import json
import tempfile
import unittest
from pathlib import Path

from pgai_patient_bot.call_review import (
    format_transcript,
    openai_analyze_transcript,
    openai_transcribe_mp3,
    review_call,
)
from pgai_patient_bot.cli import main


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class Checkpoint29Tests(unittest.TestCase):
    def test_format_transcript_uses_diarized_segments(self):
        transcript = format_transcript(
            {
                "segments": [
                    {
                        "speaker": "speaker_0",
                        "start": 1.25,
                        "end": 2.5,
                        "text": "I need to reschedule my appointment.",
                    },
                    {
                        "speaker": "speaker_1",
                        "start": 3.0,
                        "text": "Sure, I can help with that.",
                    },
                ]
            }
        )

        self.assertIn("[00:01.25-00:02.50] SPEAKER_0:", transcript)
        self.assertIn("I need to reschedule my appointment.", transcript)
        self.assertIn("[00:03.00] SPEAKER_1:", transcript)

    def test_review_call_writes_transcript_and_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            call_dir = Path(tmp) / "calls" / "call-live-001"
            call_dir.mkdir(parents=True)
            (call_dir / "recording.mp3").write_bytes(b"fake mp3")

            def transcriber(mp3_path, api_key):
                self.assertEqual(mp3_path, call_dir / "recording.mp3")
                self.assertEqual(api_key, "secret")
                return {"text": "PATIENT: I need a refill.\nASSISTANT: I can help."}

            def analyzer(transcript, api_key):
                self.assertIn("I need a refill", transcript)
                self.assertEqual(api_key, "secret")
                return "# Call Analysis\n\nNo confirmed bug from this short sample.\n"

            result = review_call(
                call_dir,
                "secret",
                transcriber=transcriber,
                analyzer=analyzer,
            )

            self.assertEqual(result["transcript_path"], call_dir / "transcript.txt")
            self.assertEqual(result["analysis_path"], call_dir / "analysis.md")
            self.assertIn("PATIENT:", (call_dir / "transcript.txt").read_text())
            self.assertIn("# Call Analysis", (call_dir / "analysis.md").read_text())

    def test_transcription_request_uses_mp3_and_diarized_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp3_path = Path(tmp) / "recording.mp3"
            mp3_path.write_bytes(b"fake mp3")
            requests = []

            def opener(request, timeout):
                requests.append((request, timeout))
                return FakeResponse(b'{"segments":[]}')

            payload = openai_transcribe_mp3(mp3_path, "secret", opener=opener)

            self.assertEqual(payload, {"segments": []})
            request, timeout = requests[0]
            self.assertEqual(timeout, 120)
            self.assertEqual(
                request.full_url, "https://api.openai.com/v1/audio/transcriptions"
            )
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            body = request.data
            self.assertIn(b'name="model"', body)
            self.assertIn(b"gpt-4o-transcribe-diarize", body)
            self.assertIn(b'name="response_format"', body)
            self.assertIn(b"diarized_json", body)
            self.assertIn(b'name="chunking_strategy"', body)
            self.assertIn(b"auto", body)
            self.assertIn(b'filename="recording.mp3"', body)

    def test_analysis_request_extracts_response_text(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(b'{"output_text":"# Call Analysis\\n\\nLooks good."}')

        analysis = openai_analyze_transcript("SPEAKER_0: hello", "secret", opener=opener)

        self.assertIn("Looks good", analysis)
        request, timeout = requests[0]
        self.assertEqual(timeout, 120)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        body = json.loads(request.data.decode())
        self.assertEqual(body["model"], "gpt-5-mini")
        self.assertIn("SPEAKER_0: hello", body["input"])

    def test_review_call_cli_requires_live_and_api_key(self):
        output = io.StringIO()

        missing_live = main(["transcribe-analyze-call", "calls/call-live-001"], output=output)

        self.assertEqual(missing_live, 2)
        self.assertIn("transcribe-analyze-call <call_dir> --live", output.getvalue())

        output = io.StringIO()
        missing_key = main(
            ["transcribe-analyze-call", "calls/call-live-001", "--live"],
            env={},
            output=output,
        )

        self.assertEqual(missing_key, 2)
        self.assertIn("OPENAI_API_KEY is required", output.getvalue())

    def test_review_call_cli_prints_paths_without_secret(self):
        output = io.StringIO()

        def reviewer(call_dir, api_key):
            self.assertEqual(call_dir, "calls/call-live-001")
            self.assertEqual(api_key, "secret")
            return {
                "transcript_path": Path("calls/call-live-001/transcript.txt"),
                "analysis_path": Path("calls/call-live-001/analysis.md"),
            }

        exit_code = main(
            ["transcribe-analyze-call", "calls/call-live-001", "--live"],
            env={"OPENAI_API_KEY": "secret"},
            output=output,
            call_reviewer=reviewer,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript: calls/call-live-001/transcript.txt", output.getvalue())
        self.assertIn("Analysis: calls/call-live-001/analysis.md", output.getvalue())
        self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
