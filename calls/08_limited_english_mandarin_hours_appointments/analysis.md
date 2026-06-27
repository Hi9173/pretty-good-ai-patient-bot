Summary
- Caller requested Mandarin. The system connected to a Chinese-speaking path, but multiple agent utterances were transcribed/played as unintelligible romanized fragments (e.g., "Xin Zhao Su Wonin Dei Chu Shang Riki", "Shun, Shuo, Shu...").
- A clear appointment confirmation was delivered in Chinese at 02:08 by agent C (6/26 Mon 1:30 PM, 220 Athens Way, Nashville, TN). Caller then requested clinic hours; transcript ends before hours are given.

Potential Bugs
1. Garbled Chinese output/transcription (likely ASR/TTS or language-handling bug).
2. Possible DOB mis-capture or mis-confirmation (ambiguous: caller said 1988-05-14 but later mentions 1978…).
3. Call flow incompletion: business-hours request unanswered in captured transcript (may be a session cut or agent failure to respond).

Evidence (timestamps)
- 01:01.36 — 01:07.46: B: "Xin Zhao Su Wonin Dei Chu Shang Riki" (nonsense/romanization).
- 01:31.54 — 01:36.94: B: "Shun, Shuo, Shu, Nin, De Shu, Cheng, Ri, Qi." (fragmented syllables instead of fluent Mandarin).
- 01:14.86 — 01:26.96: A states DOB: "我的出生日期是1988年5月14日…"
- 01:38.69: A: "1978年5月14日用数字说是1988-05-14" (caller mentions both years — ambiguous).
- 02:08.92 — 02:15.37: C: Correct Chinese appointment confirmation (clear, contrasts with B's outputs).
- 02:17.32 — 02:27.42: Caller requests clinic hours; no agent reply in transcript.

Expected Behavior
- When caller requests Mandarin, system should switch to fluent Mandarin audio (or a correct transcription) with intelligible phrases (either Chinese characters or accurate pinyin/English translation), not fragmented romanization.
- DOB readback/confirmation should be clear and unambiguous (confirm digits verbally in the chosen language).
- Appointment and business-hours queries should both be answered; if transfer to a Chinese agent occurs, the agent should complete the requested info.

Next Follow-up
- Reproduce the issue by calling the same flow and forcing Mandarin language path; capture full audio and system logs for 00:50–01:40 and 02:00–02:30.
- Attach the raw audio for the garbled segments and the ASR/TTS debug logs (language detection, selected TTS voice, pinyin conversion, and transcription output).
- Check whether the garbled output came from:
  - ASR transcription (wrong tokenization into Latin syllables), or
  - TTS generation (wrong voice or phoneme mapping), or
  - a middleware transliteration step mistakenly enabled.
- Verify DOB captured in the backend record for this call and confirm which year was stored (1978 vs 1988).
- If logs show the agent C provided appointment details correctly, confirm whether the remaining business-hours request was answered after the transcript end or if the call dropped—if not, schedule a re-call to complete the request.

If no bug is confirmed
- If audio shows clear Mandarin speech and the transcript-only is garbled, this is a transcription/export bug; provide the raw audio to confirm. If audio itself is garbled, it confirms a runtime ASR/TTS/language-switch bug.
