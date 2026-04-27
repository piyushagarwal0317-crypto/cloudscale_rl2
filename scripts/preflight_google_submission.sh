#!/usr/bin/env bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0

tick() {
  echo -e "${GREEN}OK${NC} - $1"
  pass_count=$((pass_count + 1))
}

warn() {
  echo -e "${YELLOW}WARN${NC} - $1"
}

fail() {
  echo -e "${RED}FAIL${NC} - $1"
  exit 1
}

echo "Checking repository submission readiness..."

[[ -f README.md ]] || fail "README.md missing"
[[ -f Dockerfile.cloudrun ]] || fail "Dockerfile.cloudrun missing"
[[ -f firebase.json ]] || fail "firebase.json missing"
[[ -f prototype/index.html ]] || fail "prototype/index.html missing"
[[ -f prototype/events.html ]] || fail "prototype/events.html missing"
[[ -f prototype/app.js ]] || fail "prototype/app.js missing"
[[ -f prototype/events.js ]] || fail "prototype/events.js missing"
[[ -f prototype/config.js ]] || fail "prototype/config.js missing"
[[ -f scripts/deploy_cloud_run.sh ]] || fail "scripts/deploy_cloud_run.sh missing"
[[ -f scripts/deploy_firebase.sh ]] || fail "scripts/deploy_firebase.sh missing"

if grep -q "POST /ai/scale-advice" README.md; then
  tick "README includes AI endpoint documentation"
else
  fail "README does not document /ai/scale-advice"
fi

if command -v uv >/dev/null 2>&1; then
  tick "uv installed"
else
  warn "uv not installed (needed for local dev)"
fi

if command -v gcloud >/dev/null 2>&1; then
  tick "gcloud installed"
else
  warn "gcloud missing (needed for Cloud Run deploy)"
fi

if command -v firebase >/dev/null 2>&1; then
  tick "firebase CLI installed"
else
  warn "firebase CLI missing (needed for Hosting deploy)"
fi

if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
  tick "GOOGLE_API_KEY set"
else
  warn "GOOGLE_API_KEY not set (service will use fallback policy)"
fi

if command -v uv >/dev/null 2>&1; then
  if uv run pytest tests/test_env.py -q >/tmp/google_submission_pytest.log 2>&1; then
    tick "tests/test_env.py passing"
  else
    [[ -f /tmp/google_submission_pytest.log ]] && cat /tmp/google_submission_pytest.log
    fail "tests/test_env.py failed"
  fi
else
  warn "Skipping tests because uv is unavailable"
fi

echo "All blocking checks passed. Ready for deployment and submission."
