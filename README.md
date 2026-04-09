---
title: OpenEnv Cloud Autoscaling Environment Server
emoji: ☁️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 8000
base_path: /docs
tags:
  - openenv
  - cloud
  - autoscaling
  - reinforcement-learning
  - llm
  - sre
---

# CloudScaleRL / AutoScaleOps
**OpenEnv Cloud Autoscaling Environment Server**

A real-world inspired cloud autoscaling simulation for reinforcement learning and LLM-based decision-making, built for OpenEnv and the Meta PyTorch OpenEnv Hackathon.

---

# 🧠 What is CloudScaleRL / AutoScaleOps?

CloudScaleRL (AutoScaleOps) is a reinforcement learning environment that simulates real-world cloud autoscaling decisions, where an agent acts like a **Site Reliability Engineer (SRE)** managing infrastructure under uncertainty.

The environment models operational tradeoffs with:
- stochastic incoming traffic 📈
- delayed scaling effects ⏳
- queue growth under overload 📦
- latency vs cost penalties 💸
- stability and oscillation constraints ⚠️

The objective is to maximize service quality while minimizing cloud spend and system instability.

---

# 🚀 Quick Start

## Run the server
```bash
uv sync
uv run python -m server.app
```

## Run baseline evaluation
In another terminal:
```bash
uv run python scripts/run_baseline.py --url http://localhost:8000 --task easy --policy performance
```

## Run tests
```bash
uv sync --dev
uv run pytest tests/ -v
```

---

# 📊 Task Descriptions and Difficulty

All tasks use fixed seeds for deterministic evaluation.

| Task   | Description                              | Initial Pods | Horizon | Latency SLA | Difficulty |
|--------|------------------------------------------|-------------:|--------:|------------:|-----------|
| easy   | Stable traffic, relaxed constraints      | 3            | 180     | 250 ms      | Intro / low volatility |
| medium | Bursty demand, tighter latency target    | 4            | 240     | 180 ms      | Moderate operational pressure |
| hard   | Adversarial spikes, delayed consequences | 4            | 300     | 120 ms      | High volatility and strong tradeoffs |

---

# 🎮 Action Space Definition

**Action type:** `CloudScaleAction`

The agent controls autoscaling through a discrete scaling delta.

| Field       | Type    | Description |
|------------|---------|-------------|
| scale_delta | integer | Number of pods to add/remove; one of `[-2, -1, 0, 1, 2]` |

- `-2` → remove 2 pods (aggressive scale-down)
- `-1` → remove 1 pod (conservative scale-down)
- `0` → maintain current scale
- `1` → add 1 pod (conservative scale-up)
- `2` → add 2 pods (aggressive scale-up)

---

# 👀 Observation Space Definition

**Observation type:** `CloudScaleObservation`

Includes complete infrastructure state and KPI counters:
- **time_step / horizon**
- **cpu_utilization**: Aggregate CPU load (0.0-1.0)
- **latency_ms**: Current average request latency
- **request_rate**: Real-time incoming traffic
- **queue_length**: Current backlog of unprocessed requests
- **active_pods**: Number of pods serving traffic now
- **pending_scale_ups/downs**: Count of in-flight scaling events
- **totals**: processed, dropped, and SLA violations
- **average_latency_ms**: Cumulative performance metric
- **reward**: current step reward and cumulative reward

---

# 🏆 Reward Design

Dense reward is applied every step to encourage efficiency and reliability:
- **SLA Compliance**: Bonus for latency <= target, penalty for exceeding it.
- **Cost Efficiency**: Penalty proportional to the number of active pods.
- **Queue Control**: Linear penalty for backlog growth.
- **Stability**: Penalty for frequent or large scaling actions.
- **Invalid Action**: Fixed penalty for attempting to scale below 1 pod.

---

# 📏 Grader

`/grader` returns a deterministic score in `[0, 1]` based on:
- **SLA Compliance**: Percentage of steps within latency target.
- **Efficiency**: Normalized pod usage vs. capacity.
- **Service Quality**: Penalty for dropped requests.
- **Response Speed**: Reward for lower average latency.

---

# 📈 Baseline Scores (Policy Benchmarks)

| Task   | Policy      | Score | SLA Compliance | Avg Latency | Avg Pods |
|--------|-------------|------:|---------------:|------------:|---------:|
| easy   | threshold   | 0.82  | 98.2%          | 145 ms      | 3.6      |
| easy   | performance | 0.88  | 99.5%          | 130 ms      | 3.9      |
| medium | threshold   | 0.74  | 91.3%          | 182 ms      | 4.7      |
| medium | performance | 0.84  | 96.1%          | 160 ms      | 4.9      |
| hard   | threshold   | 0.61  | 74.5%          | 215 ms      | 5.2      |
| hard   | performance | 0.76  | 86.8%          | 178 ms      | 5.8      |

---

# 🤖 LLM Inference Results (Example Runs)

Using `inference.py` with `gpt-4o`:

| Task   | Horizon | Steps | Done | Score |
|--------|--------:|------:|------|------:|
| easy   | 180     | 180   | true | 0.91  |
| medium | 240     | 240   | true | 0.85  |
| hard   | 300     | 300   | true | 0.74  |

---

# 🧠 Inference Script (Submission Path)

Root `inference.py` is the script used by evaluators.

- Uses OpenAI-compatible client
- Emits strict logs: `[START]`, `[STEP]`, `[END]`
- Required variables: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- Optional variables: `BENCHMARK_URL`, `MAX_STEPS`

## Reproduce Inference Runs
```bash
export API_BASE_URL="<open_ai_compat_url>"
export MODEL_NAME="<model_name>"
export HF_TOKEN="<your_key>"
export BENCHMARK_URL="http://localhost:8000"
uv run python inference.py
```

---

# 🗂️ Project Structure

```text
cloudscale_rl/
├── README.md
├── openenv.yaml
├── pyproject.toml
├── inference.py         # LLM SRE Agent
├── client.py            # OpenEnv Client
├── models.py            # Pydantic Schemas
├── decision.py          # Baseline Policies
├── scripts/
│   └── run_baseline.py  # Local Tester
├── server/
│   ├── app.py           # FastAPI Server
│   ├── cloudscale_rl_environment.py  # Core Simulation
│   ├── grader.py        # Scoring Logic
│   └── __init__.py
└── tests/               # Unit and Integration Tests
```

---

# 🧑‍⚖️ How A Judge Will Run This

1. Start Environment: `uv run python -m server.app`.
2. Set Environment Variables (`API_BASE_URL`, etc).
3. Run Inference: `uv run python inference.py`.
4. Parse `[END]` logs for final scores.

---

# ☁️ Hugging Face Spaces

Deploy using `openenv push`. After deployment, the following standard OpenEnv routes will be available:
- `POST /reset`
- `POST /step`
- `/tasks`, `/grader`, `/baseline`