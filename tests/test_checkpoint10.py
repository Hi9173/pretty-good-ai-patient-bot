import asyncio
import json
import unittest

from pgai_patient_bot.audio import (
    REAL_PCMU_SILENCE,
    is_real_audio_payload,
    is_symbolic_audio,
)
from pgai_patient_bot.mock_data import twilio_mock_call
from pgai_patient_bot.openai_realtime import (
    FakeRealtimeConnection,
    configure_realtime_connection,
    realtime_audio_from_connection,
)
from pgai_patient_bot.websocket_adapter import FakeWebSocket, handle_media_websocket


class Checkpoint10Tests(unittest.TestCase):
    def test_real_pcmu_payload_flows_through_mocked_twilio_realtime_loop(self):
        self.assertTrue(is_real_audio_payload(REAL_PCMU_SILENCE))
        self.assertFalse(is_symbolic_audio(REAL_PCMU_SILENCE))

        twilio = FakeWebSocket(twilio_mock_call([REAL_PCMU_SILENCE], stream_sid="MZREAL"))
        realtime = FakeRealtimeConnection({REAL_PCMU_SILENCE: REAL_PCMU_SILENCE})

        async def run():
            await configure_realtime_connection(realtime, "Echo a tiny PCMU fixture.")
            return await handle_media_websocket(
                twilio,
                lambda payload: realtime_audio_from_connection(realtime, payload),
            )

        self.assertEqual(asyncio.run(run()), 1)
        self.assertEqual(
            json.loads(realtime.sent[1])["audio"],
            REAL_PCMU_SILENCE,
        )
        self.assertEqual(
            json.loads(twilio.sent[0])["media"]["payload"],
            REAL_PCMU_SILENCE,
        )


if __name__ == "__main__":
    unittest.main()
