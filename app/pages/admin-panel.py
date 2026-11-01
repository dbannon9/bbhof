#%% Imports & connections
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from utils import fetch_table_data, check_password
neon = st.connection("neon",type="sql")

#%% Password Gate
if not check_password():
    st.stop()

#%% Run the App
st.set_page_config(page_title="Baseball Hall of Fame Tracker",layout="wide")

#%% Get Data

players = fetch_table_data(table_name='players')
voters = fetch_table_data(table_name='voters')
ballots = fetch_table_data(table_name='ballots')
bbwaa_ballots = fetch_table_data(table_name='bbwaa_ballots')

#%% Headers Display
st.title("Admin Panel")

#%% Page Selector
page = st.selectbox(
    "What would you like to do?",
    options=["Manage Ballots", "Manage Voter", "Manage Player", "Manage BBWAA Ballot"],
    key="admin_page",
)

#%% Manage Ballots (full width: add + edit in one)
if page == "Manage Ballots":
    st.subheader("Add Ballot", divider="red")

    # Show a message carried over from the last submit (survives st.rerun)
    if "ballot_flash" in st.session_state:
        st.success(st.session_state.pop("ballot_flash"))

    # --- Year: from bbwaa_ballots, default to max ---
    available_years = sorted(bbwaa_ballots['year'].unique().tolist())
    selected_year = st.selectbox(
        "Year",
        options=available_years,
        index=len(available_years) - 1,
    )

    # --- Voter: active voters only ---
    active_voters = voters[voters['voter_status'] == 'Active']
    voter_options = active_voters.set_index('voter_id')['voter_name'].to_dict()
    voter_anon_default = active_voters.set_index('voter_id')['is_anonymous'].to_dict()

    selected_voter_id = st.selectbox(
        "Voter",
        options=list(voter_options.keys()),
        format_func=lambda vid: voter_options[vid],
    )

    # --- Players on that year's BBWAA ballot ---
    year_ballot = (
        bbwaa_ballots[bbwaa_ballots['year'] == selected_year]
        .merge(players[['player_id', 'player_name']], on='player_id', how='left')
        .sort_values('player_name')
    )

    # --- Check for an existing ballot for this voter/year ---
    with neon.session as session:
        existing_rows = session.execute(
            text("""
                SELECT player_id, is_player_selected, is_anonymous,
                    is_pre_announcement, is_verified,
                    include_change_color, include_in_change_total
                FROM ballots
                WHERE voter_id = :voter_id AND year = :year
            """),
            {"voter_id": selected_voter_id, "year": int(selected_year)},
        ).mappings().all()

    ballot_exists = len(existing_rows) > 0
    existing_by_player = {r["player_id"]: r for r in existing_rows}

    if ballot_exists:
        st.warning(
            f"{voter_options[selected_voter_id]} has already voted in {selected_year}. "
            "Submitting will update the existing ballot."
        )
        first = existing_rows[0]
        defaults = {
            "is_anonymous": bool(first["is_anonymous"]),
            "is_pre_announcement": bool(first["is_pre_announcement"]),
            "is_verified": bool(first["is_verified"]),
            "include_change_color": bool(first["include_change_color"]),
            "include_in_change_total": bool(first["include_in_change_total"]),
        }
    else:
        defaults = {
            "is_anonymous": bool(voter_anon_default.get(selected_voter_id, False)),
            "is_pre_announcement": False,
            "is_verified": False,
            "include_change_color": True,
            "include_in_change_total": True,
        }

    # Keys include year + voter so defaults refresh whenever either changes
    key_prefix = f"{selected_year}_{selected_voter_id}"

    with st.form("add_ballot", clear_on_submit=True, enter_to_submit=False, border=True):
        st.subheader(f"{selected_year} BBWAA Ballot", divider="red")
        cols = st.columns(3)
        selections = {}
        for i, row in enumerate(year_ballot.itertuples(index=False)):
            prior = existing_by_player.get(row.player_id)
            with cols[i % 3]:
                selections[row.player_id] = st.checkbox(
                    row.player_name,
                    value=bool(prior["is_player_selected"]) if prior else False,
                    key=f"sel_{key_prefix}_{row.player_id}",
                )

        st.subheader("Ballot Settings", divider="red")
        is_anonymous = st.checkbox(
            "Anonymous?", value=defaults["is_anonymous"], key=f"anon_{key_prefix}"
        )
        is_pre_announcement = st.checkbox(
            "Pre-Announcement?", value=defaults["is_pre_announcement"], key=f"pre_{key_prefix}"
        )
        is_verified = st.checkbox(
            "Verified?", value=defaults["is_verified"], key=f"ver_{key_prefix}"
        )
        include_change_color = st.checkbox(
            "Include Change Color?", value=defaults["include_change_color"], key=f"color_{key_prefix}"
        )
        include_in_change_total = st.checkbox(
            "Include in Change Total?", value=defaults["include_in_change_total"], key=f"total_{key_prefix}"
        )

        add_ballot_submit = st.form_submit_button(
            label="Update Ballot" if ballot_exists else "Submit"
        )

    if add_ballot_submit:
        shared = {
            "year": int(selected_year),
            "voter_id": selected_voter_id,
            "is_anonymous": bool(is_anonymous),
            "is_pre_announcement": bool(is_pre_announcement),
            "is_verified": bool(is_verified),
            "include_change_color": bool(include_change_color),
            "include_in_change_total": bool(include_in_change_total),
        }

        to_update, to_insert = [], []
        for r in year_ballot.itertuples(index=False):
            row = {
                **shared,
                "bbwaa_ballot_id": r.bbwaa_ballot_id,
                "player_id": r.player_id,
                "is_player_selected": bool(selections[r.player_id]),
            }
            # Players already on the saved ballot get updated; any new ones get inserted
            (to_update if r.player_id in existing_by_player else to_insert).append(row)

        with neon.session as session:
            if to_update:
                session.execute(
                    text("""
                        UPDATE ballots
                        SET is_player_selected = :is_player_selected,
                            is_anonymous = :is_anonymous,
                            is_pre_announcement = :is_pre_announcement,
                            is_verified = :is_verified,
                            include_change_color = :include_change_color,
                            include_in_change_total = :include_in_change_total
                        WHERE voter_id = :voter_id
                        AND year = :year
                        AND player_id = :player_id
                    """),
                    to_update,
                )
            if to_insert:
                session.execute(
                    text("""
                        INSERT INTO ballots (
                            bbwaa_ballot_id, year, voter_id, player_id,
                            is_player_selected, is_anonymous, is_pre_announcement,
                            is_verified, include_change_color, include_in_change_total
                        ) VALUES (
                            :bbwaa_ballot_id, :year, :voter_id, :player_id,
                            :is_player_selected, :is_anonymous, :is_pre_announcement,
                            :is_verified, :include_change_color, :include_in_change_total
                        )
                    """),
                    to_insert,
                )
            session.commit()

        n_selected = sum(r["is_player_selected"] for r in to_update + to_insert)
        st.session_state["ballot_flash"] = (
            f"Ballot {'updated' if ballot_exists else 'added'} with {n_selected} players selected."
        )
        st.rerun()

#%% Manage Voter (add left, edit right)
elif page == "Manage Voter":
    left_col, right_col = st.columns(2, gap="medium")

    with left_col:
        st.subheader("Add Voter", divider="red")
        with st.form("add_voter", clear_on_submit=True, enter_to_submit=False, border=True):
            # TODO: fields go here, e.g. voter_name, voter_status, is_anonymous
            add_voter_submit = st.form_submit_button(label="Submit")

        if add_voter_submit:
            # TODO: build dict + insert into "voters"
            pass

    with right_col:
        st.subheader("Edit Voter", divider="red")
        # TODO: record selector (e.g. selectbox by voter_name)
        # TODO: conditional form/fields once a record is selected
        # TODO: update logic

#%% Manage Player (add left, edit right)
elif page == "Manage Player":
    left_col, right_col = st.columns(2, gap="medium")

    with left_col:
        st.subheader("Add Player", divider="red")
        with st.form("add_player", clear_on_submit=True, enter_to_submit=False, border=True):
            # TODO: fields go here, e.g. player_name
            add_player_submit = st.form_submit_button(label="Submit")

        if add_player_submit:
            # TODO: build dict + insert into "players"
            pass

    with right_col:
        st.subheader("Edit Player", divider="red")
        # TODO: record selector (e.g. selectbox by player_name)
        # TODO: conditional form/fields once a record is selected
        # TODO: update logic

#%% Manage BBWAA Ballot (add left, edit right)
elif page == "Manage BBWAA Ballot":
    left_col, right_col = st.columns(2, gap="medium")

    with left_col:
        st.subheader("Add BBWAA Ballot", divider="red")
        with st.form("add_bbwaa_ballot", clear_on_submit=True, enter_to_submit=False, border=True):
            # TODO: fields go here, e.g. year, player_id select
            add_bbwaa_ballot_submit = st.form_submit_button(label="Submit")

        if add_bbwaa_ballot_submit:
            # TODO: build dict + insert into "bbwaa_ballots"
            pass

    with right_col:
        st.subheader("Edit BBWAA Ballot", divider="red")
        # TODO: record selector (e.g. selectbox by year + player)
        # TODO: conditional form/fields once a record is selected
        # TODO: update logic