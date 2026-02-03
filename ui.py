import streamlit as st
import pandas as pd
import requests

# --- CONFIGURATION ---
BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

st.set_page_config(
    page_title="XYZ Bank - Fraud Detection",
    layout="wide"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 4px; height: 3em; }
    .status-card {
        padding: 20px;
        border-radius: 8px;
        background-color: white;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-container {
        border-left: 4px solid #0068c9;
        padding-left: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if "page" not in st.session_state: st.session_state.page = "role"
if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None
if "account_type" not in st.session_state: st.session_state.account_type = None
if "otp_ok" not in st.session_state: st.session_state.otp_ok = False

# --- HELPERS ---
@st.cache_data
def get_users_list():
    try:
        r = requests.get(f"{BACKEND_URL}/debug/users")
        return r.json() if r.status_code == 200 else []
    except:
        return []

# --- PAGE 0: ROLE SELECTION ---
if st.session_state.page == "role":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style="background-color: #0e1117; padding: 40px; border-radius: 8px; text-align: center; border: 1px solid #30333d;">
                <h1 style='margin:0; color: white;'>XYZ Bank</h1>
                <p style='color: #a0a0a0;'>Adaptive Fraud Detection System</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("### Select Access Level")
        role = st.radio("Role", ["Customer", "Admin"], label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enter System"):
            st.session_state.role = role
            st.session_state.page = "user_select"
            st.rerun()

# --- PAGE 1: USER SELECTION ---
elif st.session_state.page == "user_select":
    st.title("Account Selection")
    st.write("Select a user profile to proceed.")
    st.divider()

    users = get_users_list()
    user_map = {f"{u['user_id']} | {u['account_type'].upper()}": u for u in users}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        choice = st.selectbox("Available Accounts", ["-- Select --"] + list(user_map.keys()))
    
    st.write("")
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button("Proceed"):
            if choice != "-- Select --":
                selected = user_map[choice]
                st.session_state.user = selected["user_id"]
                st.session_state.account_type = selected["account_type"]
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.warning("Please select a valid account.")
    with c2:
        if st.button("Back"):
            st.session_state.page = "role"
            st.rerun()

# --- PAGE 2: DASHBOARD ---
elif st.session_state.page == "dashboard":
    
    # Sidebar Info
    with st.sidebar:
        st.header("Session Info")
        st.text(f"Role: {st.session_state.role}")
        
        # Only show logged-in user info if NOT admin (Admins view everyone)
        if st.session_state.role == "Customer":
            st.text(f"User: {st.session_state.user}")
            st.text(f"Type: {st.session_state.account_type.upper()}")
            
        st.divider()
        if st.button("Logout"):
            st.session_state.page = "role"
            st.rerun()
        if st.button("Change Account"):
            st.session_state.page = "user_select"
            st.rerun()

    st.title(f"{st.session_state.role} Dashboard")

    # --- CUSTOMER VIEW ---
    if st.session_state.role == "Customer":
        left, right = st.columns([2, 1], gap="large")
        
        # LEFT: HISTORY
        with left:
            st.subheader("Transaction History")
            r = requests.get(f"{BACKEND_URL}/history/{st.session_state.user}")
            history = r.json()
            
            if history:
                df = pd.DataFrame(history)
                m1, m2 = st.columns(2)
                m1.metric("Total Transactions", len(df))
                m2.metric("Total Volume", f"{df['amount'].sum():,.2f}")
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                if "fraud" in df.columns:
                    st.caption("Fraud Probability Trend")
                    st.line_chart(df["fraud"])
            else:
                st.info("No transaction history available.")

        # RIGHT: NEW TRANSACTION
        with right:
            st.subheader("New Transaction")
            with st.form("txn_form"):
                amount = st.number_input("Amount", min_value=1, step=100)
                device = st.selectbox("Device ID", ["mobile_1", "mobile_2", "laptop_1", "desktop_1"])
                submit = st.form_submit_button("Submit Transaction")
                
                if submit:
                    r = requests.post(f"{BACKEND_URL}/transaction", 
                                      json={"user_id": st.session_state.user, 
                                            "amount": amount, 
                                            "device_id": device})
                    resp = r.json()
                    
                    if resp.get("action") == "BLOCK":
                        st.error(f"Transaction Blocked: {resp.get('message')}")
                    elif resp.get("otp_required"):
                        st.warning("Verification Required")
                        st.info(f"OTP Sent: {resp['otp']}")
                    elif resp.get("action"):
                        st.success(f"Status: {resp['action']}")

    # --- ADMIN VIEW ---
    elif st.session_state.role == "Admin":
        
        # Define Tabs
        tab_monitor, tab_approvals = st.tabs(["User Monitoring", "Pending Approvals"])

        # TAB 1: User Monitoring (FIXED: Added Dropdown)
        with tab_monitor:
            col_sel, _ = st.columns([1, 2])
            
            # Fetch all users to populate the admin dropdown
            all_users_data = get_users_list()
            all_user_ids = [u['user_id'] for u in all_users_data]
            
            # Determine default index based on previous selection if possible
            try:
                curr_idx = all_user_ids.index(st.session_state.user)
            except (ValueError, TypeError):
                curr_idx = 0
            
            with col_sel:
                monitor_user = st.selectbox("Select User to Monitor", all_user_ids, index=curr_idx)

            st.divider()
            st.subheader(f"History for {monitor_user}")
            
            # Fetch history for the dynamically selected user, NOT the session user
            r = requests.get(f"{BACKEND_URL}/history/{monitor_user}")
            history = r.json()
            
            if history:
                df_h = pd.DataFrame(history)
                st.dataframe(df_h, use_container_width=True)
                if "fraud" in df_h.columns:
                    st.line_chart(df_h["fraud"])
            else:
                st.info(f"No history found for {monitor_user}.")

        # TAB 2: Pending Approvals
        with tab_approvals:
            st.subheader("Pending Transaction Queue")
            
            r = requests.get(f"{BACKEND_URL}/pending")
            pending = r.json()
            
            if not pending:
                st.success("No pending transactions requiring review.")
            else:
                df_p = pd.DataFrame(pending)
                st.dataframe(df_p[['transaction_id', 'user_id', 'risk_score', 'risk_flag']], use_container_width=True)
                
                st.divider()
                
                # Decision Interface
                col_select, col_details = st.columns([1, 2])
                
                with col_select:
                    st.markdown("##### Select Transaction")
                    txn_id = st.selectbox("Transaction ID", df_p["transaction_id"])
                
                if txn_id:
                    txn = df_p[df_p["transaction_id"] == txn_id].iloc[0]
                    
                    with col_details:
                        st.markdown(f"##### Reviewing: {txn_id} (User: {txn['user_id']})")
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Risk Score", txn['risk_score'])
                        m2.metric("RF Probability", round(txn['rf_probability'], 3))
                        m3.metric("Online Probability", round(txn['online_probability'], 3))
                        
                        st.text(f"Risk Level: {txn['risk_flag']}")

                        # OTP Logic
                        if txn['risk_score'] > 50:
                            st.markdown("---")
                            st.warning("High Risk - OTP Verification Required")
                            
                            c_otp1, c_otp2 = st.columns([2, 1])
                            with c_otp1:
                                otp_input = st.text_input("Enter OTP provided by customer")
                            with c_otp2:
                                st.write("")
                                st.write("") 
                                if st.button("Verify OTP"):
                                    v = requests.post(f"{BACKEND_URL}/verify-otp", 
                                                      data={"user_id": txn["user_id"], 
                                                            "transaction_id": txn_id, 
                                                            "otp": otp_input})
                                    if v.json().get("verified"):
                                        st.session_state.otp_ok = True
                                        st.success("OTP Verified")
                                    else:
                                        st.session_state.otp_ok = False
                                        st.error("Invalid OTP")
                        else:
                            st.session_state.otp_ok = True

                        st.markdown("---")
                        
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("Approve Transaction", type="primary"):
                                if not st.session_state.otp_ok:
                                    st.error("Cannot approve: OTP verification required.")
                                else:
                                    requests.post(f"{BACKEND_URL}/decision", 
                                                  data={"user_id": txn["user_id"], 
                                                        "transaction_id": txn_id, 
                                                        "decision": "APPROVE"})
                                    st.success("Transaction Approved")
                                    st.rerun()
                        
                        with btn_col2:
                            if st.button("Reject (Mark as Fraud)"):
                                requests.post(f"{BACKEND_URL}/decision", 
                                              data={"user_id": txn["user_id"], 
                                                    "transaction_id": txn_id, 
                                                    "decision": "REJECT"})
                                st.warning("Transaction Rejected")
                                st.rerun()