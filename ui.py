import streamlit as st
import pandas as pd
import requests

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank",
    layout="wide"
)

# --------------------------------------------------
# Session State
# --------------------------------------------------
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

# --------------------------------------------------
# Helpers
# --------------------------------------------------
@st.cache_data
def get_users():
    r = requests.get(f"{BACKEND_URL}/debug/users")
    return r.json() if r.status_code == 200 else []

# --------------------------------------------------
# PAGE 0 – ROLE
# --------------------------------------------------
if st.session_state.page == "role":
    st.markdown(
        """
        <div style="
            background: linear-gradient(90deg,#89f7fe,#66a6ff);
            padding:30px;
            border-radius:15px;
            text-align:center;">
            <h1>XYZ Bank</h1>
            <p>Adaptive Fraud Detection System</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    role = st.radio("Select Role", ["Customer", "Admin"])

    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()

# --------------------------------------------------
# PAGE 1 – USER SELECT
# --------------------------------------------------
elif st.session_state.page == "user":
    st.subheader("Account Selection")

    users = get_users()
    user_map = {
        f"{u['user_id']} ({u['account_type']})": u
        for u in users
    }

    choice = st.selectbox("Select User", ["-- Select --"] + list(user_map.keys()))

    if choice != "-- Select --":
        u = user_map[choice]
        st.session_state.user = u["user_id"]
        st.session_state.account_type = u["account_type"]

    col1, col2 = st.columns(2)

    if col1.button("Proceed"):
        st.session_state.page = "dashboard"
        st.rerun()

    if col2.button("Back"):
        st.session_state.page = "role"
        st.rerun()

# --------------------------------------------------
# PAGE 2 – DASHBOARD
# --------------------------------------------------
elif st.session_state.page == "dashboard":

    user = st.session_state.user
    role = st.session_state.role

    st.title(f"{role} Dashboard")
    st.caption(f"User: {user} | Account Type: {st.session_state.account_type}")
    st.divider()

    left, right = st.columns([2.5, 1.5])

    # --------------------------------------------------
    # LEFT – HISTORY
    # --------------------------------------------------
    with left:
        st.subheader("Transaction History")
        r = requests.get(f"{BACKEND_URL}/history/{user}")
        history = r.json()

        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)

            if "fraud" in df.columns:
                st.subheader("Fraud Trend")
                st.line_chart(df["fraud"])
        else:
            st.info("No transaction history available")

    # --------------------------------------------------
    # RIGHT – ACTIONS
    # --------------------------------------------------
    with right:

        # ==============================
        # CUSTOMER VIEW
        # ==============================
        if role == "Customer":
            st.subheader("New Transaction")

            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox("Device", ["mobile_1", "mobile_2", "laptop_1"])

            if st.button("Submit Transaction"):
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
                    st.success(f"Result: {resp['action']}")
                elif resp.get("otp_required"):
                    st.warning("OTP verification required")
                    st.info(f"OTP sent to user: {resp['otp']}")

        # ==============================
        # ADMIN VIEW
        # ==============================
        else:
            st.subheader("Pending Transactions")

            r = requests.get(f"{BACKEND_URL}/pending")
            pending = r.json()

            if not pending:
                st.success("No pending transactions")
            else:
                df = pd.DataFrame(pending)
                st.dataframe(df, use_container_width=True)

                txn_id = st.selectbox(
                    "Select Transaction",
                    df["transaction_id"]
                )

                txn = df[df["transaction_id"] == txn_id].iloc[0]

                st.markdown("### Risk Analysis")
                st.write("Risk Score:", txn["risk_score"])
                st.write("Risk Level:", txn["risk_flag"])
                st.write("RF Probability:", round(txn["rf_probability"], 3))
                st.write("Online Probability:", round(txn["online_probability"], 3))

                st.divider()

                # OTP SECTION (only when required)
                if txn["risk_score"] > 50:
                    st.subheader("OTP Verification")
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
                        if v.json().get("verified"):
                            st.session_state.otp_ok = True
                            st.success("OTP verified successfully")
                        else:
                            st.session_state.otp_ok = False
                            st.error("Invalid OTP")
                else:
                    st.session_state.otp_ok = True

                st.divider()
                col1, col2 = st.columns(2)

                if col1.button("Approve Transaction") and st.session_state.otp_ok:
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "APPROVE"
                        }
                    )
                    st.success("Transaction approved")
                    st.rerun()

                if col2.button("Reject Transaction") and st.session_state.otp_ok:
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "REJECT"
                        }
                    )
                    st.warning("Transaction rejected")
                    st.rerun()

    st.divider()
    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
