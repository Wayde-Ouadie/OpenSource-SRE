#!/usr/bin/env bash
# Code quality checks: Linting and static analysis
set -euo pipefail

echo "==> Running code quality checks..."
echo

FAILED=0

# 1. Python code quality
echo "1. Python Services - Syntax Check"
python_services=(
    " incident-management-service"
    "alert-ingestion-service"
    "oncall-service"
    "notification-service"
    "gateway-service"
    "monitoring-service"
)

for service in "${python_services[@]}"; do
    echo -n "  $service... "
    if python -m compileall -q "$service" 2>/dev/null; then
        echo "✓ OK"
    else
        echo "✗ SYNTAX ERRORS"
        FAILED=1
    fi
done

# 2. Check for Python linting (if tools available)
echo
echo "2. Python Linting (if available)"
if command -v pylint >/dev/null 2>&1; then
    for service in "${python_services[@]}"; do
        echo "  Linting $service..."
        pylint "$service" --exit-zero --score=yes || true
    done
else
    echo "  ⊘ pylint not installed (skipping)"
fi

# 3. JavaScript/TypeScript quality (web-ui)
echo
echo "3. Web UI - Build & Lint"
if [ -d "web-ui-service" ]; then
    echo -n "  Installing dependencies... "
    (cd web-ui-service && npm ci --silent) && echo "✓ OK" || { echo "✗ FAILED"; FAILED=1; }
    
    echo -n "  Building... "
    (cd web-ui-service && npm run build --silent) && echo "✓ OK" || { echo "✗ FAILED"; FAILED=1; }
    
    if [ -f "web-ui-service/package.json" ] && grep -q "\"lint\"" "web-ui-service/package.json"; then
        echo -n "  Linting... "
        (cd web-ui-service && npm run lint --silent) && echo "✓ OK" || { echo "⚠ WARNINGS"; }
    fi
fi

# 4. Dockerfile best practices
echo
echo "4. Dockerfile Best Practices"
dockerfiles=$(find . -name "Dockerfile" -not -path "*/node_modules/*")
for df in $dockerfiles; do
    echo -n "  $(dirname $df)/Dockerfile... "
    
    issues=0
    # Check for multi-stage builds
    if ! grep -q "^FROM.*AS" "$df"; then
        echo -n "[no multi-stage] "
        issues=$((issues + 1))
    fi
    
    # Check for non-root user
    if ! grep -q "^USER" "$df"; then
        echo -n "[runs as root] "
        issues=$((issues + 1))
    fi
    
    # Check for HEALTHCHECK
    if ! grep -q "^HEALTHCHECK" "$df"; then
        echo -n "[no healthcheck] "
        issues=$((issues + 1))
    fi
    
    if [ $issues -eq 0 ]; then
        echo "✓ OK"
    else
        echo "⚠ $issues issues"
    fi
done

# 5. Check docker-compose.yml validity
echo
echo "5. Docker Compose Configuration"
echo -n "  Validating docker-compose.yml... "
if docker-compose -f deployment/docker-compose.yml config >/dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ INVALID"
    FAILED=1
fi

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ Code quality checks passed!"
    exit 0
else
    echo "✗ Some quality checks failed"
    exit 1
fi
