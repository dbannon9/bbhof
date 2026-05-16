#%% Imports
import streamlit as st
import pandas as pd

#%% Connect to Neon
neon = st.connection("neon",type="sql")

#%% Run the App
st.set_page_config(layout="wide",page_title="Baseball Hall of Fame Tracker")


def fetch_table_data(table_name):
    data = neon.query(f"SELECT * FROM {table_name}", ttl=0)
    # Supabase v2 client: actual rows are in response.data
    if data.empty:
        st.warning(f"No data returned from table '{table_name}'.")
        return pd.DataFrame()

    # Normalize into DataFrame
    df = pd.DataFrame(data)
    return df

players = fetch_table_data(table_name='players')

st.title("Baseball Hall of Fame Tracker")

players["fangraphs_link"] = ("http://www.fangraphs.com/statss.aspx?playerid=" + players["fangraphs_id"].astype(str).str.lstrip('0'))
players["bref_link"] = ("https://www.baseball-reference.com/players/" + players['player_last'].str[:1].str.lower() + "/" + players["bref_id"].astype(str)) + ".shtml"
players["mlb_link"] = ("https://www.mlb.com/player/" + players["mlb_id"].astype(str))

players_display = players[['player_name', 'first_year_on_ballot', 'fangraphs_link','bref_link','mlb_link']].rename(columns={
    'player_name': 'Player',
    'first_year_on_ballot': 'First Eligible Year',
    'fangraphs_link': 'Fangraphs',
    'bref_link': 'Baseball Reference',
    'mlb_link': 'MLB'
})

st.dataframe(
    players_display,
    hide_index=True,
    column_config={
        "Fangraphs": st.column_config.LinkColumn(
            "Fangraphs",
            help="Click this link to view the player's Fangraphs page",
            display_text="Fangraphs"
        ),
        "Baseball Reference": st.column_config.LinkColumn(
            "Baseball Reference",
            help="Click this link to view the player's Baseball Reference page",
            display_text="BRef"
        ),
        "MLB": st.column_config.LinkColumn(
            "MLB",
            help="Click this link to view the player's MLB page",
            display_text="MLB"
        )
    }
)