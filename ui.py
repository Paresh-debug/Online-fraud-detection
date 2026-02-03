import streamlit as st
import pandas as pd
import requests

BACKEND_URL = "https://online-fraud-detection-jl8h.onrender.com"

# -------------------------------
# Page config + base styling
# -------------------------------
st.set_page_config(page_title="XYZ Bank – Fraud Detection", layout="wide")

st.markdown(
    """
    <style>
      .app-header {
        background: linear-gradient(90deg,#89f7fe,#66a6ff);
        padding: 20px 22px;
        border-radius: 16px;
        margin-bottom: 14px;
      }
      .app-header h1 { margin: 0; font-size: 30px; }
      .app-header p { margin: 6px 0 0 0; opacity: .9; }
      .card {
        border: 1px solid rgba(49, 51, 63, 0.12);
        border-radius: 14px;
        padding: 14px 16px;
        background: rgba(255,255,255,0.6);
      }
      .muted { opacity: .75; }
      .pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid rgba(49, 51, 63, 0.12);
      }
      .pill.low { background: #e8f7ee; color: #116a35; }
      .pill.medium { background: #fff5db; color: #7a4d00; }
      .pill.high { background: #ffe9df; color: #8a2d0b; }
      .pill.critical { background: #ffe1e1; color: #7a0b0b; }
      .pill.severe { background: #ffd6d6; color: #5b0000; }
      .kpi {
        border: 1px solid rgba(49, 51, 63, 0.12);
        border-radius: 14px;
        padding: 10px 12px;
        background: rgba(255,255,255,0.6);
      }
      .kpi .label { font-size: 12px; opacity: .75; margin-bottom: 4px; }
      .kpi .value { font-size: 18px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Session state
# -------------------------------
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


# -------------------------------
# Helpers
# -------------------------------
@st.cache_data(show_spinner=False)
def get_users():
    r = requests.get(f"{BACKEND_URL}/debug/users")
    if r.status_code != 200:
        return []
    return r.json()


def risk_pill(flag: str) -> str:
    flag_u = (flag or "").upper()
    cls = {
        "LOW": "low",
        "MEDIUM": "medium",
        "HIGH": "high",
        "CRITICAL": "critical",
        "SEVERE": "severe",
    }.get(flag_u, "medium")
    return f'<span class="pill {cls}">{flag_u}</span>'


def top_header():
    st.markdown(
        """
        <div class="app-header">
          <h1>XYZ Bank</h1>
          <p>Adaptive Fraud Detection System</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_context():
    with st.sidebar:
        st.subheader("Session")
        st.write("Role:", st.session_state.role or "—")
        st.write("User:", st.session_state.user or "—")
        st.write("Account:", st.session_state.account_type or "—")
        st.divider()
        if st.session_state.page != "role":
            if st.button("Change role / user"):
                st.session_state.page = "role"
                st.session_state.role = None
                st.session_state.user = None
                st.session_state.account_type = None
                st.session_state.otp_ok = False
                st.rerun()


# ==================================================
# PAGE 0 – ROLE SELECTION
# ==================================================
if st.session_state.page == "role":
    top_header()
    sidebar_context()

    c1, c2, c3 = st.columns([1.2, 1.6, 1.2])
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Select role")
        st.caption("Choose how you want to use the system.")
        role = st.radio("Role", ["Customer", "Admin"], horizontal=True)
        st.write("")
        if st.button("Continue", use_container_width=True):
            st.session_state.role = role
            st.session_state.page = "user_select"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# PAGE 1 – USER SELECTION
# ==================================================
elif st.session_state.page == "user_select":
    top_header()
    sidebar_context()

    st.subheader("Account selection")
    users = get_users()

    if not users:
        st.error("Unable to load users from backend.")
        st.stop()

    user_map = {f"{u['user_id']} ({u['account_type']})": u for u in users}

    c1, c2, c3 = st.columns([1.2, 1.6, 1.2])
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        choice = st.selectbox("Select user", ["-- Select --"] + list(user_map.keys()))
        if choice != "-- Select --":
            selected = user_map[choice]
            st.session_state.user = selected["user_id"]
            st.session_state.account_type = selected["account_type"]
            st.info(f"Selected: {st.session_state.user} ({st.session_state.account_type})")

        colA, colB = st.columns(2)
        if colA.button("Proceed", use_container_width=True):
            if st.session_state.user:
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.warning("Please select a user")

        if colB.button("Back", use_container_width=True):
            st.session_state.page = "role"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# PAGE 2 – DASHBOARD
# ==================================================
elif st.session_state.page == "dashboard":
    top_header()
    sidebar_context()

    user = st.session_state.user
    role = st.session_state.role

    st.markdown(
        f"""
        <div class="card">
          <div class="muted">Logged in as</div>
          <div style="font-size:18px;font-weight:700">{role} Dashboard</div>
          <div class="muted">User: <b>{user}</b> &nbsp;|&nbsp; Account Type: <b>{st.session_state.account_type}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    left, right = st.columns([2.3, 1.2], gap="large")

    # ----------------------------
    # LEFT – HISTORY
    # ----------------------------
    with left:
        st.subheader("Transaction history")

        r = requests.get(f"{BACKEND_URL}/history/{user}")
        history = r.json()

        if not history:
            st.info("No transaction history available.")
        else:
            df = pd.DataFrame(history)

            # A little UI formatting (no logic change)
            preferred = [c for c in ["timestamp", "amount", "device_id", "location", "fraud", "decision", "otp_verified", "block_reason"] if c in df.columns]
            other = [c for c in df.columns if c not in preferred]
            df = df[preferred + other]

            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "amount": st.column_config.NumberColumn(format="₹ %d"),
                    "fraud": st.column_config.NumberColumn(help="1=fraud, 0=not fraud"),
                    "otp_verified": st.column_config.CheckboxColumn(),
                },
            )

            if "fraud" in df.columns:
                st.caption("Fraud trend (based on recorded labels in history)")
                st.line_chart(df.set_index("timestamp")["fraud"] if "timestamp" in df.columns else df["fraud"])

    # ----------------------------
    # RIGHT – ACTIONS
    # ----------------------------
    with right:
        if role == "Customer":
            st.subheader("New transaction")
            st.markdown('<div class="card">', unsafe_allow_html=True)

            amount = st.number_input("Amount", min_value=1, step=100)
            device = st.selectbox("Device", ["mobile_1", "mobile_2", "laptop_1"])

            if st.button("Submit transaction", use_container_width=True):
                r = requests.post(
                    f"{BACKEND_URL}/transaction",
                    json={"user_id": user, "amount": amount, "device_id": device},
                )
                resp = r.json()

                # Same behavior, cleaner output
                if resp.get("action") == "BLOCK":
                    st.error(resp.get("message", "Transaction blocked"))
                elif resp.get("action"):
                    st.success(f"Result: {resp['action']}")
                elif resp.get("otp_required"):
                    st.warning("Transaction sent for verification")
                    st.info(f"OTP sent to user: {resp['otp']}")

            st.markdown("</div>", unsafe_allow_html=True)

        elif role == "Admin":
            st.subheader("Admin console")

            r = requests.get(f"{BACKEND_URL}/pending")
            pending = r.json()

            if not pending:
                st.success("No pending transactions.")
            else:
                df = pd.DataFrame(pending)

                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.caption("Pending queue")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

                txn_id = st.selectbox("Select transaction", df["transaction_id"])
                txn = df[df["transaction_id"] == txn_id].iloc[0]

                # Risk analysis panel (UI only)
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("#### Risk analysis")
                st.markdown(
                    f"""
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                      <div class="kpi" style="min-width:160px;">
                        <div class="label">Risk score</div>
                        <div class="value">{txn["risk_score"]}</div>
                      </div>
                      <div class="kpi" style="min-width:160px;">
                        <div class="label">Risk level</div>
                        <div class="value">{risk_pill(txn["risk_flag"])}</div>
                      </div>
                      <div class="kpi" style="min-width:160px;">
                        <div class="label">RF probability</div>
                        <div class="value">{round(float(txn["rf_probability"]), 3)}</div>
                      </div>
                      <div class="kpi" style="min-width:160px;">
                        <div class="label">Online probability</div>
                        <div class="value">{round(float(txn["online_probability"]), 3)}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                st.divider()

                # OTP SECTION (same condition as your current UI)
                if float(txn["risk_score"]) > 50:
                    st.subheader("OTP verification")
                    otp = st.text_input("Enter OTP", placeholder="6-digit OTP")

                    if st.button("Verify OTP", use_container_width=True):
                        v = requests.post(
                            f"{BACKEND_URL}/verify-otp",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "otp": otp,
                            },
                        )
                        if v.json().get("verified"):
                            st.session_state.otp_ok = True
                            st.success("OTP verified successfully")
                        else:
                            st.session_state.otp_ok = False
                            st.error("Invalid OTP")
                else:
                    # Same behavior: no OTP needed
                    st.session_state.otp_ok = True

                st.divider()

                col1, col2 = st.columns(2)

                # APPROVE → OTP REQUIRED (same logic)
                if col1.button("Approve", use_container_width=True):
                    if not st.session_state.otp_ok:
                        st.error("OTP verification required before approval")
                    else:
                        requests.post(
                            f"{BACKEND_URL}/decision",
                            data={
                                "user_id": txn["user_id"],
                                "transaction_id": txn_id,
                                "decision": "APPROVE",
                            },
                        )
                        st.success("Transaction approved")
                        st.rerun()

                # REJECT → OTP NOT REQUIRED (same logic)
                if col2.button("Reject", use_container_width=True):
                    requests.post(
                        f"{BACKEND_URL}/decision",
                        data={
                            "user_id": txn["user_id"],
                            "transaction_id": txn_id,
                            "decision": "REJECT",
                        },
                    )
                    st.warning("Transaction rejected and marked as fraud")
                    st.rerun()

    st.divider()
    if st.button("Back"):
        st.session_state.page = "user_select"
        st.rerun()