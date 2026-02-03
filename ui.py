import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION ---
BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank | Adaptive Fraud Guard",
    page_icon="🛡️",
    layout="wide"
)

# --- CUSTOM CSS FOR UI REFINEMENT ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; height: 3em; }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        border: 1px solid #e0e0e0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .risk-SEVERE { color: #dc3545; font-weight: bold; }
    .risk-HIGH { color: #fd7e14; font-weight: bold; }
    .risk-MEDIUM { color: #ffc107; font-weight: bold; }
    .risk-LOW { color: #28a745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "page" not in st.session_state: st.session_state.page = "role"
if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None
if "account_type" not in st.session_state: st.session_state.account_type = None
if "otp_ok" not in st.session_state: st.session_state.otp_ok = False

# --- HELPERS ---
@st.cache_data
def get_users():
    try:
        r = requests.get(f"{BACKEND_URL}/debug/users")
        return r.json() if r.status_code == 200 else []
    except:
        return []

def get_risk_color(flag):
    colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red", "CRITICAL": "red", "SEVERE": "red"}
    return colors.get(flag, "blue")

# --- PAGE 0: ROLE SELECTION ---
if st.session_state.page == "role":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                        padding: 40px; border-radius: 20px; text-align: center; color: white; margin-bottom: 25px;">
                <h1 style='margin:0;'>🛡️ XYZ Bank</h1>
                <p style='opacity: 0.8;'>Adaptive Fraud Detection System</p>
            </div>
            """, unsafe_allow_html=True)
        
        with st.container():
            st.write("### Welcome, please select your access level:")
            role = st.radio("", ["Customer", "Admin"], horizontal=True, label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Continue to Portal"):
                st.session_state.role = role
                st.session_state.page = "user_select"
                st.rerun()

# --- PAGE 1: USER SELECTION ---
elif st.session_state.page == "user_select":
    st.title("🔐 Identity Verification")
    st.write("Please select an active account to continue.")
    
    users = get_users()
    user_map = {f"👤 {u['user_id']} ({u['account_type'].upper()})": u for u in users}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        choice = st.selectbox("Select User Profile", ["-- Select Account --"] + list(user_map.keys()))
    
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
                st.warning("Selection required")
    with c2:
        if st.button("Back to Roles"):
            st.session_state.page = "role"
            st.rerun()

# --- PAGE 2: DASHBOARD ---
elif st.session_state.page == "dashboard":
    # Sidebar Navigation
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=100)
        st.title("Banking Portal")
        st.info(f"**User:** {st.session_state.user}\n\n**Type:** {st.session_state.account_type.upper()}")
        if st.button("Logout"):
            st.session_state.page = "role"
            st.rerun()

    st.title(f"🚀 {st.session_state.role} Dashboard")
    st.divider()

    left, right = st.columns([2, 1.2], gap="large")

    # LEFT: TRANSACTION HISTORY
    with left:
        st.subheader("Transaction History")
        r = requests.get(f"{BACKEND_URL}/history/{st.session_state.user}")
        history = r.json()
        
        if history:
            df = pd.DataFrame(history)
            
            # Summary Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Transactions", len(df))
            m2.metric("Total Spent", f"₹{df['amount'].sum():,.2f}")
            m3.metric("Fraud Alerts", len(df[df['fraud'] == 1]) if 'fraud' in df.columns else 0)

            # Data Table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Fraud Chart
            if "fraud" in df.columns:
                with st.expander("📊 Fraud Trend Analysis"):
                    st.line_chart(df["fraud"])
        else:
            st.info("No transaction history found for this account.")

    # RIGHT: ROLE-SPECIFIC ACTIONS
    with right:
        # CUSTOMER VIEW: CREATE TRANSACTION
        if st.session_state.role == "Customer":
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            st.subheader("New Transaction")
            with st.form("txn_form"):
                amount = st.number_input("Amount (₹)", min_value=1, step=100)
                device = st.selectbox("Transaction Device", ["mobile_1", "mobile_2", "laptop_1", "laptop_9"])
                submitted = st.form_submit_button("Authorize Payment")
                
                if submitted:
                    r = requests.post(f"{BACKEND_URL}/transaction", 
                                      json={"user_id": st.session_state.user, "amount": amount, "device_id": device})
                    resp = r.json()
                    
                    if resp.get("action") == "BLOCK":
                        st.error(f"❌ Transaction Blocked: {resp.get('message')}")
                    elif resp.get("otp_required"):
                        st.warning("⚠️ High Risk Transaction: Verification Required")
                        st.info(f"Your OTP is: **{resp['otp']}**")
                    elif resp.get("action"):
                        st.success(f"✅ Status: {resp['action']}")
            st.markdown('</div>', unsafe_allow_html=True)

        # ADMIN VIEW: DECISION CENTER
        elif st.session_state.role == "Admin":
            st.subheader("Pending Approvals")
            r = requests.get(f"{BACKEND_URL}/pending")
            pending = r.json()
            
            if not pending:
                st.success("Clean Queue: No pending transactions")
            else:
                df_p = pd.DataFrame(pending)
                st.dataframe(df_p[['transaction_id', 'risk_score', 'risk_flag']], use_container_width=True)
                
                st.markdown("---")
                txn_id = st.selectbox("Select Transaction to Review", df_p["transaction_id"])
                txn = df_p[df_p["transaction_id"] == txn_id].iloc[0]

                # Risk Analysis UI
                st.markdown(f"### Reviewing: `{txn_id}`")
                score = txn['risk_score']
                flag = txn['risk_flag']
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Risk Score", score, delta=f"{flag}", delta_color="inverse" if score > 50 else "normal")
                with c2:
                    st.write(f"**RF Prob:** `{round(txn['rf_probability'], 3)}`")
                    st.write(f"**Online Prob:** `{round(txn['online_probability'], 3)}`")

                # OTP Status
                if score > 50:
                    st.markdown('<div style="background:#fff3cd; padding:10px; border-radius:5px;">', unsafe_allow_html=True)
                    st.write("💬 **Verification Required**")
                    otp_input = st.text_input("Enter Customer OTP", key="admin_otp")
                    if st.button("Verify Customer Identity"):
                        v = requests.post(f"{BACKEND_URL}/verify-otp", 
                                          data={"user_id": txn["user_id"], "transaction_id": txn_id, "otp": otp_input})
                        if v.json().get("verified"):
                            st.session_state.otp_ok = True
                            st.success("OTP Verified")
                        else:
                            st.session_state.otp_ok = False
                            st.error("Invalid OTP")
                    st.markdown('</div><br>', unsafe_allow_html=True)
                else:
                    st.session_state.otp_ok = True

                # Decision Buttons
                col_a, col_r = st.columns(2)
                with col_a:
                    if st.button("Approve", type="primary"):
                        if not st.session_state.otp_ok:
                            st.error("Identity verification required")
                        else:
                            requests.post(f"{BACKEND_URL}/decision", 
                                          data={"user_id": txn["user_id"], "transaction_id": txn_id, "decision": "APPROVE"})
                            st.success("Transaction Approved")
                            st.rerun()
                with col_r:
                    if st.button("Reject / Mark Fraud"):
                        requests.post(f"{BACKEND_URL}/decision", 
                                      data={"user_id": txn["user_id"], "transaction_id": txn_id, "decision": "REJECT"})
                        st.warning("Transaction Blocked")
                        st.rerun()

    # Footer back button
    st.divider()
    if st.button("← Change Account"):
        st.session_state.page = "user_select"
        st.rerun()