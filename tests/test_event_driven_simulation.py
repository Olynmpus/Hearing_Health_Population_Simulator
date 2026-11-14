import unittest
from datetime import datetime
from types import SimpleNamespace

from src.agents.relationships import SocialRelationship
from src.simulation.event_driven_simulation import EventDrivenSimulation
from src.simulation.event_model import SimulationEvent


from unittest.mock import patch

class TestEventDrivenSimulation(unittest.TestCase):

    def setUp(self):
        self.experiment = SimpleNamespace(
            agents=[],
            relationships=[],
            random_seed=42,
        )

    def test_initialises_clock(self):
        simulation = EventDrivenSimulation(
            self.experiment,
            start_time=datetime(2026, 1, 1),
        )

        self.assertEqual(
            simulation.current_time,
            datetime(2026, 1, 1),
        )

    def test_uses_experiment_random_seed(self):
        simulation = EventDrivenSimulation(self.experiment)
        self.assertEqual(simulation.random_seed, 42)

    def test_accepts_random_seed_override(self):
        simulation = EventDrivenSimulation(
            self.experiment,
            random_seed=99,
        )

        self.assertEqual(simulation.random_seed, 99)

    def test_advances_simulated_time(self):
        simulation = EventDrivenSimulation(self.experiment)
        result = simulation.advance_time(hours=3)

        self.assertEqual(result, datetime(2026, 1, 1, 3))

    def test_rejects_negative_time(self):
        simulation = EventDrivenSimulation(self.experiment)

        with self.assertRaises(ValueError):
            simulation.advance_time(hours=-1)

    def test_initial_summary(self):
        simulation = EventDrivenSimulation(self.experiment)
        summary = simulation.summary()

        self.assertEqual(summary["population_size"], 0)
        self.assertEqual(summary["relationship_count"], 0)
        self.assertEqual(summary["event_count"], 0)
        self.assertEqual(summary["random_seed"], 42)

    def test_returns_unique_active_relationships(self):
        first = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )
        reverse = SocialRelationship(
            "PERSON-002", "PERSON-001", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                SimpleNamespace(agent_id="PERSON-001"),
                SimpleNamespace(agent_id="PERSON-002"),
            ],
            relationships=[first, reverse],
            random_seed=42,
        )

        simulation = EventDrivenSimulation(experiment)
        opportunities = simulation.get_interaction_opportunities()

        self.assertEqual(len(opportunities), 1)

    def test_excludes_inactive_relationships(self):
        relationship = SocialRelationship(
            "PERSON-001",
            "PERSON-002",
            "family",
            status="disconnected",
        )

        experiment = SimpleNamespace(
            agents=[
                SimpleNamespace(agent_id="PERSON-001"),
                SimpleNamespace(agent_id="PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        simulation = EventDrivenSimulation(experiment)

        self.assertEqual(
            simulation.get_interaction_opportunities(),
            [],
        )

    def make_agent(self, agent_id):
        state = SimpleNamespace(
            communication_confidence=0.6,
            social_participation=0.7,
            help_seeking_intention=0.5,
            trust_in_services=0.5,
            frustration=0.2,
        )
        return SimpleNamespace(agent_id=agent_id, state=state)

    def test_makes_initiation_decision_for_existing_relationship(self):
        relationship = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        simulation = EventDrivenSimulation(experiment)
        result = simulation.make_initiation_decision()

        self.assertIsNotNone(result)
        self.assertIn(
            result["initiating_agent_id"],
            ["PERSON-001", "PERSON-002"],
        )
        self.assertIn(
            result["contact_id"],
            ["PERSON-001", "PERSON-002"],
        )
        self.assertNotEqual(
            result["initiating_agent_id"],
            result["contact_id"],
        )
        self.assertIn(
            result["decision"]["action"],
            [
                "initiate_conversation",
                "avoid_interaction",
                "do_nothing",
            ],
        )

    def test_returns_none_without_interaction_opportunities(self):
        simulation = EventDrivenSimulation(self.experiment)

        self.assertIsNone(simulation.make_initiation_decision())

    def test_initiation_decision_is_reproducible(self):
        relationship = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        first = EventDrivenSimulation(experiment)
        second = EventDrivenSimulation(experiment)

        first_result = first.make_initiation_decision()
        second_result = second.make_initiation_decision()

        self.assertEqual(
            first_result["initiating_agent_id"],
            second_result["initiating_agent_id"],
        )
        self.assertEqual(
            first_result["decision"]["action"],
            second_result["decision"]["action"],
        )
    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_records_event_when_agent_initiates(self, mock_choose):
        relationship = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "initiate_conversation",
            "probabilities": {
                "initiate_conversation": 0.5,
                "avoid_interaction": 0.3,
                "do_nothing": 0.2,
            },
            "decision_basis": {"context": "initiation"},
        }

        simulation = EventDrivenSimulation(experiment)
        event = simulation.run_initiation_event()

        self.assertIsNotNone(event)
        self.assertEqual(event.event_id, "EVENT-000001")
        self.assertEqual(event.event_type, "communication_initiation")
        self.assertEqual(event.timestamp, simulation.current_time)
        self.assertEqual(len(event.participants), 2)
        self.assertEqual(event.action, "initiate_conversation")
        self.assertIsNone(event.communication)
        self.assertEqual(len(simulation.events), 1)
        self.assertEqual(simulation.next_event_id, 2)

    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_does_not_record_event_when_agent_does_nothing(self, mock_choose):
        relationship = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "do_nothing",
            "probabilities": {
                "initiate_conversation": 0.5,
                "avoid_interaction": 0.3,
                "do_nothing": 0.2,
            },
            "decision_basis": {"context": "initiation"},
        }

        simulation = EventDrivenSimulation(experiment)
        event = simulation.run_initiation_event()

        self.assertIsNone(event)
        self.assertEqual(len(simulation.events), 0)
        self.assertEqual(simulation.next_event_id, 1)
    
    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_response_decision_uses_recipient_and_reciprocal_relationship(
        self, mock_choose
    ):
        forward = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )
        reverse = SocialRelationship(
            "PERSON-002", "PERSON-001", "family"
        )

        recipient = self.make_agent("PERSON-002")

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                recipient,
            ],
            relationships=[forward, reverse],
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "continue_interaction",
            "probabilities": {
                "continue_interaction": 0.6,
                "withdraw": 0.2,
                "do_nothing": 0.2,
            },
            "decision_basis": {"context": "response"},
        }

        simulation = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        result = simulation.make_response_decision(initiation)

        self.assertEqual(
            result["responding_agent_id"], "PERSON-002"
        )
        self.assertEqual(
            result["initiating_agent_id"], "PERSON-001"
        )
        self.assertIs(result["relationship"], reverse)

        self.assertIs(
            mock_choose.call_args.kwargs["agent"], recipient
        )
        self.assertIs(
            mock_choose.call_args.kwargs["relationship"], reverse
        )
        self.assertEqual(
            mock_choose.call_args.kwargs["context"], "response"
        )

    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_response_decision_handles_missing_reciprocal_relationship(
        self, mock_choose
    ):
        forward = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[forward],
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "continue_interaction",
            "probabilities": {
                "continue_interaction": 0.6,
                "withdraw": 0.2,
                "do_nothing": 0.2,
            },
            "decision_basis": {"context": "response"},
        }

        simulation = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        result = simulation.make_response_decision(initiation)

        self.assertIsNone(result["relationship"])
        self.assertEqual(
            result["decision"]["action"],
            "continue_interaction",
        )
        self.assertIsNone(
            mock_choose.call_args.kwargs["relationship"]
        )

    def test_zero_frequency_has_no_next_opportunity(self):
        relationship = SocialRelationship(
            "PERSON-001",
            "PERSON-002",
            "community",
            interactions_per_month=0,
        )

        simulation = EventDrivenSimulation(self.experiment)

        self.assertIsNone(
            simulation.schedule_next_opportunity(relationship)
        )

    def test_next_opportunity_is_after_current_time(self):
        relationship = SocialRelationship(
            "PERSON-001",
            "PERSON-002",
            "family",
            interactions_per_month=10,
        )

        simulation = EventDrivenSimulation(self.experiment)

        next_time = simulation.schedule_next_opportunity(
            relationship
        )

        self.assertGreater(next_time, simulation.current_time)
    def test_response_decision_is_reproducible(self):
        forward = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )
        reverse = SocialRelationship(
            "PERSON-002", "PERSON-001", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[forward, reverse],
            random_seed=42,
        )

        first = EventDrivenSimulation(experiment)
        second = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=first.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        first_result = first.make_response_decision(initiation)
        second_result = second.make_response_decision(initiation)

        self.assertEqual(
            first_result["decision"]["action"],
            second_result["decision"]["action"],
        )    

    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_records_recipient_response_event(self, mock_choose):
        relationships = [
            SocialRelationship(
                "PERSON-001", "PERSON-002", "family"
            ),
            SocialRelationship(
                "PERSON-002", "PERSON-001", "family"
            ),
        ]

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=relationships,
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "continue_interaction",
            "probabilities": {
                "continue_interaction": 0.6,
                "withdraw": 0.2,
                "do_nothing": 0.2,
            },
            "decision_basis": {"context": "response"},
        }

        simulation = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        event = simulation.run_response_event(initiation)

        self.assertEqual(event.event_id, "EVENT-000001")
        self.assertEqual(event.event_type, "communication_response")
        self.assertEqual(event.initiating_agent_id, "PERSON-002")
        self.assertEqual(event.action, "continue_interaction")
        self.assertIsNotNone(event.communication)

        assessment = event.decision_basis[
            "communication_assessment"
        ]

        self.assertEqual(
            assessment["acoustic_conditions"],
            1.0,
        )
        self.assertTrue(
            assessment["visual_support"]["face_visible"]
        )
        self.assertFalse(
            assessment["visual_support"][
                "written_information_available"
            ]
        )
        self.assertEqual(
            assessment["comprehension"],
            "not_assessed",
        )
        self.assertEqual(
            event.communication.final_outcome,
            "not_assessed",
        )
        self.assertEqual(
            event.participants,
            ["PERSON-001", "PERSON-002"],
        )
        self.assertEqual(len(simulation.events), 1)
        self.assertEqual(simulation.next_event_id, 2)

    @patch("src.simulation.event_driven_simulation.choose_action")
    def test_does_not_record_event_when_recipient_does_nothing(
        self, mock_choose
    ):
        relationship = SocialRelationship(
            "PERSON-001", "PERSON-002", "family"
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        mock_choose.return_value = {
            "action": "do_nothing",
            "probabilities": {
                "continue_interaction": 0.3,
                "withdraw": 0.2,
                "do_nothing": 0.5,
            },
            "decision_basis": {"context": "response"},
        }

        simulation = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        event = simulation.run_response_event(initiation)

        self.assertIsNone(event)
        self.assertEqual(len(simulation.events), 0)
        self.assertEqual(simulation.next_event_id, 1)

    @patch.object(EventDrivenSimulation, "run_initiation_event")
    def test_interaction_cycle_returns_empty_without_initiation(
        self, mock_initiation
    ):
        simulation = EventDrivenSimulation(self.experiment)
        mock_initiation.return_value = None

        events = simulation.run_interaction_cycle()

        self.assertEqual(events, [])
        self.assertEqual(simulation.events, [])

    @patch.object(EventDrivenSimulation, "run_response_event")
    @patch.object(EventDrivenSimulation, "run_initiation_event")
    def test_interaction_cycle_returns_initiation_only(
        self, mock_initiation, mock_response
    ):
        simulation = EventDrivenSimulation(self.experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        mock_initiation.return_value = initiation
        mock_response.return_value = None

        events = simulation.run_interaction_cycle()

        self.assertEqual(events, [initiation])
        mock_response.assert_called_once_with(initiation)

    @patch.object(EventDrivenSimulation, "run_response_event")
    @patch.object(EventDrivenSimulation, "run_initiation_event")
    def test_interaction_cycle_returns_both_events(
        self, mock_initiation, mock_response
    ):
        simulation = EventDrivenSimulation(self.experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        response = SimulationEvent(
            event_id="EVENT-000002",
            timestamp=simulation.current_time,
            event_type="communication_response",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-002",
            action="continue_interaction",
        )

        mock_initiation.return_value = initiation
        mock_response.return_value = response

        events = simulation.run_interaction_cycle()

        self.assertEqual(events, [initiation, response])
    
    def test_initialises_one_scheduled_opportunity_per_relationship(self):
        relationships = [
            SocialRelationship(
                "PERSON-001",
                "PERSON-002",
                "family",
                interactions_per_month=10,
            ),
            SocialRelationship(
                "PERSON-002",
                "PERSON-001",
                "family",
                interactions_per_month=10,
            ),
            SocialRelationship(
                "PERSON-001",
                "PERSON-003",
                "community",
                interactions_per_month=0,
            ),
        ]

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
                self.make_agent("PERSON-003"),
            ],
            relationships=relationships,
            random_seed=42,
        )

        simulation = EventDrivenSimulation(experiment)
        schedule = simulation.initialise_opportunity_schedule()

        self.assertEqual(len(schedule), 1)
        self.assertIn(("PERSON-001", "PERSON-002"), schedule)
        self.assertGreater(
            schedule[("PERSON-001", "PERSON-002")],
            simulation.current_time,
        )
        
    def test_returns_earliest_scheduled_opportunity(self):
        simulation = EventDrivenSimulation(self.experiment)

        first_pair = ("PERSON-001", "PERSON-002")
        second_pair = ("PERSON-003", "PERSON-004")

        simulation.opportunity_schedule = {
            first_pair: datetime(2026, 1, 5),
            second_pair: datetime(2026, 1, 3),
        }

        result = simulation.get_next_scheduled_opportunity()

        self.assertEqual(
            result,
            (second_pair, datetime(2026, 1, 3)),
        )
        
    @patch.object(EventDrivenSimulation, "run_interaction_cycle")
    def test_processes_next_scheduled_opportunity(self, mock_cycle):
        relationship = SocialRelationship(
            "PERSON-001",
            "PERSON-002",
            "family",
            interactions_per_month=10,
        )

        experiment = SimpleNamespace(
            agents=[
                self.make_agent("PERSON-001"),
                self.make_agent("PERSON-002"),
            ],
            relationships=[relationship],
            random_seed=42,
        )

        simulation = EventDrivenSimulation(experiment)

        scheduled_time = datetime(2026, 1, 5)
        pair = ("PERSON-001", "PERSON-002")

        simulation.opportunity_schedule = {
            pair: scheduled_time,
        }

        mock_cycle.return_value = []

        simulation.process_next_opportunity()

        self.assertEqual(simulation.current_time, scheduled_time)
        mock_cycle.assert_called_once_with(relationship)
        self.assertIn(pair, simulation.opportunity_schedule)
        self.assertGreater(
            simulation.opportunity_schedule[pair],
            scheduled_time,
        )

    @patch.object(EventDrivenSimulation, "process_next_opportunity")
    def test_run_until_processes_opportunities_in_time_order(self, mock_process):
        simulation = EventDrivenSimulation(self.experiment)

        first = datetime(2026, 1, 3)
        second = datetime(2026, 1, 5)
        end_time = datetime(2026, 1, 7)

        simulation.opportunity_schedule = {
            ("PERSON-001", "PERSON-002"): first,
            ("PERSON-003", "PERSON-004"): second,
        }
        simulation.schedule_initialised = True

        def process_opportunity():
            pair, scheduled_time = simulation.get_next_scheduled_opportunity()
            simulation.current_time = scheduled_time
            del simulation.opportunity_schedule[pair]

        mock_process.side_effect = process_opportunity

        simulation.run_until(end_time)

        self.assertEqual(mock_process.call_count, 2)
        self.assertEqual(simulation.current_time, end_time)
        self.assertEqual(simulation.opportunity_schedule, {})

    def test_run_until_rejects_end_time_before_current_time(self):
        simulation = EventDrivenSimulation(self.experiment)

        with self.assertRaises(ValueError):
            simulation.run_until(datetime(2025, 12, 31))

    def test_run_until_stops_before_later_opportunity(self):
        simulation = EventDrivenSimulation(self.experiment)

        end_time = datetime(2026, 1, 5)
        later_time = datetime(2026, 1, 8)

        simulation.opportunity_schedule = {
            ("PERSON-001", "PERSON-002"): later_time,
        }

        simulation.schedule_initialised = True

        simulation.run_until(end_time)

        self.assertEqual(simulation.current_time, end_time)
        self.assertIn(
            ("PERSON-001", "PERSON-002"),
            simulation.opportunity_schedule,
        )

if __name__ == "__main__":
    unittest.main()
