# 🎬 Platform Showcase Guide

> A step-by-step walkthrough to demonstrate the full Incident Management Platform — from firing an alert to resolving an incident, complete with on-call rotation, notifications, observability, scaling, and automated rollback.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Start the Platform](#2-start-the-platform)
3. [Verify All Services Are Healthy](#3-verify-all-services-are-healthy)
4. [Set Up On-Call Schedules](#4-set-up-on-call-schedules)
5. [Fire an Alert (Automatic Incident Creation)](#5-fire-an-alert-automatic-incident-creation)
6. [Explore the Web UI](#6-explore-the-web-ui)
7. [Walk Through the Incident Lifecycle](#7-walk-through-the-incident-lifecycle)
8. [Trigger Auto-Escalation](#8-trigger-auto-escalation)
9. [Webhook & Email Notifications](#9-webhook--email-notifications)
10. [Observability Deep-Dive](#10-observability-deep-dive)
11. [Horizontal Scaling Demo](#11-horizontal-scaling-demo)
12. [Automated Rollback Demo](#12-automated-rollback-demo)
13. [Run the Full Test Suite](#13-run-the-full-test-suite)
14. [Quick Reference — Ports & URLs](#14-quick-reference--ports--urls)

---

## 1. Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker | 24+ |
| Docker Compose | v2+ (bundled with Docker Desktop) |
| `curl` | any |
| `jq` *(optional but recommended)* | any |

### Prepare secrets

```bash
# Create the secrets directory (skip if it already exists)
mkdir -p deployment/secrets

# Set a Postgres password
echo "supersecret" > deployment/secrets/postgres_password.txt

# Set a Resend API key (use "PLACEHOLDER" if you don't have one — email won't send but everything else works)
echo "PLACEHOLDER" > deployment/secrets/resend_api_key.txt
```

---

## 2. Start the Platform

```bash
# Build all images and start in detached mode
make build
make up
# or in one shot:
# make re
```

> **First run** takes 2-3 minutes while images build and Postgres initialises.

---

## 3. Verify All Services Are Healthy

```bash
make health
```

Or check manually:

```bash
curl -s http://localhost:8080/health        # web-ui (nginx)
curl -s http://localhost:8003/health        # oncall-service
curl -s http://localhost:8004/health        # notification-service
curl -s http://localhost:8010/health        # gateway
curl -s http://localhost:9090/-/healthy     # prometheus
curl -s http://localhost:3000/api/health    # grafana
```

> `incident-management` and `alert-ingestion` are internal (no fixed host port); they're reachable through the **web-ui** nginx proxy on `:8080`.

```bash
curl -s http://localhost:8080/api/health                        # proxied to incident-management
curl -s http://localhost:8080/api/v1/incidents | jq .count      # list incidents
```

---

## 4. Set Up On-Call Schedules

Before alerts trigger useful assignment, create on-call rotation schedules:

```bash
# Team: "payment-service" — primary rotation: alice → bob, secondary: charlie
curl -s -X POST http://localhost:8003/api/v1/schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "team": "payment-service",
    "primary": ["alice", "bob"],
    "secondary": ["charlie"],
    "rotation": "daily"
  }' | jq .

# Team: "auth-service" — weekly rotation
curl -s -X POST http://localhost:8003/api/v1/schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "team": "auth-service",
    "primary": ["dave", "eve"],
    "secondary": ["frank"],
    "rotation": "weekly"
  }' | jq .
```

Verify the current on-call:

```bash
curl -s "http://localhost:8003/api/v1/oncall/current?team=payment-service" | jq .
```

Expected:

```json
{
  "team": "payment-service",
  "primary": "alice",
  "secondary": "charlie",
  "rotation": "daily",
  "as_of": "2025-..."
}
```

---

## 5. Fire an Alert (Automatic Incident Creation)

This is the **main demo moment** — a single alert triggers the whole pipeline:

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

Expected response:

```json
{
  "alert_id": "a1b2c3d4-...",
  "incident_id": "e5f6a7b8-...",
  "status": "correlated",
  "action": "created_new_incident"
}
```

### What just happened (behind the scenes)

```
┌──────────────┐    ┌──────────────────────┐    ┌──────────────────┐
│ Alert Ingest │───▶│ Incident Management  │───▶│  On-Call Service  │
│  :8001       │    │  :8002               │    │  :8003            │
│              │    │  • created incident   │    │  • looked up      │
│  • validated │    │  • severity=critical  │    │    "alice"        │
│  • normlized │    │  • assigned_to=alice  │    └──────────────────┘
│  • stored    │    │  • timeline started   │            │
└──────────────┘    └──────────────────────┘            │
                             │                          ▼
                             │               ┌──────────────────┐
                             └──────────────▶│  Notification    │
                                             │  :8004           │
                                             │  • mock channel  │
                                             │  • logged + sent │
                                             └──────────────────┘
```

### Send a second alert for the **same** service within 5 minutes

```bash
curl -s -X POST http://localhost:8080/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-service",
    "severity": "critical",
    "message": "Payment gateway — connection refused",
    "labels": {"environment": "production"}
  }' | jq .
```

This time the `action` will be `"attached_to_existing_incident"` — the alert is **correlated** to the same incident, demonstrating deduplication.

---

## 6. Explore the Web UI

Open your browser to **[http://localhost:8080](http://localhost:8080)**.

| Page | What You'll See |
|------|----------------|
| **Dashboard** | Live incident count, severity breakdown chart, sortable table of all incidents |
| **Incident Detail** *(click any row)* | Full timeline, notes, status transitions, MTTA/MTTR metrics, assignment info |
| **Metrics** | MTTA/MTTR charts, incident trend over time, severity distribution (Recharts) |
| **On-Call** | Current rotation schedules, team cards, primary/secondary engineers |

---

## 7. Walk Through the Incident Lifecycle

Save the `incident_id` from Step 5 (or copy it from the Web UI), then walk through each state:

```bash
INCIDENT_ID="<paste-your-incident-id-here>"
```

### 7a. Acknowledge

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"status": "acknowledged"}' | jq .
```

> This records **MTTA** (Mean Time to Acknowledge).

### 7b. Move to In-Progress

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"status": "in_progress"}' | jq .
```

### 7c. Add an Investigation Note

```bash
curl -s -X POST "http://localhost:8080/api/v1/incidents/$INCIDENT_ID/notes" \
  -H 'Content-Type: application/json' \
  -d '{"content": "Root cause identified: connection pool exhaustion in PG bouncer", "author": "alice"}' | jq .
```

### 7d. Resolve

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"status": "resolved"}' | jq .
```

> This records **MTTR** (Mean Time to Resolve).

### 7e. Verify the full timeline

```bash
curl -s "http://localhost:8080/api/v1/incidents/$INCIDENT_ID" | jq '.timeline'
```

You'll see timestamped entries for:  
`created → status_change(acknowledged) → status_change(in_progress) → note_added → status_change(resolved)`

---

## 8. Trigger Auto-Escalation

The on-call service runs a background loop that checks for open incidents **unacknowledged for >5 minutes** (configurable via `ESCALATION_THRESHOLD_MINUTES`).

### Demo it in real time

```bash
# 1. Create a fresh incident that we intentionally DON'T acknowledge
curl -s -X POST http://localhost:8080/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-service",
    "severity": "high",
    "message": "Disk usage above 90% on payment-db-primary"
  }' | jq .

# 2. Wait 5+ minutes (the escalation loop runs every 60s by default)
echo "Waiting for auto-escalation... (check oncall-service logs)"

# 3. Watch the logs
docker compose -f deployment/docker-compose.yml logs -f oncall-service
```

After the threshold, you'll see:

```
Auto-escalating incident <id> for service payment-service (unacknowledged for >5min)
```

The incident will be **reassigned** from the primary engineer (alice) to the secondary (charlie), and an **escalation notification** is sent.

### Speed it up for demos

Set a shorter threshold before starting:

```bash
# In deployment/docker-compose.yml, add to oncall-service environment:
#   ESCALATION_THRESHOLD_MINUTES: "1"
#   ESCALATION_CHECK_INTERVAL: "15"
```

---

## 9. Webhook & Email Notifications

### 9a. Mock Channel (default)

Every notification is logged to stdout. View with:

```bash
docker compose -f deployment/docker-compose.yml logs notification-service | grep "Notification processed"
```

### 9b. Webhook Delivery

Fire a notification with a webhook target:

```bash
# Start a temporary webhook receiver (in a separate terminal)
python3 -m http.server 9999 &

# Send a webhook notification
curl -s -X POST http://localhost:8004/api/v1/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "test-123",
    "message": "Critical incident requires attention",
    "channel": "webhook",
    "target": "http://host.docker.internal:9999/webhook"
  }' | jq .
```

> **Note:** Use `http://host.docker.internal:9999` on Docker Desktop, or the host's Docker bridge IP on Linux.

The webhook POSTs a JSON body:

```json
{
  "incident_id": "test-123",
  "message": "Critical incident requires attention",
  "timestamp": "2025-..."
}
```

### 9c. Email via Resend

If you have a [Resend](https://resend.com) API key:

```bash
# 1. Update the secret
echo "re_your_actual_key" > deployment/secrets/resend_api_key.txt

# 2. Restart notification-service
docker compose -f deployment/docker-compose.yml restart notification-service

# 3. Send
curl -s -X POST http://localhost:8004/api/v1/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "email-test-001",
    "message": "Production database failover completed",
    "channel": "email",
    "target": "you@example.com"
  }' | jq .
```

---

## 10. Observability Deep-Dive

### Prometheus (Metrics)

Open **[http://localhost:9090](http://localhost:9090)** and try these queries:

| Query | What It Shows |
|-------|--------------|
| `incidents_total` | Total incidents by status |
| `alerts_received_total` | Alerts ingested by severity |
| `alerts_correlated_total` | New vs. correlated alert ratio |
| `incident_mtta_seconds` | Acknowledge time histogram |
| `incident_mttr_seconds` | Resolution time histogram |
| `notifications_sent_total` | Notifications by channel & status |
| `escalations_total` | Auto-escalation count by team |
| `oncall_current` | Current on-call engineer gauge |

### Grafana Dashboards

Open **[http://localhost:3000](http://localhost:3000)** (login: `admin` / `admin`).

Three pre-built dashboards:

| Dashboard | Content |
|-----------|---------|
| **Live Incident Overview** | Active incidents, severity breakdown, MTTA/MTTR trends |
| **SRE Performance Metrics** | Service-level MTTA/MTTR, on-call load, escalation rate |
| **System Health** | CPU, memory, HTTP request rate, error rate per service |

### Jaeger (Distributed Tracing)

Open **[http://localhost:16686](http://localhost:16686)**.

- Select a service (e.g. `alert-ingestion-service`) and click **Find Traces**.
- Follow a request through `alert-ingestion → incident-management → oncall-service → notification-service`.

### Loki (Logs)

View centralized logs in Grafana → **Explore** → select the **Loki** datasource:

```logql
{container=~".*incident-management.*"} |= "incident"
```

---

## 11. Horizontal Scaling Demo

Demonstrate that `incident-management` and `alert-ingestion` can be horizontally scaled with zero downtime:

```bash
# Scale to 3 replicas (also verifies health, DNS round-robin, and load distribution)
make scale-demo REPLICAS=3

# Or pick a specific service
make scale-demo REPLICAS=3 SERVICE=alert-ingestion
```

The script will:

1. Show current state (1 replica)
2. Scale to N replicas
3. Wait for all replicas to pass health checks
4. Verify Docker DNS round-robin resolution
5. Send test traffic and show load distributed across replicas
6. Scale back down to 1

> Prometheus automatically discovers new replicas via `dns_sd_configs`.

---

## 12. Automated Rollback Demo

Show that a bad deployment is automatically detected and rolled back:

### Simulate a failing deploy

```bash
make deploy-test-rollback SERVICE=incident-management
```

This will:

1. Tag the current working image as `:rollback`
2. Build a new image with a deliberately broken entrypoint
3. Deploy the broken image
4. Detect that health checks fail
5. **Automatically restore** the rollback image
6. Verify the service is healthy again

### Normal deploy (no failure)

```bash
make deploy SERVICE=incident-management
```

---

## 13. Run the Full Test Suite

```bash
# Smoke tests (health checks)
make health

# Integration tests
make test-integration

# End-to-end: Alert → Incident → Acknowledge → Resolve
make test-e2e

# Prometheus metrics validation
make test-metrics

# Load testing
make test-load

# Run all tests in sequence
make test-all
```

---

## 14. Quick Reference — Ports & URLs

| Service | Port | URL |
|---------|------|-----|
| **Web UI** | 8080 | [http://localhost:8080](http://localhost:8080) |
| **On-Call Service** | 8003 | [http://localhost:8003/docs](http://localhost:8003/docs) |
| **Notification Service** | 8004 | [http://localhost:8004/docs](http://localhost:8004/docs) |
| **Gateway** | 8010 | [http://localhost:8010/docs](http://localhost:8010/docs) |
| **Prometheus** | 9090 | [http://localhost:9090](http://localhost:9090) |
| **Grafana** | 3000 | [http://localhost:3000](http://localhost:3000) |
| **Jaeger** | 16686 | [http://localhost:16686](http://localhost:16686) |
| **PostgreSQL** | 5432 | `psql -h localhost -U opensource -d incident_management` |

> `incident-management` (:8002) and `alert-ingestion` (:8001) are internal-only — access them through the web-ui nginx proxy on `:8080` or via the gateway on `:8010`.

### API Quick-Reference

```bash
# Alerts
POST   /api/v1/alerts                      # Ingest an alert (auto-creates/correlates incident)
GET    /api/v1/alerts/{id}                  # Get alert by ID

# Incidents
GET    /api/v1/incidents                    # List (filter: ?status=open&service=x&severity=y)
GET    /api/v1/incidents/{id}               # Detail (includes timeline, notes, MTTA/MTTR)
GET    /api/v1/incidents/{id}/metrics       # MTTA/MTTR for one incident
PATCH  /api/v1/incidents/{id}               # Update status / assignment
POST   /api/v1/incidents/{id}/notes         # Add a note

# On-Call
GET    /api/v1/schedules                    # List all schedules
POST   /api/v1/schedules                    # Create/update a schedule
GET    /api/v1/oncall/current?team=x        # Current on-call for a team
POST   /api/v1/escalate                     # Manual escalation

# Notifications
POST   /api/v1/notify                       # Send notification (channels: mock, email, webhook, slack)
```

---

## 🏁 One-Liner Full Demo

If you want to run the entire happy path in one shot:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "📋 Creating on-call schedule..."
curl -s -X POST http://localhost:8003/api/v1/schedules \
  -H 'Content-Type: application/json' \
  -d '{"team":"demo-service","primary":["alice","bob"],"secondary":["charlie"],"rotation":"daily"}' | jq .

echo -e "\n🚨 Firing alert..."
RESP=$(curl -s -X POST http://localhost:8080/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{"service":"demo-service","severity":"critical","message":"CPU spike to 98% on web-prod-03","labels":{"env":"prod"}}')
echo "$RESP" | jq .
INC=$(echo "$RESP" | jq -r .incident_id)

sleep 1

echo -e "\n📌 Acknowledging..."
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INC" \
  -H 'Content-Type: application/json' -d '{"status":"acknowledged"}' | jq .

echo -e "\n🔧 Moving to in-progress..."
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INC" \
  -H 'Content-Type: application/json' -d '{"status":"in_progress"}' | jq .

echo -e "\n📝 Adding note..."
curl -s -X POST "http://localhost:8080/api/v1/incidents/$INC/notes" \
  -H 'Content-Type: application/json' \
  -d '{"content":"Identified runaway process, killed PID 4521","author":"alice"}' | jq .

sleep 1

echo -e "\n✅ Resolving..."
curl -s -X PATCH "http://localhost:8080/api/v1/incidents/$INC" \
  -H 'Content-Type: application/json' -d '{"status":"resolved"}' | jq .

echo -e "\n📊 Final incident state:"
curl -s "http://localhost:8080/api/v1/incidents/$INC" | jq '{status, severity, assigned_to, mtta_seconds, mttr_seconds, timeline: [.timeline[].detail]}'

echo -e "\n🎉 Demo complete!"
```

Copy-paste the above, save as `demo.sh`, run `chmod +x demo.sh && ./demo.sh`, and you have a full end-to-end showcase in under 10 seconds.
