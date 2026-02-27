import os, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import numpy as np
import joblib
import jwt
from passlib.hash import bcrypt
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

# -----------------------------
# Config
# -----------------------------
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin12345")
JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALG = "HS256"
TOKEN_TTL_SEC = 60 * 60 * 12  # 12h

# Build/load model (Render disk is ephemeral; keep it simple)
MODEL_PATH = "pv_rf_model.joblib"
if not os.path.exists(MODEL_PATH):
    # train on first boot
    import subprocess, sys
    subprocess.check_call([sys.executable, "model_train.py"])
model = joblib.load(MODEL_PATH)

# Password hash (computed at runtime)
_admin_hash = bcrypt.hash(ADMIN_PASS)

app = FastAPI(title="PV-AI Telecom Backend (Free Deploy)")

# In-memory latest per site (demo-grade). For dissertation this is OK.
LATEST: Dict[str, Dict[str, Any]] = {}
SITES: Dict[str, Dict[str, Any]] = {
    "BTS-01": {"site_id": "BTS-01", "name": "Demo BTS 01", "region": "Toshkent"}
}

# -----------------------------
# Schemas
# -----------------------------
class LoginReq(BaseModel):
    username: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Telemetry(BaseModel):
    ts: str = Field(..., description="ISO8601 timestamp")
    site_id: str
    irr_Wm2: float
    temp_C: float
    wind_ms: float
    soiling: float
    ppv_kW: float
    soc: float
    load_kW: float
    inverter_ok: int = 1

class IngestResp(BaseModel):
    site_id: str
    ppv_pred_kW: float
    fault_score: float
    action: str
    saved_at_utc: str

class Site(BaseModel):
    site_id: str
    name: str
    region: str

# -----------------------------
# Auth helpers
# -----------------------------
def make_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + TOKEN_TTL_SEC}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def require_auth(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/expired token")

# -----------------------------
# AI logic
# -----------------------------
def predict_power(t: Telemetry) -> float:
    # features: hour, irr, temp, wind, soiling
    hour = int(t.ts[11:13])
    X = np.array([[hour, t.irr_Wm2, t.temp_C, t.wind_ms, t.soiling]])
    return float(model.predict(X)[0])

def fault_score(t: Telemetry, p_hat: float) -> float:
    if t.inverter_ok == 0:
        return 0.95
    if p_hat < 0.2:
        return 0.05
    ratio = t.ppv_kW / max(p_hat, 1e-6)
    if ratio < 0.7:
        return float(min(0.9, 0.3 + (0.7 - ratio)*1.2))
    return 0.05

def control_action(t: Telemetry, p_hat: float, fs: float) -> str:
    if fs > 0.8:
        return "alert_maintenance"
    deficit = t.load_kW - p_hat
    if deficit > 0.5 and t.soc < 0.25:
        return "start_generator"
    if deficit > 0.3 and t.soc < 0.35:
        return "reduce_load"
    if p_hat > t.load_kW + 0.3 and t.soc < 0.85:
        return "battery_charge"
    if deficit > 0.2 and t.soc > 0.45:
        return "battery_discharge"
    return "normal"

# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/login", response_model=TokenResp)
def login(req: LoginReq):
    if req.username != ADMIN_USER:
        raise HTTPException(status_code=401, detail="Bad credentials")
    if not bcrypt.verify(req.password, _admin_hash):
        raise HTTPException(status_code=401, detail="Bad credentials")
    return {"access_token": make_token(req.username)}

@app.get("/sites", response_model=list[Site])
def list_sites(user: str = Depends(require_auth)):
    return list(SITES.values())

@app.post("/sites", response_model=Site)
def add_site(site: Site, user: str = Depends(require_auth)):
    if site.site_id in SITES:
        raise HTTPException(status_code=409, detail="site_id already exists")
    SITES[site.site_id] = site.model_dump()
    return site

@app.delete("/sites/{site_id}")
def delete_site(site_id: str, user: str = Depends(require_auth)):
    if site_id not in SITES:
        raise HTTPException(status_code=404, detail="Not found")
    SITES.pop(site_id, None)
    LATEST.pop(site_id, None)
    return {"deleted": site_id}

@app.post("/ingest", response_model=IngestResp)
def ingest(t: Telemetry):
    # public endpoint for demo ingest (simulator/edge device)
    if t.site_id not in SITES:
        # auto-register for demo
        SITES[t.site_id] = {"site_id": t.site_id, "name": t.site_id, "region": "unknown"}

    p_hat = predict_power(t)
    fs = fault_score(t, p_hat)
    action = control_action(t, p_hat, fs)

    now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    LATEST[t.site_id] = {
        "telemetry": t.model_dump(),
        "prediction": {"ppv_pred_kW": p_hat},
        "fault": {"fault_score": fs},
        "control": {"action": action},
        "saved_at_utc": now_utc
    }
    return {
        "site_id": t.site_id,
        "ppv_pred_kW": p_hat,
        "fault_score": fs,
        "action": action,
        "saved_at_utc": now_utc
    }

@app.get("/latest/{site_id}")
def latest(site_id: str, user: str = Depends(require_auth)):
    if site_id not in LATEST:
        return {"telemetry": None, "prediction": None, "fault": None, "control": None}
    return LATEST[site_id]
