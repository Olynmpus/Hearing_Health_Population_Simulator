"""Event records for the autonomous, event-driven simulation."""

from dataclasses import dataclass, field
from datetime import datetime

from src.behaviour.communication_model import CommunicationEvent


@dataclass
class SimulationEvent:
    """Record an event arising from an agent's decision."""

    event_id: str
    timestamp: datetime
    event_type: str
    participants: list[str]
    initiating_agent_id: str
    action: str
    decision_basis: dict = field(default_factory=dict)
    description: str | None = None
    communication: CommunicationEvent | None = None

    def validate(self):
        if not self.event_id:
            raise ValueError("Event ID is required.")

        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime.")

        if not self.event_type:
            raise ValueError("Event type is required.")

        if not self.participants:
            raise ValueError("At least one participant is required.")

        if len(self.participants) != len(set(self.participants)):
            raise ValueError("Participants must be unique.")

        if self.initiating_agent_id not in self.participants:
            raise ValueError(
                "Initiating agent must be an event participant."
            )

        if not self.action:
            raise ValueError("Action is required.")

        if self.communication is not None:
            self.communication.validate()

            communication_participants = {
                self.communication.speaker_id,
                self.communication.listener_id,
            }

            if not communication_participants.issubset(
                set(self.participants)
            ):
                raise ValueError(
                    "Communication participants must be event participants."
                )

        return True
