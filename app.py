from fastapi import FastAPI, Form
import json
import numpy as np
import random
from datetime import datetime

from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Fully Automatic Fraud Detection")

DATA_FILE = "user_transactions.json"

# -----------------------------
# Load / Save
# -----------------------------
def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()
users = {u["user_id"]: u for u in data["users"]}

# -----------------------------
# Risk flag
# -----------------------------
def get_risk_flag(score: float) -> str:
    if score <= 20:
        return "LOW"
    elif score <= 40:
        return "MEDIUM"
    elif score <= 60:
        return "HIGH"
    elif score <= 80:
        return "CRITICAL"
    else:
        return "SEVERE"

# -----------------------------
# TRANSACTION (Customer)
# -----------------------------
@app.post("/transaction")
def evaluate_transaction(txn: dict):

    user_id = txn.get("user_id")
    amount = txn.get("amount")
    device_id = txn.get("device_id")

    if not user_id or amount is None or not device_id:
        return {"error": "Invalid input"}

    user = users[user_id]
    user.setdefault("history", [])
    user.setdefault("pending", {})
    user.setdefault("profile", {"avg_amount": amount})

    location = user["history"][-1]["location"] if user["history"] else "INDIA"

    transaction = {
        "amount": amount,
        "device_id": device_id,
        "location": location,
        "timestamp": datetime.utcnow().isoformat()
    }

    # -----------------------------
    # Features
    # -----------------------------
    features = extract_features(transaction, user)

    X_rf = np.array([[ 
        features["amount"],
        features["txn_velocity"],
        features["device_change"],
        features["location_change"],
        features["amount_ratio"],
        features["account_amount_flag"],
        features["rapid_txn"]
    ]])

    rf_prob = float(rf_model.predict_proba(X_rf)[0][1])

    numeric_features = {
        k: v for k, v in features.items()
        if not k.startswith("_")
    }

    online_prob = float(
        online_model.predict_proba_one(numeric_features).get(1, 0)
    )

    # -----------------------------
    # Risk score
    # -----------------------------
    risk_score = (0.6 * online_prob + 0.4 * rf_prob) * 100

    avg_amount = user["profile"]["avg_amount"]
    if amount > avg_amount * 3:
        risk_score += 10
    if amount % 10 != 0:
        risk_score += 5
    if user["history"] and user["history"][-1]["location"] != location:
        risk_score += 10

    risk_score = round(min(risk_score, 100), 2)
    risk_flag = get_risk_flag(risk_score)

    # -----------------------------
    # OTP logic (ONLY < 50)
    # -----------------------------
    otp = None
    otp_verified = False

    if risk_score < 50:
        otp = random.randint(100000, 999999)

    txn_id = f"{user_id}_{len(user['pending'])}"

    user["pending"][txn_id] = {
        "transaction": transaction,
        "features": features,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "rf_probability": rf_prob,
        "online_probability": online_prob,
        "otp": otp,
        "otp_verified": otp_verified
    }

    save_data(data)

    return {
        "transaction_id": txn_id,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "otp_required": otp is not None,
        "otp": otp
    }

# -----------------------------
# VERIFY OTP (Admin)
# -----------------------------
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

# -----------------------------
# DECISION (Admin)
# -----------------------------
@app.post("/decision")
def transaction_decision(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    decision: str = Form(...)
):
    user = users[user_id]
    txn = user["pending"][transaction_id]

    if txn["otp"] and not txn["otp_verified"]:
        return {"error": "OTP not verified"}

    txn = user["pending"].pop(transaction_id)

    label = 0 if decision == "APPROVE" else 1

    numeric_features = {
        k: v for k, v in txn["features"].items()
        if not k.startswith("_")
    }

    online_model.learn_one(numeric_features, label)

    txn["transaction"]["fraud"] = label
    user["history"].append(txn["transaction"])

    history = user["history"]
    user["profile"]["avg_amount"] = sum(h["amount"] for h in history) / len(history)

    save_data(data)
    return {"saved": True}

# -----------------------------
# PENDING (Admin)
# -----------------------------
@app.get("/pending")
def pending():
    out = []
    for uid, u in users.items():
        for tid, t in u.get("pending", {}).items():
            out.append({
                "transaction_id": tid,
                "user_id": uid,
                "amount": t["transaction"]["amount"],
                "risk_score": t["risk_score"],
                "risk_flag": t["risk_flag"],
                "rf_probability": t["rf_probability"],
                "online_probability": t["online_probability"],
                "otp_required": t["otp"] is not None,
                "otp_verified": t["otp_verified"]
            })
    return out

# -----------------------------
# HISTORY
# -----------------------------
@app.get("/history/{user_id}")
def history(user_id: str):
    return users[user_id].get("history", [])
