from dataclasses import dataclass, field
from typing import Optional


AUDITORY_FUNCTIONAL_STATUSES = {
    "no_identified_difficulty",
    "difficulty_reported",
    "functional_difficulty_confirmed",
    "unknown",
}


COMMUNICATION_DOMAIN_FIELDS = {
    "modalities": "communication_modalities",
    "spoken_preferences": "spoken_auditory_preferences",
    "signed_communication": "signed_communication",
    "visual_supports": "visual_supports",
    "written_language_preferences": "written_language_preferences",
    "environmental_preferences": "environmental_preferences",
    "assistive_technology": "assistive_technology",
    "interaction_strategies": "interaction_strategies",
    "accessibility_accommodations": "accessibility_accommodations",
    "contexts": "communication_contexts",
}


@dataclass
class AgentCommunicationProfile:
    """Declared communication characteristics of a simulated person."""

    modalities: list[str] = field(default_factory=list)
    spoken_preferences: list[str] = field(default_factory=list)
    signed_communication: list[str] = field(default_factory=list)
    visual_supports: list[str] = field(default_factory=list)
    written_language_preferences: list[str] = field(default_factory=list)
    environmental_preferences: list[str] = field(default_factory=list)
    assistive_technology: list[str] = field(default_factory=list)
    interaction_strategies: list[str] = field(default_factory=list)
    accessibility_accommodations: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)

    def validate(self, vocabulary=None):
        """Validate profile entries and, optionally, vocabulary domains."""

        for field_name, domain_id in COMMUNICATION_DOMAIN_FIELDS.items():
            identifiers = getattr(self, field_name)

            if not isinstance(identifiers, list):
                raise ValueError(
                    f"{field_name} must be a list of vocabulary identifiers."
                )

            for identifier in identifiers:
                if not isinstance(identifier, str) or not identifier.strip():
                    raise ValueError(
                        f"Invalid identifier in {field_name}."
                    )

            if len(identifiers) != len(set(identifiers)):
                raise ValueError(
                    f"Duplicate identifier in {field_name}."
                )

            if vocabulary is not None:
                for identifier in identifiers:
                    try:
                        term = vocabulary.get_term(identifier)
                    except KeyError as exc:
                        raise ValueError(
                            f"Unknown vocabulary identifier: {identifier}"
                        ) from exc

                    if term.domain_id != domain_id:
                        raise ValueError(
                            f"Identifier '{identifier}' belongs to "
                            f"'{term.domain_id}', not '{domain_id}'."
                        )

        return True

    def to_dict(self):
        """Return a serialisable representation of the profile."""

        return {
            field_name: list(getattr(self, field_name))
            for field_name in COMMUNICATION_DOMAIN_FIELDS
        }


@dataclass
class AgentProfile:
    """Relatively stable characteristics of a simulated person."""

    age_group: str
    hearing_profile: str
    geography: str
    auditory_functional_status: str = "unknown"
    role: str = "community_member"

    onset_type: str = "unknown"
    progression_type: str = "unknown"

    communication_profile: AgentCommunicationProfile = field(
        default_factory=AgentCommunicationProfile
    )

    def validate(self, vocabulary=None):
        """Validate the agent profile."""

        if not isinstance(
            self.communication_profile,
            AgentCommunicationProfile
        ):
            raise ValueError(
                "communication_profile must be an "
                "AgentCommunicationProfile object."
            )

        if self.auditory_functional_status not in AUDITORY_FUNCTIONAL_STATUSES:
            raise ValueError(
                "Invalid auditory_functional_status: "
                f"{self.auditory_functional_status}"
            )

        self.communication_profile.validate(vocabulary)
        return True


@dataclass
class AgentState:
    """Characteristics that may change during the simulation."""

    communication_confidence: float = 0.5
    trust_in_services: float = 0.5
    perceived_support: float = 0.5
    help_seeking_intention: float = 0.5
    social_participation: float = 0.5
    perceived_loneliness: float = 0.5
    frustration: float = 0.0

    def validate(self):
        """Check that all state values are between 0 and 1."""

        for name, value in vars(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1; received {value}"
                )


@dataclass
class Agent:
    """An individual person in the simulated population."""

    agent_id: str
    profile: AgentProfile
    state: AgentState = field(default_factory=AgentState)

    current_month: int = 0
    history_id: Optional[str] = None
    household_id: Optional[str] = None

    def validate(self, vocabulary=None):
        """Validate the agent's identity, profile and state."""

        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty.")

        self.profile.validate(vocabulary)
        self.state.validate()

        return True


    def summary(self):
        """Return a complete, readable summary of the agent."""

        return {
            "agent_id": self.agent_id,
            "history_id": self.history_id,
            "household_id": self.household_id,
            "current_month": self.current_month,

            "age_group": self.profile.age_group,
            "hearing_profile": self.profile.hearing_profile,
            "auditory_functional_status": self.profile.auditory_functional_status,
            "geography": self.profile.geography,
            "role": self.profile.role,
            "onset_type": self.profile.onset_type,
            "progression_type": self.profile.progression_type,

            "communication_profile": (
                self.profile.communication_profile.to_dict()
            ),

            "communication_confidence": (
                self.state.communication_confidence
            ),
            "trust_in_services": self.state.trust_in_services,
            "perceived_support": self.state.perceived_support,
            "help_seeking_intention": (
                self.state.help_seeking_intention
            ),
            "social_participation": self.state.social_participation,
            "perceived_loneliness": self.state.perceived_loneliness,
            "frustration": self.state.frustration,
        }
