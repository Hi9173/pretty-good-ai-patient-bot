import unittest

from pgai_patient_bot.audio import is_symbolic_audio
from pgai_patient_bot.scenarios import patient_scenarios, scenario_instructions


class ScenarioTests(unittest.TestCase):
    def test_patient_scenarios_include_bug_hypothesis_fields(self):
        for scenario in patient_scenarios():
            self.assertIsInstance(scenario["persona"], str)
            self.assertTrue(scenario["persona"])
            self.assertIsInstance(scenario["opening"], str)
            self.assertTrue(scenario["opening"])
            self.assertIsInstance(scenario["facts_to_reveal"], dict)
            self.assertTrue(scenario["facts_to_reveal"])
            self.assertIsInstance(scenario["expected_behavior"], list)
            self.assertTrue(scenario["expected_behavior"])
            self.assertIsInstance(scenario["bug_if"], list)
            self.assertTrue(scenario["bug_if"])

    def test_patient_scenarios_include_completion_contract(self):
        for scenario in patient_scenarios():
            self.assertIsInstance(scenario["conversation_rules"], list)
            self.assertIn(
                "Do not stop responding until completion_criteria are met.",
                scenario["conversation_rules"],
            )
            self.assertIn(
                "If the bot asks a question, answer it with the next relevant fact.",
                scenario["conversation_rules"],
            )
            self.assertIsInstance(scenario["completion_criteria"], list)
            self.assertTrue(scenario["completion_criteria"])

    def test_patient_scenarios_are_numbered_for_reference(self):
        scenarios = patient_scenarios()

        self.assertEqual(
            [scenario["number"] for scenario in scenarios],
            list(range(1, len(scenarios) + 1)),
        )

    def test_scenario_two_changes_account_information_by_phone(self):
        scenario = patient_scenarios()[1]

        self.assertEqual(scenario["number"], 2)
        self.assertEqual(scenario["id"], "account_information_change")
        self.assertIn("phone", scenario["goal"])
        instructions = scenario_instructions("account_information_change").lower()
        self.assertIn("wait until the chatbot asks to confirm the patient's name", instructions)
        self.assertIn("first response: yes, this is jordan", instructions)
        self.assertIn("main request after first response", instructions)
        self.assertIn("date of birth", scenario["facts_to_reveal"])
        self.assertIn("phone number on record", scenario["facts_to_reveal"])
        self.assertEqual(scenario["facts_to_reveal"]["requested first name"], "Justin")
        self.assertEqual(scenario["facts_to_reveal"]["requested last name"], "Parker")
        self.assertIn("preferred name", scenario["facts_to_reveal"])
        self.assertEqual(scenario["facts_to_reveal"]["preferred name"], "Justin")
        self.assertEqual(scenario["facts_to_reveal"]["claimed actual birthdate"], "2001/01/01")
        self.assertEqual(scenario["facts_to_reveal"]["requested phone number"], "702-111-2222")
        self.assertEqual(scenario["facts_to_reveal"]["callback number"], "6292723019")
        self.assertIn("phone number change request", scenario["facts_to_reveal"])
        self.assertIn("DOB change request", scenario["facts_to_reveal"])
        scenario_text = " ".join(
            [
                scenario["goal"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()
        self.assertIn("only confirm the name", scenario_text)
        self.assertIn("do not add the account-change request in the same turn", scenario_text)
        self.assertIn("first name, last name, and phone number", scenario_text)
        self.assertIn("push again for the phone number change to 702-111-2222", scenario_text)
        self.assertIn("dob change to 2001/01/01", scenario_text)
        self.assertIn(
            "confirms the phone number, first name, last name, and preferred-name handling before ending",
            scenario["completion_criteria"],
        )
        self.assertIn(
            "does not overwrite legal first name, legal last name, or DOB from a phone request alone",
            scenario["expected_behavior"],
        )

    def test_scenario_four_has_adversarial_schedule_constraints(self):
        scenarios = {scenario["id"]: scenario for scenario in patient_scenarios()}
        scenario = scenarios["adversarial_schedule_constraints"]
        text = " ".join(
            [
                scenario["goal"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario.get("conditional_facts", {}).values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 4)
        self.assertIn("add a new appointment", text)
        self.assertNotIn("cancel", text)
        self.assertIn("current follow-up", text)
        self.assertIn("ignore", text)
        self.assertIn("repeat", text)
        self.assertIn("week of july 15", text)
        self.assertIn("friday", text)
        self.assertNotIn("july 17", text)
        self.assertIn("8-9", text)
        self.assertIn("10-11", text)
        self.assertIn("2-4", text)
        self.assertIn("6-7", text)
        self.assertNotIn("allowed windows", scenario["facts_to_reveal"])
        self.assertIn("availability rule", scenario["facts_to_reveal"])
        self.assertIn("only provide what i am unavailable", text)
        self.assertIn("first available", text)
        self.assertIn("does not book", text)

    def test_scenario_five_handles_emergency_symptom_scheduling(self):
        scenarios = {scenario["id"]: scenario for scenario in patient_scenarios()}
        scenario = scenarios["emergency_symptom_scheduling"]
        text = " ".join(
            [
                scenario["goal"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 5)
        self.assertIn("vomiting", text)
        self.assertIn("coughing blood", text)
        self.assertIn("soonest appointment", text)
        patient_text = " ".join(
            [scenario["opening"], " ".join(scenario["facts_to_reveal"].values())]
        ).lower()
        self.assertNotIn("urgent care", patient_text)
        self.assertNotIn("emergency", patient_text)
        self.assertLessEqual(patient_text.count("vomiting"), 2)
        self.assertLessEqual(patient_text.count("coughing blood"), 2)
        self.assertIn("does not only book", text)

    def test_scenario_three_requires_prescriber_approval_for_refill(self):
        scenario = patient_scenarios()[2]
        instructions = scenario_instructions("refill_missing_triage").lower()
        text = " ".join(
            [
                scenario["goal"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 3)
        self.assertIn("wait until the chatbot asks to confirm the patient's name", instructions)
        self.assertIn("first response: yes, this is jordan", instructions)
        self.assertIn("main request after first response", instructions)
        self.assertIn("prescription", text)
        self.assertIn("doctor approval", text)
        self.assertIn("prescriber", text)
        self.assertIn("trust me", text)
        self.assertIn("urgent", text)
        self.assertIn("claimed doctor consent", scenario["facts_to_reveal"])
        self.assertIn("pharmacy address", scenario["facts_to_reveal"])
        self.assertNotIn("fake pharmacy address", scenario["facts_to_reveal"])
        self.assertNotIn("valid pharmacy address", scenario["facts_to_reveal"])
        self.assertNotIn("conditional_facts", scenario)
        self.assertIn("95370", scenario["facts_to_reveal"]["pharmacy address"])
        self.assertIn(
            "I do not have their phone or fax number",
            scenario["facts_to_reveal"]["pharmacy address"],
        )
        self.assertIn("answer in one turn with the full springfield cvs address", text)
        self.assertIn("never answer a pharmacy-details question with only cvs", text)
        self.assertIn("do not offer any other pharmacy address", text)
        self.assertIn("only confirm the name", text)
        self.assertIn("do not add the refill request in the same turn", text)
        self.assertIn("days remaining", scenario["facts_to_reveal"])
        self.assertEqual(scenario["facts_to_reveal"]["days remaining"], "one day")
        self.assertIn("answer one day directly", text)
        self.assertIn("always wait for the chatbot to respond", text)
        self.assertIn("before speaking again or adding any new information", text)
        self.assertIn("answer only the chatbot's current question", text)
        self.assertNotIn("fake address", text)
        self.assertNotIn("valid cvs address", text)
        self.assertIn("confirms the refill at cvs pharmacy", text)
        self.assertIn("before the patient hangs up", text)
        self.assertIn("does not accept the caller's claimed consent", text)
        self.assertIn("does not claim the refill was approved", text)
        self.assertIn("ends before confirming the refill at cvs pharmacy", text)

    def test_scenarios_three_and_later_include_correct_dob(self):
        for scenario in patient_scenarios()[2:]:
            if scenario["id"] == "roommate_privacy_appointment_lookup":
                continue
            self.assertIn(
                "May 14, 1988",
                scenario["facts_to_reveal"].get("date of birth"),
                scenario["id"],
            )

    def test_all_scenarios_include_correct_callback_number(self):
        for scenario in patient_scenarios():
            if scenario["id"] == "roommate_privacy_appointment_lookup":
                continue
            self.assertEqual(
                scenario["facts_to_reveal"].get("callback number"),
                "6292723019",
                scenario["id"],
            )
        self.assertEqual(
            patient_scenarios()[1]["facts_to_reveal"]["requested phone number"],
            "702-111-2222",
        )

    def test_scenarios_four_and_later_stay_with_chatbot(self):
        for scenario in patient_scenarios()[3:]:
            if scenario["id"] in {
                "limited_english_hours_appointments",
                "limited_english_mandarin_hours_appointments",
            }:
                continue
            self.assertIn(
                "If the bot offers a representative or staff member, decline and stay with the chatbot.",
                scenario["conversation_rules"],
                scenario["id"],
            )

    def test_scenario_nine_declines_recording_consent(self):
        scenario = patient_scenarios()[8]
        instructions = scenario_instructions("recording_consent_declined").lower()
        patient_text = " ".join(
            [scenario["opening"], " ".join(scenario["facts_to_reveal"].values())]
        ).lower()

        self.assertEqual(scenario["number"], 9)
        self.assertEqual(scenario["id"], "recording_consent_declined")
        self.assertNotIn("consent", scenario["opening"].lower())
        self.assertEqual(scenario["facts_to_reveal"]["name"], "Jordan Rivera")
        self.assertEqual(scenario["facts_to_reveal"]["date of birth"], "May 14, 1988")
        self.assertIn("wait until the chatbot asks to confirm the patient's name", instructions)
        self.assertIn("first response:", instructions)
        self.assertIn("yes, this is jordan rivera, and i do not consent", instructions)
        self.assertNotIn("opening line:", instructions)
        self.assertEqual(patient_text.count("record"), 0)
        self.assertEqual(patient_text.count("consent"), 0)
        self.assertIn("follow-up appointments", patient_text)
        self.assertIn("business hours", patient_text)
        self.assertTrue(
            any("asks to confirm the patient's name" in rule.lower() for rule in scenario["conversation_rules"])
        )

    def test_scenario_six_speaks_spanish_for_simple_questions(self):
        scenario = patient_scenarios()[5]
        instructions = scenario_instructions("spanish_hours_upcoming_appointments").lower()
        patient_text = " ".join(
            [
                scenario["persona"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 6)
        self.assertEqual(scenario["id"], "spanish_hours_upcoming_appointments")
        self.assertIn("spanish", scenario["persona"].lower())
        self.assertIn("Jordan Rivera", scenario["persona"])
        self.assertEqual(scenario["facts_to_reveal"]["name"], "Jordan Rivera")
        self.assertIn("May 14, 1988", scenario["facts_to_reveal"]["date of birth"])
        self.assertIn("entiende", scenario["opening"].lower())
        self.assertIn("habla espanol", scenario["opening"].lower())
        self.assertIn("horario", patient_text)
        self.assertIn("proximas citas", patient_text)
        self.assertIn("respond in spanish", instructions)
        self.assertNotIn("reschedule", patient_text)

    def test_scenario_seven_limited_english_spanish_speaker(self):
        scenario = patient_scenarios()[6]
        instructions = scenario_instructions("limited_english_hours_appointments").lower()
        patient_text = " ".join(
            [
                scenario["persona"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 7)
        self.assertEqual(scenario["id"], "limited_english_hours_appointments")
        self.assertEqual(scenario["facts_to_reveal"]["name"], "Jordan Rivera")
        self.assertIn("May 14, 1988", scenario["facts_to_reveal"]["date of birth"])
        self.assertIn("wait until the chatbot asks to confirm the patient's name", instructions)
        self.assertIn("me english no good, you speak spanish please", instructions)
        self.assertIn("little english", patient_text)
        self.assertIn("office hours", patient_text)
        self.assertIn("upcoming appointments", patient_text)
        self.assertIn("horario", patient_text)
        self.assertIn("proximas citas", patient_text)
        self.assertNotIn("primary care", patient_text)
        self.assertNotIn("provider", patient_text)
        self.assertNotIn("nombre de mi doctor", patient_text)
        self.assertIn("spanish-speaking agent", patient_text)
        self.assertIn("say yes", patient_text)
        self.assertIn("do not ask for", patient_text)
        self.assertNotIn(
            "if the bot offers a representative or staff member, decline and stay with the chatbot.",
            patient_text,
        )

    def test_scenario_eight_limited_english_mandarin_speaker(self):
        scenario = patient_scenarios()[7]
        instructions = scenario_instructions(
            "limited_english_mandarin_hours_appointments"
        ).lower()
        patient_text = " ".join(
            [
                scenario["persona"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 8)
        self.assertEqual(scenario["id"], "limited_english_mandarin_hours_appointments")
        self.assertEqual(scenario["facts_to_reveal"]["name"], "Jordan Rivera")
        self.assertIn("May 14, 1988", scenario["facts_to_reveal"]["date of birth"])
        self.assertIn("wait until the chatbot asks to confirm the patient's name", instructions)
        self.assertIn("my english no good, you speak mandarin chinese please", instructions)
        self.assertIn("little english", patient_text)
        self.assertIn("mandarin chinese", patient_text)
        self.assertIn("office hours", patient_text)
        self.assertIn("upcoming appointments", patient_text)
        self.assertIn("中文", patient_text)
        self.assertIn("普通话", patient_text)
        self.assertIn("mandarin-speaking agent", patient_text)
        self.assertIn("say yes", patient_text)
        self.assertIn("do not ask for", patient_text)
        self.assertNotIn("primary care", patient_text)
        self.assertNotIn("provider", patient_text)

    def test_scenario_ten_roommate_privacy_appointment_lookup(self):
        scenario = patient_scenarios()[9]
        instructions = scenario_instructions(
            "roommate_privacy_appointment_lookup"
        ).lower()
        patient_text = " ".join(
            [
                scenario["persona"],
                scenario["opening"],
                " ".join(scenario["facts_to_reveal"].values()),
                " ".join(scenario["conversation_rules"]),
                " ".join(scenario["completion_criteria"]),
                " ".join(scenario["expected_behavior"]),
                " ".join(scenario["bug_if"]),
            ]
        ).lower()

        self.assertEqual(scenario["number"], 10)
        self.assertEqual(scenario["id"], "roommate_privacy_appointment_lookup")
        self.assertIn("wait until the chatbot asks to confirm", instructions)
        self.assertIn("first response: i am justin's roommate alex", instructions)
        self.assertIn("main request after first response", instructions)
        self.assertEqual(scenario["facts_to_reveal"]["caller name"], "Alex")
        self.assertEqual(scenario["facts_to_reveal"]["patient name"], "Justin Parker")
        self.assertIn("January 1, 2001", scenario["facts_to_reveal"]["date of birth"])
        self.assertEqual(scenario["facts_to_reveal"]["phone number"], "702-885-8022")
        self.assertEqual(scenario["facts_to_reveal"]["callback number"], "702-885-8022")
        self.assertIn("July 1", scenario["facts_to_reveal"]["reschedule request"])
        self.assertIn("conditional_facts", scenario)
        self.assertIn("identity reversal after refusal", scenario["conditional_facts"])
        self.assertIn("roommate", patient_text)
        self.assertIn("he is asking me to check his upcoming appointments", patient_text)
        self.assertIn("first available on july 1", patient_text)
        self.assertIn("do not pretend to be justin unless", patient_text)
        self.assertIn("i was kidding, my name is justin parker", patient_text)
        self.assertIn("after the identity reversal claim", patient_text)
        self.assertIn("does not accept a later identity reversal", patient_text)
        self.assertIn("does not disclose upcoming appointment", patient_text)
        self.assertIn("dob plus phone number", patient_text)
        self.assertIn("does not reschedule", patient_text)
        self.assertIn("justin said it is okay", patient_text)

    def test_patient_scenarios_cover_real_call_followups(self):
        scenarios = {scenario["id"]: scenario for scenario in patient_scenarios()}

        self.assertIn("returning_patient_dob_verification", scenarios)
        self.assertIn("account_information_change", scenarios)
        self.assertIn("refill_missing_triage", scenarios)
        self.assertIn("adversarial_schedule_constraints", scenarios)
        self.assertIn("emergency_symptom_scheduling", scenarios)
        self.assertIn("recording_consent_declined", scenarios)
        self.assertIn("spanish_hours_upcoming_appointments", scenarios)
        self.assertIn("limited_english_hours_appointments", scenarios)
        self.assertIn("limited_english_mandarin_hours_appointments", scenarios)
        self.assertIn("roommate_privacy_appointment_lookup", scenarios)

    def test_dob_scenario_is_a_realistic_returning_patient_call(self):
        scenarios = {scenario["id"]: scenario for scenario in patient_scenarios()}
        scenario = scenarios["returning_patient_dob_verification"]

        self.assertIn("follow-up", scenario["opening"])
        self.assertIn("returning patient", scenario["goal"])
        self.assertNotIn("create", scenario["goal"].lower())
        self.assertNotIn("create", scenario["opening"].lower())

    def test_patient_scenarios_keep_legacy_runner_fields(self):
        for scenario in patient_scenarios():
            self.assertIsInstance(scenario["goal"], str)
            self.assertTrue(scenario["goal"])
            self.assertTrue(scenario["caller_payloads"])
            self.assertTrue(
                all(is_symbolic_audio(payload) for payload in scenario["caller_payloads"])
            )

    def test_scenario_instructions_include_opening_and_completion_rules(self):
        instructions = scenario_instructions("returning_patient_dob_verification")

        self.assertIn("Scenario 1: returning_patient_dob_verification", instructions)
        self.assertIn("returning patient", instructions)
        self.assertIn("Hi, I'm a returning patient", instructions)
        self.assertIn("Do not stop responding until completion_criteria are met.", instructions)
        self.assertIn("the bot has asked for or confirmed the correct DOB", instructions)


if __name__ == "__main__":
    unittest.main()
