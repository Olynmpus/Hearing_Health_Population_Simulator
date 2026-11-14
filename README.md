# Hearing Health Population Simulator

A configurable, agent-based simulation project for exploring hearing health, communication experiences, access to hearing support, healthcare services, funding arrangements and individual care pathways.

## Overview

The Hearing Health Population Simulator is a research, educational and scenario-exploration project. It uses synthetic individuals (agents) to explore how personal circumstances, hearing and communication experiences, access to support, service availability, funding arrangements and interventions may interact over time.

The simulator is designed to be **country-agnostic**. Australia is the initial reference framework for developing and exploring hearing-care pathways, healthcare structures, funding concepts and service contexts. The simulated population is hypothetical; it is not a representation or estimate of Australia's actual population.

Country-specific configurations can be developed to represent different population characteristics, geographical settings, healthcare systems, funding arrangements, service capacities and policy environments.

The project aims to support structured exploration of questions such as:

- How might geographical barriers affect access to hearing assessment and support?
- How might service capacity, workforce availability and operational costs influence service delivery?
- How do communication difficulties affect individual experiences and relationships?
- How might funding arrangements and personal contributions influence access to care?
- How could changes to technology, services, campaigns or policy affect individual hearing-care pathways?
- How might outcomes differ between population groups and geographical settings?

The project is under active development.
## Architecture overview

The architecture below illustrates the intended direction of the Hearing Health Population Simulator: individual agents communicate, interpret experiences from their own perspectives, develop relationships and memories, and contribute to population-level patterns over time.

![Hearing Health Population Simulator Architecture Overview](documentation/Hearing%20Health%20Simulator%20Architecture%20Overview.png)

### Agent interaction cycle

The event-driven communication model is designed around an independent, multi-step interaction:

1. An agent independently decides whether to initiate an interaction.
2. The local LLM generates the initiating agent's message using that agent's own state and relevant history.
3. The receiving agent interprets the message using its own context and perspective.
4. The receiving agent independently decides whether and how to respond.
5. The LLM generates the response using the responding agent's own context and the message it received.
6. The original initiating agent interprets the response from its own perspective.
7. Each participant's experience is recorded separately in their individual memory.

The LLM supports natural-language generation and interpretation. Statistical and rule-based simulation logic remains responsible for decisions, validated experience assessment and numerical changes to agent states and relationships.

An LLM interpretation is not proof of comprehension, agreement or a successful communication outcome.

### Individual memory and social relationships

Each agent maintains an individual interaction history. The memory model distinguishes between:

- Messages received and messages sent
- The agent's own interpretation of received messages
- The other participant's response, where available
- Interaction timing and evidence status

Participants do not share a single interpretation of an interaction. Each agent's record represents its own perspective.

Social relationships are represented separately from individual memories. The longer-term model is intended to explore how repeated interactions and experiences may influence relationships, create new connections and change the structure of social support networks over time.

### Population-level simulation and development status

The simulation is intended to connect individual communication experiences with broader population patterns, including help-seeking, service access, hearing health outcomes and social participation.

The architecture diagram includes both implemented capabilities and planned development. In particular:

**Implemented foundations**
- Agent profiles and individual state representations
- Independent interaction and response decisions
- Local LLM message generation and recipient interpretation
- Event-driven interaction recording
- Separate memory records for each participant
- Existing population, service and intervention modelling components

**Further development**
- Evidence-based assessment of individual communication experiences
- Validated emotional and experiential responses
- Controlled updates to agent states and relationship attributes
- Dynamic social network growth and change
- Longitudinal analysis of communication, help-seeking and population outcomes
- Feedback between simulation findings and intervention scenarios

These capabilities will be developed incrementally. The architecture represents the intended integrated model, not a claim that every component is currently operational.

## Research and modelling principles

The simulator follows several important principles.

### Hearing-aid ownership is not a measure of successful hearing care

The model distinguishes between:

- Access to hearing assessment and services
- Suitability of available support
- Acquisition of hearing devices or other support
- Actual use of support
- Functional effectiveness
- Individual satisfaction
- Longer-term individual outcomes

Ownership does not automatically imply use or benefit. Similarly, not owning a hearing aid does not necessarily mean that an individual has received unsuccessful care.

### Hearing ability and functional communication are distinct

A hearing profile alone does not determine an individual's communication experience.

People with normal audiometric profiles may still report functional hearing or communication difficulties. The simulator therefore distinguishes hearing profiles from reported and confirmed functional difficulties.

Functional difficulty should not automatically be interpreted as a specific clinical diagnosis.

### Unknown information remains unknown

Missing information is not automatically interpreted as a negative outcome or absence of difficulty.

### Evidence and assumptions are distinguished

Model information is classified using evidence-status concepts, including:

- Evidence-supported
- Simulation assumption
- Not yet established

Synthetic population characteristics and illustrative assumptions must not be interpreted as measured population estimates.

## Country configuration

The simulator includes an initial country-profile configuration layer.

The initial reference profile is:

`config/countries/australia_reference.json`

It identifies Australia as the initial reference country and records basic configuration information, including:

- Country identity and profile type
- Evidence status
- Currency
- Healthcare funding pathways
- Geographic service contexts
- Configuration notes

The country profile is currently loaded by the population experiment runner and its identifying information is included in the experiment summary.

**Important:** The initial country profile is a foundation for future country configurability. It does not yet control every population, funding, policy or service-delivery parameter. Country-specific rules and assumptions require further implementation and evidence.

Australian reference information, country-specific evidence and simulation assumptions must remain distinguishable.

## Main components

| Component | Purpose |
|---|---|
| Population | Generates synthetic individuals and integrates population records. |
| Agents | Represents individual profiles, states, relationships and memory. |
| Communication | Models communication environments, events and communication experiences. |
| Behaviour | Represents individual experiences and relationship changes. |
| Hearing support | Models support needs, funding arrangements, service access and care journeys. |
| Service capacity | Represents workforce, geographical access, costs, funding and operational capacity. |
| Service delivery | Models service demand, allocation, assessment and delivery. |
| Interventions | Loads and represents configurable interventions. |
| Country configuration | Loads and validates country reference profiles. |
| Simulation | Runs longitudinal demonstrations and population experiments. |

## Optional local language-model integration

The project includes an experimental local LLM communication interpretation module.

It uses Ollama to access a locally installed language model.

Current characteristics:

- LLM integration is optional.
- The current default model is `qwen3:1.7b`.
- Individual participant requests are handled separately.
- Generated interpretations are explicitly marked as unverified.
- LLM output does not directly modify authoritative agent states, relationships, clinical status or simulation outcomes.
- The simulation remains controlled by Python logic.

The LLM integration is experimental. Structurally valid model output should not be interpreted as factually or clinically validated.

The longer-term architecture keeps language interpretation separate from authoritative simulation logic. AI may assist with interpreting questions and explaining results, but it must not invent simulation outcomes or silently change model parameters.

## Technology

- Python 3.11+
- SQLite for simulation memory and event storage
- `pytest` for automated testing
- Ollama for optional local language-model experimentation

The project uses Python modules for its simulation logic. `pytest` is required to run the automated test suite. Additional dependencies may be required as reporting, analysis and other capabilities develop.

## Project structure

```text
Hearing_Health_Population_Simulator/
│
├── config/
│   ├── countries/
│   │   └── australia_reference.json
│   ├── HH-EXP-001.json
│   ├── communication_vocabulary.json
│   └── population_baseline.synthetic.json
│
├── documentation/
│   ├── communication_vocabulary.md
│   ├── hearing_support_and_funding_model.md
│   └── Hearing Support Access and Individual.docx
││  ├── Hearing Health Simulator Architecture Overview.png
├── outputs/
│   └── SQLite simulation databases
│
├── src/
│   ├── agents/
│   ├── behaviour/
│   ├── communication/
│   ├── hearing_support/
│   ├── interventions/
│   ├── population/
│   ├── service_capacity/
│   ├── service_delivery/
│   ├── simulation/
│   └── country_config.py
│
└── tests/
    └── Automated test suite
```

## Installation

Clone the repository:

```bash
git clone git@github.com:Olynmpus/Hearing_Health_Population_Simulator.git
cd Hearing_Health_Population_Simulator
```

Create a virtual environment:

```bash
python3.11 -m venv .venv
```

Activate it on Linux or WSL:

```bash
source .venv/bin/activate
```

Install the test dependency:

```bash
python -m pip install pytest
```

## Running the tests

From the project root:

```bash
python -m pytest -q
```

The automated test suite covers population generation, agents, communication, relationships, hearing support, funding, service access, service capacity, service delivery, interventions, country configuration and simulation integration.

## Running the longitudinal demonstration

The longitudinal demonstration can be started with:

```bash
python -m src.simulation.longitudinal_demo
```

By default, the demonstration writes to:

```text
outputs/HH-EXP-001-longitudinal-demo-v2.db
```

The application protects existing databases and stops if the selected output database already exists. Use a new output path when running another experiment rather than overwriting previous results.

## Current development status

The project is actively evolving.

Current implementation areas include:

- Synthetic population generation
- Individual agent profiles and state
- Communication events and participant perspectives
- Relationships and individual memory histories
- Hearing support needs and individual support records
- Funding and service access representation
- Service capacity and delivery modelling
- Longitudinal simulation
- Population experiment execution
- Initial country-profile loading and validation
- Optional local LLM communication interpretation

Further development is required to operationalise country-specific configurations, calibrate assumptions against appropriate evidence, validate model behaviour and establish the suitability of different scenarios for research or policy exploration.

## Limitations

This project is not currently:

- A calibrated representation of the Australian population or any other country's population.
- A validated epidemiological or clinical prediction model.
- A clinical diagnostic or treatment recommendation system.
- A complete implementation of country-specific healthcare funding, eligibility or policy rules.
- Evidence that a particular policy or intervention will produce a specific real-world outcome.

Simulation outputs depend on the assumptions, parameters and mechanisms implemented in the model. Results should be interpreted as exploratory outputs rather than predictions of actual population or hearing-health outcomes.

## Research direction

The longer-term objective is to develop an interactive educational and scenario-exploration platform.

Users should be able to describe hearing-health scenarios in ordinary language, explore controlled baseline and intervention simulations, and examine the resulting changes alongside assumptions, uncertainty, limitations and potential unintended consequences.

The intended workflow is:

1. Interpret a user's scenario or question.
2. Translate it into explicit, validated model parameters.
3. Run a controlled baseline simulation.
4. Run the proposed intervention or alternative scenario.
5. Compare the resulting simulation outputs.
6. Explain the results, assumptions, uncertainty and limitations.

AI may assist with interpreting questions and explaining results. The underlying Python simulation remains responsible for generating authoritative model outcomes.

## Licence

No licence has currently been specified for this repository.
