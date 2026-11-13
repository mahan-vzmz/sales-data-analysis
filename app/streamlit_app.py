"""Streamlit navigation and data readiness."""

import sys
from pathlib import Path

import streamlit as st

# The Streamlit CLI adds the script directory to its import path.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

st.set_page_config(
    page_title="Sales analytics", page_icon=":material/monitoring:", layout="wide"
)


def home() -> None:
    from app.ui.data import (
        DataUnavailable,
        app_settings,
        load_model_artifact,
        read_mart,
    )

    st.title("Sales analytics")
    st.caption("Gold warehouse and saved model evaluations")
    settings = app_settings()
    st.subheader("Warehouse")
    try:
        summary = read_mart(settings, "mart_executive")
    except DataUnavailable as exc:
        st.info(str(exc))
    else:
        if summary.empty:
            st.info("The executive snapshot has no rows.")
        else:
            st.success("Gold executive snapshot is available.")
            st.page_link(
                "app_pages/gold_data.py",
                label="Browse Gold data",
                icon=":material/table_chart:",
            )
    st.subheader("Model evaluations")
    for model in ("forecast", "propensity"):
        try:
            artifact = load_model_artifact(settings, model)
        except DataUnavailable as exc:
            st.info(str(exc))
        else:
            st.write(f"{model.capitalize()}: {artifact['model']}")


st.navigation(
    [
        st.Page(home, title="Home", icon=":material/home:", default=True),
        st.Page(
            "app_pages/gold_data.py", title="Gold data", icon=":material/table_chart:"
        ),
    ]
).run()
