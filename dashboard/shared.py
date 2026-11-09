from pathlib import Path
import tempfile
import uuid

import streamlit as st

from src.simulation.longitudinal_demo import run_experiment


@st.cache_resource(show_spinner="Running four-month interaction experiment...")
def load_longitudinal(enable_llm):
    database_path = (
        Path(tempfile.gettempdir())
        / f"hearing_dashboard_{uuid.uuid4().hex}.db"
    )
    return run_experiment(database_path, enable_llm=enable_llm)
