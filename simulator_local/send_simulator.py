import os, time, json
from datetime import datetime, timezone, timedelta
import numpy as np
import requests

API_INGEST = os.getenv("API_INGEST", "").rstrip("/")
if not API_INGEST:
    raise SystemExit("Set API_INGEST like: https://<your-render-app>.onrender.com/ingest")

rng = np.random.default_rng(42)

def make_sample(t, site_id="BTS-01"):
    hour = t.hour
    clear = max(np.sin((hour - 6) / 12 * np.pi), 0)
    cloud = rng.beta(4, 2)
    irr = 900 * clear * cloud
    temp = 20 + 10*np.sin(2*np.pi*(hour-14)/24) + rng.normal(0, 1.0)
    wind = max(rng.normal(2.5, 1.0), 0)
    soiling = float(np.clip(0.05 + 0.02*rng.normal(), 0.0, 0.25))
    P_rated = 5.0
    ppv = max(P_rated * (irr/1000.0) * (1 - soiling) * (1 - 0.004*(temp-25)), 0)
    load = 1.8 + (0.6 if 18 <= hour <= 23 else 0.3 if 8 <= hour <= 17 else 0) + rng.normal(0,0.1)
    load = float(max(load, 1.2))
    soc = float(np.clip(0.55 + 0.15*np.sin(2*np.pi*(hour)/24) + rng.normal(0,0.03), 0.1, 0.95))
    inverter_ok = 1
    if rng.random() < 0.02:
        inverter_ok = 0
        ppv *= 0.1
    return {
        "ts": t.isoformat(),
        "site_id": site_id,
        "irr_Wm2": float(irr),
        "temp_C": float(temp),
        "wind_ms": float(wind),
        "soiling": soiling,
        "ppv_kW": float(ppv),
        "soc": soc,
        "load_kW": load,
        "inverter_ok": inverter_ok
    }

def main():
    tz = timezone(timedelta(hours=5))
    while True:
        t = datetime.now(tz=tz).replace(microsecond=0)
        payload = make_sample(t, site_id="BTS-01")
        r = requests.post(API_INGEST, json=payload, timeout=10)
        print(r.status_code, r.text[:120])
        time.sleep(2)

if __name__ == "__main__":
    main()
