# Product Requirements Document (PRD)
## Smart Municipal Complaint Intelligence

| Field | Value |
|---|---|
| Version | 1.0 |
| Status | Approved |
| Document type | PRD |
| Companion document | TRD.md |

---

## 1. Overview

### 1.1 Product Summary
Smart Municipal Complaint Intelligence is an AI-powered platform that improves how municipal complaints are received, analyzed, prioritized, and resolved. It uses Artificial Intelligence, Machine Learning, Natural Language Processing (NLP), Retrieval-Augmented Generation (RAG), and GIS to turn unstructured citizen complaints into actionable information for municipal authorities.

### 1.2 Problem Statement
Municipal bodies receive complaints through many channels (apps, calls, letters, social media). Today:
- Complaints are sorted and routed manually, which is slow and error-prone.
- The same issue is reported many times and handled as separate tickets.
- Urgent issues (burst pipes, open manholes) are not separated from routine ones.
- Officials cannot easily see where problems cluster.
- Policy and SLA information is scattered in documents, so officers answer inconsistently.
- Citizens get little visibility into status.

### 1.3 Vision
A smart, transparent, and efficient civic complaint management system that combines AI-driven automation with municipal data and decision support.

### 1.4 Goals
1. Reduce manual effort in sorting and routing complaints.
2. Improve response time, especially for high-priority complaints.
3. Detect and group duplicate complaints automatically.
4. Give officials reliable, source-cited policy and SLA guidance.
5. Show geographic hotspots for better resource allocation.
6. Give citizens transparent status tracking.

### 1.5 Non-Goals (v1)
- Payment or billing features.
- Native mobile apps (a responsive web app is in scope).
- Integration with legacy ERP/e-governance systems (design for it, do not build it).
- Fully automated resolution without human involvement.

---

## 2. Users and Personas

| Persona | Description | Main needs |
|---|---|---|
| **Citizen** | Resident who reports a civic issue | Easy submission in their language, photo and location, status tracking |
| **Field/Department Officer** | Employee who resolves complaints | Clear assigned queue, priority, location, similar complaints, SLA info |
| **Administrator / Commissioner** | Oversees departments | Trends, workload, overdue items, hotspots, performance |
| **System Admin** | Manages the platform | User management, departments, knowledge base, model settings |

---

## 3. User Stories

### Citizen
- As a citizen, I can submit a complaint with text, a photo, and a location so that the right team can act.
- As a citizen, I can write in English, Hindi, or Hinglish.
- As a citizen, I can track my complaint by ID and see status history.
- As a citizen, I am told when my complaint is assigned or resolved.

### Officer
- As an officer, I see my assigned complaints sorted by priority and SLA deadline.
- As an officer, I see why the AI chose a category and priority and can override it.
- As an officer, I see similar or duplicate complaints grouped together.
- As an officer, I can ask the policy assistant "What is the SLA for X?" and get a cited answer.

### Administrator
- As an admin, I see complaint trends, priority levels, department workload, and unresolved complaints.
- As an admin, I see a map of hotspots to plan resources.
- As an admin, I am alerted when SLAs are breached.

### System Admin
- As a system admin, I can upload policy documents to the knowledge base.
- As a system admin, I can manage users, roles, departments, and SLA rules.

---

## 4. Functional Requirements

### FR-1 Complaint Intake
| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | Citizens can submit complaints with free text, optional photo, and location (map pin, GPS, or address) | Must |
| FR-1.2 | Support English, Hindi, and Hinglish text | Must |
| FR-1.3 | Each complaint receives a unique tracking ID | Must |
| FR-1.4 | Validate input (length, file type, file size) | Must |
| FR-1.5 | Anonymous or guest submission with optional contact details | Should |

### FR-2 AI Classification
| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Automatically classify complaints into categories: roads, garbage, water supply, drainage, streetlights, sanitation, other | Must |
| FR-2.2 | Store confidence score and short explanation for each classification | Must |
| FR-2.3 | Low-confidence results are flagged for manual review | Must |
| FR-2.4 | Officers can correct the category, and corrections are logged for retraining | Should |

### FR-3 Location Intelligence
| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Extract location mentions (road, colony, landmark) from text | Must |
| FR-3.2 | Geocode to coordinates, preferring user-provided coordinates | Must |
| FR-3.3 | Unresolvable locations go to a manual location queue | Should |

### FR-4 Priority Prediction
| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | Predict priority: Low, Medium, High, Critical | Must |
| FR-4.2 | Consider category, urgency language, proximity to sensitive places (hospital, school), duplicate count, and age | Must |
| FR-4.3 | Show the top reasons behind the priority in plain language | Must |
| FR-4.4 | Officers can override priority, and overrides are logged | Must |

### FR-5 Duplicate Detection and Grouping
| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Detect duplicate or closely related complaints using semantic similarity (embeddings), location proximity, and category | Must |
| FR-5.2 | Group related complaints into a cluster | Must |
| FR-5.3 | Cluster size increases priority | Should |
| FR-5.4 | Officers can merge or split clusters | Should |

### FR-6 Routing and Workflow
| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | Route each complaint to the correct department automatically | Must |
| FR-6.2 | Status workflow: Submitted, Assigned, In Progress, Resolved, Closed | Must |
| FR-6.3 | Assign to an officer based on area and workload | Should |
| FR-6.4 | Automatic escalation when an SLA deadline is missed | Should |
| FR-6.5 | Full audit trail of status changes and AI decisions | Must |

### FR-7 RAG Knowledge Assistant
| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Ingest policy, SLA, guideline, and escalation documents (PDF/DOCX/TXT) | Must |
| FR-7.2 | Answer officer questions using only retrieved sources, with citations (document, page) | Must |
| FR-7.3 | Respond "insufficient information" when sources do not support an answer | Must |
| FR-7.4 | For a given complaint, show the applicable SLA and escalation steps | Should |

### FR-8 GIS and Dashboard
| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Map with complaint markers colored by priority | Must |
| FR-8.2 | Hotspot detection and heatmap | Must |
| FR-8.3 | Charts: trends over time, priority distribution, category breakdown, department workload | Must |
| FR-8.4 | Unresolved and overdue complaint lists | Must |
| FR-8.5 | Filters: date, category, department, priority, area | Must |
| FR-8.6 | KPI cards: total, open, overdue, average resolution time | Must |

### FR-9 Notifications
| ID | Requirement | Priority |
|---|---|---|
| FR-9.1 | Notify citizens on assignment and resolution (email/SMS via pluggable providers) | Should |
| FR-9.2 | Notify officers of new assignments and SLA risk | Should |

### FR-10 Administration and Security
| ID | Requirement | Priority |
|---|---|---|
| FR-10.1 | Role-based access control: citizen, officer, admin | Must |
| FR-10.2 | Manage departments, users, SLA rules | Must |
| FR-10.3 | Upload and manage knowledge base documents | Must |
