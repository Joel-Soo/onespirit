# Copilot: Smoke Check Script and Steps (2025-11-19)

A “quick smoke” is a fast sanity check that the basics work. It’s not exhaustive—just enough to catch obvious breakages before deeper testing.

- Definition: Minimal checks to ensure core services start and critical commands succeed.
- Goal: Quick confidence, not full validation; fail fast if something’s clearly wrong.

## One-Command Smoke Script

Copy-paste and run from the repo root to run the smoke and get a PASS/FAIL summary for each step.

```bash
# Smoke check for OneSpirit dev stack
# Run from repo root

set -u  # continue on failures; we capture exit codes manually

step() { echo; echo "==> $1"; }
result() {
  code=$1; name=$2
  if [ "$code" -eq 0 ]; then echo "[PASS] $name"; else echo "[FAIL] $name (exit $code)"; fi
  return "$code"
}

OVERALL_OK=0

step "Start Postgres"
docker compose up -d postgres
CID=$(docker compose ps -q postgres)
if [ -z "${CID:-}" ]; then echo "[FAIL] postgres container not found"; OVERALL_OK=1; fi

step "Wait for Postgres health (max 120s)"
TIMEOUT=120; ELAPSED=0; HEALTH=unknown
if [ -n "${CID:-}" ]; then
  printf "Waiting for postgres health"
  while true; do
    HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo "unknown")
    if [ "$HEALTH" = "healthy" ]; then echo; echo "[PASS] Postgres healthy"; break; fi
    sleep 2; ELAPSED=$((ELAPSED+2)); printf "."
    if [ $ELAPSED -ge $TIMEOUT ]; then echo; echo "[FAIL] Timeout waiting for postgres (last: $HEALTH)"; OVERALL_OK=1; break; fi
  done
fi

step "Compose status"
./setup.sh status
STATUS_CODE=$?
result "$STATUS_CODE" "compose status" || OVERALL_OK=1

step "Django check"
./setup.sh check
CHECK_CODE=$?
result "$CHECK_CODE" "django check" || OVERALL_OK=1

step "Migrations drift check"
./setup.sh makemigrations-check
MKMIG_CODE=$?
result "$MKMIG_CODE" "makemigrations --check --dry-run" || OVERALL_OK=1

step "Quick tests"
./setup.sh test -q
TEST_CODE=$?
result "$TEST_CODE" "pytest -q" || OVERALL_OK=1

step "Start web"
./setup.sh up
UP_CODE=$?
result "$UP_CODE" "web up" || OVERALL_OK=1

step "Hit /health"
curl -sf http://localhost:8000/health >/dev/null
HEALTH_CODE=$?
result "$HEALTH_CODE" "GET /health" || OVERALL_OK=1

echo
if [ "$OVERALL_OK" -eq 0 ]; then
  echo "SMOKE PASSED"
  exit 0
else
  echo "SMOKE FAILED"
  exit 1
fi
```

## Step-by-Step Alternative

```zsh
docker compose up -d postgres
./setup.sh status
./setup.sh check
./setup.sh makemigrations-check
./setup.sh test -q
./setup.sh up
curl -sf http://localhost:8000/health
```