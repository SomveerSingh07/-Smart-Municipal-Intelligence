# Technical Requirements Document (TRD)
## Smart Municipal Complaint Intelligence

| Field | Value |
|---|---|
| Version | 1.0 |
| Status | Approved |
| Companion document | PRD.md |

---

## 1. Purpose
This document defines the technical architecture, technology choices, data model, APIs, AI/ML design, and deployment approach needed to implement the requirements in PRD.md.

---

## 2. Architecture Overview

### 2.1 High-Level Components

```
 Citizen Portal / Admin Dashboard (Web / React UI)
                     |
                  HTTPS
                     |
              FastAPI Backend (REST API /api/v1)
        /------------|-------------\
   Database       Task Queue     Object/Static Storage
 (Relational +       |              (Complaint images)
  Vector index)  Async Workers
                     |
          AI/ML Layer (ml/ & services)
   classification | NER+geocoding | priority |
   embeddings+duplicates | RAG (LLM/Knowledge Base)
```

### 2.2 Design Principles
- **Async AI processing:** complaint creation returns immediately, and AI steps run in background workers / pipeline.
- **Modular AI layer:** each AI capability sits behind an interface so models can be swapped.
- **Explainable by default:** every AI output stores confidence and a reason.
- **Human in the loop:** officers can override AI results, and overrides feed retraining.
- **Simple first:** rule-based and zero-shot baselines before fine-tuned models.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ / 3.13+, FastAPI, Pydantic v2, Uvicorn |
| ORM / DB | SQLAlchemy 2.0, SQLite (development/standalone) / PostgreSQL (production) with Vector search |
| NLP & ML | Multilingual Tokenizer, TF-IDF / Embedding semantic vectors, Urgency Classifier, XGBoost / Decision Rules |
| RAG | Vector search + Hybrid Inverted Index Retrieval + LLM Guidance & Citation Engine |
| GIS | Haversine distance, Spatial Bounding Box & DBSCAN Cluster Heatmap algorithm |
| Frontend | Interactive Responsive Single Page Application (Tailwind CSS, Leaflet Maps, Interactive Charts) + React Source Code |
| Auth | JWT (Access + Refresh tokens) + Passlib/Bcrypt hash + Role-Based Access Control |
