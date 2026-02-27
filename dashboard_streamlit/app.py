import os, time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="PV-AI Telecom Admin", layout="wide")
st.title("🔐 PV + AI Telecom — Admin Panel (Free Deploy)")

API_URL = st.secrets.get("API_URL", os.getenv("API_URL", "")).rstrip("/")
if not API_URL:
    st.error("API_URL yo‘q. Streamlit secrets ga API_URL qo‘ying.")
    st.stop()

# -------------------------
# Auth
# -------------------------
def api_post(path, json_data=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(f"{API_URL}{path}", json=json_data, headers=headers, timeout=10)

def api_get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(f"{API_URL}{path}", headers=headers, timeout=10)

def api_delete(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.delete(f"{API_URL}{path}", headers=headers, timeout=10)

if "token" not in st.session_state:
    st.session_state.token = None

with st.sidebar:
    st.subheader("Login")
    user = st.text_input("Username", value="admin")
    pwd = st.text_input("Password", type="password")
    if st.button("Sign in"):
        r = api_post("/auth/login", {"username": user, "password": pwd})
        if r.status_code == 200:
            st.session_state.token = r.json()["access_token"]
            st.success("Logged in ✅")
        else:
            st.error("Login xato. Username/parolni tekshiring.")
    if st.session_state.token and st.button("Logout"):
        st.session_state.token = None

token = st.session_state.token
if not token:
    st.info("Admin panelga kirish uchun login qiling.")
    st.stop()

# -------------------------
# Sites management
# -------------------------
st.subheader("📍 Telekom obyektlar (Sites)")
colA, colB = st.columns([2, 1])

with colA:
    rs = api_get("/sites", token=token)
    if rs.status_code != 200:
        st.error("Sites o‘qib bo‘lmadi. Token yoki API ishlamayapti.")
        st.stop()
    sites = rs.json()
    sites_df = pd.DataFrame(sites)
    st.dataframe(sites_df, use_container_width=True)

with colB:
    st.markdown("### Site qo‘shish")
    site_id = st.text_input("site_id", value="BTS-02")
    name = st.text_input("name", value="Demo BTS 02")
    region = st.text_input("region", value="Farg‘ona")
    if st.button("Add site"):
        r = api_post("/sites", {"site_id": site_id, "name": name, "region": region}, token=token)
        if r.status_code == 200:
            st.success("Qo‘shildi ✅")
            st.rerun()
        else:
            st.error(f"Xato: {r.text}")

    st.markdown("### Site o‘chirish")
    del_id = st.text_input("Delete site_id", value="BTS-02")
    if st.button("Delete"):
        r = api_delete(f"/sites/{del_id}", token=token)
        if r.status_code == 200:
            st.success("O‘chirildi ✅")
            st.rerun()
        else:
            st.error(f"Xato: {r.text}")

# -------------------------
# Monitoring
# -------------------------
st.subheader("📊 Real-time monitoring")
site_list = [s["site_id"] for s in sites]
selected = st.selectbox("Kuzatish uchun site tanlang", site_list, index=0)

auto = st.toggle("Auto-refresh (2s)", value=True)

chart_ph = st.empty()
table_ph = st.empty()

if "hist" not in st.session_state:
    st.session_state.hist = []

def fetch_latest():
    r = api_get(f"/latest/{selected}", token=token)
    if r.status_code != 200:
        st.error("Latest olishda xato.")
        return None
    return r.json()

def render(data):
    if not data or not data.get("telemetry"):
        st.warning("Hali telemetriya kelmadi. Simulator/edge data yuboryaptimi?")
        return
    telem = data["telemetry"]
    pred = data["prediction"]
    fault = data["fault"]
    ctrl = data["control"]

    row = {
        "ts": telem["ts"],
        "irr_Wm2": telem["irr_Wm2"],
        "temp_C": telem["temp_C"],
        "soiling": telem["soiling"],
        "ppv_kW": telem["ppv_kW"],
        "ppv_pred_kW": pred["ppv_pred_kW"],
        "soc": telem["soc"],
        "load_kW": telem["load_kW"],
        "fault_score": fault["fault_score"],
        "action": ctrl["action"],
    }
    st.session_state.hist.append(row)
    st.session_state.hist = st.session_state.hist[-250:]
    df = pd.DataFrame(st.session_state.hist)

    c1, c2, c3, c4 = st.columns(4)
    last = df.iloc[-1]
    c1.metric("PV (kW)", f"{last.ppv_kW:.2f}", f"pred {last.ppv_pred_kW:.2f}")
    c2.metric("Load (kW)", f"{last.load_kW:.2f}")
    c3.metric("SOC", f"{last.soc:.2f}")
    c4.metric("Action", f"{last.action}")

    chart_ph.line_chart(df.set_index("ts")[["ppv_kW","ppv_pred_kW","load_kW"]])
    table_ph.dataframe(df.tail(25), use_container_width=True)

# single render
data = fetch_latest()
render(data)

if auto:
    time.sleep(2)
    st.rerun()
