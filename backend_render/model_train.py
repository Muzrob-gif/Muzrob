import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

rng = np.random.default_rng(7)

def gen(n=4000):
    hour = rng.integers(0, 24, size=n)
    clear = np.clip(np.sin((hour-6)/12*np.pi), 0, None)
    irr = 900*clear*rng.beta(4,2,size=n)
    temp = 20 + 10*np.sin(2*np.pi*(hour-14)/24) + rng.normal(0, 1.2, size=n)
    wind = np.clip(rng.normal(2.5, 1.0, size=n), 0, None)
    soiling = np.clip(rng.normal(0.08, 0.03, size=n), 0.0, 0.25)

    P_rated = 5.0
    ppv = P_rated*(irr/1000.0)*(1-soiling)*(1-0.004*(temp-25))
    ppv = np.clip(ppv + rng.normal(0,0.12,size=n), 0, None)
    X = np.column_stack([hour, irr, temp, wind, soiling])
    y = ppv
    return X, y

X, y = gen()
model = RandomForestRegressor(n_estimators=350, random_state=7, min_samples_leaf=2)
model.fit(X, y)
joblib.dump(model, "pv_rf_model.joblib")
print("Saved pv_rf_model.joblib")
