# Pretty Good AI Patient Bot

Offline-first scaffold for the Pretty Good AI voice-bot challenge.

The project is currently paused before Twilio execution. Everything in the test suite runs locally with fake Twilio media, fake WebSockets, and a fake Realtime connection; live OpenAI Realtime checks are guarded behind explicit CLI flags.

## What Works

- Builds a safe Twilio call request targeting the assessment number only.
- Serves local TwiML for a future `/media` WebSocket stream.
- Parses Twilio `start`, `media`, and `stop` events.
- Runs an in-process Twilio media loop.
- Mocks OpenAI Realtime `session.update`, `input_audio_buffer.append`, and `response.output_audio.delta` events.
- Keeps symbolic mock payloads separate from real base64 PCMU-shaped payloads.
- Defines five patient scenario fixtures.
- Generates mocked `calls/call-001` through `calls/call-005` artifacts plus `bug_report.md`.
- Runs guarded live Realtime session and audio-commit smoke tests when explicitly requested.
- Bridges Twilio media frames into a Realtime connection shape and streams model audio frames back.
- Starts a local `/media` WebSocket server for Twilio media streams.
- Starts a single-port public server that serves both `/twiml` and `/media`.
- Verifies public tunnel URL wiring before Twilio is configured.
- Verifies public `/twiml` and `/media` endpoints in one command.
- Verifies local `/twiml` and `/media` server processes before a public tunnel exists.
- Probes `/media` safely without opening a live Realtime session.
- Has passed a real localhost `/twiml` plus `/media?probe=1` process rehearsal.

## Call Flow

The live loop is speech-to-speech through Realtime:

1. Start a Twilio call to the assessment number.
2. Twilio requests this app's TwiML and opens a media stream to `/media`.
3. Twilio sends caller audio frames to the media bridge.
4. The bridge forwards those PCMU audio frames to OpenAI Realtime.
5. Realtime handles speech understanding, response generation, and response audio.
6. The bridge sends Realtime audio deltas back to Twilio as media frames.
7. Repeat until Twilio sends `stop`.

Transcripts are artifacts for evaluation and bug reports; they are not a separate ChatGPT hop in the hot path.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the checkpoint-by-checkpoint design notes.

## Project Layout

```text
pgai_patient_bot/
  app.py                local TwiML HTTP surface
  checkpoint.py         Twilio request construction and config
  endpoint_check.py     public /twiml and /media verification
  media.py              Twilio media event contract and loop
  media_server.py       local /media WebSocket server wrapper
  openai_realtime.py    fake Realtime event/session helpers
  public_server.py      single-port public TwiML and media server
  runner.py             offline mocked call and batch runner
  scenarios.py          patient scenario fixtures
  artifacts.py          call artifact and bug report writers
tests/                  unittest checkpoint coverage
```

## Setup

Most tests use only the Python standard library. The guarded live Realtime adapter uses `websocket-client`.

```bash
python3 -m pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Fill in `.env` before using Twilio-facing commands. Do not commit real secrets.
For OpenAI Realtime work, set `OPENAI_API_KEY` in `.env` only.

## Run Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
```

## Dry-Run Twilio Request

This prints the request details without placing a call.

```bash
python3 -m pgai_patient_bot.cli dry-run-call
```

## Start Local TwiML Server

```bash
python3 -m pgai_patient_bot.cli serve
```

Then visit:

```text
http://127.0.0.1:8000/twiml
```

## Start Local Media WebSocket Server

This starts a local `/media` WebSocket listener. Twilio still needs a public tunnel before it can reach this from the internet.

```bash
export OPENAI_API_KEY=your_openai_api_key
python3 -m pgai_patient_bot.cli serve-media --live
```

By default it listens at:

```text
ws://127.0.0.1:8765/media
```

## Check Tunnel URLs

For a single public tunnel, start the combined public server and expose port `8000`.

```bash
export OPENAI_API_KEY=your_openai_api_key
python3 -m pgai_patient_bot.cli serve-public --live
```

Then start the tunnel:

```bash
ngrok http 8000
```

After starting a public HTTPS/WSS tunnel, set its public base URL and verify the URLs Twilio will use.

```bash
export PUBLIC_BASE_URL=https://your-tunnel.example
python3 -m pgai_patient_bot.cli tunnel-check
```

To verify that public `/twiml` returns TwiML pointing at the expected public `/media` WebSocket, and that the media server accepts a safe probe connection:

```bash
python3 -m pgai_patient_bot.cli endpoint-check
```

Before the tunnel is running, use local mode while `serve` and `serve-media --live` are running in separate terminals. The media probe uses `/media?probe=1`, so it should not open a live Realtime session.

```bash
python3 -m pgai_patient_bot.cli endpoint-check --local
```

If `/twiml` and `/media` are exposed through different tunnels, keep `PUBLIC_BASE_URL` for the HTTP TwiML endpoint and set `PUBLIC_MEDIA_BASE_URL` for the WebSocket media endpoint:

```bash
export PUBLIC_BASE_URL=https://your-http-tunnel.example
export PUBLIC_MEDIA_BASE_URL=https://your-media-tunnel.example
python3 -m pgai_patient_bot.cli tunnel-check
```

## Manual Realtime Smoke Tests

This opens one guarded OpenAI Realtime WebSocket session, sends `session.update`, reads one event, and exits. It does not place a Twilio call.

```bash
export OPENAI_API_KEY=your_openai_api_key
python3 -m pgai_patient_bot.cli realtime-smoke --live
```

This appends and commits a short generated PCMU silence payload to the live Realtime input buffer. It still does not place a Twilio call.

```bash
export OPENAI_API_KEY=your_openai_api_key
python3 -m pgai_patient_bot.cli realtime-audio-smoke --live
```

## Current Status

Built and tested: offline call flow, fake Realtime loop, guarded live Realtime adapter shape, guarded manual Realtime session and audio smoke commands, local `/media` WebSocket server, single-port public server, public tunnel URL readiness check, optional separate media tunnel URL, combined `/twiml` and `/media` endpoint verification, verified local and ngrok endpoint process rehearsals, safe media probing, scenario fixtures, mocked artifacts, and bug report shape.

Not built yet: running public tunnel process, actual Twilio call execution, real recordings, or real transcripts.
