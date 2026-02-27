# Free Online Deploy: PV + AI Telecom (Admin Panel)

Bu paket 100% bepul deploy uchun tayyor:
- Backend (FastAPI) -> Render (free)
- Admin Dashboard (Streamlit) -> Streamlit Community Cloud (free)
- Telemetry simulator -> lokal kompyuteringizdan Render'ga yuboradi

## 0) Nimalar kerak
- GitHub account
- Render account (GitHub bilan kirish)
- Streamlit Community Cloud account (GitHub bilan kirish)
- Lokal kompyuterda Python (simulyator uchun)

---

## 1) Backend'ni Render'ga deploy qilish
1) GitHub'ga yangi repo oching: `pv-ai-telecom`
2) Shu zipni repo'ga joylang (ayniqsa `backend_render/` papkasi).
3) Render.com -> New -> "Blueprint" tanlang
4) Repo'ni tanlang, Render avtomatik `backend_render/render.yaml` ni topadi.
5) Deploy bo‘lgach sizga URL beradi:
   `https://<your-app>.onrender.com`

Tekshirish:
- https://<your-app>.onrender.com/health

Admin login:
- username: Render env `ADMIN_USER`
- password: Render env `ADMIN_PASS`

⚠️ Muhim: Render'da `ADMIN_PASS` ni kuchli parolga o‘zgartiring.

---

## 2) Dashboard'ni Streamlit Cloud'ga deploy qilish
1) Shu repo ichida `dashboard_streamlit/` papkasi bo‘lsin.
2) Streamlit Cloud -> New app
3) Repo tanlang, main file: `dashboard_streamlit/app.py`
4) Advanced settings -> Secrets (ya’ni Streamlit secrets) ga quyidagini yozing:

API_URL = "https://<your-app>.onrender.com"

5) Deploy qiling. Sizga Streamlit URL beradi.

---

## 3) Telemetry yuborish (simulyator)
Backend ishlashi uchun telemetriya kelishi kerak. Lokal kompyuteringizdan yuborasiz:

1) `simulator_local/` papkaga kiring
2) virtualenv tavsiya:
   python -m venv .venv
   .venv\Scripts\activate  (Windows)
   source .venv/bin/activate (Linux/Mac)
3) pip install -r requirements.txt
4) API_INGEST ni qo‘ying:

Windows (PowerShell):
  $env:API_INGEST="https://<your-app>.onrender.com/ingest"

Linux/Mac:
  export API_INGEST="https://<your-app>.onrender.com/ingest"

5) ishga tushiring:
  python send_simulator.py

---

## 4) Admin paneldan foydalanish
- Streamlit URL ni oching
- Admin login qiling
- Sites qo‘shing/o‘chiring
- Real-time monitoringni ko‘ring

---

## Tez-tez uchraydigan muammo
- Render free: servis "sleep" ga ketadi. Birinchi so‘rovda 10-30s sekin ochilishi mumkin.
- Telemetriya kelmasa dashboard "Hali telemetriya kelmadi" deydi: simulyator ishlayaptimi tekshiring.
