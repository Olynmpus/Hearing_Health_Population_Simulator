"""Event-driven simulation of autonomous agent interactions."""

import random
from datetime import datetime, timedelta
from src.agents.memory_store import MemoryStore
from src.simulation.event_model import SimulationEvent
from src.behaviour.decision_model import choose_action
from src.behaviour.llm_interpreter import (
    generate_message,
    interpret_recipient_message,
)
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
        memory_path="outputs/event_simulation_memory.db",
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

        self.start_time = start_time or datetime(2026, 1, 1)
        self.current_time = self.start_time
        self.events = []
        self.next_event_id = 1
        self.memory = MemoryStore(memory_path)
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

    def build_agent_context(
        self,
        agent_id,
        other_agent_id,
        relationship,
    ):
        """Build private context for one agent's interaction perspective."""

        agent = self.agents[agent_id]
        other_agent = self.agents[other_agent_id]

        return {
            "agent": {
                "agent_id": agent.agent_id,
                "profile": {
                    "age_group": agent.profile.age_group,
                    "hearing_profile": agent.profile.hearing_profile,
                    "auditory_functional_status": (
                        agent.profile.auditory_functional_status
                    ),
                    "geography": agent.profile.geography,
                    "role": agent.profile.role,
                    "communication_profile": (
                        agent.profile.communication_profile.to_dict()
                    ),
                },
                "state": {
                    "communication_confidence": (
                        agent.state.communication_confidence
                    ),
                    "trust_in_services": agent.state.trust_in_services,
                    "perceived_support": agent.state.perceived_support,
                    "help_seeking_intention": (
                        agent.state.help_seeking_intention
                    ),
                    "social_participation": (
                        agent.state.social_participation
                    ),
                    "perceived_loneliness": (
                        agent.state.perceived_loneliness
                    ),
                    "frustration": agent.state.frustration,
                },
                "recent_history": self.memory.get_history(agent_id)[-3:],
            },
            "other_participant": {
                "agent_id": other_agent.agent_id,
                "role": other_agent.profile.role,
            },
            "relationship": {
                "relationship_type": relationship.relationship_type,
                "trust": relationship.trust,
                "perceived_support": relationship.perceived_support,
                "interactions_per_month": (
                    relationship.interactions_per_month
                ),
                "status": relationship.status,
            },
            "simulation_time": self.current_time.isoformat(),
        }

    def generate_initiation_message(self, initiation_event):
        """Generate the initiating agent's message using private context."""

        speaker_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != speaker_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.status == "active"
                and (
                    (
                        item.agent_id == speaker_id
                        and item.contact_id == recipient_id
                    )
                    or (
                        item.agent_id == recipient_id
                        and item.contact_id == speaker_id
                    )
                )
            ),
            None,
        )

        if relationship is None:
            raise ValueError(
                "An active relationship is required to generate a message."
            )

        context = self.build_agent_context(
            speaker_id,
            recipient_id,
            relationship,
        )

        return generate_message(
            agent_id=speaker_id,
            interaction_context=context,
        )

    def interpret_initiation_message(self, initiation_event, message):
        """Interpret an incoming message from the recipient's perspective."""

        sender_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != sender_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.status == "active"
                and (
                    (
                        item.agent_id == sender_id
                        and item.contact_id == recipient_id
                    )
                    or (
                        item.agent_id == recipient_id
                        and item.contact_id == sender_id
                    )
                )
            ),
            None,
        )

        if relationship is None:
            raise ValueError(
                "An active relationship is required to interpret a message."
            )

        context = self.build_agent_context(
            recipient_id,
            sender_id,
            relationship,
        )

        return interpret_recipient_message(
            recipient_id=recipient_id,
            message=message,
            interaction_context=context,
        )

    def prepare_initiation_communication(self, initiation_event):
        """Generate and interpret the initiating communication."""

        generated = self.generate_initiation_message(initiation_event)

        if generated.status != "generated" or not generated.text:
            initiation_event.decision_basis["message_generation"] = {
                "status": generated.status,
                "model": generated.model,
                "error": generated.error,
            }
            return False

        sender_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != sender_id
        )

        communication = CommunicationEvent(
            speaker_id=sender_id,
            listener_id=recipient_id,
            intended_message=generated.text,
            perceived_message=None,
            listener_interpretation=None,
            environment=self.generate_communication_environment(),
        )

        interpreted = self.interpret_initiation_message(
            initiation_event,
            generated.text,
        )

        if interpreted.status == "interpreted":
            communication.perceived_message = interpreted.perceived_message
            communication.listener_interpretation = (
                interpreted.interpretation
            )

        initiation_event.communication = communication

        initiation_event.decision_basis["message_generation"] = {
            "status": generated.status,
            "model": generated.model,
        }
        initiation_event.decision_basis["recipient_interpretation"] = {
            "status": interpreted.status,
            "model": interpreted.model,
            "comprehension_assessment": (
                interpreted.comprehension_assessment
            ),
            "error": interpreted.error,
            "evidence_status": "llm_interpretation_not_verified",
        }

        return True

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

    def generate_response_message(
        self,
        response_result,
        incoming_communication=None,
    ):
        """Generate a response using the agent's own interpretation."""

        speaker_id = response_result["responding_agent_id"]
        recipient_id = response_result["initiating_agent_id"]
        relationship = response_result["relationship"]

        context = self.build_agent_context(
            speaker_id,
            recipient_id,
            relationship,
        )

        if incoming_communication is not None:
            context["incoming_communication"] = {
                "message": incoming_communication.intended_message,
                "perceived_message": (
                    incoming_communication.perceived_message
                ),
                "interpretation": (
                    incoming_communication.listener_interpretation
                ),
            }

        return generate_message(
            agent_id=speaker_id,
            interaction_context=context,
        )

    def interpret_response_message(self, response_result, message):
        """Interpret the response from the original initiator's perspective."""

        recipient_id = response_result["initiating_agent_id"]
        sender_id = response_result["responding_agent_id"]

        relationship = response_result["relationship"]

        context = self.build_agent_context(
            recipient_id,
            sender_id,
            relationship,
        )

        return interpret_recipient_message(
            recipient_id=recipient_id,
            message=message,
            interaction_context=context,
        )

    def run_response_event(self, initiation_event):
        """Record the recipient's response when an active response occurs."""

        result = self.make_response_decision(initiation_event)
        decision = result["decision"]

        if decision["action"] == "do_nothing":
            return None

        response = self.generate_response_message(
            result,
            initiation_event.communication,
        )

        interpreted = None

        if response.status == "generated" and response.text:
            interpreted = self.interpret_response_message(
                result,
                response.text,
            )

        communication = CommunicationEvent(
            speaker_id=result["responding_agent_id"],
            listener_id=result["initiating_agent_id"],
            intended_message=(
                response.text if response.status == "generated" else None
            ),
            perceived_message=(
                interpreted.perceived_message
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
            listener_interpretation=(
                interpreted.interpretation
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
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
                "message_generation": {
                    "status": response.status,
                    "model": response.model,
                    "error": response.error,
                },
                "recipient_interpretation": {
                    "status": (
                        interpreted.status if interpreted else "not_attempted"
                    ),
                    "model": interpreted.model if interpreted else None,
                    "comprehension_assessment": (
                        interpreted.comprehension_assessment
                        if interpreted else None
                    ),
                    "error": interpreted.error if interpreted else None,
                    "evidence_status": "llm_interpretation_not_verified",
                },
            },
            description="The recipient responded to a conversation initiation.",
            communication=communication,
        )

        return self.record_event(event)

    def record_interaction_memories(
        self,
        initiation_event,
        response_event=None,
    ):
        """Record each participant's individual perspective."""

        month = (
            (self.current_time.year - self.start_time.year) * 12
            + self.current_time.month
            - self.start_time.month
        )

        interaction_id = initiation_event.event_id
        initial = initiation_event.communication

        if initial is None:
            return

        initiator_id = initial.speaker_id
        recipient_id = initial.listener_id

        response = (
            response_event.communication
            if response_event is not None
            else None
        )

        # Record the original recipient's perspective.
        self.memory.record_event(
            agent_id=recipient_id,
            month=month,
            event_type="communication_interaction",
            sender_id=initiator_id,
            recipient_id=recipient_id,
            actual_message=initial.intended_message,
            agent_interpretation=initial.listener_interpretation,
            outcome="not_assessed",
            emotional_appraisal=None,
            additional_details={
                "interaction_id": interaction_id,
                "perspective": "recipient",
                "perceived_message": initial.perceived_message,
                "response_sent": (
                    response.intended_message if response else None
                ),
                "interpretation_evidence": (
                    "llm_interpretation_not_verified"
                ),
            },
        )

        # Record the original initiator's perspective.
        self.memory.record_event(
            agent_id=initiator_id,
            month=month,
            event_type="communication_interaction",
            sender_id=(
                response.speaker_id if response else None
            ),
            recipient_id=(
                response.listener_id if response else None
            ),
            actual_message=(
                response.intended_message if response else None
            ),
            agent_interpretation=(
                response.listener_interpretation if response else None
            ),
            outcome="not_assessed",
            emotional_appraisal=None,
            additional_details={
                "interaction_id": interaction_id,
                "perspective": "initiator",
                "message_sent": initial.intended_message,
                "perceived_response": (
                    response.perceived_message if response else None
                ),
                "interpretation_evidence": (
                    "llm_interpretation_not_verified"
                ),
            },
        )

    def run_interaction_cycle(self, opportunity=None):
        """Run one independent initiation and response cycle."""

        initiation_event = self.run_initiation_event(opportunity)

        if initiation_event is None:
            return []

        generated_events = [initiation_event]

        if not self.prepare_initiation_communication(initiation_event):
            return generated_events

        response_event = self.run_response_event(initiation_event)

        if response_event is not None:
            generated_events.append(response_event)

        self.record_interaction_memories(
            initiation_event,
            response_event,
        )

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
