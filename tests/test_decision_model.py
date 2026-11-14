import random
import unittest

from src.agents.agent import Agent, AgentProfile, AgentState
from src.agents.relationships import SocialRelationship
from src.behaviour.decision_model import choose_action


class TestDecisionModel(unittest.TestCase):

    def setUp(self):
        self.agent = Agent(
            agent_id="PERSON-001",
            profile=AgentProfile(
                age_group="working_age_adult",
                hearing_profile="moderate",
                geography="regional",
            ),
            state=AgentState(),
        )

        self.relationship = SocialRelationship(
            agent_id="PERSON-001",
            contact_id="PERSON-002",
            relationship_type="friend",
        )

    def test_decision_is_reproducible_with_same_seed(self):
        actions = [
            "initiate_conversation",
            "withdraw",
            "do_nothing",
        ]

        first = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )
        second = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )

        self.assertEqual(first, second)

    def test_probabilities_sum_to_one(self):
        result = choose_action(
            self.agent,
            ["initiate_conversation", "withdraw", "seek_help"],
            self.relationship,
            random.Random(42),
        )

        self.assertAlmostEqual(
            sum(result["probabilities"].values()), 1.0
        )

    def test_higher_confidence_increases_initiation_probability(self):
        actions = ["initiate_conversation", "withdraw"]

        baseline = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )

        self.agent.state.communication_confidence = 0.9

        confident = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )

        self.assertGreater(
            confident["probabilities"]["initiate_conversation"],
            baseline["probabilities"]["initiate_conversation"],
        )

    def test_relationship_support_influences_decision(self):
        actions = ["continue_interaction", "withdraw"]

        baseline = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )

        self.relationship.perceived_support = 0.9

        supported = choose_action(
            self.agent, actions, self.relationship,
            random.Random(42),
        )

        self.assertGreater(
            supported["probabilities"]["continue_interaction"],
            baseline["probabilities"]["continue_interaction"],
        )

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_action(
                self.agent,
                ["invented_action"],
                rng=random.Random(42),
            )

    def test_empty_action_list_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_action(self.agent, [])

if __name__ == "__main__":
    unittest.main()


class TestDecisionContexts(unittest.TestCase):

    def setUp(self):
        self.agent = Agent(
            agent_id="PERSON-001",
            profile=AgentProfile(
                age_group="working_age_adult",
                hearing_profile="moderate",
                geography="regional",
            ),
            state=AgentState(),
        )

    def test_initiation_context_restricts_actions(self):
        actions = [
            "initiate_conversation",
            "avoid_interaction",
            "do_nothing",
        ]

        result = choose_action(
            self.agent, actions,
            context="initiation",
            rng=random.Random(42),
        )

        self.assertIn(result["action"], actions)

    def test_response_context_restricts_actions(self):
        actions = [
            "continue_interaction",
            "withdraw",
            "do_nothing",
        ]

        result = choose_action(
            self.agent, actions,
            context="response",
            rng=random.Random(42),
        )

        self.assertIn(result["action"], actions)

    def test_repair_context_restricts_actions(self):
        actions = [
            "repeat_information",
            "rephrase_information",
            "provide_written_information",
            "decline_repair",
            "do_nothing",
        ]

        result = choose_action(
            self.agent, actions,
            context="repair",
            rng=random.Random(42),
        )

        self.assertIn(result["action"], actions)

    def test_invalid_context_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_action(
                self.agent,
                ["do_nothing"],
                context="invalid",
            )

    def test_action_from_wrong_context_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_action(
                self.agent,
                ["withdraw"],
                context="initiation",
            )


