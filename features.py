from datetime import datetime, timedelta

ACCOUNT_LIMITS = {
    "student": 5000,
    "savings": 20000,
    "salary": 40000,
    "business": 100000
}

def extract_features(transaction: dict, user: dict):

    amount = float(transaction["amount"])
    device_id = transaction["device_id"]
    location = transaction["location"]
    timestamp = datetime.fromisoformat(transaction["timestamp"])

    history = user.get("history", [])
    profile = user["profile"]

    # -----------------------
    # Device & location flags
    # -----------------------
    known_devices = {h["device_id"] for h in history}
    known_locations = {h["location"] for h in history}

    device_change = 1 if device_id not in known_devices else 0
    location_change = 1 if location not in known_locations else 0

    # -----------------------
    # Transaction velocity
    # -----------------------
    window_start = timestamp - timedelta(minutes=10)
    txn_velocity = sum(
        1 for h in history
        if datetime.fromisoformat(h["timestamp"]) >= window_start
    )

    # -----------------------
    # ACCOUNT TYPE LOGIC ✅
    # -----------------------
    avg_amount = profile.get("avg_amount", 1)
    account_type = profile.get("account_type", "savings")

    amount_ratio = amount / avg_amount if avg_amount > 0 else 1

    account_limit = ACCOUNT_LIMITS.get(account_type, 20000)
    account_amount_flag = 1 if amount > account_limit else 0

    rapid_txn = 1 if txn_velocity > 5 else 0

    return {
    # ---- numeric features ONLY ----
    "amount": amount,
    "txn_velocity": txn_velocity,
    "device_change": device_change,
    "location_change": location_change,
    "amount_ratio": amount_ratio,
    "account_amount_flag": account_amount_flag,
    "rapid_txn": rapid_txn,

    # ---- metadata (NOT for models) ----
    "_meta": {
        "account_type": account_type
    }
}

