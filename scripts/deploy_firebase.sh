#!/usr/bin/env bash

set -euo pipefail

FIREBASE_PROJECT_ID="${1:-}"
BACKEND_URL="${2:-}"

if [[ -z "$FIREBASE_PROJECT_ID" ]]; then
  echo "Usage: $0 <firebase_project_id> [backend_url]"
  exit 1
fi

if ! command -v firebase >/dev/null 2>&1; then
  echo "Error: firebase CLI is required. Install with: npm install -g firebase-tools"
  exit 1
fi

if ! firebase login:list >/dev/null 2>&1; then
  echo "Error: Firebase CLI is not authenticated. Run: firebase login"
  exit 1
fi

if [[ -z "$BACKEND_URL" ]]; then
  BACKEND_URL="http://localhost:8000"
  echo "Warning: backend URL not provided. Defaulting to ${BACKEND_URL}"
fi

echo "[1/3] Writing runtime frontend config"
cat > prototype/config.js <<EOF
window.APP_CONFIG = {
  backendUrl: "${BACKEND_URL}",
};
EOF

echo "[2/3] Selecting Firebase project"
firebase use "$FIREBASE_PROJECT_ID"

echo "[3/3] Deploying Hosting"
firebase deploy --only hosting

echo "Firebase Hosting deploy complete."
