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

## Checkpoint 14: guarded live Realtime audio commit

This checkpoint proves one real audio-shaped payload can reach the live Realtime input buffer:

- `pcmu_silence_payload(...)` generates base64 G.711 mu-law silence for a requested duration
- `live_realtime_audio_smoke(...)` opens a Realtime connection, disables server VAD for a manual commit, appends 200 ms of PCMU silence, commits the input buffer, and reads the commit event
- `python3 -m pgai_patient_bot.cli realtime-audio-smoke --live` is the only CLI path that attempts the live audio smoke test
- tests inject fake connections and smoke functions, so normal verification stays offline and secret-free

## Checkpoint 15: in-process Twilio-to-Realtime media bridge

This checkpoint adds the bridge that a future `/media` WebSocket server will call:

- `handle_media_websocket(...)` now streams model audio back to Twilio as media frames arrive, instead of buffering until the call ends
- `handle_realtime_media_websocket(...)` configures a Realtime session, forwards Twilio `media.payload` chunks as `input_audio_buffer.append`, and sends Realtime `response.output_audio.delta` chunks back as Twilio `media` frames
- `handle_live_media_websocket(...)` opens a live Realtime connection from an API key and delegates to the same bridge
- tests still inject fake Twilio and fake Realtime objects, so no Twilio call, public tunnel, or live call media is required yet

## Checkpoint 16: local `/media` WebSocket server

This checkpoint exposes the bridge through a local WebSocket server process:

- `media_handler(...)` accepts only `/media` WebSocket connections and rejects other paths
- `serve_media_websocket(...)` wraps the `websockets` server factory and delegates accepted connections to the live media bridge
- `python3 -m pgai_patient_bot.cli serve-media --live` starts the local WebSocket server with `OPENAI_API_KEY`
- tests inject fake server factories and bridge callbacks, so normal verification still avoids Twilio, tunnels, and live OpenAI calls

## Checkpoint 17: public tunnel readiness

This checkpoint verifies the URL wiring needed once a tunnel exists:

- `tunnel_urls(...)` requires an `https://` `PUBLIC_BASE_URL` and derives the public TwiML URL plus public `wss://.../media` URL
- `python3 -m pgai_patient_bot.cli tunnel-check` prints the public and local TwiML/media URLs without requiring Twilio credentials
- the check is intentionally tunnel-provider agnostic: ngrok, Cloudflare Tunnel, or another HTTPS/WSS tunnel can supply `PUBLIC_BASE_URL`
- no tunnel process, Twilio account, or live call is started by this checkpoint

## Checkpoint 18: separate media tunnel URL

This checkpoint removes a real tunnel mismatch before running Twilio:

- `PUBLIC_BASE_URL` remains the public HTTP base Twilio calls for `/twiml`
- optional `PUBLIC_MEDIA_BASE_URL` can point the TwiML `<Stream>` to a different public WebSocket-capable tunnel
- when `PUBLIC_MEDIA_BASE_URL` is absent, the existing one-base behavior remains unchanged
- `tunnel-check` prints the derived TwiML and media URLs for either one-tunnel or two-tunnel setup

## Checkpoint 19: combined `/twiml` and `/media` endpoint verification

This checkpoint turns tunnel wiring into one runnable endpoint check:

- `endpoint-check` fetches the public `/twiml` URL derived from `PUBLIC_BASE_URL`
- the TwiML XML is parsed and its `<Stream url="...">` value must match the expected public `/media` WebSocket URL
- the same command opens the public `/media` WebSocket URL to prove the media endpoint is reachable
- tests inject fake HTTP and WebSocket clients, so normal verification still avoids Twilio, real tunnels, and live calls

## Checkpoint 20: local endpoint process rehearsal

This checkpoint lets the two local server processes be checked before any public tunnel exists:

- `endpoint-check --local` fetches local `http://127.0.0.1:8000/twiml`
- the TwiML must still point at the configured public `wss://.../media` URL that Twilio will eventually use
- the same command probes local `ws://127.0.0.1:8765/media?probe=1` to verify the media server process is listening
- tests inject fake HTTP and WebSocket clients, so normal verification still avoids live sockets and OpenAI calls

## Checkpoint 21: probe-safe `/media`

This checkpoint prevents endpoint checks from opening live Realtime sessions:

- endpoint checks probe media with `/media?probe=1`
- `media_handler(...)` closes probe connections with code `1000` before delegating to the Realtime bridge
- normal `/media` connections still delegate to the live bridge for Twilio media streams
- unsupported paths still close with code `1008`

## Checkpoint 22: real local process rehearsal

This checkpoint verifies the local processes together, not just injected tests:

- the local TwiML HTTP server was started with dummy non-secret Twilio config
- the local media WebSocket server was started with a dummy placeholder OpenAI key
- `endpoint-check --local` fetched real localhost `/twiml` and probed real localhost `/media?probe=1`
- the check returned `TwiML: ok`, `Media: ok`, and `Stream URL: wss://public.example.test/media`
- both local server processes were stopped after the rehearsal

## Checkpoint 23: single-port public tunnel rehearsal

This checkpoint adapts the public tunnel setup to ngrok's one-host behavior:

- two named ngrok tunnels both received the same public hostname, and `/media?probe=1` routed to the TwiML HTTP server on port `8000`
- `serve-public --live` starts one WebSocket-capable server on port `8000`
- the same server returns TwiML for HTTP `/twiml` and handles WebSocket `/media`
- one ngrok tunnel to port `8000` successfully verified public `/twiml` and public `/media?probe=1`
- the public check returned `TwiML: ok`, `Media: ok`, and a stream URL shaped like `wss://<ngrok-host>/media`

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
- guarded live Realtime audio append/commit smoke command
- in-process Twilio media to Realtime media bridge
- local `/media` WebSocket server process
- single-port public TwiML and media server
- public tunnel URL readiness check
- optional separate public media tunnel URL
- combined public `/twiml` and `/media` endpoint verification
- local endpoint process rehearsal
- safe `/media` probe path
- verified local HTTP/WebSocket process rehearsal
- verified public ngrok tunnel rehearsal
- symbolic and tiny real base64 PCMU payload fixtures
- patient scenario fixtures
- mocked call artifacts and bug report generation

Not built yet:

- running public tunnel process
- real Twilio media audio
- actual Twilio call execution
- real recordings
- real transcripts
