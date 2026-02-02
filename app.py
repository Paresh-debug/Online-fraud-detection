from fastapi import FastAPI
import json
import numpy as np
from fastapi.responses import HTMLResponse
from fastapi import Form


from features import extract_features
from model import rf_model, online_model

app = FastAPI(title="Fully Automatic Fraud Detection")

with open("user_transactions.json") as f:
    data = json.load(f)

users = {u["user_id"]: u for u in data["users"]}

from datetime import datetime
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

from datetime import datetime
import numpy as np


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

    from datetime import datetime
    timestamp = datetime.utcnow().isoformat()
    location = user["history"][-1]["location"] if user["history"] else "UNKNOWN"

    full_transaction = {
        "amount": amount,
        "device_id": device_id,
        "location": location,
        "timestamp": timestamp
    }

    features = extract_features(full_transaction, user)

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

    proba = online_model.predict_proba_one(numeric_features)
    online_prob = float(proba.get(True, 0.0)) if isinstance(proba, dict) else 0.0


    risk_score = float(round((0.6 * online_prob + 0.4 * rf_prob) * 100, 2))
    risk_flag = get_risk_flag(risk_score)

    txn_id = f"{user_id}_{len(user.get('history', []))}"

    user.setdefault("pending", {})[txn_id] = {
        "transaction": full_transaction,
        "features": features,
        "risk_score": risk_score,
        "risk_flag": risk_flag
    }

    return {
        "transaction_id": txn_id,
        "user_id": user_id,
       "account_type": features["_meta"]["account_type"],   # 🔑
        "risk_score": risk_score,
        "risk_flag": risk_flag,
        "recommended_action": (
            "AUTO_APPROVE" if risk_score <= 20 else
            "REVIEW" if risk_score <= 60 else
            "BLOCK_RECOMMENDED"
        )
    }
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

    # Convert decision to label
    label = 0 if decision == "APPROVE" else 1

    numeric_features = {
    k: v for k, v in txn_data["features"].items()
    if not k.startswith("_")
}

    online_model.learn_one(numeric_features, label)



    # Save transaction
    txn_data["transaction"]["fraud"] = label
    user["history"].append(txn_data["transaction"])

    # Update avg amount
    history = user["history"]
    user["profile"]["avg_amount"] = sum(h["amount"] for h in history) / len(history)

    return {
        "transaction_id": transaction_id,
        "decision": decision,
        "saved": True
    }
@app.get("/debug/users")
def debug_users():
    return list(users.keys())

@app.get("/history/{user_id}")
def get_transaction_history(user_id: str):
    """
    Returns transaction history for both user and admin views
    """

    if user_id not in users:
        return []

    return users[user_id].get("history", [])

@app.get("/pending")
def get_pending_transactions():
    """
    Returns all pending transactions for admin review
    """
    pending_list = []

    for user_id, data in users.items():
        pending = data.get("pending", {})
        for txn_id, txn_data in pending.items():
            pending_list.append({
                "transaction_id": txn_id,
                "user_id": user_id,
                "amount": txn_data["transaction"]["amount"],
                "device_id": txn_data["transaction"]["device_id"],
                "risk_score": txn_data["risk_score"],
                "risk_flag": txn_data["risk_flag"]
            })

    return pending_list
