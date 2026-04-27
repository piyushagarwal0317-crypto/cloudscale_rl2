# Demo Script (90 Seconds)

## 0-15s: Problem

"Cloud teams often miss the right autoscaling moment during traffic spikes. That causes user latency and cost waste."

## 15-35s: Show Prototype Input

- Open hosted frontend.
- Enter high-load metrics (high CPU, high latency, long queue).
- Click **Get Scaling Advice**.

Expected output: scale-up action (`+1` or `+2`) with rationale.

## 35-55s: Show Another Scenario

- Change metrics to low load (low CPU, empty queue).
- Click again.

Expected output: scale-down (`-1`) or hold (`0`).

## 55-75s: Explain AI + Reliability

"Gemini generates a recommendation using structured infra state. If the model/API is unavailable, a deterministic fallback policy still returns a safe action."

## 75-90s: Show Proof of Real System

- Open `/health` endpoint.
- Show Firestore collection `scale_advice_events` updated after requests.
- Close with impact statement:
  - faster decisions
  - more consistent scaling behavior
  - ready to extend with historical trends.
