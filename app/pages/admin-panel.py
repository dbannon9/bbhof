#%% Imports
import streamlit as st
import pandas as pd

#%% Connect to Neon
neon = st.connection("neon",type="sql")

#%% Run the App
st.set_page_config(page_title="Baseball Hall of Fame Tracker")


def fetch_table_data(table_name):
    data = neon.query(f"SELECT * FROM {table_name}", ttl=0)
    # Supabase v2 client: actual rows are in response.data
    if data.empty:
        st.warning(f"No data returned from table '{table_name}'.")
        return pd.DataFrame()

    # Normalize into DataFrame
    df = pd.DataFrame(data)
    return df

#%% Get Data

players = fetch_table_data(table_name='players')
voters = fetch_table_data(table_name='voters')
ballots = fetch_table_data(table_name='ballots')
