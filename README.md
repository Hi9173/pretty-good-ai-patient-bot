# Pretty Good AI Patient Bot

Offline-first scaffold for the Pretty Good AI voice-bot challenge.

The project is currently paused before live OpenAI Realtime or Twilio execution. Everything in the test suite runs locally with fake Twilio media, fake WebSockets, and a fake Realtime connection.

## What Works

- Builds a safe Twilio call request targeting the assessment number only.
- Serves local TwiML for a future `/media` WebSocket stream.
- Parses Twilio `start`, `media`, and `stop` events.
- Runs an in-process Twilio media loop.
- Mocks OpenAI Realtime `session.update`, `input_audio_buffer.append`, and `response.output_audio.delta` events.
- Keeps symbolic mock payloads separate from real base64 PCMU-shaped payloads.
- Defines five patient scenario fixtures.
- Generates mocked `calls/call-001` through `calls/call-005` artifacts plus `bug_report.md`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the checkpoint-by-checkpoint design notes.

## Project Layout

```text
pgai_patient_bot/
  app.py                local TwiML HTTP surface
  checkpoint.py         Twilio request construction and config
  media.py              Twilio media event contract and loop
  openai_realtime.py    fake Realtime event/session helpers
  runner.py             offline mocked call and batch runner
  scenarios.py          patient scenario fixtures
  artifacts.py          call artifact and bug report writers
tests/                  unittest checkpoint coverage
```

## Setup

This project currently uses only the Python standard library.

```bash
cp .env.example .env
```

Fill in `.env` before using Twilio-facing commands. Do not commit real secrets.

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

## Current Status

Built and tested: offline call flow, fake Realtime loop, scenario fixtures, mocked artifacts, and bug report shape.

Not built yet: actual `/media` WebSocket server, generated speech audio, live OpenAI Realtime connection/auth, actual Twilio call execution, real recordings, or real transcripts.
