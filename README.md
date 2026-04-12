# InsightX AI

An AI-powered data analytics copilot built for the **NatWest Group Hackathon**. Upload a CSV or Excel file, ask questions in plain English, and get SQL-backed answers with full transparency — including the query it ran, confidence level, anomaly detection, and a hallucination check on every response.

**Live:** [natwest-zeta.vercel.app](https://natwest-zeta.vercel.app)

---

## Stack

- **Frontend** — Next.js 16, TypeScript, Tailwind CSS → deployed on Vercel
- **Backend** — FastAPI, DuckDB, Claude (Anthropic) → deployed on Railway

---

## Run locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and SECRET_KEY
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
# create frontend/.env.local and set:
# BACKEND_URL=http://127.0.0.1:8000
npm run dev
```

Open [localhost:3000](http://localhost:3000).
