import streamlit as st
import pandas as pd
import requests
import json

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="XYZ Bank | Fraud Detection",
    layout="wide"
)

# -----------------------------
# Custom CSS (beautification)
# -----------------------------
st.markdown("""
<style>
body {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 2rem;
}

h1, h2, h3 {
    color: #1f2a44;
}

.card {
    background-color: white;
    padding: 1.2rem;
    border-radius: 12px;
    box-shadow: 0px 4px 14px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1f2a44;
    margin-bottom: 0.5rem;
}

.stButton>button {
    width: 100%;
    border-radius: 8px;
    padding: 0.6rem;
    font-weight: 600;
}

.approve button {
    background-color: #2e7d32;
    color: white;
}

.reject button {
    background-color: #c62828;
    color: white;
}

.small-text {
    font-size: 0.85rem;
    color: #6b7280;
}
</style>
""", unsafe_allow_html=True)

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
# Session state
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

# ======================================================
# ROLE SELECTION
# ======================================================
if st.session_state.page == "role":
    st.markdown("<h1 style='text-align:center'>XYZ Bank</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#6b7280'>Fraud Detection Platform</p>", unsafe_allow_html=True)

    st.write("")
    st.write("")

    role = st.radio("Select Access Role", ["Customer", "Admin"], horizontal=True)

    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()

# ======================================================
# USER SELECTION
# ======================================================
elif st.session_state.page == "user":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Account Selection</div>", unsafe_allow_html=True)

    user = st.selectbox("User ID", users)

    col1, col2 = st.columns(2)

    if col1.button("Proceed"):
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()

    if col2.button("Back"):
        st.session_state.page = "role"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# DASHBOARD
# ======================================================
elif st.session_state.page == "dashboard":
    user = st.session_state.user
    role = st.session_state.role

    st.markdown(f"<h2>{role} Dashboard</h2>", unsafe_allow_html=True)
    st.markdown(f"<p class='small-text'>Account ID: {user}</p>", unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([2.7, 1.3])

    # -----------------------------
    # LEFT – HISTORY + GRAPHS
    # -----------------------------
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Transaction History</div>", unsafe_allow_html=True)

        res = requests.get(f"{BACKEND_URL}/history/{user}")
        history = res.json()

        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)

            if "amount" in df.columns:
                st.markdown("<div class='section-title'>Amount Trend</div>", unsafe_allow_html=True)
                st.line_chart(df["amount"])

            if "fraud" in df.columns:
                st.markdown("<div class='section-title'>Fraud Decisions</div>", unsafe_allow_html=True)
                st.line_chart(df["fraud"])
        else:
            st.info("No transaction history available")

        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------
    # RIGHT – ACTION PANEL
    # -----------------------------
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        # CUSTOMER
        if role == "Customer":
            st.markdown("<div class='section-title'>New Transaction</div>", unsafe_allow_html=True)

            amount = st.number_input("Transaction Amount", min_value=1)
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
                st.success("Transaction submitted for evaluation")

        # ADMIN
        else:
            st.markdown("<div class='section-title'>Pending Transactions</div>", unsafe_allow_html=True)

            res = requests.get(f"{BACKEND_URL}/pending")
            pending = res.json()

            if pending:
                df = pd.DataFrame(pending)
                st.dataframe(df, use_container_width=True)

                txn_id = st.selectbox("Select Transaction", df["transaction_id"])
                txn = df[df["transaction_id"] == txn_id].iloc[0]

                st.markdown("<hr>", unsafe_allow_html=True)
                st.write("Risk Score:", txn["risk_score"])
                st.write("Risk Flag:", txn["risk_flag"])
                st.write("RF Probability:", txn["rf_probability"])
                st.write("Online Probability:", txn["online_probability"])

                with st.form("decision_form"):
                    col1, col2 = st.columns(2)

                    approve = col1.form_submit_button("Approve")
                    reject = col2.form_submit_button("Reject")

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

        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
