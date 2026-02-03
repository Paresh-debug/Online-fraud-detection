import streamlit as st
import pandas as pd
import requests

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank – Fraud Detection",
    layout="wide"
)

# -------------------------------------------------
# Session State
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"

if "role" not in st.session_state:
    st.session_state.role = None

if "user" not in st.session_state:
    st.session_state.user = None

if "otp_ok" not in st.session_state:
    st.session_state.otp_ok = False

# -------------------------------------------------
# Utilities
# -------------------------------------------------
@st.cache_data
def get_users():
    res = requests.get(f"{BACKEND_URL}/debug/users")
    if res.status_code != 200:
        return []
    return [u["user_id"] for u in res.json()]

# -------------------------------------------------
# PAGE 0 – ROLE
# -------------------------------------------------
if st.session_state.page == "role":
    st.markdown(
        """
        <div style="background:linear-gradient(90deg,#89f7fe,#66a6ff);
                    padding:30px;border-radius:12px;">
        <h1 style="text-align:center;">XYZ Bank</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    role = st.radio("Select Role", ["Customer", "Admin"])

    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()

# -------------------------------------------------
# PAGE 1 – USER SELECT
# -------------------------------------------------
elif st.session_state.page == "user":
    users = get_users()
    user = st.selectbox("User ID", ["-- Select --"] + users)

    c1, c2 = st.columns(2)

    if user != "-- Select --" and c1.button("Proceed"):
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()

    if c2.button("Back"):
        st.session_state.page = "role"
        st.rerun()

# -------------------------------------------------
# PAGE 2 – DASHBOARD
# -------------------------------------------------
elif st.session_state.page == "dashboard":

    user = st.session_state.user
    role = st.session_state.role

    st.title(f"{role} Dashboard")
    st.caption(f"Account: {user}")
    st.divider()

    left, right = st.columns([2.5, 1.5])

    # ---------------------------------------------
    # HISTORY
    # ---------------------------------------------
    with left:
        res = requests.get(f"{BACKEND_URL}/history/{user}")
        history = res.json()

        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)

            if "fraud" in df.columns:
                st.subheader("Fraud Trend")
                st.line_chart(df["fraud"])
        else:
            st.info("No transactions found")

    # ---------------------------------------------
    # ACTIONS
    # ---------------------------------------------
    with right:

        # CUSTOMER
        if role == "Customer":
            st.subheader("New Transaction")
            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox("Device", ["mobile_1","mobile_2","laptop_1"])

            if st.button("Submit"):
                res = requests.post(
                    f"{BACKEND_URL}/transaction",
                    json={
                        "user_id": user,
                        "amount": amount,
                        "device_id": device
                    }
                )
                r = res.json()

                if "action" in r:
                    st.success(f"Action: {r['action']}")
                elif r.get("otp_required"):
                    st.warning("OTP verification required")
                    st.info(f"OTP: {r['otp']}")

        # ADMIN
        else:
            st.subheader("Pending Transactions")
            res = requests.get(f"{BACKEND_URL}/pending")
            pending = res.json()

            if not pending:
                st.info("No pending transactions")
            else:
                df = pd.DataFrame(pending)
                st.dataframe(df, use_container_width=True)

                txn_id = st.selectbox("Transaction ID", df["transaction_id"])
                txn = df[df["transaction_id"] == txn_id].iloc[0]

                st.write("Risk Score:", txn["risk_score"])
                st.write("Risk Level:", txn["risk_flag"])
                st.write("RF Probability:", round(txn["rf_probability"],3))
                st.write("Online Probability:", round(txn["online_probability"],3))

                if txn["risk_score"] > 50:
                    otp = st.text_input("Enter OTP")

                    if st.button("Verify OTP"):
                        v = requests.post(
                            f"{BACKEND_URL}/verify-otp",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "otp": otp
                            }
                        )
                        st.session_state.otp_ok = v.json().get("verified", False)

                else:
                    st.session_state.otp_ok = True

                c1, c2 = st.columns(2)
                if c1.button("Approve") and st.session_state.otp_ok:
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "APPROVE"
                        }
                    )
                    st.success("Approved")
                    st.rerun()

                if c2.button("Reject") and st.session_state.otp_ok:
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "REJECT"
                        }
                    )
                    st.warning("Rejected")
                    st.rerun()

    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
