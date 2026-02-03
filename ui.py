import streamlit as st
import pandas as pd
import requests
import json

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank – Fraud Detection",
    layout="wide"
)

# -------------------------------------------------
# Load users from JSON
# -------------------------------------------------
@st.cache_data
def load_users():
    with open("user_transactions.json", "r") as f:
        data = json.load(f)
    return sorted(user["user_id"] for user in data["users"])


users = load_users()

# -------------------------------------------------
# Session State
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"

if "role" not in st.session_state:
    st.session_state.role = None

if "user" not in st.session_state:
    st.session_state.user = None


# =================================================
# PAGE 0 – ROLE SELECTION
# =================================================
if st.session_state.page == "role":
    st.title("XYZ Bank")
    st.markdown("### Access Role")

    role = st.radio("Select role", ["Customer", "Admin"])

    if st.button("Continue", key="role_continue"):
        st.session_state.role = role
        st.session_state.page = "user_select"
        st.rerun()


# =================================================
# PAGE 1 – USER SELECTION
# =================================================
elif st.session_state.page == "user_select":
    st.title("Account Selection")

    user = st.selectbox("User ID", ["-- Select --"] + users)

    col1, col2 = st.columns(2)

    if user != "-- Select --" and col1.button("Proceed", key="user_proceed"):
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()

    if col2.button("Back", key="user_back"):
        st.session_state.page = "role"
        st.rerun()


# =================================================
# PAGE 2 – DASHBOARD
# =================================================
elif st.session_state.page == "dashboard":
    user = st.session_state.user
    role = st.session_state.role

    st.title(f"{role} Dashboard")
    st.caption(f"Account: {user}")

    st.divider()
    left, right = st.columns([2.5, 1.5])

    # -------------------------------------------------
    # LEFT – TRANSACTION HISTORY
    # -------------------------------------------------
    with left:
        st.subheader("Transaction History")

        try:
            res = requests.get(f"{BACKEND_URL}/history/{user}")
            history = res.json()

            if history:
                df = pd.DataFrame(history)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No transaction history")

        except Exception as e:
            st.error("Unable to load history")
            st.code(str(e))

    # -------------------------------------------------
    # RIGHT – CUSTOMER / ADMIN PANEL
    # -------------------------------------------------
    with right:

        # =============================
        # CUSTOMER VIEW
        # =============================
        if role == "Customer":
            st.subheader("New Transaction")

            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox(
                "Device",
                ["mobile_1", "mobile_2", "laptop_1"]
            )

            if st.button("Submit Transaction", key="submit_txn"):
                payload = {
                    "user_id": user,
                    "amount": amount,
                    "device_id": device
                }

                res = requests.post(
                    f"{BACKEND_URL}/transaction",
                    json=payload
                )

                if res.status_code == 200:
                    st.success("Transaction submitted for evaluation")
                else:
                    st.error("Transaction submission failed")

        # =============================
        # ADMIN VIEW
        # =============================
        else:
            st.subheader("Pending Transaction Requests")

            try:
                res = requests.get(f"{BACKEND_URL}/pending")
                pending = res.json()

                if pending:
                    df = pd.DataFrame(pending)
                    st.dataframe(df, use_container_width=True)

                    selected_txn = st.selectbox(
                        "Select Transaction ID",
                        df["transaction_id"],
                        key="admin_txn_select"
                    )

                    txn = df[df["transaction_id"] == selected_txn].iloc[0]

                    st.markdown("#### Transaction Details")
                    st.write("User:", txn["user_id"])
                    st.write("Amount:", txn["amount"])
                    st.write("Risk Flag:", txn["risk_flag"])
                    st.write("Risk Score:", txn["risk_score"])

                    st.divider()
                    st.markdown("#### Model Probabilities")

                    st.metric(
                        "Random Forest Probability",
                        f"{txn['rf_probability']:.2f}"
                    )

                    st.metric(
                        "Online Model Probability",
                        f"{txn['online_probability']:.2f}"
                    )

                    # -----------------------------------------
                    # SINGLE-CLICK APPROVE / REJECT (FORM FIX)
                    # -----------------------------------------
                    with st.form(
                        key=f"decision_form_{txn['transaction_id']}"
                    ):
                        col1, col2 = st.columns(2)

                        approve = col1.form_submit_button("Approve")
                        reject = col2.form_submit_button("Reject")

                        if approve or reject:
                            decision = (
                                "APPROVE" if approve else "REJECT"
                            )

                            requests.post(
                                f"{BACKEND_URL}/decision",
                                data={
                                    "user_id": txn["user_id"],
                                    "transaction_id": txn["transaction_id"],
                                    "decision": decision
                                }
                            )

                            st.success(
                                f"Transaction {decision.lower()}d"
                            )
                            st.rerun()

                else:
                    st.info("No pending transactions")

            except Exception as e:
                st.error("Unable to load pending requests")
                st.code(str(e))

    st.divider()

    if st.button("Back", key="dashboard_back"):
        st.session_state.page = "user_select"
        st.rerun()
