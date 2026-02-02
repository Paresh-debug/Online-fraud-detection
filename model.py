import numpy as np
from sklearn.ensemble import RandomForestClassifier

from river import preprocessing, linear_model

rf_model = RandomForestClassifier(n_estimators=50, random_state=42)

X_init = np.array([
    [300, 1, 0, 0, 0.25, 0, 0],     # student normal
    [12000, 3, 0, 0, 0.8, 0, 0],    # salary normal
    [5000, 3, 1, 1, 4.0, 1, 1],     # student fraud
    [60000, 8, 1, 1, 3.0, 1, 1]     # business fraud
])

y_init = np.array([0, 0, 1, 1])

rf_model.fit(X_init, y_init)

online_model = preprocessing.StandardScaler() | linear_model.LogisticRegression()
