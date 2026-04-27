# Google Solution Challenge 2026 - Direct Submission Guide

This guide gives you an end-to-end path from local code to a live, submission-ready prototype.

## What You Will Submit

- Live frontend URL (Firebase Hosting)
- Live API URL (Cloud Run)
- Public repository with setup instructions
- 60-120 second demo video
- One clear AI feature: autoscaling recommendation (`/ai/scale-advice`)

## 1. Local Preflight

Run this from repo root:

```bash
./scripts/preflight_google_submission.sh
```

If tools are missing:
- gcloud: install Google Cloud SDK
- firebase: `npm install -g firebase-tools`

## 2. Deploy Backend to Cloud Run

Choose your project/region/service:

```bash
export GOOGLE_API_KEY="YOUR_GEMINI_KEY"
./scripts/deploy_cloud_run.sh <gcp_project_id> us-central1 autoscaleops-api gemini-api-key
```

This deploy flow uses Secret Manager by default:
- if `GOOGLE_API_KEY` is set, it creates/updates secret `gemini-api-key`
- Cloud Run reads `GOOGLE_API_KEY` from secret at runtime
- plaintext env injection is not required

Output includes your API URL, for example:
- `https://autoscaleops-api-xxxx.a.run.app`

Test it:

```bash
curl -s "<cloud_run_url>/health"
curl -s -X POST "<cloud_run_url>/ai/scale-advice" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id":"medium",
    "time_step":10,
    "horizon":240,
    "cpu_utilization":0.86,
    "latency_ms":190,
    "request_rate":420,
    "queue_length":580,
    "active_pods":4,
    "pending_scale_ups":0,
    "pending_scale_downs":0,
    "average_latency_ms":170,
    "total_sla_violations":8,
    "total_requests_dropped":2
  }'
```

## 3. Deploy Frontend to Firebase Hosting

Use the Cloud Run URL from step 2:

```bash
./scripts/deploy_firebase.sh <firebase_project_id> <cloud_run_url>
```

This script writes `prototype/config.js` and deploys Hosting.

After deploy:
- advisor UI: `<firebase_url>/index.html`
- event feed UI: `<firebase_url>/events.html`

## 4. Verify Firestore Logging

When `FIRESTORE_LOGGING_ENABLED=true`, each `/ai/scale-advice` request stores an event in collection `scale_advice_events`.

Quick API check:

```bash
curl -s "<cloud_run_url>/ai/scale-advice/events?limit=5"
```

In Firebase Console:
- Firestore Database -> Data
- Check collection: `scale_advice_events`

## 5. Submission Form Content Template

Use these points in your form:

- Problem: Teams struggle to make real-time autoscaling decisions under volatile demand.
- AI feature: Gemini recommends one autoscaling action with rationale from live metrics.
- Impact: Faster response to spikes, fewer SLA violations, lower overprovisioning risk.
- Safety: Fallback heuristic ensures deterministic output when model/API fails.

## 6. Final Checklist

- [ ] Frontend URL opens and works on mobile
- [ ] Backend `/health` returns status ok
- [ ] Backend `/ai/scale-advice` returns valid JSON
- [ ] Firestore logging enabled in production
- [ ] README has setup + architecture + demo steps
- [ ] Demo video recorded and uploaded

## Fast Command Order

```bash
./scripts/preflight_google_submission.sh
export GOOGLE_API_KEY="YOUR_GEMINI_KEY"
./scripts/deploy_cloud_run.sh <gcp_project_id> us-central1 autoscaleops-api gemini-api-key
./scripts/deploy_firebase.sh <firebase_project_id> <cloud_run_url>
```
