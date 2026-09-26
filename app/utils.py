import streamlit as st
import pandas as pd
neon = st.connection("neon",type="sql")

def fetch_table_data(table_name):
    data = neon.query(f"SELECT * FROM {table_name}", ttl=0)
    # neon v2 client: actual rows are in response.data
    if data.empty:
        st.warning(f"No data returned from table '{table_name}'.")
        return pd.DataFrame()

    # Normalize into DataFrame
    df = pd.DataFrame(data)
    return df

#%% Password Gate

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]["value"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Incorrect password")
    return False