"""
Feature engineering for fraud detection
Keeps everything numeric & model-friendly
"""

def extract_features(txn: dict) -> dict:
    """
    Convert raw transaction JSON into ML-ready features
    """

    amount = float(txn.get("amount", 0))
    txn_velocity = int(txn.get("txn_velocity", 0))
    device_change = int(txn.get("device_change", 0))
    location_change = int(txn.get("location_change", 0))

    # Basic derived features (very effective for fraud)
    high_amount = 1 if amount > 10000 else 0
    rapid_txn = 1 if txn_velocity > 5 else 0

    return {
        "amount": amount,
        "txn_velocity": txn_velocity,
        "device_change": device_change,
        "location_change": location_change,
        "high_amount": high_amount,
        "rapid_txn": rapid_txn
    }
