"""Event-driven simulation of autonomous agent interactions."""

import random
from datetime import datetime, timedelta

from src.simulation.event_model import SimulationEvent
from src.behaviour.decision_model import choose_action
from src.behaviour.communication_model import (
    CommunicationEvent,
    CommunicationEnvironment,
)
from src.behaviour.communication_assessment import (
    assess_acoustic_conditions,
    assess_visual_support,
)

class EventDrivenSimulation:
    """Run a reproducible, event-driven simulation using a population."""

    def __init__(
        self,
        experiment,
        start_time=None,
        random_seed=None,
    ):
        self.agents = {
            agent.agent_id: agent
            for agent in experiment.agents
        }

        self.relationships = experiment.relationships

        seed = (
            random_seed
            if random_seed is not None
            else experiment.random_seed
        )

        self.random_seed = seed
        self.rng = random.Random(seed)

        self.current_time = start_time or datetime(2026, 1, 1)

        self.events = []
        self.next_event_id = 1
        self.opportunity_schedule = {}
        self.schedule_initialised = False

    def advance_time(self, hours=1):
        """Advance the simulated clock by a number of hours."""

        if hours < 0:
            raise ValueError("Time cannot move backwards.")

        self.current_time += timedelta(hours=hours)

        return self.current_time

    def generate_communication_environment(self):
        """Generate illustrative environmental conditions for an exchange."""

        environment = CommunicationEnvironment(
            background_noise=self.rng.uniform(0.0, 0.6),
            distance_metres=self.rng.uniform(0.5, 5.0),
            speaker_face_visible=self.rng.choice([True, False]),
            written_information_available=self.rng.choice([True, False]),
        )

        environment.validate()

        return environment
    def schedule_next_opportunity(self, relationship):
        """Calculate the next contact opportunity for a relationship."""

        if relationship.interactions_per_month < 0:
            raise ValueError(
                "Interaction frequency cannot be negative."
            )

        if relationship.interactions_per_month == 0:
            return None

        mean_interval_days = (
            30.44 / relationship.interactions_per_month
        )

        interval_days = self.rng.expovariate(
            1 / mean_interval_days
        )

        return self.current_time + timedelta(days=interval_days)

    def initialise_opportunity_schedule(self):
        """Schedule the first contact opportunity for each active relationship."""

        self.opportunity_schedule = {}

        for relationship in self.get_interaction_opportunities():
            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))

            next_time = self.schedule_next_opportunity(relationship)

            if next_time is not None:
                self.opportunity_schedule[pair] = next_time

        self.schedule_initialised = True
        return self.opportunity_schedule
    
    def get_next_scheduled_opportunity(self):
        """Return the earliest scheduled relationship opportunity."""

        if not self.opportunity_schedule:
            return None

        pair = min(
            self.opportunity_schedule,
            key=self.opportunity_schedule.get,
        )

        return pair, self.opportunity_schedule[pair]

    def process_next_opportunity(self):
        """Process the next scheduled relationship opportunity."""

        scheduled = self.get_next_scheduled_opportunity()

        if scheduled is None:
            return []

        pair, scheduled_time = scheduled
        self.current_time = scheduled_time

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == pair[0]
                and item.contact_id == pair[1]
                and item.status == "active"
            ),
            None,
        )

        if relationship is None:
            relationship = next(
                (
                    item for item in self.relationships
                    if item.agent_id == pair[1]
                    and item.contact_id == pair[0]
                    and item.status == "active"
                ),
                None,
            )

        del self.opportunity_schedule[pair]

        if relationship is None:
            return []

        events = self.run_interaction_cycle(relationship)

        next_time = self.schedule_next_opportunity(relationship)

        if next_time is not None:
            self.opportunity_schedule[pair] = next_time

        return events

    def run_until(self, end_time):
        """Process scheduled opportunities until the specified end time."""

        if end_time < self.current_time:
            raise ValueError("End time cannot be before current time.")

        if not self.schedule_initialised:
            self.initialise_opportunity_schedule()

        while True:
            scheduled = self.get_next_scheduled_opportunity()

            if scheduled is None:
                break

            _, scheduled_time = scheduled

            if scheduled_time > end_time:
                break

            self.process_next_opportunity()

        self.current_time = end_time

        return self.events
    
    def record_event(self, event):
        """Validate and record a simulation event."""

        event.validate()
        self.events.append(event)

        self.next_event_id += 1

        return event

    def get_interaction_opportunities(self):
        """Return unique active relationships between simulated agents."""

        opportunities = []
        seen_pairs = set()

        for relationship in self.relationships:
            if relationship.status != "active":
                continue

            if (
                relationship.agent_id not in self.agents
                or relationship.contact_id not in self.agents
            ):
                continue

            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))

            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)
            opportunities.append(relationship)

        return opportunities

    def make_initiation_decision(self, opportunity=None):
        """Select an interaction opportunity and decide whether to initiate."""

        if opportunity is None:
            opportunities = self.get_interaction_opportunities()

            if not opportunities:
                return None

            opportunity = self.rng.choice(opportunities)

        participants = [
            opportunity.agent_id,
            opportunity.contact_id,
        ]

        initiating_agent_id = self.rng.choice(participants)
        contact_id = next(
            participant
            for participant in participants
            if participant != initiating_agent_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == initiating_agent_id
                and item.contact_id == contact_id
                and item.status == "active"
            ),
            opportunity,
        )

        decision = choose_action(
            agent=self.agents[initiating_agent_id],
            available_actions=[
                "initiate_conversation",
                "avoid_interaction",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="initiation",
        )

        return {
            "initiating_agent_id": initiating_agent_id,
            "contact_id": contact_id,
            "relationship": relationship,
            "decision": decision,
        }

    def run_initiation_event(self, opportunity=None):
        """Record a communication initiation when an agent chooses to initiate."""

        result = self.make_initiation_decision(opportunity)

        if result is None:
            return None

        decision = result["decision"]

        if decision["action"] != "initiate_conversation":
            return None

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="communication_initiation",
            participants=[
                result["initiating_agent_id"],
                result["contact_id"],
            ],
            initiating_agent_id=result["initiating_agent_id"],
            action=decision["action"],
            decision_basis={
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
            },
            description="An agent initiated a conversation.",
        )

        return self.record_event(event)

    def make_response_decision(self, initiation_event):
        """Let the recipient independently decide how to respond."""

        if initiation_event.event_type != "communication_initiation":
            raise ValueError(
                "A communication initiation event is required."
            )

        initiating_agent_id = initiation_event.initiating_agent_id

        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != initiating_agent_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == recipient_id
                and item.contact_id == initiating_agent_id
                and item.status == "active"
            ),
            None,
        )

        decision = choose_action(
            agent=self.agents[recipient_id],
            available_actions=[
                "continue_interaction",
                "withdraw",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="response",
        )

        return {
            "responding_agent_id": recipient_id,
            "initiating_agent_id": initiating_agent_id,
            "relationship": relationship,
            "decision": decision,
        }

    def run_response_event(self, initiation_event):
        """Record the recipient's response when an active response occurs."""

        result = self.make_response_decision(initiation_event)
        decision = result["decision"]

        if decision["action"] == "do_nothing":
            return None

        communication = CommunicationEvent(
            speaker_id=result["initiating_agent_id"],
            listener_id=result["responding_agent_id"],
            intended_message=None,
            perceived_message=None,
            listener_interpretation=None,
            environment=self.generate_communication_environment(),
        )

        communication_assessment = {
            "acoustic_conditions": assess_acoustic_conditions(
                communication.environment,
                communication.channel,
            ),
            "visual_support": assess_visual_support(
                communication.environment,
            ),
            "comprehension": "not_assessed",
        }

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="communication_response",
            participants=[
                result["initiating_agent_id"],
                result["responding_agent_id"],
            ],
            initiating_agent_id=result["responding_agent_id"],
            action=decision["action"],
            decision_basis={
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
                "communication_assessment": communication_assessment,
            },
            description="The recipient responded to a conversation initiation.",
            communication=communication,
        )

        return self.record_event(event)

    def run_interaction_cycle(self, opportunity=None):
        """Run one independent initiation and response cycle."""

        initiation_event = self.run_initiation_event(opportunity)

        if initiation_event is None:
            return []

        generated_events = [initiation_event]

        response_event = self.run_response_event(initiation_event)

        if response_event is not None:
            generated_events.append(response_event)

        return generated_events
    
    def summary(self):
        """Return a concise summary of the simulation."""

        return {
            "population_size": len(self.agents),
            "relationship_count": len(self.relationships),
            "event_count": len(self.events),
            "current_time": self.current_time.isoformat(),
            "random_seed": self.random_seed,
        }
