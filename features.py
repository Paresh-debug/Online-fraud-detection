from datetime import datetime

# -------------------------------
# Account limits by type
# -------------------------------
ACCOUNT_LIMITS = {
    "SAVINGS": 50000,
    "CURRENT": 200000,
    "PREMIUM": 500000,
    "STUDENT": 20000
}

def extract_features(transaction, user):
    history = user.get("history", [])
    profile = user.get("profile", {})

    account_type = profile.get("account_type", "SAVINGS")
    limit = ACCOUNT_LIMITS.get(account_type, 50000)

    amount = transaction["amount"]
    device_id = transaction["device_id"]
    location = transaction["location"]
    timestamp = datetime.fromisoformat(transaction["timestamp"])

    # -------------------------------
    # Velocity
    # -------------------------------
    txn_velocity = 0
    rapid_txn = 0
    if history:
        last_time = datetime.fromisoformat(history[-1]["timestamp"])
        diff = (timestamp - last_time).total_seconds()
        txn_velocity = diff
        rapid_txn = 1 if diff < 60 else 0

    # -------------------------------
    # Device change
    # -------------------------------
    device_change = 0
    if history:
        device_change = 1 if history[-1]["device_id"] != device_id else 0

    # -------------------------------
    # Location change
    # -------------------------------
    location_change = 0
    if history:
        location_change = 1 if history[-1]["location"] != location else 0

    # -------------------------------
    # Amount ratio
    # -------------------------------
    avg_amount = profile.get("avg_amount", amount)
    amount_ratio = amount / avg_amount if avg_amount > 0 else 1

    # -------------------------------
    # HARD LIMIT FLAG
    # -------------------------------
    account_amount_exceeded = 1 if amount > limit else 0

    return {
        "amount": amount,
        "txn_velocity": txn_velocity,
        "device_change": device_change,
        "location_change": location_change,
        "amount_ratio": amount_ratio,
        "rapid_txn": rapid_txn,
        "account_amount_flag": account_amount_exceeded,

        "_meta": {
            "account_type": account_type,
            "account_limit": limit
        }
    }
