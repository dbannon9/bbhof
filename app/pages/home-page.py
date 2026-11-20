from __future__ import annotations

import streamlit as st
from tracker_table import CONNECTION_NAME, render_tracker_table

st.set_page_config(page_title="Baseball Hall of Fame Tracker", layout="wide")


@st.cache_data(ttl=600)
def ballot_years() -> list[int]:
    conn = st.connection(CONNECTION_NAME, type="sql")
    df = conn.query("SELECT DISTINCT year FROM bbwaa_ballots ORDER BY year DESC", ttl=0)
    return [int(y) for y in df["year"]]


st.title("Baseball Hall of Fame Tracker")

year = st.selectbox("Year", ballot_years(), key="tracker_year")

render_tracker_table(year)