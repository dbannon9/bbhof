#%% Imports & connections
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter, MultipleLocator
from utils import fetch_table_data
neon = st.connection("neon",type="sql")

#%% Run the App
st.set_page_config(page_title="Baseball Hall of Fame Tracker")

#%% Get Data

players = fetch_table_data(table_name='players')
ballots = fetch_table_data(table_name='ballots')
bbwaa_ballots = fetch_table_data(table_name='bbwaa_ballots')

# Normalize the selection flag to a clean boolean (handles NULLs from the DB)
ballots['is_player_selected'] = ballots['is_player_selected'].fillna(False).astype(bool)

#%% Headers Display
st.title("Baseball Hall of Fame Tracker")
st.header("Player Summary",divider="red")

# Selectors
ALL_YEARS = 'All Years'
year_options = [ALL_YEARS] + sorted(bbwaa_ballots['year'].dropna().unique().tolist(), reverse=True)

year_col, player_col = st.columns([1, 3], gap='small')

with year_col:
    selected_year = st.selectbox("Ballot Year:", options=year_options, index=1)

# Limit players to those on the BBWAA ballot for the selected year
if selected_year == ALL_YEARS:
    filtered_players = players
else:
    year_player_ids = bbwaa_ballots.loc[bbwaa_ballots['year'] == selected_year, 'player_id'].unique()
    filtered_players = players[players['player_id'].isin(year_player_ids)]

player_options = filtered_players.set_index('player_id')['player_name'].to_dict()

with player_col:
    selected_player_id = st.selectbox(
        "Select a Player:",
        options=list(player_options.keys()),
        format_func=lambda pid: player_options[pid]
    )

if selected_player_id is None:
    st.info(f"No players found on the {selected_year} ballot.")
    st.stop()

selected_player_name = player_options[selected_player_id]

#%% Player Ballot History

# Years the player was eligible/on the bbwaa ballot
player_years = bbwaa_ballots[bbwaa_ballots['player_id'] == selected_player_id][['year']]

# Votes the player received, by year (only ballots where the player was selected)
player_votes = ballots[
    (ballots['player_id'] == selected_player_id) &
    (ballots['is_player_selected'])
]
votes_by_year = (
    player_votes
    .groupby('year')
    .size()
    .reset_index(name='vote_count')
)

# Total ballots cast per year (all voters, regardless of who they voted for)
total_ballots_by_year = (
    ballots
    .groupby('year')['voter_id']
    .nunique()
    .reset_index(name='total_ballots')
)

# Combine: every eligible year, votes received, total ballots that year
player_history = player_years.merge(votes_by_year, on='year', how='left')
player_history = player_history.merge(total_ballots_by_year, on='year', how='left')

player_history['vote_count'] = player_history['vote_count'].fillna(0).astype(int)
player_history['total_ballots'] = player_history['total_ballots'].fillna(0).astype(int)
player_history['percentage'] = (
    player_history['vote_count'] / player_history['total_ballots'].where(player_history['total_ballots'] > 0)
) * 100

player_history = player_history.sort_values(by='year', ascending=False)

#%% Display
st.subheader(f"Voting History for {selected_player_name}", divider="red")

left_col, right_col = st.columns(2, gap='small')

with left_col:
    history_display = player_history[
        ['year', 'vote_count', 'percentage']
    ].rename(columns={
        'year': 'Year',
        'vote_count': 'Total Votes',
        'percentage': 'Percentage of Ballots'
    })
    st.dataframe(
        history_display,
        hide_index=True,
        column_config={'Percentage of Ballots': st.column_config.NumberColumn(format='%.1f%%')}
    )

with right_col:
    chart_data = player_history.sort_values(by='year', ascending=True)

    background_color = "#000e29"
    grid_color = "#949caa"
    accent_color = "#ba0c2f"

    fig, ax = plt.subplots()
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    ax.plot(
        chart_data['year'], chart_data['percentage'],
        marker='o', color=accent_color
    )
    ax.axhline(y=75, color=accent_color, linestyle='--')

    ax.set_ylim(0, 100)
    ax.set_xlim(chart_data['year'].min() - 1, chart_data['year'].max() + 1)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MultipleLocator(25))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{int(y)}%'))

    ax.set_xlabel('Year', color='white')
    ax.set_ylabel('Percentage of Ballots', color='white')
    ax.tick_params(colors='white')

    for spine in ax.spines.values():
        spine.set_color(grid_color)

    st.pyplot(fig)