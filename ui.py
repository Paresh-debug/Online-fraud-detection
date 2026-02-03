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

# -------------------------------------------------
# Utility
# -------------------------------------------------
def get_users():
    res = requests.get(f"{BACKEND_URL}/debug/users")
    return res.json() if res.status_code == 200 else []

# -------------------------------------------------
# PAGE 0 – ROLE SELECTION
# -------------------------------------------------
if st.session_state.page == "role":
    st.markdown(
        """
        <div style="background: linear-gradient(90deg,#6dd5fa,#ffffff);
                    padding:30px;border-radius:10px;">
        <h1 style="text-align:center;">XYZ Bank</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("Access Role")
    role = st.radio("Select role", ["Customer", "Admin"])

    if st.button("Continue", key="role_continue"):
        st.session_state.role = role
        st.session_state.page = "user_select"
        st.rerun()

# -------------------------------------------------
# PAGE 1 – USER SELECTION
# -------------------------------------------------
elif st.session_state.page == "user_select":
    st.title("Account Selection")

    users = get_users()
    user = st.selectbox("User ID", ["-- Select --"] + users)

    c1, c2 = st.columns(2)

    if user != "-- Select --" and c1.button("Proceed", key="user_proceed"):
        st.session_state.user = user
        st.session_state.page = "dashboard"
        st.rerun()

    if c2.button("Back", key="user_back"):
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
    # LEFT – TRANSACTION HISTORY
    # ---------------------------------------------
    with left:
        st.subheader("Transaction History")

        try:
            res = requests.get(f"{BACKEND_URL}/history/{user}")
            history = res.json()

            if history:
                df = pd.DataFrame(history)
                st.dataframe(df, use_container_width=True)

                if "fraud" in df.columns:
                    st.subheader("Fraud Trend")
                    st.line_chart(df["fraud"])
            else:
                st.info("No transactions available")

        except:
            st.error("Unable to load history")

    # ---------------------------------------------
    # RIGHT – CUSTOMER / ADMIN
    # ---------------------------------------------
    with right:

        # =============================
        # CUSTOMER
        # =============================
        if role == "Customer":
            st.subheader("New Transaction")

            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox("Device", ["mobile_1", "mobile_2", "laptop_1"])

            if st.button("Submit Transaction", key="submit_txn"):
                payload = {
                    "user_id": user,
                    "amount": amount,
                    "device_id": device
                }

                res = requests.post(f"{BACKEND_URL}/transaction", json=payload)
                resp = res.json()

                if "action" in resp:
                    if resp["action"] == "APPROVE":
                        st.success("Transaction approved automatically")
                    elif resp["action"] == "APPROVE_MONITOR":
                        st.warning("Approved but under monitoring")
                    elif resp["action"] == "BLOCK":
                        st.error("Transaction blocked due to high risk")

                elif resp.get("otp_required"):
                    st.warning("Transaction sent for verification (OTP required)")
                    st.info(f"OTP sent to user: {resp['otp']}")

                else:
                    st.error("Transaction failed")

        # =============================
        # ADMIN
        # =============================
        else:
            st.subheader("Pending Transactions")

            try:
                res = requests.get(f"{BACKEND_URL}/pending")
                pending = res.json()

                if not pending:
                    st.info("No pending transactions")
                else:
                    df = pd.DataFrame(pending)
                    st.dataframe(df, use_container_width=True)

                    txn_id = st.selectbox(
                        "Select Transaction",
                        df["transaction_id"],
                        key="txn_select"
                    )

                    txn = df[df["transaction_id"] == txn_id].iloc[0]

                    st.markdown("### Risk Analysis")
                    st.write("Risk Score:", txn["risk_score"])
                    st.write("Risk Level:", txn["risk_flag"])
                    st.write("RF Probability:", round(txn["rf_probability"], 3))
                    st.write("Online Probability:", round(txn["online_probability"], 3))

                    # OTP REQUIRED FOR HIGH / CRITICAL
                    if txn["risk_score"] > 50:
                        st.subheader("OTP Verification")

                        otp = st.text_input("Enter OTP", key="otp_input")

                        if st.button("Verify OTP", key="verify_otp"):
                            r = requests.post(
                                f"{BACKEND_URL}/verify-otp",
                                data={
                                    "user_id": txn["user_id"],
                                    "transaction_id": txn_id,
                                    "otp": otp
                                }
                            )
                            if r.json().get("verified"):
                                st.success("OTP verified")
                                st.session_state.otp_ok = True
                            else:
                                st.error("Invalid OTP")
                                st.session_state.otp_ok = False
                    else:
                        st.session_state.otp_ok = True

                    st.divider()
                    c1, c2 = st.columns(2)

                    if c1.button("Approve", key="approve_btn") and st.session_state.get("otp_ok"):
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

                    if c2.button("Reject", key="reject_btn") and st.session_state.get("otp_ok"):
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

            except Exception as e:
                st.error("Unable to load pending requests")

    st.divider()

    if st.button("Back", key="dashboard_back"):
        st.session_state.page = "user_select"
        st.rerun()
