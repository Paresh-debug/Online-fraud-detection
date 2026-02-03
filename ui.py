import streamlit as st
import pandas as pd
import requests

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(page_title="XYZ Bank", layout="wide")

# -------------------------------
# Session state
# -------------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None
if "account_type" not in st.session_state:
    st.session_state.account_type = None
if "otp_ok" not in st.session_state:
    st.session_state.otp_ok = False

# -------------------------------
@st.cache_data
def get_users():
    r = requests.get(f"{BACKEND_URL}/debug/users")
    return r.json() if r.status_code == 200 else []

# -------------------------------
# ROLE
# -------------------------------
if st.session_state.page == "role":
    st.title("XYZ Bank")
    role = st.radio("Select role", ["Customer", "Admin"])
    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()

# -------------------------------
# USER SELECT
# -------------------------------
elif st.session_state.page == "user":
    users = get_users()

    label_map = {
        f"{u['user_id']} ({u['account_type']})": u for u in users
    }

    choice = st.selectbox("Select user", ["-- Select --"] + list(label_map.keys()))

    if choice != "-- Select --":
        u = label_map[choice]
        st.session_state.user = u["user_id"]
        st.session_state.account_type = u["account_type"]

    if st.button("Proceed"):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("Back"):
        st.session_state.page = "role"
        st.rerun()

# -------------------------------
# DASHBOARD
# -------------------------------
elif st.session_state.page == "dashboard":

    user = st.session_state.user
    role = st.session_state.role

    st.title(f"{role} Dashboard")
    st.caption(f"User: {user} | Account Type: {st.session_state.account_type}")
    st.divider()

    left, right = st.columns([2.5, 1.5])

    # History
    with left:
        r = requests.get(f"{BACKEND_URL}/history/{user}")
        hist = r.json()
        if hist:
            df = pd.DataFrame(hist)
            st.dataframe(df, use_container_width=True)
            if "fraud" in df.columns:
                st.line_chart(df["fraud"])
        else:
            st.info("No history")

    # Actions
    with right:
        if role == "Customer":
            st.subheader("New Transaction")
            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox("Device", ["mobile_1","mobile_2","laptop_1"])

            if st.button("Submit"):
                r = requests.post(
                    f"{BACKEND_URL}/transaction",
                    json={
                        "user_id": user,
                        "amount": amount,
                        "device_id": device
                    }
                )
                resp = r.json()

                if resp.get("action") == "BLOCK":
                    st.error(resp.get("message"))
                elif resp.get("action"):
                    st.success(resp["action"])
                elif resp.get("otp_required"):
                    st.warning("OTP required")
                    st.info(f"OTP: {resp['otp']}")

        else:
            st.subheader("Pending Transactions")
            p = requests.get(f"{BACKEND_URL}/pending").json()
            if not p:
                st.info("No pending")
            else:
                df = pd.DataFrame(p)
                st.dataframe(df, use_container_width=True)

    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
