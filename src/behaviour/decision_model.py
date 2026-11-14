"""State-dependent, probabilistic decisions for simulated agents."""

import random


DECISION_CONTEXTS = {
    "initiation": {
        "initiate_conversation",
        "avoid_interaction",
        "do_nothing",
    },
    "response": {
        "continue_interaction",
        "withdraw",
        "do_nothing",
    },
    "repair": {
        "repeat_information",
        "rephrase_information",
        "provide_written_information",
        "decline_repair",
        "do_nothing",
    },
}


def choose_action(
    agent,
    available_actions,
    relationship=None,
    rng=None,
    context=None,
):
    """Select an action using the agent's current state and relationship.

    Action weights are provisional simulation assumptions, not
    empirically estimated behavioural probabilities.

    A context optionally restricts the actions available.
    Pass a seeded random.Random instance for reproducibility.
    """

    if not available_actions:
        raise ValueError("At least one available action is required.")

    if len(available_actions) != len(set(available_actions)):
        raise ValueError("Available actions must be unique.")

    if context is not None:
        if context not in DECISION_CONTEXTS:
            raise ValueError(f"Unknown decision context: {context}")

        invalid_actions = (
            set(available_actions) - DECISION_CONTEXTS[context]
        )

        if invalid_actions:
            raise ValueError(
                f"Actions not available in {context} context: "
                f"{sorted(invalid_actions)}"
            )

    state = agent.state

    confidence = state.communication_confidence
    participation = state.social_participation
    help_intention = state.help_seeking_intention
    service_trust = state.trust_in_services
    frustration = state.frustration

    relationship_trust = (
        relationship.trust if relationship is not None else 0.5
    )
    relationship_support = (
        relationship.perceived_support
        if relationship is not None else 0.5
    )

    weights = {
        "initiate_conversation": (
            1.0 + 0.8 * confidence + 0.5 * participation
            + 0.4 * relationship_trust
            + 0.3 * relationship_support - 0.5 * frustration
        ),
        "attempt_clarification": (
            1.0 + 0.7 * confidence
            + 0.4 * relationship_trust
            + 0.4 * relationship_support - 0.3 * frustration
        ),
        "continue_interaction": (
            1.0 + 0.5 * confidence
            + 0.5 * relationship_trust
            + 0.5 * relationship_support - 0.4 * frustration
        ),
        "withdraw": (
            1.0 + 0.6 * (1.0 - confidence)
            + 0.5 * frustration
            + 0.4 * (1.0 - relationship_support)
        ),
        "avoid_interaction": (
            1.0 + 0.8 * (1.0 - confidence)
            + 0.5 * frustration
        ),
        "seek_help": (
            1.0 + 0.8 * help_intention
            + 0.5 * service_trust
        ),
        "repeat_information": (
            1.0 + 0.5 * relationship_support
            + 0.3 * relationship_trust
        ),
        "rephrase_information": (
            1.0 + 0.5 * relationship_support
            + 0.3 * relationship_trust
        ),
        "provide_written_information": (
            1.0 + 0.4 * relationship_support
            + 0.2 * relationship_trust
        ),
        "decline_repair": (
            1.0 + 0.5 * frustration
            + 0.3 * (1.0 - relationship_support)
        ),
        "do_nothing": 1.0,
    }

    unknown_actions = set(available_actions) - set(weights)

    if unknown_actions:
        raise ValueError(
            f"Unknown actions: {sorted(unknown_actions)}"
        )

    selected_weights = {
        action: max(0.05, weights[action])
        for action in available_actions
    }

    total = sum(selected_weights.values())

    probabilities = {
        action: weight / total
        for action, weight in selected_weights.items()
    }

    rng = rng or random.Random()

    selected_action = rng.choices(
        population=list(probabilities),
        weights=list(probabilities.values()),
        k=1,
    )[0]

    return {
        "action": selected_action,
        "probabilities": probabilities,
        "decision_basis": {
            "context": context,
            "communication_confidence": confidence,
            "social_participation": participation,
            "help_seeking_intention": help_intention,
            "trust_in_services": service_trust,
            "frustration": frustration,
            "relationship_trust": relationship_trust,
            "relationship_support": relationship_support,
        },
    }
