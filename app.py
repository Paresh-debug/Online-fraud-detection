from fastapi import FastAPI, Form
import json, random
import numpy as np
from datetime import datetime

from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Risk-Aware Fraud Detection")

DATA_FILE = "user_transactions.json"

# -------------------------------
# Load / Save
# -------------------------------
def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

data = load_data()
users = {u["user_id"]: u for u in data["users"]}

# -------------------------------
# Risk flags
# -------------------------------
def get_risk_flag(score):
    if score <= 20: return "LOW"
    if score <= 40: return "MEDIUM"
    if score <= 60: return "HIGH"
    if score <= 80: return "CRITICAL"
    return "SEVERE"

# -------------------------------
# Transaction endpoint
# -------------------------------
@app.post("/transaction")
def evaluate_transaction(txn: dict):

    user_id = txn["user_id"]
    amount = txn["amount"]
    device_id = txn["device_id"]

    user = users[user_id]
    user.setdefault("history", [])
    user.setdefault("pending", {})
    user.setdefault("profile", {"avg_amount": amount})

    transaction = {
        "amount": amount,
        "device_id": device_id,
        "location": "INDIA",
        "timestamp": datetime.utcnow().isoformat()
    }

    features = extract_features(transaction, user)

    txn_id = f"{user_id}_{len(user['history']) + len(user['pending'])}"

    # -------------------------------------------------
    # HARD BLOCK: account limit exceeded
    # -------------------------------------------------
    if features["account_amount_flag"] == 1:
        transaction["fraud"] = 1
        transaction["block_reason"] = "AMOUNT_EXCEEDS_ACCOUNT_LIMIT"
        user["history"].append(transaction)
        save_data(data)

        return {
            "transaction_id": txn_id,
            "risk_score": 100,
            "risk_flag": "SEVERE",
            "action": "BLOCK",
            "message": (
                f"Transaction blocked: amount exceeds limit for "
                f"{features['_meta']['account_type']} account"
            )
        }

    # -------------------------------------------------
    # ML scoring
    # -------------------------------------------------
    X_rf = np.array([[features[k] for k in [
        "amount",
        "txn_velocity",
        "device_change",
        "location_change",
        "amount_ratio",
        "account_amount_flag",
        "rapid_txn"
    ]]])

    rf_prob = float(rf_model.predict_proba(X_rf)[0][1])

    online_prob = float(
        online_model.predict_proba_one(
            {k:v for k,v in features.items() if not k.startswith("_")}
        ).get(1, 0)
    )

    risk_score = (0.6 * online_prob + 0.4 * rf_prob) * 100

    # Explainable boosts
    if amount > user["profile"]["avg_amount"] * 3:
        risk_score += 10
    if amount % 10 != 0:
        risk_score += 5
    if features["location_change"] == 1:
        risk_score += 10

    risk_score = round(min(risk_score, 100), 2)
    risk_flag = get_risk_flag(risk_score)

    # -------------------------------------------------
    # Risk policy
    # -------------------------------------------------
    if risk_flag == "LOW":
        transaction["fraud"] = 0
        user["history"].append(transaction)
        save_data(data)
        return {"action": "AUTO_APPROVE"}

    if risk_flag == "MEDIUM":
        transaction["fraud"] = 0
        user["history"].append(transaction)
        save_data(data)
        return {"action": "APPROVE_MONITOR"}

    if risk_flag == "SEVERE":
        transaction["fraud"] = 1
        user["history"].append(transaction)
        save_data(data)
        return {"action": "BLOCK"}

    # HIGH / CRITICAL → OTP + Admin
    otp = random.randint(100000, 999999)

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

# -------------------------------
# OTP verification
# -------------------------------
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

# -------------------------------
# Admin decision
# -------------------------------
@app.post("/decision")
def decision(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    decision: str = Form(...)
):
    user = users[user_id]

    if transaction_id not in user.get("pending", {}):
        return {"error": "Transaction not found"}

    txn = user["pending"].pop(transaction_id)

    otp_verified = txn.get("otp_verified", False)

    # -----------------------------------------
    # STRICT POLICY
    # -----------------------------------------
    if decision == "APPROVE":
        if not otp_verified:
            return {
                "error": "OTP verification required before approval"
            }
        fraud_label = 0

    elif decision == "REJECT":
        # ❗ ALWAYS fraud, OTP or not
        fraud_label = 1

    else:
        return {"error": "Invalid decision"}

    # -----------------------------------------
    # Online learning (only trusted labels)
    # -----------------------------------------
    if otp_verified:
        online_model.learn_one(
            {k: v for k, v in txn["features"].items() if not k.startswith("_")},
            fraud_label
        )

    # -----------------------------------------
    # Save transaction
    # -----------------------------------------
    txn["transaction"]["fraud"] = fraud_label
    txn["transaction"]["decision"] = decision
    txn["transaction"]["otp_verified"] = otp_verified

    user["history"].append(txn["transaction"])
    save_data(data)

    return {
        "transaction_id": transaction_id,
        "decision": decision,
        "fraud": fraud_label,
        "otp_verified": otp_verified,
        "saved": True
    }

# -------------------------------
# Views
# -------------------------------
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
    return [
        {
            "user_id": u["user_id"],
            "account_type": u.get("profile", {}).get("account_type", "SAVINGS")
        }
        for u in users.values()
    ]
