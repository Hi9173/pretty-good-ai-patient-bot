import os
import sys
from urllib.parse import parse_qs

from pgai_patient_bot.app import make_server
from pgai_patient_bot.checkpoint import build_call_request, load_config


def dry_run_call(config, output):
    request = build_call_request(config)
    body = parse_qs(request.data.decode())

    print(f"{request.get_method()} {request.full_url}", file=output)
    print(f"To: {body['To'][0]}", file=output)
    print(f"From: {body['From'][0]}", file=output)
    print(f"Url: {body['Url'][0]}", file=output)
    return 0


def main(argv=None, env=None, output=None, server_factory=make_server):
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if env is None else env
    output = sys.stdout if output is None else output

    if argv == ["dry-run-call"]:
        return dry_run_call(load_config(env), output)
    if argv == ["serve"]:
        server_factory(env).serve_forever()
        return 0

    print("usage: python3 -m pgai_patient_bot.cli [dry-run-call|serve]", file=output)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
