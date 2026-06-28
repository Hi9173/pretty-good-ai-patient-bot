# Pretty Good AI Patient Bot

Local test harness for the Pretty Good AI voice-bot challenge. It places guarded Twilio calls, streams the call audio through OpenAI Realtime as a scripted patient persona, records the conversation, exports MP3, transcribes the call, and writes a short analysis artifact.

Normal tests are offline and secret-free. Live Twilio/OpenAI paths require explicit `--live` flags plus `.env` configuration.

## What It Does

- Generates TwiML for Twilio `<Connect><Stream>` calls.
- Serves one public process with both `/twiml` and `/media`.
- Bridges Twilio PCMU media frames to OpenAI Realtime and sends Realtime audio deltas back to Twilio.
- Records raw PCMU chunks and exports each captured call to `recording.mp3`.
- Transcribes and analyzes captured MP3 calls.
- Tracks Twilio Stream status callbacks in `stream_status.jsonl`.
- Runs 10 numbered patient scenarios with one command.
- Includes the final call MP3s, transcripts, analyses, and bug report as submission artifacts.

## Current Call Flow

1. The CLI starts the local public server on port `8000`.
2. The CLI starts ngrok using `PUBLIC_BASE_URL`.
3. Twilio fetches `/twiml`.
4. Twilio opens `/media` as a WebSocket stream.
5. The bridge forwards Pretty Good AI audio frames to OpenAI Realtime.
6. Realtime acts as the scripted patient and returns audio.
7. The bridge sends patient audio back to Twilio.
8. After the call completes, the CLI exports MP3, transcribes, and writes analysis.

Transcription and analysis happen after the call. They are not in the live speech-to-speech path.

See [system_architecture.md](system_architecture.md) for the short architecture summary. The detailed build history is preserved in [tests/checkpoint_history.md](tests/checkpoint_history.md).

## Project Layout

```text
pgai_patient_bot/
  app.py                local TwiML HTTP surface
  artifacts.py          MP3 export and artifact helpers
  call_review.py        transcription and analysis helpers
  checkpoint.py         Twilio request construction and config
  cli.py                command-line entry point
  endpoint_check.py     public /twiml and /media verification
  media.py              Twilio media event contract
  media_server.py       local /media WebSocket server wrapper
  openai_realtime.py    Realtime event/session helpers
  public_server.py      single-port public TwiML and media server
  runner.py             offline mocked call runner
  scenarios.py          patient scenario fixtures
tests/                  unittest coverage
calls/                  final call recordings, transcripts, and analyses
```

## Setup

Use Python 3. The offline test suite only needs the standard library. Live calling also needs:

- `websockets`
- `websocket-client`
- `ffmpeg`
- `ngrok`

Install the Python packages in your preferred environment:

```bash
python3 -m pip install websockets websocket-client
```

Install `ffmpeg` and `ngrok` separately if they are not already available on your machine.

Create a local environment file:

```bash
cp .env.example .env
```

Fill in `.env`:

```text
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=...
PUBLIC_BASE_URL=https://your-static-ngrok-domain.example
OPENAI_API_KEY=...
CALL_ARTIFACT_ROOT=.
```

Do not commit real secrets. `.env` is local-only.

## Run Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

## Run Live Scenarios

Run one scenario:

```bash
python3 -m pgai_patient_bot.cli run-live-scenarios 2 --live
```

Run a range:

```bash
python3 -m pgai_patient_bot.cli run-live-scenarios 1-10 --live
```

The command:

1. reads `.env`
2. starts the public `/twiml` plus `/media` server
3. starts ngrok
4. checks the public endpoints
5. places the Twilio call
6. waits for Twilio completion
7. exports `recording.mp3`
8. writes `transcript.txt` and `analysis.md`

Artifacts are written to numbered scenario folders, for example:

```text
calls/02_account_information_change/
  audio/
  audio_manifest.json
  recording.mp3
  stream_status.jsonl
  transcript.txt
  analysis.md
```

## Scenarios

1. `returning_patient_dob_verification`
2. `account_information_change`
3. `refill_missing_triage`
4. `adversarial_schedule_constraints`
5. `emergency_symptom_scheduling`
6. `spanish_hours_upcoming_appointments`
7. `limited_english_hours_appointments`
8. `limited_english_mandarin_hours_appointments`
9. `recording_consent_declined`
10. `roommate_privacy_appointment_lookup`

Each scenario includes a persona, facts to reveal, conversation rules, completion criteria, expected behavior, and bug triggers.

## Useful Commands

Dry-run the Twilio request without placing a call:

```bash
python3 -m pgai_patient_bot.cli dry-run-call
```

Check Twilio-facing config without printing secrets:

```bash
python3 -m pgai_patient_bot.cli twilio-check
```

Verify public tunnel URL wiring:

```bash
python3 -m pgai_patient_bot.cli tunnel-check
```

Verify `/twiml` and `/media` through the configured public URL:

```bash
python3 -m pgai_patient_bot.cli endpoint-check
```

Start the combined public server manually:

```bash
python3 -m pgai_patient_bot.cli serve-public --live
```

Export an existing captured call to MP3:

```bash
python3 -m pgai_patient_bot.cli export-mp3 calls/03_refill_missing_triage
```

Transcribe and analyze an existing MP3 call:

```bash
python3 -m pgai_patient_bot.cli transcribe-analyze-call calls/03_refill_missing_triage --live
```

Run OpenAI Realtime smoke checks without placing a Twilio call:

```bash
python3 -m pgai_patient_bot.cli realtime-smoke --live
python3 -m pgai_patient_bot.cli realtime-audio-smoke --live
```

## Local Server Notes

For most live work, use `run-live-scenarios`; it starts the needed server and tunnel for you.

Manual local TwiML server:

```bash
python3 -m pgai_patient_bot.cli serve
```

Manual local media WebSocket server:

```bash
python3 -m pgai_patient_bot.cli serve-media --live
```

Manual combined public server:

```bash
python3 -m pgai_patient_bot.cli serve-public --live
```

If `/twiml` and `/media` use separate public tunnels, set both:

```bash
PUBLIC_BASE_URL=https://your-http-tunnel.example
PUBLIC_MEDIA_BASE_URL=https://your-media-tunnel.example
```

## Submission Artifacts

- `calls/` contains the final MP3 recordings, transcripts, analyses, and stream status evidence for the 10 scenarios.
- `bug_report.md` ranks the discovered issues by severity and links each finding to the relevant call artifact.
- Raw captured audio chunks under `calls/*/audio/` are local debug data and should stay out of git.
- `public_server.log` files are temporary debugging logs and should not be committed.
- Keep real API keys, Twilio tokens, ngrok tokens, phone numbers, and `.env` out of the public repo.
