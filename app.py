from fastapi import FastAPI, Form
import json
import numpy as np
from datetime import datetime
from typing import Dict

from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Fully Automatic Fraud Detection")

DATA_FILE = "user_transactions.json"


# -------------------------------------------------
# Load / Save JSON safely
# -------------------------------------------------
def load_data() -> Dict:
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


data = load_data()

# users indexed by user_id
users = {u["user_id"]: u for u in data.get("users", [])}


# -------------------------------------------------
# Risk Flag Logic (20–40–60–80)
# -------------------------------------------------
def get_risk_flag(risk_score: float) -> str:
    if risk_score <= 20:
        return "LOW"
    elif risk_score <= 40:
        return "MEDIUM"
    elif risk_score <= 60:
        return "HIGH"
    elif risk_score <= 80:
        return "CRITICAL"
    else:
        return "SEVERE"


# -------------------------------------------------
# HEALTH CHECK (for Render)
# -------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "users_loaded": len(users)
    }


# -------------------------------------------------
# CUSTOMER: SUBMIT TRANSACTION
# -------------------------------------------------
@app.post("/transaction")
def evaluate_transaction(transaction: dict):

    user_id = transaction.get("user_id")
    amount = transaction.get("amount")
    device_id = transaction.get("device_id")

    if not user_id or amount is None or not device_id:
        return {"error": "user_id, amount, device_id required"}

    if user_id not in users:
        return {"error": "Unknown user"}

    user = users[user_id]

    # Ensure required structures exist
    user.setdefault("history", [])
    user.setdefault("pending", {})
    user.setdefault("profile", {"avg_amount": amount})

    timestamp = datetime.utcnow().isoformat()
    last_location = (
        user["history"][-1]["location"]
        if user["history"]
        else "UNKNOWN"
    )

    full_transaction = {
        "amount": amount,
        "device_id": device_id,
        "location": last_location,
        "timestamp": timestamp
    }

    # -------------------------
    # Feature Engineering
    # -------------------------
    features = extract_features(full_transaction, user)

    # -------------------------
    # Random Forest Model
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

    rf_probability = float(rf_model.predict_proba(X_rf)[0][1])

    # -------------------------
    # Online Model
    # -------------------------
    numeric_features = {
        k: v for k, v in features.items()
        if not k.startswith("_")
    }

    proba = online_model.predict_proba_one(numeric_features)
    online_probability = float(proba.get(1, 0.0)) if isinstance(proba, dict) else 0.0

    # -------------------------
    # Risk Score (Ensemble)
    # -------------------------
    risk_score = round(
        (0.6 * online_probability + 0.4 * rf_probability) * 100,
        2
    )

    risk_flag = get_risk_flag(risk_score)

    txn_id = f"{user_id}_{len(user['history']) + len(user['pending'])}"

    user["pending"][txn_id] = {
        "transaction": full_transaction,
        "features": features,
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "rf_probability": round(rf_probability, 3),
        "online_probability": round(online_probability, 3)
    }

    save_data(data)

    return {
        "transaction_id": txn_id,
        "user_id": user_id,
        "account_type": features["_meta"]["account_type"],
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "recommended_action": (
            "AUTO_APPROVE" if risk_score <= 20 else
            "REVIEW" if risk_score <= 60 else
            "BLOCK_RECOMMENDED"
        )
    }


# -------------------------------------------------
# ADMIN: VIEW PENDING TRANSACTIONS
# -------------------------------------------------
@app.get("/pending")
def get_pending_transactions():
    pending_list = []

    for user_id, user in users.items():
        pending = user.get("pending", {})

        if not isinstance(pending, dict):
            continue

        for txn_id, txn in pending.items():
            pending_list.append({
                "transaction_id": txn_id,
                "user_id": user_id,
                "amount": txn["transaction"]["amount"],
                "device_id": txn["transaction"]["device_id"],
                "risk_score": txn["risk_score"],
                "risk_flag": txn["risk_flag"],
                "rf_probability": txn.get("rf_probability", 0.0),
                "online_probability": txn.get("online_probability", 0.0)
            })

    return pending_list


# -------------------------------------------------
# ADMIN: APPROVE / REJECT
# -------------------------------------------------
@app.post("/decision")
def transaction_decision(
    user_id: str = Form(...),
    transaction_id: str = Form(...),
    decision: str = Form(...)
):
    if user_id not in users:
        return {"error": "Unknown user"}

    user = users[user_id]
    pending = user.get("pending", {})

    if transaction_id not in pending:
        return {"error": "Transaction not found"}

    txn_data = pending.pop(transaction_id)

    label = 0 if decision == "APPROVE" else 1

    numeric_features = {
        k: v for k, v in txn_data["features"].items()
        if not k.startswith("_")
    }

    # Online learning update
    online_model.learn_one(numeric_features, label)

    txn = txn_data["transaction"]
    txn["fraud"] = label

    user["history"].append(txn)

    # Update average amount
    history = user["history"]
    user["profile"]["avg_amount"] = (
        sum(h["amount"] for h in history) / len(history)
    )

    save_data(data)

    return {
        "transaction_id": transaction_id,
        "decision": decision,
        "saved": True
    }


# -------------------------------------------------
# HISTORY (USER + ADMIN)
# -------------------------------------------------
@app.get("/history/{user_id}")
def get_transaction_history(user_id: str):
    if user_id not in users:
        return []
    return users[user_id].get("history", [])
