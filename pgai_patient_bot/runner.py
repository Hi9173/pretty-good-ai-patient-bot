import json
from pathlib import Path

from pgai_patient_bot.artifacts import write_bug_report, write_call_artifacts
from pgai_patient_bot.audio import symbolic_audio
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.openai_realtime import (
    FakeRealtimeConnection,
    configure_realtime_connection,
    realtime_audio_from_connection,
)
from pgai_patient_bot.scenarios import patient_scenarios
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_media_websocket


async def run_mock_call(root, call_id, scenario):
    root = Path(root)
    response_payload = symbolic_audio(f"{scenario['id']}-response")
    responses = {payload: response_payload for payload in scenario["caller_payloads"]}
    twilio = FakeWebSocket(twilio_mock_call(scenario["caller_payloads"], stream_sid=call_id))
    realtime = FakeRealtimeConnection(responses)

    await configure_realtime_connection(realtime, scenario["goal"])
    # This mirrors the future live path while keeping all network boundaries fake.
    outbound_count = await handle_media_websocket(
        twilio,
        lambda payload: realtime_audio_from_connection(realtime, payload),
    )

    metadata = {
        "call_id": call_id,
        "scenario_id": scenario["id"],
        "goal": scenario["goal"],
        "mocked": True,
        "outbound_media_frames": outbound_count,
        "realtime_event_types": [json.loads(message)["type"] for message in realtime.sent],
    }
    transcript = (
        f"PATIENT: {scenario['goal']}\n"
        f"ASSISTANT: Mock response payload {response_payload}\n"
    )
    analysis = (
        "# Mock analysis\n\n"
        f"Scenario `{scenario['id']}` completed through fake Twilio and fake Realtime.\n"
    )

    call_dir = write_call_artifacts(root, call_id, metadata, transcript, analysis)
    return {
        "root": root,
        "call_id": call_id,
        "call_dir": call_dir,
        "issue": {
            "title": f"Mock issue: {scenario['id']}",
            "severity": "Low",
            "call": call_id,
            "evidence": "Mock analysis placeholder.",
            "expected": "Replace with real call evidence before submission.",
        },
    }


async def run_mock_batch(root, scenarios=None):
    scenarios = patient_scenarios() if scenarios is None else list(scenarios)
    results = []
    for index, scenario in enumerate(scenarios, start=1):
        results.append(await run_mock_call(root, f"call-{index:03d}", scenario))

    write_bug_report(root, [result["issue"] for result in results])
    return results
