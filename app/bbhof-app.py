#%% Imports
import streamlit as st
import pandas as pd

#%% Connect to Neon
neon = st.connection("neon",type="sql")

#%% Run the App
st.set_page_config(layout="wide",page_title="Baseball Hall of Fame Tracker")


def fetch_table_data(table_name):
    response = neon.client.table(table_name).select("*").execute()

    # Supabase v2 client: actual rows are in response.data
    data = response.data
    if not data:
        st.warning(f"No data returned from table '{table_name}'.")
        return pd.DataFrame()

    # Normalize into DataFrame
    df = pd.DataFrame(data)
    return df

players = fetch_table_data(table_name='players')

st.title("Baseball Hall of Fame Tracker")
st.dataframe()
