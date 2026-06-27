import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pgai_patient_bot import cli
from pgai_patient_bot.cli import main


class LiveScenariosCliTests(unittest.TestCase):
    def test_run_live_scenarios_requires_live_flag(self):
        output = io.StringIO()

        exit_code = main(["run-live-scenarios", "2"], output=output)

        self.assertEqual(exit_code, 2)
        self.assertIn("run-live-scenarios <scenario-or-range> --live", output.getvalue())

    def test_run_live_scenarios_runs_each_selected_scenario(self):
        calls = []
        output = io.StringIO()

        def runner(env, output):
            calls.append(
                (
                    env["PATIENT_SCENARIO_ID"],
                    env["CALL_ARTIFACT_ID"],
                    env["CALL_ARTIFACT_ROOT"],
                )
            )
            print(f"ran {env['PATIENT_SCENARIO_ID']}", file=output)
            return 0

        exit_code = main(
            ["run-live-scenarios", "2-3", "--live"],
            env={"OPENAI_API_KEY": "secret"},
            output=output,
            live_scenarios_runner=runner,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [
                ("account_information_change", "02_account_information_change", "."),
                ("refill_missing_triage", "03_refill_missing_triage", "."),
            ],
        )
        self.assertIn("Scenario 2: account_information_change", output.getvalue())
        self.assertIn("Scenario 3: refill_missing_triage", output.getvalue())
        self.assertNotIn("secret", output.getvalue())

    def test_run_live_scenarios_rejects_unknown_number(self):
        output = io.StringIO()

        exit_code = main(
            ["run-live-scenarios", "99", "--live"],
            env={"OPENAI_API_KEY": "secret"},
            output=output,
        )

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown patient scenario number: 99", output.getvalue())

    def test_run_live_scenarios_reads_dotenv_for_one_command_use(self):
        calls = []
        output = io.StringIO()

        def runner(env, output):
            calls.append((env["OPENAI_API_KEY"], env["CALL_ARTIFACT_ROOT"]))
            return 0

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                Path(".env").write_text(
                    "OPENAI_API_KEY=from_dotenv\nCALL_ARTIFACT_ROOT=artifacts\n"
                )
                exit_code = main(
                    ["run-live-scenarios", "2", "--live"],
                    env={},
                    output=output,
                    live_scenarios_runner=runner,
                )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [("from_dotenv", "artifacts")])
        self.assertNotIn("from_dotenv", output.getvalue())

    def test_live_runner_prints_progress_checkpoints(self):
        output = io.StringIO()
        env = {
            "OPENAI_API_KEY": "secret",
            "TWILIO_ACCOUNT_SID": "AC123",
            "TWILIO_AUTH_TOKEN": "twilio-secret",
            "TWILIO_FROM_NUMBER": "+15551234567",
            "PUBLIC_BASE_URL": "https://example.ngrok-free.app",
            "PATIENT_SCENARIO_ID": "account_information_change",
            "CALL_ARTIFACT_ID": "account_information_change",
            "CALL_ARTIFACT_ROOT": ".",
            "LIVE_SERVER_DRAIN_SECONDS": "2.5",
        }

        with (
            patch.object(cli, "start_public_server_process", return_value=Mock()),
            patch.object(cli, "start_ngrok_process", return_value=Mock()),
            patch.object(cli, "wait_for_endpoints", return_value=True),
            patch.object(
                cli,
                "place_call_payload",
                return_value={"status": "queued", "sid": "CA123"},
            ),
            patch.object(
                cli,
                "wait_for_twilio_call",
                return_value={"status": "completed", "error_code": None},
            ),
            patch.object(
                cli,
                "export_call_mp3",
                return_value=Path("calls/account_information_change/recording.mp3"),
            ),
            patch.object(
                cli,
                "review_call",
                return_value={
                    "transcript_path": Path(
                        "calls/account_information_change/transcript.txt"
                    ),
                    "analysis_path": Path("calls/account_information_change/analysis.md"),
                },
            ),
            patch.object(cli.time, "sleep") as sleep,
            patch.object(cli, "stop_process"),
        ):
            exit_code = cli.run_one_live_scenario(env, output)

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("Starting public /twiml + /media server", text)
        self.assertIn("Starting ngrok tunnel", text)
        self.assertIn("Endpoint check: ok", text)
        self.assertIn("Placing Twilio call", text)
        self.assertIn("Call SID: CA123", text)
        self.assertIn("Waiting for Twilio call to finish", text)
        self.assertIn("Waiting for media bridge cleanup", text)
        self.assertIn("Exporting MP3", text)
        self.assertIn("Transcribing and analyzing call", text)
        self.assertNotIn("secret", text)
        sleep.assert_called_with(2.5)

    def test_public_server_process_omits_non_string_env_values(self):
        with patch.object(cli.subprocess, "Popen", return_value=Mock()) as popen:
            cli.start_public_server_process(
                {
                    "OPENAI_API_KEY": "secret",
                    "PATIENT_SCENARIO_ID": "refill_missing_triage",
                    "argv": ["run-live-scenarios", "3", "--live"],
                }
            )

        process_env = popen.call_args.kwargs["env"]
        self.assertEqual(process_env["OPENAI_API_KEY"], "secret")
        self.assertEqual(process_env["PATIENT_SCENARIO_ID"], "refill_missing_triage")
        self.assertEqual(process_env["PYTHONUNBUFFERED"], "1")
        self.assertNotIn("argv", process_env)

    def test_public_server_process_writes_child_output_to_call_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Mock()
            with patch.object(cli.subprocess, "Popen", return_value=process) as popen:
                cli.start_public_server_process(
                    {
                        "OPENAI_API_KEY": "secret",
                        "CALL_ARTIFACT_ROOT": tmp,
                        "CALL_ARTIFACT_ID": "refill_missing_triage",
                    }
                )

            log_path = Path(tmp) / "calls" / "refill_missing_triage" / "public_server.log"
            self.assertEqual(popen.call_args.kwargs["stdout"].name, str(log_path))
            self.assertEqual(popen.call_args.kwargs["stderr"], cli.subprocess.STDOUT)

            cli.stop_process(process)
            self.assertTrue(popen.call_args.kwargs["stdout"].closed)


if __name__ == "__main__":
    unittest.main()
