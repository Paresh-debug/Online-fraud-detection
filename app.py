from fastapi import FastAPI, Form
import json, random
import numpy as np
from datetime import datetime

from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Risk-Aware Fraud Detection")

DATA_FILE = "user_transactions.json"

# -------------------------------------------------
# Load & Save
# -------------------------------------------------
def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

data = load_data()
users = {u["user_id"]: u for u in data.get("users", [])}

# -------------------------------------------------
# Risk Levels
# -------------------------------------------------
def get_risk_flag(score):
    if score <= 20: return "LOW"
    if score <= 40: return "MEDIUM"
    if score <= 60: return "HIGH"
    if score <= 80: return "CRITICAL"
    return "SEVERE"

# -------------------------------------------------
# Transaction Evaluation
# -------------------------------------------------
@app.post("/transaction")
def evaluate_transaction(txn: dict):

    user_id = txn["user_id"]
    user = users[user_id]

    user.setdefault("history", [])
    user.setdefault("pending", {})
    user.setdefault("profile", {"avg_amount": txn["amount"]})

    transaction = {
        "amount": txn["amount"],
        "device_id": txn["device_id"],
        "location": "INDIA",
        "timestamp": datetime.utcnow().isoformat()
    }

    features = extract_features(transaction, user)

    X_rf = np.array([[features[k] for k in [
        "amount","txn_velocity","device_change",
        "location_change","amount_ratio",
        "account_amount_flag","rapid_txn"
    ]]])

    rf_prob = float(rf_model.predict_proba(X_rf)[0][1])

    online_prob = float(
        online_model.predict_proba_one(
            {k:v for k,v in features.items() if not k.startswith("_")}
        ).get(1, 0)
    )

    risk_score = (0.6 * online_prob + 0.4 * rf_prob) * 100

    # Rule-based boosts
    avg = user["profile"]["avg_amount"]
    if txn["amount"] > avg * 3: risk_score += 10
    if txn["amount"] % 10 != 0: risk_score += 5
    if features["location_change"] == 1: risk_score += 10

    risk_score = round(min(risk_score, 100), 2)
    risk_flag = get_risk_flag(risk_score)

    txn_id = f"{user_id}_{len(user['history']) + len(user['pending'])}"

    # -------------------------------------------------
    # Risk Policy Enforcement
    # -------------------------------------------------
    otp = None
    auto_action = None

    if risk_flag == "LOW":
        auto_action = "APPROVE"
    elif risk_flag == "MEDIUM":
        auto_action = "APPROVE_MONITOR"
    elif risk_flag in ["HIGH", "CRITICAL"]:
        otp = random.randint(100000, 999999)
    elif risk_flag == "SEVERE":
        auto_action = "BLOCK"

    if auto_action:
        transaction["fraud"] = 1 if auto_action == "BLOCK" else 0
        user["history"].append(transaction)
        save_data(data)

        return {
            "transaction_id": txn_id,
            "risk_score": risk_score,
            "risk_flag": risk_flag,
            "action": auto_action
        }

    # Pending for admin
    user["pending"][txn_id] = {
        "transaction": transaction,
        "features": features,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "rf_probability": rf_prob,
        "online_probability": online_prob,
        "otp": otp,
        "otp_verified": False
    }

    save_data(data)

    return {
        "transaction_id": txn_id,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "otp_required": True,
        "otp": otp
    }

# -------------------------------------------------
# OTP Verification
# -------------------------------------------------
@app.post("/verify-otp")
def verify_otp(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    otp: int = Form(...)
):
    txn = users[user_id]["pending"][transaction_id]
    if txn["otp"] != otp:
        return {"verified": False}

    txn["otp_verified"] = True
    save_data(data)
    return {"verified": True}

# -------------------------------------------------
# Admin Decision
# -------------------------------------------------
@app.post("/decision")
def decision(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    decision: str = Form(...)
):
    user = users[user_id]
    txn = user["pending"].pop(transaction_id)

    if not txn["otp_verified"]:
        return {"error": "OTP not verified"}

    label = 0 if decision == "APPROVE" else 1

    online_model.learn_one(
        {k:v for k,v in txn["features"].items() if not k.startswith("_")},
        label
    )

    txn["transaction"]["fraud"] = label
    user["history"].append(txn["transaction"])
    save_data(data)

    return {"saved": True}

# -------------------------------------------------
# Views
# -------------------------------------------------
@app.get("/pending")
def pending():
    out = []
    for uid, u in users.items():
        for tid, t in u.get("pending", {}).items():
            out.append({
                "transaction_id": tid,
                "user_id": uid,
                "risk_score": t["risk_score"],
                "risk_flag": t["risk_flag"],
                "rf_probability": t["rf_probability"],
                "online_probability": t["online_probability"],
                "otp_verified": t["otp_verified"]
            })
    return out

@app.get("/history/{user_id}")
def history(user_id: str):
    return users[user_id].get("history", [])

@app.get("/debug/users")
def debug_users():
    return [{"user_id": u} for u in users.keys()]
