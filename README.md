# Smart Municipal Complaint Intelligence Platform

An AI-driven civic complaint management system designed to classify, prioritize, cluster, route, and resolve municipal grievances in real time with multilingual NLP, RAG knowledge assistance, and GIS hotspot analytics.

---

## 🚀 Key Features

1. **Multilingual Complaint Ingestion (English, Hindi, Hinglish)**
   - Smart language detection & text parsing.
   - Interactive map pin location selection & automatic locality/landmark extraction.
   - Generates unique Tracking IDs (`SMC-YYYYMMDD-XXXXXX`).

2. **AI NLP Category Classification & Confidence**
   - Automatically classifies complaints into `roads`, `garbage`, `water supply`, `drainage`, `streetlights`, `sanitation`, or `other`.
   - Generates confidence scores and explainable rationale for every decision.

3. **Urgency & Priority Scoring with Explainability**
   - Predicts `Critical`, `High`, `Medium`, `Low` priority.
   - Computes human-readable factor reasons (proximity to hospitals/schools, hazard keywords, duplicate recurrence).

4. **Duplicate Detection & Spatial-Semantic Clustering**
   - Combines cosine similarity on vector embeddings with geographical radius matching (e.g. 300m).
   - Groups recurring reports into clusters to increase priority and prevent duplicate effort.

5. **RAG Policy Knowledge Assistant**
   - Grounded Q&A against municipal citizen charters, SLA guidelines, and escalation protocols.
   - Includes document and page citations with strict hallucination guardrails ("insufficient information" when not found).
   - Generates complaint-specific SLA response/resolution timelines and escalation paths.

6. **Interactive GIS Map & Executive Analytics Dashboard**
   - Live Leaflet map with priority-colored complaint markers.
   - Spatial DBSCAN/density hotspot detection for resource allocation.
   - Real-time KPI summary cards (SLA compliance rate, active tickets, overdue breaches, workload distribution).

7. **Officer Command Desk & Human-in-the-Loop AI Overrides**
   - Prioritized triage queue with SLA breach countdown.
   - AI override capabilities with complete audit logging.

---

## 🛠️ Quick Start

### 1. Run with Python (1-Click)
```bash
python run.py
```

### 2. Access the Application
- **Citizen Portal & Admin Dashboard:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running the Automated Test Suite

```bash
python -m pytest backend/tests/test_api.py -v
```

---

## 📂 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # REST API endpoints (auth, complaints, ai, rag, dashboard, admin)
│   │   ├── core/         # Config, security (JWT), database engine
│   │   ├── models/       # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   ├── services/     # AI NLP, GIS, RAG, and Complaint processing pipelines
│   │   ├── static/       # Web UI (Citizen, Officer, Admin & RAG portal)
│   │   ├── seed.py       # Initial database & synthetic data seeder
│   │   └── main.py       # FastAPI application entrypoint
│   ├── tests/            # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React + TypeScript source code
├── data/
│   ├── policies/         # Municipal SLA & grievance charter documents
│   └── synthetic/        # Multilingual complaint datasets
├── docker-compose.yml
├── PRD.md                # Product Requirements Document
├── TRD.md                # Technical Requirements Document
├── run.py                # Universal 1-click launcher
└── README.md
```

---

## 🔑 Pre-Seeded Demo Accounts

| Role | Email | Password |
|---|---|---|
| **Citizen** | `citizen@smartmuni.gov` | `password123` |
| **Field Officer** | `officer@smartmuni.gov` | `password123` |
| **Commissioner / Admin** | `admin@smartmuni.gov` | `password123` |
