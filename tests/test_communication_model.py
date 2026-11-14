import unittest

from src.behaviour.communication_model import CommunicationEvent


class TestCommunicationEvent(unittest.TestCase):

    def create_event(self, **overrides):
        values = {
            "speaker_id": "CLINICIAN-001",
            "listener_id": "PERSON-001",
            "intended_message": "Your appointment is Thursday at 10 am.",
            "perceived_message": "Your appointment is Thursday at 10 am.",
            "listener_interpretation": "The appointment is Thursday at 10 am.",
        }

        values.update(overrides)

        return CommunicationEvent(**values)

    def test_valid_communication_event(self):
        event = self.create_event()

        self.assertTrue(event.validate())

    def test_unknown_listener_interpretation_is_valid(self):
        event = self.create_event(
            listener_interpretation=None
        )

        self.assertTrue(event.validate())

    def test_unknown_intended_message_is_valid(self):
        event = self.create_event(
            intended_message=None
        )

        self.assertTrue(event.validate())

    def test_unknown_perceived_message_is_valid(self):
        event = self.create_event(
            perceived_message=None
        )

        self.assertTrue(event.validate())

    def test_empty_listener_interpretation_is_rejected(self):
        event = self.create_event(
            listener_interpretation=""
        )

        with self.assertRaises(ValueError):
            event.validate()

    def test_same_speaker_and_listener_is_rejected(self):
        event = self.create_event(
            listener_id="CLINICIAN-001"
        )

        with self.assertRaises(ValueError):
            event.validate()

    def test_empty_message_is_rejected(self):
        event = self.create_event(
            intended_message=""
        )

        with self.assertRaises(ValueError):
            event.validate()

    def test_invalid_channel_is_rejected(self):
        event = self.create_event(
            channel="telepathy"
        )

        with self.assertRaises(ValueError):
            event.validate()

    def test_invalid_outcome_is_rejected(self):
        event = self.create_event(
            initial_outcome="confused"
        )

        with self.assertRaises(ValueError):
            event.validate()

    def test_successful_clarification_can_be_recorded(self):
        event = self.create_event(
            perceived_message="Your appointment is Tuesday at 10 am.",
            listener_interpretation="The appointment is Tuesday at 10 am.",
            clarification_requested=True,
            initial_outcome="misunderstood",
            final_outcome="understood",
        )

        self.assertTrue(event.validate())
        self.assertTrue(event.clarification_requested)
        self.assertEqual(event.initial_outcome, "misunderstood")
        self.assertEqual(event.final_outcome, "understood")

    def test_event_accepts_custom_environment(self):
        from src.behaviour.communication_model import CommunicationEnvironment

        environment = CommunicationEnvironment(
            background_noise=0.7,
            distance_metres=3.0,
            speaker_face_visible=False,
            written_information_available=True,
            message_clarity=0.8,
        )

        event = self.create_event(environment=environment)

        self.assertTrue(event.validate())
        self.assertEqual(event.environment.background_noise, 0.7)
        self.assertTrue(event.environment.written_information_available)

    def test_event_rejects_invalid_environment(self):
        from src.behaviour.communication_model import CommunicationEnvironment

        environment = CommunicationEnvironment(background_noise=1.5)

        event = self.create_event(environment=environment)

        with self.assertRaises(ValueError):
            event.validate()


if __name__ == "__main__":
    unittest.main()
