
import streamlit as st
import pandas as pd
import requests

# --- CONFIGURATION ---
BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank | Adaptive Fraud Guard",
    layout="wide"
)

# --- CUSTOM CSS FOR UI REFINEMENT ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3em; }
    .status-card {
        padding: 18px;
        border-radius: 12px;
        background-color: white;
        border: 1px solid #e6e6e6;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.04);
    }
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 0.25rem 0;
    }
    .muted {
        color: rgba(0,0,0,0.6);
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
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

# --- HELPERS ---
@st.cache_data
def get_users():
    try:
        r = requests.get(f"{BACKEND_URL}/debug/users")
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {}

# --- PAGE 0: ROLE SELECTION ---
if st.session_state.page == "role":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                padding: 40px; border-radius: 18px; text-align: center; color: white; margin-bottom: 20px;">
                <h1 style="margin:0;">XYZ Bank</h1>
                <p style="opacity:0.85; margin: 8px 0 0 0;">Adaptive Fraud Detection System</p>
            </div>
        """, unsafe_allow_html=True)

        st.write("Select access level")
        role = st.radio("", ["Customer", "Admin"], horizontal=True, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Continue"):
            st.session_state.role = role
            st.session_state.page = "user_select"
            st.rerun()

# --- PAGE 1: USER SELECTION ---
elif st.session_state.page == "user_select":
    st.title("Account Selection")
    st.caption("Select an account to continue")

    users = get_users()
    user_map = {f"{u['user_id']} ({u['account_type']})": u for u in users}

    choice = st.selectbox("User", ["-- Select Account --"] + list(user_map.keys()))

    st.divider()
    c1, c2, _ = st.columns([1, 1, 2])

    with c1:
        if st.button("Proceed"):
            if choice != "-- Select Account --":
                selected = user_map[choice]
                st.session_state.user = selected["user_id"]
                st.session_state.account_type = selected["account_type"]
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.warning("Please select an account")

    with c2:
        if st.button("Back"):
            st.session_state.page = "role"
            st.rerun()

# --- PAGE 2: DASHBOARD ---
elif st.session_state.page == "dashboard":
    # Sidebar
    with st.sidebar:
        st.title("Bank Portal")
        st.info(
            f"User: {st.session_state.user}\n\n"
            f"Account Type: {str(st.session_state.account_type).upper()}"
        )
        if st.button("Logout"):
            st.session_state.page = "role"
            st.rerun()

    st.title(f"{st.session_state.role} Dashboard")
    st.divider()

    left, right = st.columns([2, 1.2], gap="large")

    # LEFT: TRANSACTION HISTORY
    with left:
        st.subheader("Transaction History")
        r = requests.get(f"{BACKEND_URL}/history/{st.session_state.user}")
        history = safe_json(r)

        if history:
            df = pd.DataFrame(history)

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Transactions", len(df))
            m2.metric("Total Spent", f"{df['amount'].sum():,.2f}" if "amount" in df.columns else "0")
            if "fraud" in df.columns:
                m3.metric("Fraud Alerts", int((df["fraud"] == 1).sum()))
            else:
                m3.metric("Fraud Alerts", 0)

            st.dataframe(df, use_container_width=True, hide_index=True)

            if "fraud" in df.columns:
                with st.expander("Fraud Trend"):
                    st.line_chart(df["fraud"])
        else:
            st.info("No transaction history found for this account")

    # RIGHT: ROLE-SPECIFIC ACTIONS
    with right:
        # CUSTOMER VIEW
        if st.session_state.role == "Customer":
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">New Transaction</div>', unsafe_allow_html=True)
            st.markdown('<div class="muted">Submit a transaction for risk evaluation</div>', unsafe_allow_html=True)
            st.write("")

            with st.form("txn_form"):
                amount = st.number_input("Amount", min_value=1, step=100)
                device = st.selectbox("Device", ["mobile_1", "mobile_2", "laptop_1", "laptop_9"])
                submitted = st.form_submit_button("Submit Transaction")

                if submitted:
                    r = requests.post(
                        f"{BACKEND_URL}/transaction",
                        json={
                            "user_id": st.session_state.user,
                            "amount": amount,
                            "device_id": device
                        }
                    )
                    resp = safe_json(r)

                    if resp.get("action") == "BLOCK":
                        st.error(resp.get("message", "Transaction blocked"))
                    elif resp.get("otp_required"):
                        st.warning("Transaction sent for verification")
                        st.info(f"OTP sent to user: {resp.get('otp')}")
                    elif resp.get("action"):
                        st.success(f"Result: {resp['action']}")
                    else:
                        st.info("Unexpected response from server")

            st.markdown("</div>", unsafe_allow_html=True)

        # ADMIN VIEW
        elif st.session_state.role == "Admin":
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Admin Actions</div>', unsafe_allow_html=True)
            st.markdown('<div class="muted">Review and approve or reject high-risk transactions</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.write("")

            # Separate section: Pending Approvals (full width below history/actions)
            st.info("Pending approvals are shown in a separate section below.")

    # SEPARATE SECTION: PENDING APPROVALS (ADMIN ONLY)
    if st.session_state.role == "Admin":
        st.divider()
        st.subheader("Pending Approvals")

        # Two-column section: left list, right review panel
        p_left, p_right = st.columns([1.35, 1], gap="large")

        r = requests.get(f"{BACKEND_URL}/pending")
        pending = safe_json(r)

        if not pending:
            st.success("No pending transactions")
        else:
            dfp = pd.DataFrame(pending)

            with p_left:
                st.markdown('<div class="status-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">Queue</div>', unsafe_allow_html=True)
                st.markdown('<div class="muted">Select a transaction to review</div>', unsafe_allow_html=True)
                st.write("")
                st.dataframe(
                    dfp[["transaction_id", "user_id", "risk_score", "risk_flag", "otp_verified"]],
                    use_container_width=True,
                    hide_index=True
                )
                st.write("")
                txn_id = st.selectbox("Transaction", dfp["transaction_id"].tolist())
                st.markdown("</div>", unsafe_allow_html=True)

            txn = dfp[dfp["transaction_id"] == txn_id].iloc[0]

            with p_right:
                st.markdown('<div class="status-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">Review</div>', unsafe_allow_html=True)
                st.caption(f"Transaction ID: {txn_id}")

                st.metric("Risk Score", float(txn["risk_score"]))
                st.write("Risk Level:", txn["risk_flag"])
                st.write("RF Probability:", round(float(txn["rf_probability"]), 3))
                st.write("Online Probability:", round(float(txn["online_probability"]), 3))
                st.write("OTP Verified:", bool(txn["otp_verified"]))
                st.divider()

                # OTP SECTION (only when required per original logic: score > 50)
                if float(txn["risk_score"]) > 50:
                    st.markdown('<div class="section-title">OTP Verification</div>', unsafe_allow_html=True)
                    otp = st.text_input("Enter OTP", key="otp_input")

                    if st.button("Verify OTP"):
                        v = requests.post(
                            f"{BACKEND_URL}/verify-otp",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "otp": otp
                            }
                        )
                        if safe_json(v).get("verified"):
                            st.session_state.otp_ok = True
                            st.success("OTP verified successfully")
                        else:
                            st.session_state.otp_ok = False
                            st.error("Invalid OTP")
                else:
                    st.session_state.otp_ok = True

                st.divider()
                col1, col2 = st.columns(2)

                # APPROVE -> OTP REQUIRED
                if col1.button("Approve Transaction"):
                    if not st.session_state.otp_ok:
                        st.error("OTP verification required before approval")
                    else:
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

                # REJECT -> OTP NOT REQUIRED
                if col2.button("Reject Transaction"):
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "REJECT"
                        }
                    )
                    st.warning("Transaction rejected and marked as fraud")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    if st.button("Back"):
        st.session_state.page = "user_select"
        st.rerun()