
"""Structured records of communication between simulated agents."""

from dataclasses import dataclass, field


@dataclass
class CommunicationEnvironment:
    """Environmental conditions affecting a communication exchange."""

    background_noise: float = 0.0
    distance_metres: float = 1.0
    speaker_face_visible: bool = True
    written_information_available: bool = False
    message_clarity: float = 1.0

    def validate(self):
        """Validate environmental conditions."""

        if not 0.0 <= self.background_noise <= 1.0:
            raise ValueError("Background noise must be between 0 and 1.")

        if self.distance_metres < 0:
            raise ValueError("Distance cannot be negative.")

        if not 0.0 <= self.message_clarity <= 1.0:
            raise ValueError("Message clarity must be between 0 and 1.")

        if not isinstance(self.speaker_face_visible, bool):
            raise ValueError("speaker_face_visible must be True or False.")

        if not isinstance(self.written_information_available, bool):
            raise ValueError(
                "written_information_available must be True or False."
            )

        return True


@dataclass
class CommunicationEvent:
    """Record what happened during a communication exchange."""

    speaker_id: str
    listener_id: str

    intended_message: str | None
    perceived_message: str | None
    listener_interpretation: str | None

    channel: str = "speech"

    environment: CommunicationEnvironment = field(
        default_factory=CommunicationEnvironment
    )

    clarification_requested: bool = False

    initial_outcome: str = "not_assessed"
    final_outcome: str = "not_assessed"

    def validate(self):
        """Validate the communication event."""

        if not self.speaker_id or not self.listener_id:
            raise ValueError("Speaker and listener IDs are required.")

        if self.speaker_id == self.listener_id:
            raise ValueError(
                "Speaker and listener must be different agents."
            )

        if self.intended_message is not None:
            if not isinstance(self.intended_message, str):
                raise ValueError(
                    "intended_message must be a string or None."
                )

            if not self.intended_message.strip():
                raise ValueError("intended_message cannot be empty.")

        optional_messages = {
            "perceived_message": self.perceived_message,
            "listener_interpretation": self.listener_interpretation,
        }

        for field_name, value in optional_messages.items():
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"{field_name} must be a non-empty string or None."
                    )

        allowed_channels = {
            "speech",
            "text",
            "sign",
            "visual",
            "other",
        }

        if self.channel not in allowed_channels:
            raise ValueError(
                f"Invalid communication channel: {self.channel}"
            )

        allowed_outcomes = {
            "understood",
            "partially_understood",
            "misunderstood",
            "not_assessed",
        }

        if self.initial_outcome not in allowed_outcomes:
            raise ValueError(
                f"Invalid initial outcome: {self.initial_outcome}"
            )

        if self.final_outcome not in allowed_outcomes:
            raise ValueError(
                f"Invalid final outcome: {self.final_outcome}"
            )

        if not isinstance(self.clarification_requested, bool):
            raise ValueError(
                "clarification_requested must be True or False."
            )

        if not isinstance(self.environment, CommunicationEnvironment):
            raise ValueError(
                "Environment must be a CommunicationEnvironment object."
            )

        self.environment.validate()

        return True
