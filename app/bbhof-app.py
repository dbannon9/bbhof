#%% Imports
import streamlit as st
import pandas as pd

#%% Connect to Neon
neon = st.connection("neon",type="sql")

#%% Run the App
st.set_page_config(layout="wide",page_title="Baseball Hall of Fame Tracker")

dashboard = st.Page("pages/dashboard.py",title="Home",icon=":material/home:")
nav = st.navigation([
    dashboard
])
nav.run()