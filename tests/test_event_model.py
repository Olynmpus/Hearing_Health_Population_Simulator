import unittest
from datetime import datetime

from src.simulation.event_model import SimulationEvent
from src.behaviour.communication_model import CommunicationEvent


class TestSimulationEvent(unittest.TestCase):

    def make_event(self, **overrides):
        values = {
            "event_id": "EVENT-001",
            "timestamp": datetime(2026, 1, 1, 9, 30),
            "event_type": "communication_attempt",
            "participants": ["PERSON-001", "PERSON-002"],
            "initiating_agent_id": "PERSON-001",
            "action": "initiate_conversation",
        }
        values.update(overrides)
        return SimulationEvent(**values)

    def test_valid_event(self):
        self.assertTrue(self.make_event().validate())

    def test_timestamp_must_be_datetime(self):
        event = self.make_event(timestamp="2026-01-01 09:30")
        with self.assertRaises(ValueError):
            event.validate()

    def test_participants_must_be_unique(self):
        event = self.make_event(
            participants=["PERSON-001", "PERSON-001"]
        )
        with self.assertRaises(ValueError):
            event.validate()

    def test_initiating_agent_must_be_participant(self):
        event = self.make_event(initiating_agent_id="PERSON-003")
        with self.assertRaises(ValueError):
            event.validate()

    def test_communication_must_involve_event_participants(self):
        communication = CommunicationEvent(
            speaker_id="PERSON-003",
            listener_id="PERSON-004",
            intended_message="Hello",
            perceived_message=None,
            listener_interpretation=None,
        )
        event = self.make_event(communication=communication)

        with self.assertRaises(ValueError):
            event.validate()

    def test_valid_communication_record(self):
        communication = CommunicationEvent(
            speaker_id="PERSON-001",
            listener_id="PERSON-002",
            intended_message="Hello",
            perceived_message=None,
            listener_interpretation=None,
        )
        event = self.make_event(communication=communication)

        self.assertTrue(event.validate())


if __name__ == "__main__":
    unittest.main()
