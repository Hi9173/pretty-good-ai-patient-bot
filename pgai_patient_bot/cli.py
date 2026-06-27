import base64
import os
import sys
import json
import subprocess
import time
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pgai_patient_bot.app import make_server, media_websocket_url
from pgai_patient_bot.artifacts import export_call_mp3
from pgai_patient_bot.call_review import review_call
from pgai_patient_bot.checkpoint import build_call_request, load_config
from pgai_patient_bot.endpoint_check import run_endpoint_check
from pgai_patient_bot.openai_realtime import (
    live_realtime_audio_smoke,
    live_realtime_smoke,
)
from pgai_patient_bot.scenarios import scenario_by_number
from pgai_patient_bot.tunnel import print_tunnel_check


def dry_run_call(config, output):
    request = build_call_request(config)
    body = parse_qs(request.data.decode())

    print(f"{request.get_method()} {request.full_url}", file=output)
    print(f"To: {body['To'][0]}", file=output)
    print(f"From: {body['From'][0]}", file=output)
    print(f"Url: {body['Url'][0]}", file=output)
    return 0


def twilio_check_call(config, output):
    request = build_call_request(config)
    body = parse_qs(request.data.decode())

    print("Twilio config: ok", file=output)
    print(f"To: {body['To'][0]}", file=output)
    print(f"From: {body['From'][0]}", file=output)
    print(f"TwiML URL: {body['Url'][0]}", file=output)
    print(f"Media URL: {media_websocket_url(config)}", file=output)
    return 0


def place_call_payload(config, opener=urlopen):
    request = build_call_request(config)
    with opener(request, timeout=10) as response:
        return json.loads(response.read().decode())


def place_call(config, output, opener=urlopen):
    payload = place_call_payload(config, opener=opener)

    print(f"Twilio call: {payload.get('status', 'unknown')}", file=output)
    print(f"Call SID: {payload.get('sid', 'unknown')}", file=output)
    return 0


def place_call_command(env, output, opener=urlopen):
    if "--live" not in env["argv"]:
        print("usage: python3 -m pgai_patient_bot.cli place-call --live", file=output)
        return 2

    try:
        config = load_config(env)
    except ValueError as error:
        print(str(error), file=output)
        return 2

    return place_call(config, output, opener=opener)


def export_mp3_command(argv, output, exporter=export_call_mp3):
    if len(argv) != 2:
        print("usage: python3 -m pgai_patient_bot.cli export-mp3 <call_dir>", file=output)
        return 2

    path = exporter(argv[1])
    print(f"MP3: {path}", file=output)
    return 0


def transcribe_analyze_call_command(env, output, reviewer=review_call):
    argv = env["argv"]
    if len(argv) != 3 or argv[2] != "--live":
        print(
            "usage: python3 -m pgai_patient_bot.cli "
            "transcribe-analyze-call <call_dir> --live",
            file=output,
        )
        return 2

    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    options = {}
    if env.get("OPENAI_TRANSCRIPTION_MODEL"):
        options["transcribe_model"] = env["OPENAI_TRANSCRIPTION_MODEL"]
    if env.get("OPENAI_ANALYSIS_MODEL"):
        options["analysis_model"] = env["OPENAI_ANALYSIS_MODEL"]

    result = reviewer(argv[1], api_key, **options)
    print(f"Transcript: {result['transcript_path']}", file=output)
    print(f"Analysis: {result['analysis_path']}", file=output)
    return 0


def realtime_smoke_call(env, output, smoke=live_realtime_smoke):
    if "--live" not in env["argv"]:
        print("usage: python3 -m pgai_patient_bot.cli realtime-smoke --live", file=output)
        return 2

    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    event = smoke(api_key)
    return print_realtime_result(event, output, "Realtime smoke")


def realtime_audio_smoke_call(env, output, smoke=live_realtime_audio_smoke):
    if "--live" not in env["argv"]:
        print(
            "usage: python3 -m pgai_patient_bot.cli realtime-audio-smoke --live",
            file=output,
        )
        return 2

    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=output)
        return 2

    event = smoke(api_key)
    return print_realtime_result(event, output, "Realtime audio smoke")


def print_realtime_result(event, output, label):
    if event.get("type") == "error":
        error = event.get("error", {})
        print(f"{label} error: {error.get('code', 'unknown')}", file=output)
        return 1

    print(f"{label} event: {event.get('type')}", file=output)
    return 0


def run_media_server(env, output):
    from pgai_patient_bot.media_server import run_media_server as runner

    return runner(env, output)


def run_public_server(env, output):
    from pgai_patient_bot.public_server import run_public_server as runner

    return runner(env, output)


def serve_media_call(env, output, runner=run_media_server):
    if "--live" not in env["argv"]:
        print("usage: python3 -m pgai_patient_bot.cli serve-media --live", file=output)
        return 2

    if not env.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required", file=output)
        return 2

    return runner(env, output)


def serve_public_call(env, output, runner=run_public_server):
    if "--live" not in env["argv"]:
        print("usage: python3 -m pgai_patient_bot.cli serve-public --live", file=output)
        return 2

    if not env.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required", file=output)
        return 2

    return runner(env, output)


def env_with_dotenv(env, path=".env"):
    merged = dict(env)
    dotenv = Path(path)
    if not dotenv.exists():
        return merged

    for line in dotenv.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in merged:
            merged[key] = value
    return merged


def selected_scenarios(selection):
    if "-" in selection:
        try:
            start, end = (int(part) for part in selection.split("-", 1))
        except ValueError:
            raise ValueError(f"invalid scenario selection: {selection}")
        if start > end:
            raise ValueError(f"invalid scenario selection: {selection}")
        return [scenario_by_number(number) for number in range(start, end + 1)]

    try:
        number = int(selection)
    except ValueError:
        raise ValueError(f"invalid scenario selection: {selection}")
    return [scenario_by_number(number)]


def run_live_scenarios_command(env, output, runner):
    argv = env["argv"]
    if len(argv) != 3 or argv[2] != "--live":
        print(
            "usage: python3 -m pgai_patient_bot.cli "
            "run-live-scenarios <scenario-or-range> --live",
            file=output,
        )
        return 2

    if not env.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required", file=output)
        return 2

    try:
        scenarios = selected_scenarios(argv[1])
    except ValueError as error:
        print(str(error), file=output)
        return 2

    for scenario in scenarios:
        scenario_env = dict(env)
        scenario_env["PATIENT_SCENARIO_ID"] = scenario["id"]
        scenario_env["CALL_ARTIFACT_ID"] = scenario_artifact_id(scenario)
        scenario_env.setdefault("CALL_ARTIFACT_ROOT", ".")
        print(f"Scenario {scenario['number']}: {scenario['id']}", file=output)
        exit_code = runner(scenario_env, output)
        if exit_code:
            return exit_code
    return 0


def scenario_artifact_id(scenario):
    return f"{scenario['number']:02d}_{scenario['id']}"


def run_one_live_scenario(env, output):
    try:
        config = load_config(env)
    except ValueError as error:
        print(str(error), file=output)
        return 2

    server = None
    tunnel = None
    try:
        progress(output, "Starting public /twiml + /media server")
        server = start_public_server_process(env)
        progress(output, "Starting ngrok tunnel")
        tunnel = start_ngrok_process(env)
        progress(output, "Checking public /twiml and /media endpoints")
        if not wait_for_endpoints(env, output):
            return 1
        progress(output, "Endpoint check: ok")

        progress(output, "Placing Twilio call")
        payload = place_call_payload(config)
        call_sid = payload.get("sid", "unknown")
        print(f"Twilio call: {payload.get('status', 'unknown')}", file=output)
        print(f"Call SID: {call_sid}", file=output)
        flush_output(output)

        progress(output, "Waiting for Twilio call to finish")
        status = wait_for_twilio_call(config, call_sid, env)
        print(f"Twilio status: {status.get('status', 'unknown')}", file=output)
        flush_output(output)
        if status.get("error_code"):
            print(f"Twilio error: {status['error_code']}", file=output)
            return 1
        if status.get("status") != "completed":
            return 1
        wait_for_media_bridge_cleanup(env, output)
    except OSError as error:
        print(f"Live scenario failed to start: {error}", file=output)
        return 1
    finally:
        if server is not None:
            stop_process(server)
        if tunnel is not None:
            stop_process(tunnel)

    call_dir = Path(env.get("CALL_ARTIFACT_ROOT", ".")) / "calls" / env["CALL_ARTIFACT_ID"]
    progress(output, "Exporting MP3")
    mp3_path = export_call_mp3(call_dir)
    print(f"MP3: {mp3_path}", file=output)
    flush_output(output)

    progress(output, "Transcribing and analyzing call")
    result = review_call(call_dir, env["OPENAI_API_KEY"])
    print(f"Transcript: {result['transcript_path']}", file=output)
    print(f"Analysis: {result['analysis_path']}", file=output)
    flush_output(output)
    return 0


def progress(output, message):
    print(f"[live] {message}", file=output)
    flush_output(output)


def flush_output(output):
    if hasattr(output, "flush"):
        output.flush()


def wait_for_media_bridge_cleanup(env, output):
    seconds = float(env.get("LIVE_SERVER_DRAIN_SECONDS", "5"))
    if seconds <= 0:
        return
    progress(output, "Waiting for media bridge cleanup")
    time.sleep(seconds)


def start_public_server_process(env):
    process_env = child_process_env(env)
    stdout = public_server_log_file(env) or subprocess.DEVNULL
    process = subprocess.Popen(
        [sys.executable, "-m", "pgai_patient_bot.cli", "serve-public", "--live"],
        env=process_env,
        stdout=stdout,
        stderr=subprocess.STDOUT,
    )
    if hasattr(stdout, "close"):
        process._pgai_stdout = stdout
    return process


def public_server_log_file(env):
    root = env.get("CALL_ARTIFACT_ROOT")
    call_id = env.get("CALL_ARTIFACT_ID")
    if not root or not call_id:
        return None
    path = Path(root) / "calls" / call_id / "public_server.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a")


def child_process_env(env):
    process_env = dict(os.environ)
    process_env["PYTHONUNBUFFERED"] = "1"
    process_env.update(
        {
            key: value
            for key, value in env.items()
            if isinstance(value, (str, bytes, os.PathLike))
        }
    )
    return process_env


def start_ngrok_process(env):
    public_url = urlparse(env["PUBLIC_BASE_URL"])
    port = env.get("PUBLIC_SERVER_PORT", "8000")
    return subprocess.Popen(
        ["ngrok", "http", f"--url={public_url.netloc}", port],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def wait_for_endpoints(env, output):
    attempts = int(env.get("LIVE_ENDPOINT_ATTEMPTS", "30"))
    delay = float(env.get("LIVE_ENDPOINT_DELAY_SECONDS", "1"))
    last_output = ""
    for _attempt in range(attempts):
        buffer = StringIO()
        if run_endpoint_check(env, buffer) == 0:
            print(buffer.getvalue().strip(), file=output)
            return True
        last_output = buffer.getvalue().strip()
        time.sleep(delay)

    print(last_output or "Endpoint check failed", file=output)
    return False


def wait_for_twilio_call(config, call_sid, env, opener=urlopen):
    terminal = {"completed", "failed", "busy", "no-answer", "canceled"}
    deadline = time.monotonic() + int(env.get("LIVE_CALL_TIMEOUT_SECONDS", "600"))
    delay = float(env.get("LIVE_CALL_POLL_SECONDS", "5"))
    status = {"status": "unknown"}
    while time.monotonic() < deadline:
        status = fetch_twilio_call(config, call_sid, opener=opener)
        if status.get("status") in terminal:
            return status
        time.sleep(delay)
    return status


def fetch_twilio_call(config, call_sid, opener=urlopen):
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{config.account_sid}/Calls/{call_sid}.json"
    )
    token = f"{config.account_sid}:{config.auth_token}".encode()
    request = Request(
        url,
        headers={
            "Authorization": "Basic " + base64.b64encode(token).decode(),
        },
    )
    with opener(request, timeout=10) as response:
        return json.loads(response.read().decode())


def stop_process(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    stdout = getattr(process, "_pgai_stdout", None)
    if stdout:
        stdout.close()


def main(
    argv=None,
    env=None,
    output=None,
    server_factory=make_server,
    realtime_smoke=live_realtime_smoke,
    realtime_audio_smoke=live_realtime_audio_smoke,
    media_server_runner=run_media_server,
    public_server_runner=run_public_server,
    endpoint_checker=run_endpoint_check,
    twilio_call_opener=urlopen,
    mp3_exporter=export_call_mp3,
    call_reviewer=review_call,
    live_scenarios_runner=run_one_live_scenario,
):
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if env is None else env
    output = sys.stdout if output is None else output

    if argv == ["dry-run-call"]:
        return dry_run_call(load_config(env), output)
    if argv == ["twilio-check"]:
        try:
            return twilio_check_call(load_config(env), output)
        except ValueError as error:
            print(str(error), file=output)
            return 2
    if argv and argv[0] == "place-call":
        call_env = dict(env)
        call_env["argv"] = argv
        return place_call_command(call_env, output, opener=twilio_call_opener)
    if argv and argv[0] == "export-mp3":
        return export_mp3_command(argv, output, exporter=mp3_exporter)
    if argv and argv[0] == "transcribe-analyze-call":
        review_env = dict(env)
        review_env["argv"] = argv
        return transcribe_analyze_call_command(review_env, output, call_reviewer)
    if argv == ["serve"]:
        server_factory(env).serve_forever()
        return 0
    if argv == ["tunnel-check"]:
        return print_tunnel_check(env, output)
    if argv == ["endpoint-check"] or argv == ["endpoint-check", "--local"]:
        check_env = dict(env)
        check_env["argv"] = argv
        return endpoint_checker(check_env, output)
    if argv and argv[0] == "realtime-smoke":
        smoke_env = dict(env)
        smoke_env["argv"] = argv
        return realtime_smoke_call(smoke_env, output, realtime_smoke)
    if argv and argv[0] == "realtime-audio-smoke":
        smoke_env = dict(env)
        smoke_env["argv"] = argv
        return realtime_audio_smoke_call(smoke_env, output, realtime_audio_smoke)
    if argv and argv[0] == "serve-media":
        media_env = dict(env)
        media_env["argv"] = argv
        return serve_media_call(media_env, output, media_server_runner)
    if argv and argv[0] == "serve-public":
        public_env = dict(env)
        public_env["argv"] = argv
        return serve_public_call(public_env, output, public_server_runner)
    if argv and argv[0] == "run-live-scenarios":
        live_env = env_with_dotenv(env)
        live_env["argv"] = argv
        return run_live_scenarios_command(live_env, output, live_scenarios_runner)

    print(
        "usage: python3 -m pgai_patient_bot.cli "
        "[dry-run-call|twilio-check|place-call --live|serve|"
        "export-mp3 <call_dir>|transcribe-analyze-call <call_dir> --live|"
        "serve-media --live|serve-public --live|"
        "run-live-scenarios <scenario-or-range> --live|"
        "tunnel-check|endpoint-check|"
        "realtime-smoke --live|realtime-audio-smoke --live]",
        file=output,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
