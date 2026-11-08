from pathlib import Path
import sys
import tempfile
import uuid
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.simulation.population_experiment import run_population_experiment
from src.simulation.longitudinal_demo import run_experiment


CONFIG = ROOT / "config" / "HH-EXP-001.json"
DISTRIBUTION = ROOT / "config" / "population_baseline.synthetic.json"
INTERVENTION = ROOT / "config" / "interventions" / "mobile_hearing_outreach.json"


st.set_page_config(
    page_title="Hearing Health Population Simulator",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0b1220; color: #e5eaf3; }
    [data-testid="stSidebar"] { background-color: #111c2e; }
    [data-testid="stMetric"] {
        background: #152238;
        border: 1px solid #263750;
        padding: 16px;
        border-radius: 10px;
    }
    .hero {
        padding: 24px 28px;
        border: 1px solid #263750;
        border-radius: 14px;
        background: linear-gradient(115deg, #14243b, #182d43);
        margin-bottom: 20px;
    }
    .hero h1 { margin: 0; color: #f3f6fb; font-size: 2rem; }
    .hero p { color: #a9bad0; margin-bottom: 0; }
    .credit {
        color: #8294aa;
        text-align: center;
        font-size: 0.82rem;
        padding: 24px 0 10px 0;
    }
    h2, h3 { color: #eaf0f8; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Running population experiment...")
def load_population(use_intervention):
    intervention_path = str(INTERVENTION) if use_intervention else None
    return run_population_experiment(
        str(CONFIG),
        str(DISTRIBUTION),
        intervention_path,
    )


@st.cache_resource(show_spinner="Running four-month interaction experiment...")
def load_longitudinal(enable_llm):
    database_path = (
        Path(tempfile.gettempdir())
        / f"hearing_dashboard_{uuid.uuid4().hex}.db"
    )
    return run_experiment(database_path, enable_llm=enable_llm)


def distribution_frame(distribution):
    return pd.DataFrame([
        {"Category": key.replace("_", " ").title(),
         "People": value["count"],
         "Percentage": value["percentage"]}
        for key, value in distribution.items()
    ])


def outcome_group(outcome):
    if outcome in {
        "negative_communication",
        "misdirected_information",
        "blocked_service_access",
    }:
        return "Negative experience"
    if outcome == "supportive_communication":
        return "Positive experience"
    return "Not classified"


def make_network(relationships, selected_agent, status_filter):
    nodes = {
        "PERSON-001": {
            "label": "Person",
            "role": "Community member",
            "colour": "#38bdf8",
            "x": 0,
            "y": 0,
        },
        "FAMILY-001": {
            "label": "Family",
            "role": "Family member",
            "colour": "#a78bfa",
            "x": -1.2,
            "y": 0.8,
        },
        "FRIEND-001": {
            "label": "Friend",
            "role": "Friend",
            "colour": "#34d399",
            "x": -1.2,
            "y": -0.8,
        },
        "SERVICE-001": {
            "label": "Service",
            "role": "Service representative",
            "colour": "#fbbf24",
            "x": 1.2,
            "y": 0,
        },
    }

    agent_relationships = relationships.get(selected_agent, {})

    status_colours = {
        "active": "#34d399",
        "strained": "#f59e0b",
        "disconnected": "#f87171",
    }

    edge_traces = []

    for contact_id, relationship in agent_relationships.items():
        if status_filter != "All" and relationship.status != status_filter:
            continue

        start = nodes[selected_agent]
        end = nodes[contact_id]
        colour = status_colours.get(relationship.status, "#94a3b8")

        edge_traces.append(go.Scatter(
            x=[start["x"], end["x"]],
            y=[start["y"], end["y"]],
            mode="lines",
            line=dict(width=3, color=colour),
            hovertemplate=(
                f"<b>{selected_agent} → {contact_id}</b><br>"
                f"Relationship: {relationship.relationship_type}<br>"
                f"Trust: {relationship.trust:.2f}<br>"
                f"Perceived support: {relationship.perceived_support:.2f}<br>"
                f"Interactions/month: "
                f"{relationship.interactions_per_month:.2f}<br>"
                f"Status: {relationship.status}<extra></extra>"
            ),
            showlegend=False,
        ))

    visible_nodes = {selected_agent}

    for contact_id, relationship in agent_relationships.items():
        if status_filter == "All" or relationship.status == status_filter:
            visible_nodes.add(contact_id)

    node_trace = go.Scatter(
        x=[nodes[agent_id]["x"] for agent_id in visible_nodes],
        y=[nodes[agent_id]["y"] for agent_id in visible_nodes],
        mode="markers+text",
        text=[nodes[agent_id]["label"] for agent_id in visible_nodes],
        textposition="bottom center",
        customdata=[
            [nodes[agent_id]["role"], agent_id]
            for agent_id in visible_nodes
        ],
        hovertemplate=(
            "<b>%{text}</b><br>%{customdata[0]}"
            "<br>%{customdata[1]}<extra></extra>"
        ),
        marker=dict(
            size=[
                48 if agent_id == selected_agent else 38
                for agent_id in visible_nodes
            ],
            color=[
                nodes[agent_id]["colour"]
                for agent_id in visible_nodes
            ],
            line=dict(width=2, color="#e2e8f0"),
        ),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])

    fig.update_layout(
        height=470,
        margin=dict(l=20, r=20, t=25, b=35),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font=dict(color="#e5eaf3"),
        xaxis=dict(visible=False, range=[-1.8, 1.8]),
        yaxis=dict(visible=False, range=[-1.2, 1.2]),
        hovermode="closest",
    )

    return fig


def make_household_network(agents, relationships, household_id=None):
    """Display one household or the combined population household network."""

    if household_id is None:
        members = list(agents)
    else:
        members = [
            agent for agent in agents
            if agent.household_id == household_id
        ]

    households = {}
    for agent in members:
        key = agent.household_id or agent.agent_id
        households.setdefault(key, []).append(agent)

    positions = {}
    household_keys = sorted(households)
    columns = max(1, math.ceil(math.sqrt(len(household_keys))))

    for index, key in enumerate(household_keys):
        centre_x = (index % columns) * 2.5
        centre_y = -(index // columns) * 2.5
        household = households[key]

        for member_index, agent in enumerate(household):
            angle = 2 * math.pi * member_index / max(len(household), 1)
            radius = 0.38 if len(household) > 1 else 0
            positions[agent.agent_id] = (
                centre_x + radius * math.cos(angle),
                centre_y + radius * math.sin(angle),
            )

    member_ids = set(positions)
    edge_x, edge_y = [], []
    seen_edges = set()

    for relationship in relationships:
        source = relationship.agent_id
        target = relationship.contact_id

        if source not in member_ids or target not in member_ids:
            continue

        edge = tuple(sorted((source, target)))
        if edge in seen_edges:
            continue

        seen_edges.add(edge)
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        edge_x.extend([x1, x2, None])
        edge_y.extend([y1, y2, None])

    fig = go.Figure()

    if edge_x:
        fig.add_trace(go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="#64748b"),
            hoverinfo="skip",
            showlegend=False,
        ))

    geography_colours = {
        "metropolitan": "#38bdf8",
        "regional": "#a78bfa",
        "remote_very_remote": "#f59e0b",
    }

    show_labels = household_id is not None

    for geography, colour in geography_colours.items():
        group = [
            agent for agent in members
            if agent.summary()["geography"] == geography
        ]
        if not group:
            continue

        fig.add_trace(go.Scatter(
            x=[positions[a.agent_id][0] for a in group],
            y=[positions[a.agent_id][1] for a in group],
            mode="markers+text" if show_labels else "markers",
            text=[a.agent_id for a in group] if show_labels else None,
            textposition="bottom center",
            customdata=[
                [
                    a.summary()["age_group"],
                    a.summary()["geography"],
                    a.summary()["hearing_profile"],
                    a.summary()["auditory_functional_status"],
                    a.household_id or "No household recorded",
                ]
                for a in group
            ],
            hovertemplate=(
                "<b>%{text}</b><br>" if show_labels else
                "<b>Participant</b><br>"
            ) + (
                "Age group: %{customdata[0]}<br>"
                "Geography: %{customdata[1]}<br>"
                "Hearing profile: %{customdata[2]}<br>"
                "Functional status: %{customdata[3]}<br>"
                "Household: %{customdata[4]}"
                "<extra></extra>"
            ),
            marker=dict(
                size=28 if show_labels else 9,
                color=colour,
                line=dict(width=1, color="#e2e8f0"),
            ),
            name=geography.replace("_", " ").title(),
        ))

    fig.update_layout(
        height=850 if household_id is None else 480,
        margin=dict(l=30, r=30, t=30, b=50),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font=dict(color="#e5eaf3"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        legend=dict(orientation="h", y=-0.04),
        hovermode="closest",
    )

    return fig, len(seen_edges)


# Sidebar
st.sidebar.markdown("## Experiment controls")

scenario = st.sidebar.selectbox(
    "Population scenario",
    ["Baseline", "Mobile hearing outreach"],
)

enable_llm = st.sidebar.checkbox(
    "Enable local LLM interpretations",
    value=False,
    help="Uses the configured local Ollama model for the first interaction.",
)

st.sidebar.caption(
    "The population scenario and the four-agent longitudinal demonstration "
    "are separate model runs."
)

use_intervention = scenario == "Mobile hearing outreach"

try:
    population = load_population(use_intervention)
    summary = population.summary()
    person, relationships, histories, snapshots = load_longitudinal(enable_llm)
except Exception as error:
    st.error(f"The experiment could not be loaded: {error}")
    st.stop()


# Header
st.markdown("""
<div class="hero">
    <h1>Hearing Health Population Simulator</h1>
    <p>Explore population characteristics, service access, individual experiences
    and relationships in a simulated hearing-health system.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    f"{summary['experiment_name']} · {summary['country_name']} reference framework "
    f"· Evidence status: {summary['evidence_status']}"
)

overview_tab, population_explorer_tab, relationships_tab, timeline_tab, research_tab = st.tabs([
    "Population overview",
    "Population explorer",
    "Relationships",
    "Timeline & interactions",
    "Research exploration",
])


# Population overview
with overview_tab:
    st.subheader("Population at a glance")
    st.write(
        "A high-level view of the simulated population and the service "
        "system supporting it."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulated people", f"{summary['population_size']:,}")
    c2.metric("Simulation duration", f"{summary['duration_months']} months")
    c3.metric("Support records", f"{summary['support_record_count']:,}")
    c4.metric("Service demands", summary["service_delivery"]["total_demands"])

    st.divider()
    st.markdown("#### Service system performance")
    service = summary["service_delivery"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Allocated", service["allocated"])
    c2.metric("Unallocated", service["unallocated"])
    c3.metric("Total demand", service["total_demands"])

    delivery_left, delivery_right = st.columns(2)

    with delivery_left:
        st.markdown("**Attendance**")
        attendance = pd.DataFrame([
            {"Status": key.replace("_", " ").title(), "Count": value}
            for key, value in service["attendance"].items()
        ])
        if not attendance.empty:
            st.dataframe(attendance, hide_index=True, use_container_width=True)

    with delivery_right:
        st.markdown("**Delivery outcomes**")
        delivery = pd.DataFrame([
            {"Status": key.replace("_", " ").title(), "Count": value}
            for key, value in service["delivery_outcomes"].items()
        ])
        if not delivery.empty:
            st.dataframe(delivery, hide_index=True, use_container_width=True)

    st.caption(
        "The population is hypothetical and generated from simulation "
        "assumptions. It is not an estimate of Australia's population."
    )


# Population explorer
with population_explorer_tab:
    st.subheader("Explore population characteristics")
    st.write(
        "Examine the distribution of hearing profiles, geography, age "
        "groups and auditory functional status."
    )

    distributions = summary["population_distributions"]

    left, right = st.columns(2)

    with left:
        st.markdown("#### Hearing profile")
        frame = distribution_frame(distributions["hearing_profile"])
        fig = px.bar(
            frame, x="Category", y="People",
            color="Category", text="People",
        )
        fig.update_layout(
            showlegend=False, height=340,
            paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
            font_color="#e5eaf3",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Geographic distribution")
        frame = distribution_frame(distributions["geography"])
        fig = px.pie(
            frame, names="Category", values="People", hole=0.55,
        )
        fig.update_layout(
            height=340,
            paper_bgcolor="#0b1220",
            font_color="#e5eaf3",
            legend_title_text="Geography",
        )
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.markdown("#### Age groups")
        frame = distribution_frame(distributions["age_group"])
        fig = px.bar(frame, x="Category", y="People", text="People")
        fig.update_layout(
            height=330, xaxis_tickangle=-25,
            paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
            font_color="#e5eaf3",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Auditory functional status")
        frame = distribution_frame(distributions["functional_status"])
        fig = px.bar(
            frame, x="Category", y="People",
            color="Category", text="People",
        )
        fig.update_layout(
            height=330, xaxis_tickangle=-20,
            showlegend=False,
            paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
            font_color="#e5eaf3",
        )
        st.plotly_chart(fig, use_container_width=True)


# Relationships
# Relationships
with relationships_tab:
    st.subheader("Population household relationships")
    st.write(
        "Explore simulated family relationships within the synthetic "
        "population. These are household connections, not a complete "
        "social network."
    )

    household_members = {}
    for agent in population.agents:
        if agent.household_id is not None:
            household_members.setdefault(agent.household_id, []).append(agent)

    household_ids = sorted(household_members)
    unique_connections = {
        tuple(sorted((relationship.agent_id, relationship.contact_id)))
        for relationship in population.relationships
    }

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Population", f"{len(population.agents):,}")
    metric2.metric("Households", f"{len(household_ids):,}")
    metric3.metric("Unique family connections", f"{len(unique_connections):,}")

    household_options = ["All households"] + household_ids

    selected_household = st.selectbox(
        "Network view",
        household_options,
        format_func=lambda value: (
            value if value == "All households"
            else (
                f"{value} ({len(household_members[value])} "
                f"{'member' if len(household_members[value]) == 1 else 'members'})"
            )
        ),
    )

    if selected_household == "All households":
        st.markdown("#### Combined population household network")
        fig, connection_count = make_household_network(
            population.agents,
            population.relationships,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            f"Showing {len(population.agents):,} people across "
            f"{len(household_ids):,} households, with "
            f"{connection_count:,} unique family connections. "
            "Each cluster represents one household."
        )

        geography_counts = (
            pd.DataFrame([
                {
                    "Geography": agent.summary()["geography"].replace(
                        "_", " "
                    ).title()
                }
                for agent in population.agents
            ])
            ["Geography"].value_counts().rename_axis("Geography")
            .reset_index(name="People")
        )
        st.markdown("#### Population geography")
        st.dataframe(
            geography_counts,
            hide_index=True,
            use_container_width=True,
        )

    else:
        selected_members = household_members[selected_household]
        selected_member_ids = {
            agent.agent_id for agent in selected_members
        }

        st.markdown("#### Household relationship network")
        fig, connection_count = make_household_network(
            population.agents,
            population.relationships,
            selected_household,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            f"{len(selected_members)} household members | "
            f"{connection_count} unique family connections"
        )

        st.markdown("#### Household members")
        member_rows = [
            {
                "Participant": agent.agent_id,
                "Age group": agent.summary()["age_group"],
                "Hearing profile": agent.summary()["hearing_profile"],
                "Functional status": agent.summary()[
                    "auditory_functional_status"
                ],
                "Geography": agent.summary()["geography"],
            }
            for agent in selected_members
        ]
        st.dataframe(
            pd.DataFrame(member_rows),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("#### Recorded family connections")
        connection_rows = []
        seen_connections = set()

        for relationship in population.relationships:
            if (
                relationship.agent_id not in selected_member_ids
                or relationship.contact_id not in selected_member_ids
            ):
                continue

            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))
            if pair in seen_connections:
                continue
            seen_connections.add(pair)

            connection_rows.append({
                "Participant": relationship.agent_id,
                "Household member": relationship.contact_id,
                "Relationship": relationship.relationship_type.replace(
                    "_", " "
                ).title(),
                "Trust": relationship.trust,
                "Perceived support": relationship.perceived_support,
                "Interactions per month": relationship.interactions_per_month,
                "Status": relationship.status.replace("_", " ").title(),
            })

        if connection_rows:
            st.dataframe(
                pd.DataFrame(connection_rows),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info(
                "This household has no recorded connections. "
                "It may be a single-person household."
            )

    st.caption(
        "Relationships are synthetic household-family assumptions. "
        "They do not represent measured relationships or broader "
        "friendship, community or service networks. Relationship values "
        "are initial simulation values."
    )


# Timeline and interactions
with timeline_tab:
    st.subheader("Individual experience over time")

    months = [snapshot["month"] for snapshot in snapshots]
    selected_month = st.slider(
        "Select simulation month",
        min_value=min(months),
        max_value=max(months),
        value=max(months),
        step=1,
    )

    selected_snapshot = next(
        snapshot for snapshot in snapshots
        if snapshot["month"] == selected_month
    )

    state = selected_snapshot["state"]

    st.markdown(f"#### Month {selected_month}")

    state_fields = [
        ("Communication confidence", "communication_confidence"),
        ("Trust in services", "trust_in_services"),
        ("Perceived support", "perceived_support"),
        ("Social participation", "social_participation"),
        ("Perceived loneliness", "perceived_loneliness"),
        ("Frustration", "frustration"),
    ]

    columns = st.columns(3)
    for index, (label, key) in enumerate(state_fields):
        columns[index % 3].metric(label, f"{state[key]:.2f}")

    state_rows = []
    for snapshot in snapshots:
        for label, key in state_fields:
            state_rows.append({
                "Month": snapshot["month"],
                "Measure": label,
                "Value": snapshot["state"][key],
            })

    state_frame = pd.DataFrame(state_rows)
    fig = px.line(
        state_frame,
        x="Month",
        y="Value",
        color="Measure",
        markers=True,
    )
    fig.update_layout(
        height=390,
        yaxis=dict(range=[0, 1], title="Modelled value"),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font_color="#e5eaf3",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Recorded interactions")

    event_rows = []
    for agent_id, events in histories.items():
        for event in events:
            details = event.get("additional_details", {})
            event_rows.append({
                "Month": event["month"],
                "Participant": agent_id,
                "Interaction": details.get("interaction_id", ""),
                "Event type": event["event_type"].replace("_", " ").title(),
                "Outcome": event["outcome"].replace("_", " ").title(),
                "Experience": outcome_group(event["outcome"]),
                "Message": event["actual_message"],
                "Interpretation": event["agent_interpretation"],
                "LLM": details.get("llm_interpretation", {}),
            })

    event_frame = pd.DataFrame(event_rows)
    visible_events = event_frame[event_frame["Month"] == selected_month]

    if visible_events.empty:
        st.info("No interaction records for this month.")
    else:
        participant_filter = st.selectbox(
            "Participant perspective",
            ["All participants"] + sorted(visible_events["Participant"].unique()),
        )

        if participant_filter != "All participants":
            visible_events = visible_events[
                visible_events["Participant"] == participant_filter
            ]

        for _, event in visible_events.iterrows():
            with st.expander(
                f"{event['Participant']} · {event['Interaction']} · "
                f"{event['Experience']}"
            ):
                st.write(f"**Event:** {event['Message']}")
                st.write(f"**Participant interpretation:** {event['Interpretation']}")
                st.write(f"**Outcome:** {event['Outcome']}")

                llm = event["LLM"]
                if llm.get("status") == "generated" and llm.get("text"):
                    st.write("**Local LLM interpretation (unverified):**")
                    st.write(llm["text"])
                    st.caption(
                        f"Model: {llm.get('model')} · "
                        "Model-generated, unverified; not used to change state."
                    )
                elif llm.get("status") == "failed":
                    st.caption("Local LLM interpretation failed for this record.")
                else:
                    st.caption("No local LLM interpretation was generated.")

    st.caption(
        "Monthly state values are recorded model outputs. Positive and negative "
        "labels describe the scenario's coded interaction outcomes, not clinical "
        "judgements or measured real-world effects."
    )


# Research exploration
with research_tab:
    st.subheader("Explore a research question")

    question = st.selectbox(
        "Research question",
        [
            "How are hearing profiles distributed across the population?",
            "How does geography relate to the simulated population?",
            "What service demand and delivery outcomes are recorded?",
            "What changes across the selected intervention scenario?",
        ],
    )

    st.markdown("#### Current scenario")
    st.write(
        "The selected population scenario is **"
        + scenario
        + "**."
    )

    st.info(
        "This first dashboard version runs the configured baseline or mobile "
        "outreach scenario and reports its actual outputs. It does not yet "
        "translate arbitrary free-text questions into new model parameters."
    )

    st.markdown("#### Experiment definition")
    st.write(f"Experiment: {summary['experiment_id']}")
    st.write(f"Population configuration: {summary['distribution_profile_id']}")
    st.write(f"Random seed: {summary['random_seed']}")
    st.write(f"Evidence status: {summary['evidence_status']}")

    if summary["intervention"]:
        st.write(f"Intervention: {summary['intervention']['name']}")
        st.write(
            f"Intervention evidence status: "
            f"{summary['intervention']['evidence_status']}"
        )
    else:
        st.write("Intervention: None (baseline)")


st.markdown("""
<div class="credit">
    Designed and developed by Jorge Mejia<br>
    Hearing Health Population Simulator · Research and Experimental Platform
</div>
""", unsafe_allow_html=True)
