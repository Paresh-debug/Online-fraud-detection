import streamlit as st
import pandas as pd
import requests
import json

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="XYZ Bank | Fraud Detection",
    layout="wide"
)

# --------------------------------------------------
# Custom CSS – Soft Mesh Background
# --------------------------------------------------
st.markdown("""
<style>
body {
    background:
        radial-gradient(circle at 20% 20%, #e9f0ff 0%, transparent 40%),
        radial-gradient(circle at 80% 0%, #f3e8ff 0%, transparent 35%),
        radial-gradient(circle at 50% 80%, #ecfeff 0%, transparent 40%),
        #f8fafc;
}

.block-container { padding-top: 2rem; }

.card {
    background: rgba(255,255,255,0.95);
    padding: 1.4rem;
    border-radius: 16px;
    box-shadow: 0 12px 28px rgba(0,0,0,0.08);
    margin-bottom: 1.2rem;
}

.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
    color: #0f172a;
}

.subtitle { color: #475569; }

.risk-low { color: #16a34a; font-weight: 600; }
.risk-medium { color: #ca8a04; font-weight: 600; }
.risk-high { color: #ea580c; font-weight: 600; }
.risk-severe { color: #dc2626; font-weight: 700; }

.stButton>button {
    border-radius: 10px;
    padding: 0.6rem;
    font-weight: 600;
    background: linear-gradient(90deg, #6366f1, #3b82f6);
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Load users
# --------------------------------------------------
@st.cache_data
def load_users():
    with open("user_transactions.json") as f:
        data = json.load(f)
    return sorted(u["user_id"] for u in data["users"])

users = load_users()

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "role"
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None

# ==================================================
# ROLE SELECTION
# ==================================================
if st.session_state.page == "role":
    st.markdown("<h1 style='text-align:center'>XYZ Bank</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle' style='text-align:center'>Adaptive Fraud Detection Platform</p>",
        unsafe_allow_html=True
    )

    role = st.radio("Select Role", ["Customer", "Admin"], horizontal=True)

    if st.button("Continue"):
        st.session_state.role = role
        st.session_state.page = "user"
        st.rerun()

# ==================================================
# USER SELECTION
# ==================================================
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

# ==================================================
# DASHBOARD
# ==================================================
elif st.session_state.page == "dashboard":
    user = st.session_state.user
    role = st.session_state.role

    st.markdown(f"<h2>{role} Dashboard</h2>", unsafe_allow_html=True)
    st.markdown(f"<p class='subtitle'>Account ID: {user}</p>", unsafe_allow_html=True)

    left, right = st.columns([2.6, 1.4])

    # --------------------------------------------------
    # LEFT – HISTORY + GRAPHS
    # --------------------------------------------------
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
            st.info("No transaction history")

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # RIGHT – ACTION PANEL
    # --------------------------------------------------
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        # ======================
        # CUSTOMER VIEW
        # ======================
        if role == "Customer":
            st.markdown("<div class='section-title'>New Transaction</div>", unsafe_allow_html=True)

            amount = st.number_input("Transaction Amount", min_value=1)
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

                st.success("Transaction submitted")

                if resp.get("otp_required"):
                    st.info(
                        f"OTP for this transaction: {resp['otp']} "
                        "(share this OTP with the admin)"
                    )

        # ======================
        # ADMIN VIEW
        # ======================
        else:
            st.markdown("<div class='section-title'>Pending Transactions</div>", unsafe_allow_html=True)

            res = requests.get(f"{BACKEND_URL}/pending")
            pending = res.json()

            if pending:
                df = pd.DataFrame(pending)
                st.dataframe(df, use_container_width=True)

                txn_id = st.selectbox("Transaction ID", df["transaction_id"])
                txn = df[df["transaction_id"] == txn_id].iloc[0]

                flag = txn["risk_flag"]
                flag_class = (
                    "risk-low" if flag == "LOW" else
                    "risk-medium" if flag == "MEDIUM" else
                    "risk-high" if flag in ["HIGH", "CRITICAL"] else
                    "risk-severe"
                )

                st.markdown(f"""
                <p><strong>Risk Score:</strong> {txn["risk_score"]}</p>
                <p><strong>Risk Flag:</strong> <span class="{flag_class}">{flag}</span></p>
                <p><strong>RF Probability:</strong> {txn["rf_probability"]}</p>
                <p><strong>Online Probability:</strong> {txn["online_probability"]}</p>
                """, unsafe_allow_html=True)

                # ---------- OTP ----------
                otp_verified = txn["otp_verified"]
                otp_required = txn["otp_required"]

                if otp_required and not otp_verified:
                    otp_input = st.text_input("Enter OTP provided by user", type="password")

                    if st.button("Verify OTP"):
                        vr = requests.post(
                            f"{BACKEND_URL}/verify-otp",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "otp": otp_input
                            }
                        )
                        if vr.json().get("verified"):
                            st.success("OTP verified")
                            st.rerun()
                        else:
                            st.error("Invalid OTP")

                st.divider()

                approve_disabled = otp_required and not otp_verified

                col1, col2 = st.columns(2)
                if col1.button("Approve", disabled=approve_disabled):
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

                if col2.button("Reject"):
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

            else:
                st.info("No pending transactions")

        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Back"):
        st.session_state.page = "user"
        st.rerun()
