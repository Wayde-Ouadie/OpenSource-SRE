# OpenSource Incident & On-Call Platform (Local Edition)

[![Health](https://img.shields.io/badge/health-passing-brightgreen)]()
[![Services](https://img.shields.io/badge/services-8-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688)]()

Production-ready incident management and on-call platform built with microservices architecture, full observability, and DevOps best practices.

> 📐 **[Architecture Diagram & Request Flow →](docs/architecture.md)**

## 🚀 Quick Start

```bash
# Start the entire stack
make up

# Or rebuild and restart everything
make re

# Check health
make health

# Run all tests
make test-all

# View logs
make logs
```

**Access Points:**
- 🌐 Web UI: http://localhost:8080
- 📊 Grafana: http://localhost:3000 (admin/admin)
- 📈 Prometheus: http://localhost:9090
- 📚 API Docs: http://localhost:8002/docs (and other services)

## 📋 Architecture

6 microservices + monitoring stack:

```
Services:
├── alert-ingestion (8001)      - Receives and correlates alerts
├── incident-management (8002)  - Core incident lifecycle management
├── oncall-service (8003)       - On-call scheduling and escalation
├── notification-service (8004) - Multi-channel notifications
├── gateway (8010)              - API gateway
└── web-ui (8080)               - React frontend

Infrastructure:
├── postgres (5432)             - PostgreSQL database
├── prometheus (9090)           - Metrics collection
└── grafana (3000)              - Dashboards and visualization
```

## 💡 Key Features

✅ **Complete Incident Lifecycle** - Create, acknowledge, resolve with MTTA/MTTR tracking  
✅ **Smart Alert Correlation** - Automatically groups related alerts  
✅ **On-Call Management** - Weekly/daily rotations with escalation  
✅ **Multi-Channel Notifications** - Mock notifications with extensible channels  
✅ **Full Observability** - Prometheus metrics + Grafana dashboards  
✅ **API Documentation** - Auto-generated Swagger UI for all services  
✅ **Request Tracing** - X-Request-ID for distributed debugging  
✅ **Structured Logging** - JSON logs with context  
✅ **Resilient Communication** - HTTP retry logic and timeouts  

## 🔧 API Examples

### Create Alert
```bash
curl -X POST http://localhost:8001/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-api",
    "severity": "high",
    "message": "High error rate detected",
    "labels": {"environment": "production"}
  }'
```

### List Incidents
```bash
curl http://localhost:8002/api/v1/incidents?status=open
```

### Create On-Call Schedule
```bash
curl -X POST http://localhost:8003/api/v1/schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "team": "platform-engineering",
    "primary": ["alice", "bob", "carol"],
    "secondary": ["dave"],
    "rotation": "weekly"
  }'
```

### Get Current On-Call
```bash
curl "http://localhost:8003/api/v1/oncall/current?team=platform-engineering"
```

## 🧪 Testing

```bash
make health              # Health checks for all services
make test-integration    # API integration tests
make test-e2e            # End-to-end workflow tests
make test-metrics        # Prometheus metrics validation
make test-all            # Run all tests
```

## 📊 Monitoring & Metrics

### Grafana Dashboards
1. **Live Incident Overview** (http://localhost:3000)
   - Open incidents by severity
   - MTTA/MTTR gauges
   - Incident timeline
   - Top noisy services

2. **SRE Performance Metrics**
   - MTTA/MTTR trends
   - Incident volume by service
   - Acknowledgment time distribution

### Custom Metrics
All services expose `/metrics` endpoints:
- `incidents_total{status}` - Incident counter by status
- `incident_mtta_seconds` - Time to acknowledge (histogram)
- `incident_mttr_seconds` - Time to resolve (histogram)
- `alerts_received_total{severity}` - Alert counter
- `oncall_notifications_sent_total{channel}` - Notification counter

## 🏗️ Tech Stack

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL 16
- **Monitoring**: Prometheus + Grafana
- **Orchestration**: Docker Compose
- **Language**: Python 3.12
- **ORM**: SQLAlchemy 2.0

## 📚 Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Detailed list of professional enhancements
- API Documentation: Visit `/docs` on any service port
- Hackathon Spec: See `scripts/hackathon_spec.txt`

## 🛠️ Development

```bash
# Rebuild specific service
docker compose -f deployment/docker-compose.yml build incident-management

# Restart specific service
docker compose -f deployment/docker-compose.yml restart incident-management

# Shell into container
docker exec -it incident-management bash

# View service logs
docker logs -f incident-management

# Clean everything
make clean
```

## 🔐 Environment Variables

Key configurations (see `deployment/.env`):
```bash
DATABASE_URL=postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management
INCIDENT_MGMT_BASE_URL=http://incident-management:8002
ONCALL_BASE_URL=http://oncall-service:8003
NOTIFICATION_BASE_URL=http://notification-service:8004
```

## 📝 CI/CD Pipeline

7-stage automated pipeline:
```bash
make pipeline                # Run local CI/CD pipeline
make all-workflows          # Run all workflow tests
make workflow-act           # Run with 'act' (GitHub Actions locally)
```

> **Note:** `make workflow-act` requires [act](https://github.com/nektos/act) to be installed:
> ```bash
> curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
> ```

Stages:
1. **Quality** - Code linting and basic checks
2. **Security** - Secret scanning with GitLeaks
3. **Build** - Docker image building
4. **Scan** - Container vulnerability scanning (Trivy)
5. **Test** - Integration and E2E tests
6. **Deploy** - Stack deployment
7. **Verify** - Post-deployment verification

## 🎯 Project Status

**Current State**: ✅ Professional skeleton with health endpoints  
**What Works**:
- All services running and healthy
- Database connectivity
- Service-to-service communication
- Prometheus metrics collection
- Grafana dashboards
- API documentation
- Request tracing
- Structured logging

**Next Phase**: Extend with full business logic (incident workflows, attachment management, etc.)

## 📄 License

See [LICENSE](LICENSE) file.

## 👥 Team

| Name | Role |
|---|---|
| **Abderrahmane Riyad** | Frontend Developer |
| **Yasser Rafai** | Backend Developer |
| **Ouadie El Fengour** | DevOps Engineer / Backend Developer |

## 🤝 Contributing

Built for OpenSource Days Event - Hackathon 2026

---

**Status**: 🟢 Healthy | **Services**: 8/8 Running | **Coverage**: Professional-grade skeleton

