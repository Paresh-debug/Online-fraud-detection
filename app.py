from fastapi import FastAPI, Form
import json
import numpy as np
from datetime import datetime
from typing import Dict

from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Adaptive Fraud Detection System")

DATA_FILE = "user_transactions.json"


# -----------------------------
# JSON helpers
# -----------------------------
def load_data() -> Dict:
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


data = load_data()
users = {u["user_id"]: u for u in data["users"]}


# -----------------------------
# Risk bands (20–40–60–80)
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
# Health (Render)
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "users": len(users)}


# -----------------------------
# Submit transaction (Customer)
# -----------------------------
@app.post("/transaction")
def evaluate_transaction(txn: dict):

    user_id = txn.get("user_id")
    amount = txn.get("amount")
    device_id = txn.get("device_id")

    if not user_id or amount is None or not device_id:
        return {"error": "user_id, amount, device_id required"}

    if user_id not in users:
        return {"error": "Unknown user"}

    user = users[user_id]
    user.setdefault("history", [])
    user.setdefault("pending", {})
    user.setdefault("profile", {"avg_amount": amount})

    last_location = (
        user["history"][-1]["location"]
        if user["history"]
        else "UNKNOWN"
    )

    transaction = {
        "amount": amount,
        "device_id": device_id,
        "location": last_location,
        "timestamp": datetime.utcnow().isoformat()
    }

    # -------------------------
    # Feature extraction
    # -------------------------
    features = extract_features(transaction, user)

    # -------------------------
    # Random Forest
    # -------------------------
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

    # -------------------------
    # Online model
    # -------------------------
    numeric_features = {
        k: v for k, v in features.items()
        if not k.startswith("_")
    }

    proba = online_model.predict_proba_one(numeric_features)
    online_prob = float(proba.get(1, 0.0))

    # -------------------------
    # Base ML risk score
    # -------------------------
    risk_score = (0.6 * online_prob + 0.4 * rf_prob) * 100

    # -------------------------
    # RULE-BASED RISK BOOSTS
    # -------------------------
    avg_amount = user["profile"].get("avg_amount", amount)

    # Large amount
    if amount > avg_amount * 3:
        risk_score += 10

    # Weird amount (not ending with 0)
    if amount % 10 != 0:
        risk_score += 5

    # Sudden city/location change
    prev_loc = user["history"][-1]["location"] if user["history"] else None
    if prev_loc and prev_loc != transaction["location"]:
        risk_score += 10

    risk_score = round(min(risk_score, 100), 2)
    risk_flag = get_risk_flag(risk_score)

    txn_id = f"{user_id}_{len(user['history']) + len(user['pending'])}"

    user["pending"][txn_id] = {
        "transaction": transaction,
        "features": features,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "rf_probability": round(rf_prob, 3),
        "online_probability": round(online_prob, 3)
    }

    save_data(data)

    return {
        "transaction_id": txn_id,
        "risk_score": risk_score,
        "risk_flag": risk_flag
    }


# -----------------------------
# Pending (Admin)
# -----------------------------
@app.get("/pending")
def pending_transactions():
    out = []

    for uid, user in users.items():
        for tid, txn in user.get("pending", {}).items():
            out.append({
                "transaction_id": tid,
                "user_id": uid,
                "amount": txn["transaction"]["amount"],
                "risk_score": txn["risk_score"],
                "risk_flag": txn["risk_flag"],
                "rf_probability": txn["rf_probability"],
                "online_probability": txn["online_probability"]
            })

    return out


# -----------------------------
# Decision (Admin)
# -----------------------------
@app.post("/decision")
def decision(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    decision: str = Form(...)
):
    user = users[user_id]
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
    user["profile"]["avg_amount"] = sum(t["amount"] for t in history) / len(history)

    save_data(data)

    return {"decision": decision}


# -----------------------------
# History (User + Admin)
# -----------------------------
@app.get("/history/{user_id}")
def history(user_id: str):
    return users.get(user_id, {}).get("history", [])
