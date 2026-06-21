import json


def twilio_mock_call(payloads, stream_sid="MZMOCK"):
    messages = [json.dumps({"event": "start", "start": {"streamSid": stream_sid}})]
    messages.extend(
        json.dumps({"event": "media", "media": {"payload": payload}})
        for payload in payloads
    )
    messages.append(json.dumps({"event": "stop"}))
    return messages


def fake_model_audio(responses):
    async def model(payload):
        return responses.get(payload)

    return model
