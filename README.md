# OpenSource Incident & On-Call Platform

[![Pipeline](https://img.shields.io/badge/CI%2FCD-7--stage-blue)]()
[![Services](https://img.shields.io/badge/services-6%20%2B%20infra-brightgreen)]()
[![Python](https://img.shields.io/badge/Python-3.12-3776AB)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)]()

Production-ready incident management and on-call platform — alert ingestion, correlation, on-call scheduling, escalation, notifications, and SRE dashboards. Everything runs locally via Docker Compose.

---

## Quick Start 


```bash
mkdir -p deployment/secrets                   # 1. Create secrets dir
echo "supersecret" > deployment/secrets/postgres_password.txt && \
echo "PLACEHOLDER" > deployment/secrets/resend_api_key.txt  # 2. Set secrets
cp deployment/.env.example deployment/.env    # 3. Copy env config
make re                                       # 4. Build & start everything
make health                                   # 5. Verify all services are healthy
```

> **Note:** The `.env` file configures ports and service URLs. Copy it from `.env.example` before starting — edit values if you need to change default ports.

**Access Points:**

| Service | URL |
|---------|-----|
| Web UI | http://localhost:8080 |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |
| Jaeger (tracing) | http://localhost:16686 |
| On-Call API docs | http://localhost:8003/docs |
| Notification API docs | http://localhost:8004/docs |
| Gateway API docs | http://localhost:8010/docs |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DOCKER COMPOSE STACK                          │
│                                                                        │
│  ┌──────────┐   ┌──────────────────────────────────────────────────┐   │
│  │  👤 User  │──▶│  🌐 Web UI (React + Nginx) :8080                │   │
│  └──────────┘   │    Serves SPA + reverse-proxies /api/* calls     │   │
│                  └────────┬──────────┬──────────┬──────────────────┘   │
│                           │          │          │                       │
│               ┌───────────▼──┐  ┌────▼──────┐  ┌▼────────────┐        │
│               │ 🔔 Alert     │  │ 📋 Incident│  │ 📞 On-Call  │        │
│               │  Ingestion   │  │  Management│  │  Service    │        │
│               │  :8001       │  │  :8002     │  │  :8003      │        │
│               └──┬───────┬───┘  └──┬──┬──┬──┘  └─────────────┘        │
│                  │       │         │  │  │                              │
│                  │       └────────▶┘  │  │     ┌──────────────┐        │
│                  │    create/correlate │  └────▶│ 📣 Notify    │        │
│                  │                    │        │  Service      │        │
│                  │                    │        │  :8004        │        │
│               ┌──▼────────────────────▼──┐    └──────────────┘        │
│               │  🐘 PostgreSQL :5432     │                             │
│               │  (alerts + incidents)    │                             │
│               └──────────────────────────┘                             │
│                                                                        │
│  ┌── Observability ──────────────────────────────────────────────────┐ │
│  │  Prometheus :9090  ◀── scrapes /metrics from all services        │ │
│  │  Grafana    :3000  ◀── queries Prometheus + Loki                 │ │
│  │  Loki + Promtail   ◀── collects container logs                   │ │
│  │  Jaeger     :16686 ◀── receives OpenTelemetry traces             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  🚪 Gateway :8010 — optional API proxy to incident-management         │
└─────────────────────────────────────────────────────────────────────────┘
```

> Full architecture docs with Mermaid diagrams: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Key Features

- **Complete Incident Lifecycle** — Create, acknowledge, resolve with MTTA/MTTR tracking
- **Smart Alert Correlation** — Automatically groups related alerts (same service + severity within 5 min)
- **On-Call Management** — Weekly/daily rotations with primary/secondary engineers
- **Auto-Escalation** — Unacknowledged incidents escalate to secondary after configurable threshold
- **Multi-Channel Notifications** — Mock, webhook, email (Resend), Slack channels
- **Full Observability** — Prometheus metrics, Grafana dashboards, Loki logs, Jaeger traces
- **Request Tracing** — X-Request-ID propagation across all services
- **Docker Secrets** — No hardcoded credentials; file-based secret management

---

## Demo Walkthrough

### 1. Set Up On-Call Schedules

```bash
curl -s -X POST http://localhost:8003/api/v1/schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "team": "payment-service",
    "primary": ["alice", "bob"],
    "secondary": ["charlie"],
    "rotation": "daily"
  }' | jq .
```

### 2. Fire an Alert (triggers the full pipeline)

```bash
curl -s -X POST http://localhost:8080/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-service",
    "severity": "critical",
    "message": "Payment gateway timeout — 95th percentile latency > 5s",
    "labels": {"environment": "production", "region": "us-east-1"}
  }' | jq .
```

**What happens behind the scenes:**

```
Alert Ingestion          Incident Management        On-Call Service
  • validates            • creates incident          • looks up "alice"
  • normalizes           • severity=critical           (current primary)
  • stores alert         • assigns to alice
                         • starts timeline     ──▶  Notification Service
                                                      • logs notification
```

### 3. Send a duplicate alert (demonstrates correlation)

```bash
curl -s -X POST http://localhost:8080/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-service",
    "severity": "critical",
    "message": "Payment gateway — connection refused"
  }' | jq .
```

Response will show `"action": "attached_to_existing_incident"` — deduplicated.

### 4. Walk Through the Incident Lifecycle

```bash
INCIDENT_ID="<paste-incident-id>"

# Acknowledge (records MTTA)
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' -d '{"status": "acknowledged"}' | jq .

# In-progress
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' -d '{"status": "in_progress"}' | jq .

# Add investigation note
curl -s -X POST "http://localhost:8080/api/v1/incidents/$INCIDENT_ID/notes" \
  -H 'Content-Type: application/json' \
  -d '{"content": "Root cause: connection pool exhaustion in PG bouncer", "author": "alice"}' | jq .

# Resolve (records MTTR)
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' -d '{"status": "resolved"}' | jq .

# View full timeline
curl -s "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" | jq '.timeline'
```

### 5. Explore the Web UI

Open http://localhost:8080:

| Page | What You See |
|------|-------------|
| **Dashboard** | Live incident count, severity breakdown, sortable incident table |
| **Incident Detail** | Full timeline, notes, status transitions, MTTA/MTTR, assignment |
| **Metrics** | MTTA/MTTR charts, incident trends, severity distribution |
| **On-Call** | Current rotation schedules, team cards, primary/secondary |

### 6. Auto-Escalation

The on-call service checks for unacknowledged incidents every 60s. After 5 minutes (configurable via `ESCALATION_THRESHOLD_MINUTES`), it reassigns to secondary and sends an escalation notification.

```bash
# Watch it happen
docker compose -f deployment/docker-compose.yml logs -f oncall-service
```

### 7. Webhook & Email Notifications

```bash
# Webhook delivery
curl -s -X POST http://localhost:8004/api/v1/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "test-123",
    "message": "Critical incident requires attention",
    "channel": "webhook",
    "target": "http://host.docker.internal:9999/webhook"
  }' | jq .

# Email (requires Resend API key in deployment/secrets/resend_api_key.txt)
curl -s -X POST http://localhost:8004/api/v1/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "email-test",
    "message": "Production database failover completed",
    "channel": "email",
    "target": "you@example.com"
  }' | jq .
```

---

## Observability

### Prometheus (http://localhost:9090)

| Query | Description |
|-------|-------------|
| `incidents_total` | Incidents by status |
| `alerts_received_total` | Alerts by severity |
| `alerts_correlated_total` | New vs. correlated ratio |
| `incident_mtta_seconds` | Acknowledge time histogram |
| `incident_mttr_seconds` | Resolution time histogram |
| `notifications_sent_total` | By channel & status |
| `escalations_total` | Auto-escalations by team |

### Grafana Dashboards (http://localhost:3000)

| Dashboard | Content |
|-----------|---------|
| **Live Incident Overview** | Active incidents, severity breakdown, MTTA/MTTR gauges, alert timeline |
| **SRE Performance Metrics** | MTTA/MTTR trends (p50/p95), incident volume, on-call load, escalation rate |
| **System Health** | CPU, memory, HTTP request rate, error rate per service |

### Jaeger (http://localhost:16686)

Follow requests across `alert-ingestion → incident-management → oncall-service → notification-service`.

### Loki (via Grafana Explore)

```logql
{container=~".*incident-management.*"} |= "incident"
```

---

## CI/CD Pipeline (7 Stages)

```bash
make pipeline            # Run full local pipeline
make all-workflows       # Run all workflow stages
```

| Stage | Job | What It Does |
|-------|-----|-------------|
| 1 | **Quality** | Linting, syntax checks |
| 2 | **Security** | Secret scanning (GitLeaks) |
| 3 | **Build** | Docker image building, tagged by commit SHA |
| 4 | **Scan** | Container vulnerability scanning (Trivy) |
| 5 | **Test** | Unit tests across all services |
| 6 | **Deploy** | `docker compose down` + `docker compose up -d` |
| 7 | **Verify** | Health endpoint polling, integration checks |

Individual stages: `make workflow-quality`, `make workflow-security`, `make workflow-build`, `make workflow-scan`, `make workflow-test`, `make workflow-deploy`, `make workflow-verify`.

---

## Horizontal Scaling

```bash
make scale-demo REPLICAS=3                              # Scale incident-management
make scale-demo REPLICAS=3 SERVICE=alert-ingestion      # Scale alert-ingestion
```

Scales up, verifies health, demonstrates DNS round-robin load distribution, then scales back down. Prometheus auto-discovers new replicas via `dns_sd_configs`.

---

## Automated Rollback

```bash
make deploy-test-rollback SERVICE=incident-management   # Simulate bad deploy + auto-rollback
make deploy SERVICE=incident-management                  # Normal deploy
```

Tags current image as `:rollback`, deploys a broken build, detects health check failure, automatically restores the working image.

---

## Testing

```bash
make health              # Smoke tests (health checks)
make test-integration    # API integration tests
make test-e2e            # End-to-end workflow tests
make test-metrics        # Prometheus metrics validation
make test-load           # Load testing
make test-all            # Run all tests
```

---

## API Quick Reference

```bash
# Alerts
POST   /api/v1/alerts                      # Ingest alert (auto-creates/correlates incident)
GET    /api/v1/alerts/{id}                  # Get alert by ID

# Incidents
GET    /api/v1/incidents                    # List (filter: ?status=open&service=x&severity=y)
GET    /api/v1/incidents/{id}               # Detail (timeline, notes, MTTA/MTTR)
GET    /api/v1/incidents/{id}/metrics       # MTTA/MTTR for one incident
PATCH  /api/v1/incidents/{id}               # Update status / assignment
POST   /api/v1/incidents/{id}/notes         # Add a note

# On-Call
GET    /api/v1/schedules                    # List all schedules
POST   /api/v1/schedules                    # Create/update schedule
GET    /api/v1/oncall/current?team=x        # Current on-call for team
POST   /api/v1/escalate                     # Manual escalation

# Notifications
POST   /api/v1/notify                       # Send (channels: mock, email, webhook, slack)
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Services | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Frontend | React, TypeScript, Vite |
| Database | PostgreSQL 16 |
| Monitoring | Prometheus, Grafana, Loki, Promtail |
| Tracing | Jaeger, OpenTelemetry |
| Orchestration | Docker Compose |
| CI/CD | GitHub Actions + local shell scripts |
| Security | GitLeaks, Trivy |

---

## Development

```bash
make build                          # Build all images
make up                             # Start stack
make down                           # Stop stack
make re                             # Full rebuild and restart
make logs                           # Follow all logs
make status                         # Service status + metrics check
make clean                          # Remove everything (images, volumes)
```

---

## Documentation

- [Architecture Diagram & Request Flow](docs/ARCHITECTURE.md)
- [Improvements & Enhancements](docs/IMPROVEMENTS.md)
- Hackathon Spec: `scripts/hackathon_spec.txt`
- API Documentation: `/docs` on each service port

---

## Team

| Name | Role |
|------|------|
| **Abderrahmane Riyad** | Frontend Developer |
| **Yasser Rafai** | Backend Developer |
| **Ouadie El Fengour** | DevOps Engineer / Backend Developer |

---

Built in 24hrs for OpenSource Days Event — Hackathon 2026
