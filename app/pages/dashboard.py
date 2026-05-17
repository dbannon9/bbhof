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

#%% Get Data

players = fetch_table_data(table_name='players')
voters = fetch_table_data(table_name='voters')
ballots = fetch_table_data(table_name='ballots')

#%% Current Counts Sample

# Count ballots per player
vote_counts = (
    ballots
    .groupby('player_id')
    .size()
    .reset_index(name='vote_count')
)
total_ballots = ballots['voter_id'].nunique()

# Add counts back onto players table
players_with_count = players.merge(vote_counts[['player_id', 'vote_count']], on='player_id', how='left')

# Replace NaN with 0 and convert to int
players_with_count['vote_count'] = players_with_count['vote_count'].fillna(0).astype(int)
players_with_count['percentage'] = (players_with_count['vote_count'] / total_ballots)*100
players_with_count = players_with_count.sort_values(by='vote_count', ascending=False)

# Votes on ballot counts:
votes_by_voter = (
    ballots
    .groupby('voter_id')
    .size()
    .reset_index(name='vote_count')
)
votes_by_voter = voters[['voter_id']].merge(
    votes_by_voter,
    on='voter_id',
    how='left'
)
vote_distribution = (
    votes_by_voter
    .groupby('vote_count')
    .size()
    .reset_index(name='num_voters')
    .sort_values('vote_count',ascending=False)
)

#%% Display
st.title("Current Results")


players_col, ballots_col = st.columns(2,gap='small')
with players_col:
    players_display = players_with_count[
        ['player_name', 'vote_count', 'percentage']
    ].rename(columns={
        'player_name': 'Player',
        'vote_count': 'Total Number of Votes',
        'percentage': 'Percentage of Ballots'
    })
    st.dataframe(players_display,hide_index=True,column_config={'Percentage of Ballots': st.column_config.NumberColumn(format='%.1f%%')})

with ballots_col:
    vote_dist_display = vote_distribution[['vote_count','num_voters']]
    vote_dist_display['vote_count'] = vote_dist_display['vote_count'].astype(int).astype(str) + ' Vote Ballots'
    vote_dist_display.rename(columns={
        'vote_count': 'Vote Counts',
        'num_voters': 'Number of Ballots by Vote Count'
    },inplace=True)
    st.dataframe(vote_dist_display, hide_index=True)