# Drug Discovery App

ML/GenAI web app that predicts bioactivity, toxicity and drug-likeness for a molecule (with SHAP-based explanations and a plain-English summary) and suggests approved drugs that could be repurposed for a disease.

## Setup (Phase 0)

### Backend (Python 3.13)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # add GEMINI_API_KEY later
uvicorn app.main:app --reload
```
Check http://localhost:8000/health.

### Frontend (Node 22)
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.
