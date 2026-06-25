# Architecture Document

This document records the checkpoint-by-checkpoint design for the Pretty Good AI voice-bot challenge scaffold.

## Checkpoint 1: call-request safety

This checkpoint proves three things without placing a paid phone call:

- required Twilio/public URL config can be loaded
- TwiML can connect a call to a future media WebSocket
- the outbound call request always targets the assessment number, `+18054398008`

## Checkpoint 2: local TwiML surface

This checkpoint adds the smallest runnable surface around checkpoint 1:

- `/twiml` returns TwiML with `<Connect><Stream url="wss://.../media">`
- unknown paths return `404`
- `dry-run-call` prints the Twilio request details without making a network call
- auth tokens are not printed by the dry run

## Checkpoint 3: media event contract

This checkpoint adds a local, dependency-free contract for the future `/media` WebSocket:

- Twilio `start` events record the `streamSid`
- Twilio `media` events collect inbound base64 audio payloads
- Twilio `stop` events mark the bridge closed
- outbound audio is formatted as a Twilio `media` event using the recorded `streamSid`
- outbound audio before `start` is rejected

## Checkpoint 4: in-process media loop

This checkpoint adds an async loop that can be reused by the future WebSocket handler:

- accepts an iterable of Twilio JSON messages
- feeds inbound caller audio payloads to a model-audio callback
- returns outbound Twilio `media` frames for model audio
- stops processing after a Twilio `stop` event
- skips outbound frames when the model callback returns no audio

## Checkpoint 5: mock media data

This checkpoint adds deterministic mock data for local tests:

- `twilio_mock_call(...)` creates `start`, `media`, and `stop` Twilio messages
- `fake_model_audio(...)` maps caller payloads to model payloads
- mock payloads are symbolic strings, not real audio yet
- the mock call can drive `run_media_loop(...)` end to end without sockets or APIs

## Checkpoint 6: fake WebSocket adapter

This checkpoint adds the smallest adapter shape for the future `/media` WebSocket:

- `FakeWebSocket` supports async iteration over inbound Twilio messages
- `FakeWebSocket.send(...)` records outbound messages
- `handle_media_websocket(...)` feeds inbound messages through `run_media_loop(...)`
- outbound Twilio `media` frames are sent back through the WebSocket object
- no real WebSocket server or dependency is required yet

## Checkpoint 7: OpenAI Realtime event contract

This checkpoint adds mocked OpenAI Realtime event helpers:

- `input_audio_event(...)` wraps caller audio as `input_audio_buffer.append`
- `output_audio_delta(...)` extracts `response.output_audio.delta` payloads
- `fake_realtime_audio(...)` lets the existing media loop act like a Realtime model
- event names were checked against the official OpenAI Realtime docs
- no OpenAI SDK, auth, or network calls are used yet

## Checkpoint 8: OpenAI Realtime session contract

This checkpoint adds the mocked Realtime session update event:

- `realtime_session_update(...)` builds a `session.update` event
- input and output audio use telephony-friendly `audio/pcmu`
- server VAD is enabled with automatic response creation
- model, voice, and instructions are explicit
- session shape was checked against the official OpenAI Realtime API reference

## Checkpoint 9: mocked submission slice

This combined checkpoint wires the local mock pieces into a submission-shaped loop:

- `FakeRealtimeConnection` records `session.update` and `input_audio_buffer.append`
- fake Realtime emits mocked `response.output_audio.delta` events back into the Twilio media loop
- audio helpers name `audio/pcmu`, validate real base64 payloads, and mark symbolic mock audio as `mock:...`
- `patient_scenarios(...)` provides scheduling, reschedule, refill, office-hours, and edge-case fixtures
- `write_call_artifacts(...)` creates `calls/call-001/metadata.json`, `transcript.txt`, and `analysis.md`
- `write_bug_report(...)` creates a simple issue report with severity, call reference, evidence, and expected behavior

## Checkpoint 10: real PCMU payload smoke test

This checkpoint replaces one symbolic mock path with a tiny real-shaped audio payload:

- `REAL_PCMU_SILENCE` is four bytes of PCMU silence encoded as base64
- the payload passes `is_real_audio_payload(...)`
- the payload is not treated as a `mock:...` symbolic fixture
- the same payload travels through fake Twilio media, the media loop, fake Realtime input, fake Realtime output, and outbound Twilio media
- no speech synthesis, recording, Twilio call, or OpenAI network request is involved

## Checkpoint 11: offline submission rehearsal

This checkpoint combines the remaining pre-live-Realtime work into one local runner:

- `run_mock_call(...)` turns one scenario into `calls/call-001/metadata.json`, `transcript.txt`, and `analysis.md`
- `run_mock_batch(...)` runs all five patient scenarios into `calls/call-001` through `calls/call-005`
- every mocked call uses fake Twilio media, the media loop, and `FakeRealtimeConnection`
- metadata records the Realtime event types sent during the run
- `bug_report.md` is generated from the mocked call analyses
- no real WebSocket server, Twilio call, OpenAI Realtime connection, or network request is involved

## Checkpoint 12: guarded live Realtime adapter

This checkpoint adds the live OpenAI Realtime connection shape without running it in tests:

- `realtime_websocket_url(...)` builds the GA WebSocket URL for `gpt-realtime-2`
- `realtime_headers(...)` builds the bearer auth and optional safety identifier headers
- `open_realtime_connection(...)` wraps a `websocket-client` connection behind the same `send`/`recv` shape as `FakeRealtimeConnection`
- tests inject a fake `websocket_module`, so no API key, network, or paid API call is used during normal verification

## Checkpoint 13: guarded manual Realtime smoke command

This checkpoint adds the smallest live smoke-test path while keeping normal tests offline:

- `live_realtime_smoke(...)` opens a Realtime connection, sends `session.update`, reads one event, then closes
- `python3 -m pgai_patient_bot.cli realtime-smoke --live` is the only CLI path that attempts the live smoke test
- the command requires `OPENAI_API_KEY` from the environment
- tests inject a fake smoke function, so no API key, network, or paid API call is used during normal verification

## Current Boundaries

Built:

- safe Twilio call request construction
- local TwiML HTTP endpoint
- Twilio media event parsing/formatting
- in-process media loop
- fake WebSocket adapter
- fake OpenAI Realtime session/input/output events
- guarded live OpenAI Realtime WebSocket adapter shape
- guarded manual Realtime smoke command
- symbolic and tiny real base64 PCMU payload fixtures
- patient scenario fixtures
- mocked call artifacts and bug report generation

Not built yet:

- actual `/media` WebSocket server
- generated speech audio
- actual Twilio call execution
- real recordings
- real transcripts
