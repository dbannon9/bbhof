from __future__ import annotations

import streamlit as st
from utils import fetch_table_data
from tracker_table import render_tracker_table

st.set_page_config(page_title="Baseball Hall of Fame Tracker", layout="wide")

bbwaa = fetch_table_data(table_name="bbwaa_ballots")

st.title("Baseball Hall of Fame Tracker")

year = st.selectbox("Year", sorted(bbwaa["year"].unique(), reverse=True))

render_tracker_table(int(year))