# Frontend (Web UI) – Implementation Guide

## 1. Purpose & Scope

This document defines **clear, practical, and enjoyable-to-use instructions** for building the **Web UI** of the *DevOps Incident & On‑Call Platform* (Local Edition).

The frontend is the **primary interaction layer** for SREs, on‑call engineers, and managers. It must be:
- Fast to understand
- Pleasant to use under pressure
- Reliable during incidents
- Simple to deploy locally

This guide focuses **only** on the frontend (Web UI + API Gateway responsibilities).

---

## 2. Frontend Responsibilities

The Web UI service acts as:

- 🖥 **User Interface** for humans
- 🌐 **API Gateway** for backend services
- 📊 **Visualization layer** for incidents & SRE metrics

### Core Responsibilities

- Display incidents and their lifecycle
- Enable incident actions (acknowledge, resolve)
- Show current on‑call engineers
- Surface key SRE metrics (MTTA / MTTR)
- Proxy or aggregate API calls to backend services

The frontend **must not** contain business logic that belongs to backend services.

---

## 3. Access & Service Contract

| Item | Value |
|---|---|
| Service Name | `web-ui` |
| Public URL | http://localhost:8080 |
| Protocol | HTTP |
| Containerized | Yes (Docker) |
| Health Endpoint | `/health` |
| Metrics Endpoint | `/metrics` |

---

## 4. Required Pages

### 4.1 Dashboard (Landing Page)

**Purpose:** Give instant visibility into the current incident state.

**Must Show:**
- Total open incidents
- Open incidents by severity
- MTTA (average)
- MTTR (average)
- List of active incidents (sortable)

**Incident List Fields:**
- Incident ID
- Service name
- Severity
- Status
- Assigned on‑call
- Created time

**UX Rule:**
> A user should understand system health in **under 5 seconds**.

---

### 4.2 Incident Detail Page

**Purpose:** Manage and resolve a single incident.

**Must Include:**
- Incident metadata (service, severity, timestamps)
- Current status
- Assigned engineer
- Linked alerts
- Timeline of events

**Actions:**
- ✅ Acknowledge Incident
- 🔧 Mark In Progress (optional)
- 🟢 Resolve Incident

**Rules:**
- Disable invalid transitions (e.g. resolve before acknowledge)
- Actions must update UI immediately

---

### 4.3 On‑Call Schedule Page

**Purpose:** Show who is responsible *right now*.

**Must Show:**
- Current on‑call engineer per team
- Primary vs secondary
- Escalation policy summary
- Upcoming rotations (read‑only)

This page is **read-heavy, not action-heavy**.

---

### 4.4 SRE Metrics Page

**Purpose:** Provide operational insights.

**Must Display:**
- MTTA trend
- MTTR trend
- Incidents per service
- Incident volume over time

Charts can be:
- Native frontend charts
- Or embedded Grafana panels (iframe is acceptable)

---

## 5. API Integration

The frontend communicates with backend services over the Docker network.

### Recommended Pattern

```
Browser → Web UI → Backend Services
```

### Services Consumed

| Service | Purpose |
|---|---|
| Alert Ingestion | (optional) trigger test alerts |
| Incident Management | incidents CRUD |
| On‑Call Service | current on‑call lookup |
| Notification Service | (optional) status display |

### Example Backend Calls

- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{id}`
- `PATCH /api/v1/incidents/{id}`
- `GET /api/v1/oncall/current`

**Best Practice:**
> Centralize API calls in a dedicated `api/` or `services/` layer.

---

## 6. UI/UX Principles (Important)

### Design Goals

- Calm under pressure
- Minimal clicks
- Clear status colors
- No visual noise

### Status Color Guidelines

| Status | Color |
|---|---|
| Open | Red |
| Acknowledged | Orange |
| In Progress | Blue |
| Resolved | Green |

### UX Rules

- No blocking modals for critical actions
- Confirmation only for **Resolve**
- Auto‑refresh incident list (polling or websockets)
- Show timestamps in relative format ("5 min ago")

---

## 7. Technology Stack (Recommended)

You are free to choose, but the following stack is **strongly recommended**:

- **Framework:** React + TypeScript
- **State:** React Query / SWR
- **Styling:** Tailwind CSS or simple CSS modules
- **Charts:** Recharts / Chart.js
- **Build Tool:** Vite

Why this works well:
- Fast iteration
- Small bundle size
- Excellent DX

---

## 8. Containerization Requirements

The frontend **must** be containerized.

### Dockerfile Requirements

- Multi‑stage build
- Non‑root user
- Optimized image (< 500MB)
- Healthcheck enabled

### Health Endpoint

`GET /health`

Expected response:
```json
{ "status": "ok" }
```

---

## 9. Metrics & Observability

The Web UI must expose basic metrics:

- HTTP request count
- HTTP latency
- Error count

Endpoint:
```
GET /metrics
```

Metrics must be **Prometheus compatible**.

---

## 10. Error Handling

### UI Rules

- Show friendly error messages
- Never expose stack traces
- Handle backend downtime gracefully

### Examples

- Backend unavailable → "Service temporarily unavailable"
- Empty incident list → "No active incidents 🎉"

---

## 11. Performance Expectations

- Initial load < 3 seconds
- No full page reloads
- Efficient polling (≥ 10s interval)

Remember:
> This UI may be used during **real incidents**.

---

## 12. Definition of Done

The frontend is considered **complete** when:

- [ ] Accessible at http://localhost:8080
- [ ] Dashboard shows live incidents
- [ ] Incidents can be acknowledged and resolved
- [ ] On‑call schedule visible
- [ ] Metrics page available
- [ ] `/health` returns 200
- [ ] `/metrics` is scraped by Prometheus
- [ ] Runs with `docker compose up -d`

---

## 13. Final Notes

Build it **simple**, **clear**, and **boring** in the best way.

When incidents happen, engineers don’t want surprises — they want clarity.

If the backend is the brain 🧠,
this UI is the **face under pressure**.

Make it calm. Make it obvious. Make it reliable.

