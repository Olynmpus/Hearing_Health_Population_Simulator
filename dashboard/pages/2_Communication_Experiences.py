import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_longitudinal


st.set_page_config(
    page_title="Communication Experiences",
    page_icon="◉",
    layout="wide",
)

st.title("Communication Experiences")
st.write(
    "Explore how communication experiences are represented in the "
    "four-month synthetic interaction scenario."
)

st.info(
    "These are scripted simulation events, not recordings or observations "
    "of real conversations. Participant interpretations and outcomes are "
    "scenario assumptions."
)

enable_llm = st.sidebar.checkbox(
    "Enable local LLM interpretations",
    value=False,
    help="Optional interpretations are model-generated and unverified.",
)

try:
    person, relationships, histories, snapshots = load_longitudinal(enable_llm)
except Exception as error:
    st.error(f"The interaction experiment could not be loaded: {error}")
    st.stop()


# Build one row per recorded participant perspective.
rows = []

for agent_id, events in histories.items():
    for event in events:
        details = event.get("additional_details", {})
        communication = details.get("communication_event", {})
        llm = details.get("llm_interpretation", {})

        rows.append({
            "Month": event["month"],
            "Participant": agent_id,
            "Interaction": details.get("interaction_id", ""),
            "Event type": event["event_type"].replace("_", " ").title(),
            "Perspective": details.get("perspective_type", "").replace(
                "_", " "
            ).title(),
            "Message": event["actual_message"],
            "Observed event": details.get("observed_event"),
            "Participant report": details.get("participant_report"),
            "Interpretation": event["agent_interpretation"],
            "Outcome": event["outcome"].replace("_", " ").title(),
            "Channel": communication.get("channel", "Not recorded"),
            "Initial outcome": communication.get(
                "initial_outcome", "not_assessed"
            ).replace("_", " ").title(),
            "Final outcome": communication.get(
                "final_outcome", "not_assessed"
            ).replace("_", " ").title(),
            "Clarification requested": communication.get(
                "clarification_requested", False
            ),
            "LLM": llm,
        })

events = pd.DataFrame(rows)

if events.empty:
    st.warning("No interaction records are available.")
    st.stop()


# Overview
st.subheader("Interaction overview")

interaction_count = events["Interaction"].nunique()
participant_count = events["Participant"].nunique()
month_count = events["Month"].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("Interactions", interaction_count)
col2.metric("Participant perspectives", len(events))
col3.metric("Months represented", month_count)

st.caption(
    "Each interaction can have more than one participant perspective. "
    "These are not independent conversations."
)


# Experience distribution
st.subheader("Recorded participant experiences")

outcome_counts = (
    events.groupby("Outcome")["Participant"]
    .count()
    .reset_index(name="Records")
)

fig = px.bar(
    outcome_counts,
    x="Outcome",
    y="Records",
    text="Records",
)
fig.update_layout(
    height=350,
    paper_bgcolor="#0b1220",
    plot_bgcolor="#0b1220",
    font_color="#e5eaf3",
)
st.plotly_chart(fig, use_container_width=True)


# Interaction explorer
st.subheader("Explore an interaction")

interaction_ids = sorted(events["Interaction"].unique())

selected_interaction = st.radio(
    "Select interaction",
    interaction_ids,
    format_func=lambda x: (
        f"Month {int(events.loc[events['Interaction'] == x, 'Month'].iloc[0])}"
        f" — {events.loc[events['Interaction'] == x, 'Event type'].iloc[0]}"
    ),
)

selected_events = events[
    events["Interaction"] == selected_interaction
].sort_values("Participant")

first_record = selected_events.iloc[0]

st.markdown(
    f"#### Month {first_record['Month']} · {first_record['Event type']}"
)
st.write(f"**Scenario event:** {first_record['Message']}")

for _, event in selected_events.iterrows():
    with st.expander(
        f"{event['Participant']} · {event['Perspective']}",
        expanded=True,
    ):
        st.write(f"**Interpretation:** {event['Interpretation']}")

        if pd.notna(event["Observed event"]):
            st.write(f"**Observed event:** {event['Observed event']}")

        if pd.notna(event["Participant report"]):
            st.write(f"**Participant report:** {event['Participant report']}")

        st.write(f"**Coded experience outcome:** {event['Outcome']}")

        llm = event["LLM"]
        if llm.get("status") == "generated" and llm.get("text"):
            st.write("**Local LLM interpretation (unverified):**")
            st.write(llm["text"])
            st.caption(
                f"Model: {llm.get('model')} · "
                "Not verified and not used to change simulation state."
            )


# Communication conditions
st.subheader("Communication mechanics")

st.write(
    "The communication event records the channel and potential environmental "
    "conditions. The current four-month scenario does not yet assess whether "
    "messages were understood or whether communication was repaired."
)

mechanics = selected_events.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Channel", mechanics["Channel"])
col2.metric("Initial outcome", mechanics["Initial outcome"])
col3.metric("Final outcome", mechanics["Final outcome"])

st.write(
    "**Clarification requested:** "
    + (
        "Yes"
        if mechanics["Clarification requested"]
        else "No"
    )
)

st.warning(
    "Initial and final communication outcomes are currently not assessed "
    "in this scenario. No communication breakdown, successful repair or "
    "recovery should be inferred from the participant experience labels."
)


# Timeline
st.subheader("Experiences across the four months")

timeline = (
    events.groupby(["Month", "Outcome"])
    .size()
    .reset_index(name="Records")
)

fig = px.bar(
    timeline,
    x="Month",
    y="Records",
    color="Outcome",
    barmode="stack",
)
fig.update_layout(
    height=380,
    paper_bgcolor="#0b1220",
    plot_bgcolor="#0b1220",
    font_color="#e5eaf3",
    xaxis=dict(dtick=1),
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Counts represent recorded participant perspectives, not population "
    "prevalence or measured real-world outcomes."
)
