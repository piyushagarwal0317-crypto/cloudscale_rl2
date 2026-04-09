"""CloudScaleRL / AutoScaleOps — Data Models.

Defines the action space, observation space, and all typed schemas used by
the cloud autoscaling environment.
"""

from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

ScaleDelta = Literal[-2, -1, 0, 1, 2]


class CloudScaleAction(Action):
    """Single autoscaling decision issued by the agent each time-step.

    The agent chooses how many pods to add or remove:
        -2  →  scale down by 2 pods
        -1  →  scale down by 1 pod
         0  →  hold current scale (no change)
        +1  →  scale up by 1 pod
        +2  →  scale up by 2 pods

    Scaling requests are subject to provisioning delay and are *not*
    applied instantly.  Invalid requests (e.g. scaling below 1 pod) are
    clamped and penalised.
    """

    scale_delta: ScaleDelta = Field(
        ...,
        description=(
            "Number of pods to add (+) or remove (−). "
            "Must be one of: -2, -1, 0, 1, 2."
        ),
    )


# ---------------------------------------------------------------------------
# Observation — helper sub-models
# ---------------------------------------------------------------------------

class PendingScaleEvent(BaseModel):
    """Represents a single in-flight scaling operation that has not yet
    completed (e.g. a pod that is still starting up)."""

    direction: Literal["up", "down"] = Field(
        ..., description="Whether this event is a scale-up or scale-down."
    )
    pods: int = Field(
        ..., description="Number of pods being added or removed in this event."
    )
    remaining_steps: int = Field(
        ...,
        description="Time-steps remaining before this scaling event takes effect.",
    )


class TrafficSnapshot(BaseModel):
    """A lightweight summary of recent traffic behaviour, optionally
    provided in harder task difficulties to give the agent richer context."""

    recent_avg_request_rate: float = Field(
        0.0, description="Rolling average request rate over the last N steps."
    )
    recent_peak_request_rate: float = Field(
        0.0, description="Peak request rate observed in the last N steps."
    )
    trend: Literal["rising", "falling", "stable"] = Field(
        "stable", description="Short-term traffic trend direction."
    )


# ---------------------------------------------------------------------------
# Observation — main schema
# ---------------------------------------------------------------------------

class CloudScaleObservation(Observation):
    """Complete observation returned by the environment after each step.

    Contains the full autoscaling state, cumulative KPIs, reward info,
    and episode-control flags.
    """

    # ---- time ----
    task_id: str = Field(..., description="Task difficulty id (easy / medium / hard)")
    time_step: int = Field(..., description="Current time-step of the episode")
    horizon: int = Field(..., description="Total episode length in time-steps")

    # ---- core infrastructure metrics ----
    cpu_utilization: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate CPU utilisation across active pods (0.0–1.0)",
    )
    latency_ms: float = Field(
        ..., ge=0.0, description="Current average request latency in milliseconds"
    )
    request_rate: float = Field(
        ..., ge=0.0, description="Incoming requests per second at this time-step"
    )
    queue_length: int = Field(
        ..., ge=0, description="Number of requests currently waiting in the queue"
    )
    active_pods: int = Field(
        ..., ge=0, description="Number of pods currently running and serving traffic"
    )

    # ---- pending scaling info ----
    pending_scale_ups: int = Field(
        0,
        ge=0,
        description="Total number of pods currently being provisioned (not yet active)",
    )
    pending_scale_downs: int = Field(
        0,
        ge=0,
        description="Total number of pods currently being terminated (not yet removed)",
    )
    pending_events: list[PendingScaleEvent] = Field(
        default_factory=list,
        description="Detailed list of in-flight scaling events with countdown timers.",
    )

    # ---- optional traffic context ----
    traffic_snapshot: TrafficSnapshot | None = Field(
        default=None,
        description=(
            "Optional rolling traffic summary. "
            "Provided in some task difficulties to aid decision-making."
        ),
    )

    # ---- cumulative KPIs ----
    total_requests_processed: int = Field(
        0, ge=0, description="Cumulative count of successfully processed requests"
    )
    total_requests_dropped: int = Field(
        0, ge=0, description="Cumulative count of dropped/timed-out requests"
    )
    total_sla_violations: int = Field(
        0,
        ge=0,
        description="Cumulative count of time-steps where latency exceeded the SLA target",
    )
    average_latency_ms: float = Field(
        0.0, ge=0.0, description="Running average latency across all processed requests"
    )

    # ---- reward ----
    reward: float = Field(0.0, description="Reward received at this time-step")
    cumulative_reward: float = Field(
        0.0, description="Sum of all rewards received so far in this episode"
    )

    # ---- episode control ----
    done: bool = Field(
        False, description="Whether the episode has ended (horizon reached)"
    )

    # ---- metadata ----
    metadata: dict = Field(
        default_factory=dict,
        description=(
            "Arbitrary key-value metadata for debugging or extended info "
            "(e.g. cold-start flags, cost breakdown)."
        ),
    )
