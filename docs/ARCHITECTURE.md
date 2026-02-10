# Architecture

## System Overview

```mermaid
graph TB
    subgraph "External"
        USER["👤 User / Browser"]
    end

    subgraph "Edge Layer"
        WEBUI["🌐 Web UI<br/>(React + Nginx)<br/>:8080"]
        GW["🚪 Gateway Service<br/>(FastAPI)<br/>:8010"]
    end

    subgraph "Core Services"
        AI["🔔 Alert Ingestion<br/>(FastAPI + PostgreSQL)<br/>:8001"]
        IM["📋 Incident Management<br/>(FastAPI + PostgreSQL)<br/>:8002"]
        OC["📞 On-Call Service<br/>(FastAPI, in-memory)<br/>:8003"]
        NS["📣 Notification Service<br/>(FastAPI)<br/>:8004"]
    end

    subgraph "Observability Stack"
        PROM["📈 Prometheus<br/>:9090"]
        GRAF["📉 Grafana<br/>:3000"]
        LOKI["📝 Loki"]
        PROMTAIL["📋 Promtail"]
        JAEGER["🔍 Jaeger<br/>:16686"]
    end

    subgraph "Data Layer"
        PG[("🐘 PostgreSQL<br/>:5432")]
    end

    USER -->|"HTTP :8080"| WEBUI
    USER -->|"HTTP :8010"| GW
    WEBUI -->|"/api/v1/alerts"| AI
    WEBUI -->|"/api/v1/incidents"| IM
    WEBUI -->|"/api/v1/oncall/*"| OC
    GW -->|"proxy"| IM

    AI -->|"Create/correlate<br/>incidents"| IM
    IM -->|"Lookup on-call"| OC
    IM -->|"Send notifications"| NS

    AI --> PG
    IM --> PG

    PROM -->|"scrape /metrics"| AI
    PROM -->|"scrape /metrics"| IM
    PROM -->|"scrape /metrics"| OC
    PROM -->|"scrape /metrics"| NS
    PROM -->|"scrape /metrics"| GW
    GRAF -->|"query"| PROM
    GRAF -->|"query"| LOKI
    PROMTAIL -->|"push logs"| LOKI
    AI -.->|"traces"| JAEGER
    IM -.->|"traces"| JAEGER
    OC -.->|"traces"| JAEGER
    NS -.->|"traces"| JAEGER

    classDef edge fill:#4F46E5,stroke:#312E81,color:#fff
    classDef core fill:#059669,stroke:#064E3B,color:#fff
    classDef obs fill:#D97706,stroke:#92400E,color:#fff
    classDef data fill:#2563EB,stroke:#1E3A5F,color:#fff
    classDef ext fill:#6B7280,stroke:#374151,color:#fff

    class USER ext
    class WEBUI,GW edge
    class AI,IM,OC,NS core
    class PROM,GRAF,LOKI,PROMTAIL,JAEGER obs
    class PG data
```

## Request Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Web UI (nginx)
    participant AI as Alert Ingestion
    participant IM as Incident Mgmt
    participant OC as On-Call
    participant NS as Notification
    participant DB as PostgreSQL

    User->>UI: POST /api/v1/alerts
    UI->>AI: proxy → POST /api/v1/alerts
    AI->>DB: Check existing open incidents (correlation)
    alt New incident
        AI->>DB: INSERT alert + incident
        AI->>IM: POST /api/v1/incidents (create)
        IM->>DB: INSERT incident row
        IM->>OC: GET /api/v1/oncall/current
        OC-->>IM: {engineer, team}
        IM->>NS: POST /api/v1/notify
        NS-->>IM: 202 Accepted
        IM-->>AI: {incident_id, action: "created"}
    else Correlated to existing
        AI->>DB: INSERT alert, UPDATE incident
        AI-->>User: {incident_id, action: "correlated"}
    end
    AI-->>UI: JSON response
    UI-->>User: Display result
```

## Deployment Topology

| Service               | Host Port | Internal Port | Scalable | Notes                        |
|-----------------------|-----------|---------------|----------|------------------------------|
| web-ui (nginx)        | 8080      | 8080          | ✗        | Static SPA + reverse proxy   |
| gateway               | 8010      | 8000          | ✗        | API gateway / proxy          |
| alert-ingestion       | —         | 8001          | ✓        | No host port; via nginx      |
| incident-management   | —         | 8002          | ✓        | No host port; via nginx      |
| oncall-service        | 8003      | 8003          | ✗        | In-memory schedules          |
| notification-service  | 8004      | 8004          | ✗        | Multi-channel (mock/email)   |
| PostgreSQL            | —         | 5432          | ✗        | Persistent volume            |
| Prometheus            | 9090      | 9090          | ✗        | dns_sd_configs for scaling   |
| Grafana               | 3000      | 3000          | ✗        | 3 dashboards auto-provisioned|
| Loki                  | —         | 3100          | ✗        | Log aggregation              |
| Promtail              | —         | 9080          | ✗        | Log shipper                  |
| Jaeger                | 16686     | 16686         | ✗        | Distributed tracing          |

## Docker Secrets

Sensitive credentials are managed via Docker Compose file-based secrets
(`deployment/secrets/`). Each Python service reads them at startup via
`_read_secret()` — no passwords are baked into images or environment variables.
