#%% Imports
import streamlit as st
import pandas as pd
from utils import check_password
neon = st.connection("neon",type="sql")

#%% Gate
if not check_password():
    st.stop()

#%% Run the App
st.set_page_config(page_title="Baseball Hall of Fame Tracker",layout="wide")

dashboard = st.Page("pages/dashboard.py",title="Home",icon=":material/home:")
player_page = st.Page("pages/player-page.py",title="Players",icon=":material/sports_baseball:")
# # # # # # # voter_page = st.Page("pages/voter-page.py",title="Voters",icon=":material/how_to_vote:")
admin_panel = st.Page("pages/admin-panel.py",title="Admin Panel",icon=":material/settings:")
nav = st.navigation([
    dashboard,
    player_page,
    admin_panel
])
nav.run()