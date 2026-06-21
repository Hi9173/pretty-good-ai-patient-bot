from pgai_patient_bot.audio import symbolic_audio


def patient_scenarios():
    return [
        {
            "id": "appointment_scheduling",
            "goal": "Schedule a routine primary-care appointment.",
            "caller_payloads": [symbolic_audio("appointment-hello")],
        },
        {
            "id": "reschedule",
            "goal": "Move an existing appointment to a later day.",
            "caller_payloads": [symbolic_audio("reschedule-hello")],
        },
        {
            "id": "refill",
            "goal": "Ask how to refill an existing prescription.",
            "caller_payloads": [symbolic_audio("refill-hello")],
        },
        {
            "id": "office_hours",
            "goal": "Ask when the office is open.",
            "caller_payloads": [symbolic_audio("hours-hello")],
        },
        {
            "id": "edge_case",
            "goal": "Ask for a weekend appointment after mentioning urgent symptoms.",
            "caller_payloads": [symbolic_audio("edge-weekend-urgent")],
        },
    ]
