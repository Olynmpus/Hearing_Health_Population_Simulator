import unittest
from datetime import datetime
from types import SimpleNamespace
import tempfile
from pathlib import Path
from src.agents.relationships import SocialRelationship
from src.simulation.event_driven_simulation import EventDrivenSimulation
from src.simulation.event_model import SimulationEvent
from src.behaviour.communication_model import CommunicationEvent


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

    def test_records_individual_interaction_memories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            simulation = EventDrivenSimulation(
                self.experiment,
                start_time=datetime(2026, 1, 1),
                memory_path=Path(temp_dir) / "memory.db",
            )

            simulation.current_time = datetime(2026, 3, 1)

            initiation = SimpleNamespace(
                event_id="EVENT-000001",
                communication=CommunicationEvent(
                    speaker_id="PERSON-001",
                    listener_id="PERSON-002",
                    intended_message="Could you help me?",
                    perceived_message="Could you assist?",
                    listener_interpretation=(
                        "The person is asking me for help."
                    ),
                ),
            )

            response = SimpleNamespace(
                communication=CommunicationEvent(
                    speaker_id="PERSON-002",
                    listener_id="PERSON-001",
                    intended_message="Of course.",
                    perceived_message="They are willing to help.",
                    listener_interpretation=(
                        "The other person is offering help."
                    ),
                ),
            )

            simulation.record_interaction_memories(
                initiation,
                response,
            )

            recipient_history = simulation.memory.get_history(
                "PERSON-002"
            )
            initiator_history = simulation.memory.get_history(
                "PERSON-001"
            )

            self.assertEqual(len(recipient_history), 1)
            self.assertEqual(len(initiator_history), 1)

            recipient_record = recipient_history[0]
            initiator_record = initiator_history[0]

            self.assertEqual(
                recipient_record["actual_message"],
                "Could you help me?",
            )
            self.assertEqual(
                recipient_record["agent_interpretation"],
                "The person is asking me for help.",
            )
            self.assertEqual(
                recipient_record["additional_details"]["response_sent"],
                "Of course.",
            )

            self.assertEqual(
                initiator_record["actual_message"],
                "Of course.",
            )
            self.assertEqual(
                initiator_record["agent_interpretation"],
                "The other person is offering help.",
            )
            self.assertEqual(
                initiator_record["additional_details"]["message_sent"],
                "Could you help me?",
            )

            self.assertEqual(recipient_record["month"], 2)
            self.assertEqual(initiator_record["month"], 2)

            self.assertEqual(recipient_record["outcome"], "not_assessed")
            self.assertEqual(initiator_record["outcome"], "not_assessed")
            self.assertIsNone(recipient_record["emotional_appraisal"])
            self.assertIsNone(initiator_record["emotional_appraisal"])
    def test_communication_environment_is_reproducible(self):
        first = EventDrivenSimulation(self.experiment)
        second = EventDrivenSimulation(self.experiment)

        first_environment = (
            first.generate_communication_environment()
        )
        second_environment = (
            second.generate_communication_environment()
        )

        self.assertEqual(
            first_environment,
            second_environment,
        )

    def test_successive_communication_environments_can_differ(self):
        simulation = EventDrivenSimulation(self.experiment)

        first = simulation.generate_communication_environment()
        second = simulation.generate_communication_environment()

        self.assertNotEqual(first, second)

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
            perceived_support=0.5,
            perceived_loneliness=0.2,
            frustration=0.2,
        )

        communication_profile = SimpleNamespace(
            to_dict=lambda: {}
        )

        profile = SimpleNamespace(
            age_group="working_age_adult",
            hearing_profile="moderate",
            auditory_functional_status="unknown",
            geography="regional",
            role="individual",
            communication_profile=communication_profile,
        )

        return SimpleNamespace(
            agent_id=agent_id,
            profile=profile,
            state=state,
        )

    @patch("src.simulation.event_driven_simulation.generate_message")
    def test_generates_initiation_message(self, mock_generate):
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
        context = {"agent": {"agent_id": "PERSON-001"}}
        simulation.build_agent_context = lambda *args: context

        mock_generate.return_value = SimpleNamespace(
            text="Hello, how are you?",
            status="generated",
        )

        event = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
            decision_basis={},
            description="Test initiation.",
        )

        result = simulation.generate_initiation_message(event)

        self.assertEqual(result.text, "Hello, how are you?")
        mock_generate.assert_called_once_with(
            agent_id="PERSON-001",
            interaction_context=context,
        )

    @patch(
        "src.simulation.event_driven_simulation.interpret_recipient_message"
    )
    def test_interprets_initiation_message_from_recipient_perspective(
        self, mock_interpret
    ):
        relationship = SocialRelationship(
            "PERSON-002", "PERSON-001", "family"
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
        context = {"agent": {"agent_id": "PERSON-002"}}
        simulation.build_agent_context = lambda *args: context

        mock_interpret.return_value = SimpleNamespace(
            perceived_message="Hello",
            interpretation="The sender is greeting me.",
            comprehension_assessment="understood",
            status="interpreted",
        )

        event = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
            decision_basis={},
            description="Test initiation.",
        )

        result = simulation.interpret_initiation_message(
            event,
            "Hello, how are you?",
        )

        self.assertEqual(
            result.interpretation,
            "The sender is greeting me.",
        )
        mock_interpret.assert_called_once_with(
            recipient_id="PERSON-002",
            message="Hello, how are you?",
            interaction_context=context,
        )

    @patch(
        "src.simulation.event_driven_simulation.interpret_recipient_message"
    )
    @patch("src.simulation.event_driven_simulation.generate_message")
    def test_prepares_initiation_communication(
        self, mock_generate, mock_interpret
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

        simulation = EventDrivenSimulation(experiment)
        simulation.build_agent_context = lambda *args: {}

        mock_generate.return_value = SimpleNamespace(
            text="Hello, how are you?",
            model="qwen3:1.7b",
            status="generated",
            error=None,
        )

        mock_interpret.return_value = SimpleNamespace(
            perceived_message="Hello",
            interpretation="The sender is greeting me.",
            comprehension_assessment="understood",
            model="qwen3:1.7b",
            status="interpreted",
            error=None,
        )

        event = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
            decision_basis={},
            description="Test initiation.",
        )

        result = simulation.prepare_initiation_communication(event)

        self.assertTrue(result)
        self.assertEqual(
            event.communication.intended_message,
            "Hello, how are you?",
        )
        self.assertEqual(
            event.communication.perceived_message,
            "Hello",
        )
        self.assertEqual(
            event.communication.listener_interpretation,
            "The sender is greeting me.",
        )
        self.assertEqual(
            event.communication.initial_outcome,
            "not_assessed",
        )
        self.assertEqual(
            event.communication.final_outcome,
            "not_assessed",
        )

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

    @patch("src.simulation.event_driven_simulation.interpret_recipient_message")
    @patch("src.simulation.event_driven_simulation.choose_action")
    @patch("src.simulation.event_driven_simulation.generate_message")
    def test_records_recipient_response_event(
        self, mock_generate, mock_choose, mock_interpret
    ):
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

        mock_generate.return_value = SimpleNamespace(
            text="Hello, how are you?",
            model="test-model",
            status="generated",
            error=None,
        )

        mock_interpret.return_value = SimpleNamespace(
            perceived_message="A greeting",
            interpretation="The recipient understands the greeting.",
            comprehension_assessment="understood",
            model="test-model",
            status="interpreted",
            error=None,
        )
        simulation = EventDrivenSimulation(experiment)

        initiation = SimulationEvent(
            event_id="EVENT-000001",
            timestamp=simulation.current_time,
            event_type="communication_initiation",
            participants=["PERSON-001", "PERSON-002"],
            initiating_agent_id="PERSON-001",
            action="initiate_conversation",
        )

        initiation.communication = CommunicationEvent(
            speaker_id="PERSON-001",
            listener_id="PERSON-002",
            intended_message="Could you help me?",
            perceived_message="Could you assist?",
            listener_interpretation="The person is asking me for help.",
        )

        event = simulation.run_response_event(initiation)

        # Verify response direction.
        # Verify response direction.
        assert event.communication.speaker_id == "PERSON-002"
        assert event.communication.listener_id == "PERSON-001"

        # Verify the responding agent received its own interpretation.
        generated_context = mock_generate.call_args.kwargs[
            "interaction_context"
        ]

        assert generated_context["agent"]["agent_id"] == "PERSON-002"
        assert generated_context["incoming_communication"]["message"] == (
            "Could you help me?"
        )
        assert generated_context["incoming_communication"]["perceived_message"] == (
            "Could you assist?"
        )
        assert generated_context["incoming_communication"]["interpretation"] == (
            "The person is asking me for help."
        )

        # Verify the generated response was recorded.
        assert event.communication.intended_message == "Hello, how are you?"

        # Verify the original initiator's interpretation was recorded.
        assert event.communication.perceived_message == "A greeting"
        assert (
            event.communication.listener_interpretation
            == "The recipient understands the greeting."
        )

        # Verify interpretation used the original initiator's perspective.
        mock_interpret.assert_called_once()
        interpretation_args = mock_interpret.call_args.kwargs

        assert interpretation_args["recipient_id"] == "PERSON-001"
        assert interpretation_args["message"] == "Hello, how are you?"
        assert (
            interpretation_args["interaction_context"]["agent"]["agent_id"]
            == "PERSON-001"
        )

        # Verify the interpretation is not treated as validated evidence.
        assert (
            event.decision_basis["recipient_interpretation"]["evidence_status"]
            == "llm_interpretation_not_verified"
        )

        self.assertEqual(event.event_id, "EVENT-000001")
        self.assertEqual(event.event_type, "communication_response")
        self.assertEqual(event.initiating_agent_id, "PERSON-002")
        self.assertEqual(event.action, "continue_interaction")
        self.assertIsNotNone(event.communication)

        assessment = event.decision_basis[
            "communication_assessment"
        ]

        self.assertGreaterEqual(
            assessment["acoustic_conditions"],
            0.0,
        )
        self.assertLessEqual(
            assessment["acoustic_conditions"],
            1.0,
        )
        self.assertIsInstance(
            assessment["visual_support"]["face_visible"],
            bool,
        )
        self.assertIsInstance(
            assessment["visual_support"][
                "written_information_available"
            ],
            bool,
        )

        self.assertGreaterEqual(
            event.communication.environment.background_noise,
            0.0,
        )
        self.assertLessEqual(
            event.communication.environment.background_noise,
            0.6,
        )
        self.assertGreaterEqual(
            event.communication.environment.distance_metres,
            0.5,
        )
        self.assertLessEqual(
            event.communication.environment.distance_metres,
            5.0,
        )
        self.assertEqual(
            event.communication.environment.message_clarity,
            1.0,
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

    @patch.object(
        EventDrivenSimulation, "prepare_initiation_communication"
    )
    @patch.object(EventDrivenSimulation, "run_response_event")
    @patch.object(EventDrivenSimulation, "run_initiation_event")
    def test_interaction_cycle_returns_initiation_only(
        self, mock_initiation, mock_response, mock_prepare
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
        mock_prepare.return_value = True

        events = simulation.run_interaction_cycle()

        self.assertEqual(events, [initiation])
        mock_response.assert_called_once_with(initiation)

    @patch.object(
        EventDrivenSimulation, "prepare_initiation_communication"
    )
    @patch.object(EventDrivenSimulation, "run_response_event")
    @patch.object(EventDrivenSimulation, "run_initiation_event")
    def test_interaction_cycle_returns_both_events(
        self, mock_initiation, mock_response, mock_prepare
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
        mock_prepare.return_value = True
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
