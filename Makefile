DC := docker compose -f deployment/docker-compose.yml --env-file deployment/.env
ENV_FILE := deployment/.env

.DEFAULT_GOAL := help

build:
	$(DC) build

up:
	$(DC) up

down:
	$(DC) down

logs:
	$(DC) logs -f

ps:
	$(DC) ps

re:
	@docker rm -f postgres prometheus grafana incident-management web-ui \
		alert-ingestion oncall-service notification-service gateway monitoring 2>/dev/null || true
	$(DC) down --volumes --remove-orphans
	$(DC) build
	$(DC) up -d

health:
	@bash scripts/smoke-test.sh

test-integration:
	@bash scripts/integration-test.sh

test-e2e:
	@bash scripts/e2e-test.sh

test-load:
	@bash scripts/load-test.sh

test-metrics:
	@bash scripts/metrics-test.sh

test-security:
	@bash scripts/security-scan.sh

test-quality:
	@bash scripts/quality-check.sh

test-all: health test-integration test-e2e test-metrics
	@echo ""
	@echo "✓ All tests completed!"

verify: test-integration test-e2e test-metrics
	@echo ""
	@echo "✓ Deployment verification passed!"

test-unit:
	@echo "==> Running unit tests with coverage..."
	@for svc in incident-management-service alert-ingestion-service oncall-service notification-service gateway-service; do \
		echo "  Testing $$svc..."; \
		cd $$svc && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=60 2>/dev/null && cd .. || { echo "  ✗ $$svc tests failed"; cd ..; }; \
	done
	@echo "✓ Unit tests completed!"

scale-demo:
	@bash scripts/scaling-demo.sh $(or $(REPLICAS),3) $(or $(SERVICE),incident-management)

deploy:
	@bash scripts/rollback.sh $(or $(SERVICE),incident-management)

deploy-test-rollback:
	@bash scripts/rollback.sh $(or $(SERVICE),incident-management) --simulate-failure

pipeline:
	@bash scripts/run-pipeline.sh

workflow-quality:
	@bash scripts/workflows-tests/quality-check-workflow.sh

workflow-security:
	@bash scripts/workflows-tests/security-scan-workflow.sh

workflow-build:
	@bash scripts/workflows-tests/build-images-workflow.sh

workflow-scan:
	@bash scripts/workflows-tests/scan-images-workflow.sh

workflow-test:
	@bash scripts/workflows-tests/test-unit-workflow.sh

workflow-deploy:
	@bash scripts/workflows-tests/deploy-stack-workflow.sh

workflow-verify:
	@bash scripts/workflows-tests/verify-deployment-workflow.sh

all-workflows: workflow-quality workflow-security workflow-build workflow-test workflow-deploy workflow-verify
	@echo ""
	@echo "✓ All workflow tests completed!"

workflow-act:
	@if ! command -v act >/dev/null 2>&1; then \
		echo "✗ 'act' is not installed. Install it with:"; \
		echo "  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"; \
		exit 1; \
	fi
	@act -W .github/workflows/pipeline.yml

clean:
	$(DC) down --rmi all --volumes --remove-orphans
	@docker system prune -f

export-openapi:
	@bash scripts/export-openapi.sh

status:
	@echo "==> Service Status"
	@$(DC) ps
	@echo ""
	@echo "==> Quick Metrics Check"
	@$(DC) exec -T incident-management curl -s http://localhost:8002/metrics 2>/dev/null | grep -E "incidents_total|incident_mtta|incident_mttr" || echo "Metrics not available"

.phony: build up down logs ps re health test-integration test-e2e test-load test-metrics test-security test-quality test-all test-unit verify scale-demo deploy deploy-test-rollback pipeline workflow-quality workflow-security workflow-build workflow-scan workflow-test workflow-deploy workflow-verify all-workflows workflow-act clean export-openapi status