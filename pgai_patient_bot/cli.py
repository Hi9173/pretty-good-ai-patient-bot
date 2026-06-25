import os
import sys
from urllib.parse import parse_qs

from pgai_patient_bot.app import make_server
from pgai_patient_bot.checkpoint import build_call_request, load_config
from pgai_patient_bot.endpoint_check import run_endpoint_check
from pgai_patient_bot.media_server import run_media_server
from pgai_patient_bot.openai_realtime import (
    live_realtime_audio_smoke,
    live_realtime_smoke,
)
from pgai_patient_bot.public_server import run_public_server
from pgai_patient_bot.tunnel import print_tunnel_check


def dry_run_call(config, output):
    request = build_call_request(config)
    body = parse_qs(request.data.decode())

    print(f"{request.get_method()} {request.full_url}", file=output)
    print(f"To: {body['To'][0]}", file=output)
    print(f"From: {body['From'][0]}", file=output)
    print(f"Url: {body['Url'][0]}", file=output)
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
):
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if env is None else env
    output = sys.stdout if output is None else output

    if argv == ["dry-run-call"]:
        return dry_run_call(load_config(env), output)
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

    print(
        "usage: python3 -m pgai_patient_bot.cli "
        "[dry-run-call|serve|serve-media --live|serve-public --live|"
        "tunnel-check|endpoint-check|"
        "realtime-smoke --live|realtime-audio-smoke --live]",
        file=output,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
