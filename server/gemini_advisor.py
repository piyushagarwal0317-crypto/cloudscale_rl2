from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from pydantic import BaseModel, Field


class GeminiScaleAdviceRequest(BaseModel):
    task_id: str = Field(default="medium")
    time_step: int = Field(default=0, ge=0)
    horizon: int = Field(default=240, ge=1)
    cpu_utilization: float = Field(default=0.5, ge=0.0, le=1.0)
    latency_ms: float = Field(default=120.0, ge=0.0)
    request_rate: float = Field(default=300.0, ge=0.0)
    queue_length: int = Field(default=0, ge=0)
    active_pods: int = Field(default=3, ge=1)
    pending_scale_ups: int = Field(default=0, ge=0)
    pending_scale_downs: int = Field(default=0, ge=0)
    average_latency_ms: float = Field(default=120.0, ge=0.0)
    total_sla_violations: int = Field(default=0, ge=0)
    total_requests_dropped: int = Field(default=0, ge=0)


class GeminiScaleAdviceResponse(BaseModel):
    scale_delta: int = Field(..., ge=-2, le=2)
    rationale: str
    provider: str
    model: str
    used_fallback: bool = False


SYSTEM_INSTRUCTION = (
    "You are an SRE autoscaling copilot. Decide one action for pod scaling. "
    "Always respond as JSON with keys: scale_delta, rationale. "
    "scale_delta must be an integer in [-2, -1, 0, 1, 2]."
)


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _clamp_delta(delta: int) -> int:
    return max(-2, min(2, int(delta)))


def fallback_scale_advice(payload: GeminiScaleAdviceRequest) -> GeminiScaleAdviceResponse:
    # Deterministic heuristic for reliability when API is unavailable.
    if (payload.latency_ms > 300 or payload.queue_length > 2000) and payload.pending_scale_ups == 0:
        delta = 2
        reason = "Severe latency/queue pressure detected; scale up aggressively."
    elif (
        payload.cpu_utilization > 0.85
        or payload.latency_ms > 150
        or payload.queue_length > 500
    ) and payload.pending_scale_ups == 0:
        delta = 1
        reason = "Moderate pressure detected; scale up conservatively."
    elif (
        payload.cpu_utilization < 0.2
        and payload.queue_length == 0
        and payload.active_pods > 1
        and payload.pending_scale_downs == 0
    ):
        delta = -1
        reason = "Low utilization and no queue; scale down to reduce cost."
    else:
        delta = 0
        reason = "Current state is stable; hold capacity."

    return GeminiScaleAdviceResponse(
        scale_delta=delta,
        rationale=reason,
        provider="heuristic",
        model="fallback-v1",
        used_fallback=True,
    )


def request_gemini_scale_advice(payload: GeminiScaleAdviceRequest) -> GeminiScaleAdviceResponse:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        return fallback_scale_advice(payload)

    user_payload = {
        "task_id": payload.task_id,
        "time_step": payload.time_step,
        "horizon": payload.horizon,
        "cpu_utilization": payload.cpu_utilization,
        "latency_ms": payload.latency_ms,
        "request_rate": payload.request_rate,
        "queue_length": payload.queue_length,
        "active_pods": payload.active_pods,
        "pending_scale_ups": payload.pending_scale_ups,
        "pending_scale_downs": payload.pending_scale_downs,
        "average_latency_ms": payload.average_latency_ms,
        "total_sla_violations": payload.total_sla_violations,
        "total_requests_dropped": payload.total_requests_dropped,
    }

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    request_body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Autoscaling state JSON:\n"
                        + json.dumps(user_payload, separators=(",", ":"), ensure_ascii=True)
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 220,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(endpoint, json=request_body, timeout=20)
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        parsed = _extract_json(text) or {}
        delta = _clamp_delta(parsed.get("scale_delta", 0))
        rationale = str(parsed.get("rationale", "Autoscaling recommendation generated."))

        return GeminiScaleAdviceResponse(
            scale_delta=delta,
            rationale=rationale,
            provider="google",
            model=model,
            used_fallback=False,
        )
    except Exception:
        return fallback_scale_advice(payload)