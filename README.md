---
title: AutoScaleOps AI Prototype
emoji: ☁️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /docs
tags:
  - openenv
  - cloud
  - autoscaling
  - reinforcement-learning
  - gemini
  - google-ai
---

# AutoScaleOps AI Prototype (Google Solution Guide 2026 Aligned)

AutoScaleOps is a cloud autoscaling simulator where an AI agent acts like an SRE and recommends scale actions (`-2` to `+2` pods) from live infrastructure signals.

This repo now includes:
- OpenEnv environment + grader (your original hackathon core)
- Gemini-powered autoscaling advisor endpoint
- Minimal web prototype for demo/submission
- Firestore event logging for production demo evidence

## 1) Problem Statement (Locked)

Cloud teams struggle to make fast, consistent autoscaling decisions during bursty traffic. Manual decisions often cause SLA violations or overspending.

Target user and use case:
- User: SRE or platform engineer operating a latency-sensitive service.
- Use case: Input current system metrics and receive one AI recommendation to scale up/down/hold with rationale.

## 2) Scope (Cut Aggressively)

Prototype scope is intentionally small:
- Feature 1: User enters infrastructure snapshot (CPU, latency, queue, pods).
- Feature 2: AI returns one scaling action (`scale_delta`) and rationale.
- Feature 3: Same logic can be tested against OpenEnv tasks (`easy`, `medium`, `hard`).

Not in scope:
- Multi-agent orchestration
- Full production alerting/on-call workflow
- Advanced dashboard analytics

## 3) Core AI Logic (Input -> AI -> Output)

Flow:
1. User submits current autoscaling state.
2. Backend sends structured prompt to Gemini (`generateContent`).
3. Gemini returns JSON with `scale_delta` and `rationale`.
4. If Gemini is unavailable, deterministic heuristic fallback is used.
5. UI displays final recommendation.

## 4) Test and Improve

Recommended prompt tests:
- High pressure case: high latency + long queue should return `+1` or `+2`.
- Low load case: low CPU + empty queue should return `-1`.
- Stable case: moderate metrics should return `0`.

Edge-case strategy used in code:
- Strict JSON extraction and clamping to valid action range.
- Safe fallback when external model/API fails.

## 5) Build and Run Prototype

### Backend
```bash
uv sync
uv run python -m server.app
```

Backend endpoints:
- `POST /ai/scale-advice` -> Gemini/heuristic autoscaling recommendation
- `GET /ai/scale-advice/events` -> recent logged recommendations (Firestore)
- `POST /reset`, `POST /step` -> OpenEnv simulation APIs
- `POST /grader` -> deterministic scoring

### Frontend
Open the prototype folder with any static server:
```bash
cd prototype
python3 -m http.server 4173
```
Then open `http://localhost:4173` in your browser.

In the UI:
- Set Backend URL to `http://localhost:8000`
- Enter metrics
- Click **Get Scaling Advice**

### Environment Variables
Copy `.env.example` to `.env` and fill values.

## 6) Make It Presentable (Submission Checklist)

What to submit:
- Working prototype video (60-120s)
- Problem statement + why it matters
- One meaningful AI feature demo (`/ai/scale-advice`)
- Clear architecture explanation

Suggested demo script:
1. Show input metrics for a traffic spike.
2. Click recommendation and show `scale_delta` with rationale.
3. Change to low-load metrics and show scale-down behavior.
4. Mention fallback safety behavior.

## Google AI + Firebase Path

This project is currently Python backend + static frontend.

For Solution Challenge style hosting, deploy the frontend on Firebase Hosting and point it to a deployed API (Cloud Run or similar). The `prototype/` folder is ready for this flow.

### One-Command Deploy Path

1. Run preflight:
```bash
./scripts/preflight_google_submission.sh
```

2. Deploy API:
```bash
export GOOGLE_API_KEY="<google_api_key>"
./scripts/deploy_cloud_run.sh <gcp_project_id> us-central1 autoscaleops-api gemini-api-key
```

The deploy script configures Secret Manager by default and mounts `GOOGLE_API_KEY` securely into Cloud Run.

3. Deploy UI:
```bash
./scripts/deploy_firebase.sh <firebase_project_id> <cloud_run_url>
```

After this, your hosted frontend calls your hosted backend automatically via `prototype/config.js`.
You can demo both pages:
- advisor: `/index.html`
- logged events feed: `/events.html`

## Submission Docs Pack

- `docs/SUBMISSION_GUIDE_GOOGLE_2026.md` - exact submit flow
- `docs/ARCHITECTURE.md` - architecture and component explanation
- `docs/DEMO_SCRIPT.md` - 90-second demo script
- `docs/JUDGING_CHECKLIST.md` - final self-review before submit

## Inference (OpenEnv Benchmark)

The evaluator script supports two providers:

### OpenAI-compatible
```bash
export LLM_PROVIDER=openai_compat
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<token>"
export BENCHMARK_URL="http://localhost:8000"
uv run python inference.py
```

### Gemini
```bash
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY="<google_api_key>"
export GEMINI_MODEL="gemini-2.5-flash"
export BENCHMARK_URL="http://localhost:8000"
uv run python inference.py
```

## Tests
```bash
uv sync --dev
uv run pytest tests/ -v
```

## Project Structure

```text
.
├── README.md
├── inference.py
├── client.py
├── models.py
├── server/
│   ├── app.py
│   ├── gemini_advisor.py
│   ├── event_logger.py
│   ├── cloudscale_rl_environment.py
│   └── grader.py
├── prototype/
│   ├── index.html
│   ├── styles.css
│   ├── config.js
│   └── app.js
├── scripts/
│   ├── deploy_cloud_run.sh
│   ├── deploy_firebase.sh
│   └── preflight_google_submission.sh
├── docs/
│   ├── SUBMISSION_GUIDE_GOOGLE_2026.md
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md
│   └── JUDGING_CHECKLIST.md
└── tests/
```

## Why This Is Submission-Ready

- Small but real working prototype
- One clear AI capability with user-facing output
- Fast to demo and easy to improve iteratively
- Keeps your original OpenEnv hackathon core intact
