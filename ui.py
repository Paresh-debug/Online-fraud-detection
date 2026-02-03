import streamlit as st
import pandas as pd
import requests
import json

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank – Fraud Detection",
    layout="wide"
)

# -----------------------------
# Load users
# -----------------------------
@st.cache_data
def load_users():
    with open("user_transactions.json") as f:
        data = json.load(f)
    return sorted(u["user_id"] for u in data["users"])


users = load_users()

# -----------------------------
# Session
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None


# -----------------------------
# Role selection
# -----------------------------
if st.session_state.page == "role":
    st.title("XYZ Bank")
    role = st.radio("Select role", ["Customer", "Admin"])

    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()


# -----------------------------
# User select
# -----------------------------
elif st.session_state.page == "user":
    user = st.selectbox("User ID", users)

    if st.button("Proceed"):
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("Back"):
        st.session_state.page = "role"
        st.rerun()


# -----------------------------
# Dashboard
# -----------------------------
elif st.session_state.page == "dashboard":
    user = st.session_state.user
    role = st.session_state.role

    st.title(f"{role} Dashboard")
    st.caption(f"Account: {user}")

    left, right = st.columns([2.5, 1.5])

    # -------------------------
    # History + Graphs
    # -------------------------
    with left:
        res = requests.get(f"{BACKEND_URL}/history/{user}")
        history = res.json()

        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)

            if "fraud" in df.columns:
                st.subheader("Fraud Trend")
                st.line_chart(df["fraud"])

            if "amount" in df.columns:
                st.subheader("Amount Trend")
                st.line_chart(df["amount"])
        else:
            st.info("No history")

    # -------------------------
    # Right panel
    # -------------------------
    with right:
        if role == "Customer":
            amount = st.number_input("Amount", min_value=1)
            device = st.selectbox("Device", ["mobile_1", "mobile_2", "laptop_1"])

            if st.button("Submit Transaction"):
                requests.post(
                    f"{BACKEND_URL}/transaction",
                    json={
                        "user_id": user,
                        "amount": amount,
                        "device_id": device
                    }
                )
                st.success("Transaction submitted")

        else:
            res = requests.get(f"{BACKEND_URL}/pending")
            pending = res.json()

            if pending:
                df = pd.DataFrame(pending)
                st.dataframe(df)

                txn_id = st.selectbox("Transaction", df["transaction_id"])
                txn = df[df["transaction_id"] == txn_id].iloc[0]

                st.write("Risk Score:", txn["risk_score"])
                st.write("Risk Flag:", txn["risk_flag"])
                st.write("RF Probability:", txn["rf_probability"])
                st.write("Online Probability:", txn["online_probability"])

                with st.form("decision"):
                    approve = st.form_submit_button("Approve")
                    reject = st.form_submit_button("Reject")

                    if approve or reject:
                        requests.post(
                            f"{BACKEND_URL}/decision",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "decision": "APPROVE" if approve else "REJECT"
                            }
                        )
                        st.success("Decision saved")
                        st.rerun()
            else:
                st.info("No pending requests")

    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
