#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${2:-us-central1}"
SERVICE_NAME="${3:-autoscaleops-api}"
SECRET_NAME="${4:-gemini-api-key}"
USE_SECRET_MANAGER="${USE_SECRET_MANAGER:-true}"

is_truthy() {
  local value="${1:-}"
  case "${value,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <gcp_project_id> [region] [service_name] [secret_name]"
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Error: gcloud CLI is required. Install Google Cloud SDK first."
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "Error: No active gcloud auth session. Run: gcloud auth login"
  exit 1
fi

echo "[1/5] Setting project and enabling required APIs"
gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com >/dev/null

TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TAG}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

echo "[2/5] Building Cloud Run image from Dockerfile.cloudrun"
gcloud builds submit --tag "$IMAGE" --file Dockerfile.cloudrun .

env_vars=(
  "GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash}"
  "FIRESTORE_LOGGING_ENABLED=${FIRESTORE_LOGGING_ENABLED:-true}"
  "FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION:-scale_advice_events}"
)

set_secrets_args=()

if is_truthy "$USE_SECRET_MANAGER"; then
  echo "[3/5] Configuring Secret Manager (${SECRET_NAME})"

  if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
    if gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
      printf "%s" "$GOOGLE_API_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=- >/dev/null
      echo "Added new secret version for ${SECRET_NAME}."
    else
      printf "%s" "$GOOGLE_API_KEY" | gcloud secrets create "$SECRET_NAME" --replication-policy=automatic --data-file=- >/dev/null
      echo "Created secret ${SECRET_NAME}."
    fi
  fi

  if gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
      --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor" >/dev/null
    set_secrets_args=(--set-secrets "GOOGLE_API_KEY=${SECRET_NAME}:latest")
  else
    echo "Warning: Secret ${SECRET_NAME} not found and GOOGLE_API_KEY not provided."
    echo "Service will run in fallback mode until secret is created."
  fi
else
  echo "[3/5] Secret Manager disabled (USE_SECRET_MANAGER=${USE_SECRET_MANAGER})"
  if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
    env_vars+=("GOOGLE_API_KEY=${GOOGLE_API_KEY}")
  else
    echo "Warning: GOOGLE_API_KEY not set. API will run in fallback mode until key is configured."
  fi
fi

echo "[4/5] Deploying service to Cloud Run"
deploy_cmd=(
  gcloud run deploy "$SERVICE_NAME"
  --image "$IMAGE"
  --platform managed
  --region "$REGION"
  --allow-unauthenticated
  --service-account "$RUNTIME_SERVICE_ACCOUNT"
  --port 8080
  --memory 1Gi
  --cpu 1
  --set-env-vars "$(IFS=, ; echo "${env_vars[*]}")"
)

if [[ ${#set_secrets_args[@]} -gt 0 ]]; then
  deploy_cmd+=("${set_secrets_args[@]}")
fi

"${deploy_cmd[@]}"

URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

echo "[5/5] Deployment complete"
echo "Cloud Run URL: ${URL}"
echo "Health check: ${URL}/health"
if [[ ${#set_secrets_args[@]} -gt 0 ]]; then
  echo "Gemini key source: Secret Manager (${SECRET_NAME})"
else
  echo "Gemini key source: Environment variable or fallback heuristic"
fi
