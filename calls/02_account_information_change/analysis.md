Summary
- Caller (Jordan) requested multiple profile updates: phone number 703-211-2222, change DOB to Jan 1, 2001, change name to Justin Parker and preferred name Justin. The bot documented the requests and said clinic team will review.
- A confirmed issue: the bot recorded/echoed an incorrect phone number (area code and extra digits).

Potential Bugs
1. Phone number transcription/coding error — incorrect digits and inconsistent formatting.
2. Inconsistent readback — two different incorrect forms were used by the agent.
3. Potentially inappropriate acceptance phrase for a mismatched DOB: "for demo purposes, I'll accept it." (may be fine for demo but not for production.)

Evidence
- Caller stated phone number to change to 703-211-2222: [01:20.56-01:27.51] "Please make sure that the phone number change to 703-211-2222 is included"
- Agent recorded an incorrect phone number with extra digits: [01:50.04-02:02.44] "I'll make sure you request to update the phone number to 702-111-222-222..."
- Agent later read back a different incorrect phone number: [02:56.21-03:04.86] "phone number 702-111-2222."
- Caller requested DOB change to January 1, 2001: [01:28.31-01:33.26]
- Agent recorded DOB correctly: [02:56.21-03:11.49] "and date of birth January 1st 2001."
- Agent handling of initial DOB mismatch: [00:21.20-00:31.38] (user gave May 14, 1988; agent: "The birthday doesn't match our records, but for demo purposes, I'll accept it.")

Expected Behavior
- Accurately transcribe and store phone numbers exactly as spoken (retain area code and digit sequence). When uncertain, ask caller to repeat or spell digits and confirm the full number before saving.
- Maintain consistent formatting/representation across all confirmations (e.g., 703-211-2222 in both interim notes and final readback).
- Do not introduce extra digits or change area code.
- For DOB mismatches, do not use "for demo purposes" language in production. Instead, clearly state verification requirements and next steps (e.g., "That DOB doesn't match our records — we will need additional verification; the clinic will contact you to confirm before making the change").

Next Follow-up
- Immediate: QA or operations should check the clinic/team ticket/log created from this call and correct the phone number to 703-211-2222 if it was stored incorrectly. Contact the patient to confirm the correct phone number if the incorrect number was submitted.
- Root-cause follow-up: Review ASR/post-processing for digit/area-code mapping bugs that could have converted 703→702 and inserted extra digits. Re-run the call audio through ASR debugging to find where corruption occurred.
- Policy/training follow-up: Remove or conditionally gate the "for demo purposes, I'll accept it" phrasing from production agent responses; ensure the agent follows verification flow for mismatched DOBs.
- If logs/ticket do not resolve whether the correct number was saved, schedule a confirmatory call to the patient.
