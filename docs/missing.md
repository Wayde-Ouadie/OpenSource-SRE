# Deductions & Missing Items — Hackathon Evaluation

## Final Score: 86 / 100 (Grade: A-)

---

## 1. Platform Functionality (26 / 30) — Deductions: -4

### -2 | Web UI silent mock fallback
**File:** `web-ui-service/src/services/api.ts`
**Issue:** When the backend is unreachable, the UI silently falls back to hardcoded mock data (`mockIncidents`, `mockOnCall`, etc.) instead of showing an error state. This could mislead judges during evaluation if backend services fail to start — the UI would appear functional with fake data.
**Fix:** Show an error banner or toast when API calls fail, rather than silently returning mock data.

### -1 | On-call schedules are not persisted
**File:** `oncall-service/app/main.py`
**Issue:** Schedules are stored in an in-memory Python dictionary (`SCHEDULES: dict[str, dict[str, Any]] = {}`). If the on-call service container restarts, all schedules are lost. The spec expects data persistence.
**Fix:** Store schedules in PostgreSQL or a local SQLite volume-mounted file.

### -1 | Missing `GET /api/v1/alerts` list endpoint
**File:** `alert-ingestion-service/app/main.py`
**Issue:** The spec requires listing alerts, but only `GET /api/v1/alerts/{alert_id}` (single alert) exists. There is no endpoint to list all alerts or filter them. The spec lists `GET /api/v1/alerts/{alert_id}` and implies a list endpoint.
**Fix:** Add a `GET /api/v1/alerts` endpoint with optional filters (service, severity, limit).

---

## 2. DevOps Implementation (27 / 30) — Deductions: -3

### -1 | Test coverage threshold not enforced in pipeline
**File:** `scripts/run-pipeline.sh` (Stage 5), `Makefile` (`test-unit` target)
**Issue:** The pipeline runs `python -m pytest tests/ -v --tb=short` but never passes `--cov` or `--cov-fail-under=60`. The `fail_under = 60` in `pyproject.toml` is dead configuration — it's never invoked. The pipeline will pass even with 0% coverage.
**Fix:** Change the pytest invocation to: `python -m pytest tests/ -v --tb=short --cov=app --cov-report=term --cov-fail-under=60`

### -1 | PostgreSQL port exposed to host unnecessarily
**File:** `deployment/docker-compose.yml` (line ~21)
**Issue:** `ports: - "${POSTGRES_PORT:-5432}:5432"` exposes the database to localhost. The database should only be reachable within the Docker network. Exposing it is a security risk and violates container security best practices.
**Fix:** Replace `ports:` with `expose: ["5432"]` or remove the port mapping entirely (services already connect over the Docker network).

### -1 | Linter not actually executed in quality checks
**File:** `scripts/quality-check.sh`, `scripts/workflows-tests/quality-check-workflow.sh`
**Issue:** The quality check script only runs `python -m compileall` (syntax validation). The Ruff linter is fully configured in `pyproject.toml` with sensible rules (`E`, `W`, `F`, `I`, `B`, `UP`, `SIM`, `RUF`) but is never executed. The script says "pylint not installed (skipping)" and moves on.
**Fix:** Add `ruff check incident-management-service/ alert-ingestion-service/ oncall-service/ notification-service/ gateway-service/` to the quality check scripts.

---

## 3. Monitoring & SRE Metrics (18 / 20) — Deductions: -2

### -1 | Metric naming mismatch with spec
**File:** `notification-service/app/main.py`
**Issue:** The spec requires metric `oncall_notifications_sent_total{channel="mock|webhook"}`. The service defines both `notifications_sent_total` and `oncall_notifications_sent_total`, but the `metrics-test.sh` checks for `oncall_notifications_sent_total` only on the notification service. The separation between the two counters is unclear and slightly inconsistent with the spec's single metric expectation.
**Fix:** Clarify the purpose of each counter or consolidate into the spec-required name.

### -1 | Grafana dashboards lack advanced PromQL
**Files:** `monitoring-service/grafana/dashboards/*.json`
**Issue:** While all 3 dashboards are present and auto-provisioned (which is excellent), the dashboard queries could be more sophisticated. The spec asks for MTTA/MTTR "moving averages" and "trends" — using `rate()` or `histogram_quantile()` over sliding windows. The current dashboards use basic instant queries. No Grafana alerting rules are configured (only Prometheus alerting rules exist in `alert_rules.yml`).
**Fix:** Use `histogram_quantile(0.95, rate(incident_mtta_seconds_bucket[1h]))` for p95 MTTA trend panels. Add Grafana alert rules for SRE thresholds.

---

## 4. Architecture & Design (12 / 15) — Deductions: -3

### -1 | Gateway service adds minimal value
**File:** `gateway-service/app/main.py`
**Issue:** The gateway service is a very thin FastAPI app that only proxies `/api/health` to incident-management. All real API routing is handled by the nginx config in `web-ui-service/nginx.conf`. The gateway service counts toward the "6 services" number but doesn't provide meaningful functionality like rate limiting, auth, or request aggregation.
**Fix:** Either enrich the gateway with actual gateway functionality (rate limiting, auth middleware, request logging aggregation) or remove it and document nginx as the API gateway.

### -1 | Shared database without schema separation
**Files:** `alert-ingestion-service/app/main.py`, `incident-management-service/app/main.py`
**Issue:** Both services connect to the same PostgreSQL database (`incident_management`) and both call `Base.metadata.create_all()` at startup. While they use separate tables (`alerts` vs `incidents`), there is no schema separation (e.g., `alert_schema.alerts` vs `incident_schema.incidents`). The spec states: "Each service manages its own data (can share database with schema separation)."
**Fix:** Use PostgreSQL schemas: `CREATE SCHEMA alert_ingestion;` and `CREATE SCHEMA incident_management;` and prefix table names accordingly.

### -1 | No static OpenAPI spec committed
**Issue:** FastAPI generates excellent interactive API docs at `/docs` at runtime, but no static `openapi.json` or `openapi.yaml` file is committed to the repository. The spec submission requirements include "API documentation (OpenAPI spec or equivalent)." Judges reviewing the repo without running containers won't see the API documentation.
**Fix:** Export and commit OpenAPI specs: `curl http://localhost:8002/openapi.json > docs/openapi-incident-management.json` for each service.

---

## 5. Security & Quality (3 / 5) — Deductions: -2

### -1 | Test coverage is configured but never measured
**Files:** `pyproject.toml`, `scripts/run-pipeline.sh`, `Makefile`
**Issue:** `pyproject.toml` has `[tool.coverage.report] fail_under = 60` and `[tool.coverage.run] source = ["app"]` — but no script or pipeline step ever runs `pytest --cov`. The coverage tool is fully configured but never invoked. The hackathon requires "Test coverage ≥ 60% (FAIL if below)" as a hard constraint.
**Fix:** Update `Makefile` `test-unit` target:
```
cd $$svc && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=60 && cd ..
```

### -1 | Ruff linter configured but never run
**Files:** `pyproject.toml`, `scripts/quality-check.sh`
**Issue:** Ruff is configured with a comprehensive rule set in `pyproject.toml` (`E`, `W`, `F`, `I`, `B`, `UP`, `SIM`, `RUF`) but no pipeline stage ever runs `ruff check`. The quality check script falls back to `python -m compileall` (basic syntax check only). The spec requires "Linter passes" as a hard constraint under Code Quality.
**Fix:** Add `pip install ruff` to CI dependencies and run `ruff check .` in `quality-check.sh` and `quality-check-workflow.sh`.

---

## Summary Table

| Category | Score | Max | Deductions |
|---|---|---|---|
| Platform Functionality | 26 | 30 | -4 |
| DevOps Implementation | 27 | 30 | -3 |
| Monitoring & SRE Metrics | 18 | 20 | -2 |
| Architecture & Design | 12 | 15 | -3 |
| Security & Quality | 3 | 5 | -2 |
| **TOTAL** | **86** | **100** | **-14** |
