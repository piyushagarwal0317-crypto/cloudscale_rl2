"""
Decision logic for CloudScaleRL / AutoScaleOps.

Provides deterministic heuristic baseline policies for benchmark comparison.
These policies mirror the role that nearest/hybrid/noop play in the original baseline script.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from models import CloudScaleAction, CloudScaleObservation
except ImportError:
    from .models import CloudScaleAction, CloudScaleObservation


META_ACTIONS = [
    "threshold_cpu",
    "latency_queue",
    "hybrid",
    "noop",
    "emergency_scale",
]


@dataclass
class ActionChoice:
    action: CloudScaleAction
    label: str


def action_mask(obs: CloudScaleObservation) -> list[int]:
    """Return a binary mask for valid meta-actions."""
    is_emergency = obs.latency_ms > 300 or obs.queue_length > 2000
    # threshold_cpu, latency_queue, hybrid, and noop are always valid.
    # emergency_scale relies on there being actual severe pressure.
    return [1, 1, 1, 1, 1 if is_emergency else 0]


def choose_heuristic(
    policy_id: str, obs: CloudScaleObservation
) -> CloudScaleAction:
    if policy_id == "noop":
        return CloudScaleAction(scale_delta=0)

    if policy_id == "threshold_cpu":
        if obs.cpu_utilization > 0.80:
            if obs.pending_scale_ups == 0:
                return CloudScaleAction(scale_delta=1)
        elif obs.cpu_utilization < 0.30:
            if obs.active_pods > 1 and obs.pending_scale_downs == 0:
                return CloudScaleAction(scale_delta=-1)
        return CloudScaleAction(scale_delta=0)

    if policy_id == "latency_queue":
        if obs.latency_ms > 300 or obs.queue_length > 2000:
            if obs.pending_scale_ups == 0:
                return CloudScaleAction(scale_delta=2)
        if obs.latency_ms > 150 or obs.queue_length > 500 or obs.cpu_utilization > 0.85:
            if obs.pending_scale_ups == 0:
                return CloudScaleAction(scale_delta=1)
        if (
            obs.cpu_utilization < 0.20
            and obs.queue_length == 0
            and obs.active_pods > 1
            and obs.pending_scale_downs == 0
        ):
            return CloudScaleAction(scale_delta=-1)
        return CloudScaleAction(scale_delta=0)

    # hybrid - considers traffic trend if available
    trend = "stable"
    if obs.traffic_snapshot is not None:
        trend = obs.traffic_snapshot.trend

    # Prevent oscillation
    if obs.pending_scale_ups > 0 and obs.pending_scale_downs > 0:
        return CloudScaleAction(scale_delta=0)

    if obs.latency_ms > 300 or obs.queue_length > 2000:
        return CloudScaleAction(scale_delta=2)

    if trend == "rising" and obs.cpu_utilization > 0.60 and obs.pending_scale_ups == 0:
        return CloudScaleAction(scale_delta=1)

    if obs.latency_ms > 150 or obs.queue_length > 500:
        if obs.pending_scale_ups == 0:
            return CloudScaleAction(scale_delta=1)

    if obs.cpu_utilization > 0.85 and obs.pending_scale_ups == 0:
        return CloudScaleAction(scale_delta=1)

    if (
        trend == "falling"
        and obs.cpu_utilization < 0.30
        and obs.queue_length == 0
        and obs.active_pods > 1
        and obs.pending_scale_downs == 0
    ):
        return CloudScaleAction(scale_delta=-1)

    if (
        obs.cpu_utilization < 0.15
        and obs.queue_length == 0
        and obs.active_pods > 1
        and obs.pending_scale_downs == 0
    ):
        return CloudScaleAction(scale_delta=-1)

    return CloudScaleAction(scale_delta=0)


def choose_meta_action(action_id: int, obs: CloudScaleObservation) -> ActionChoice:
    action_id = max(0, min(action_id, len(META_ACTIONS) - 1))
    label = META_ACTIONS[action_id]

    if label in {"threshold_cpu", "latency_queue", "hybrid", "noop"}:
        return ActionChoice(action=choose_heuristic(label, obs), label=label)

    if label == "emergency_scale":
        if obs.latency_ms > 300 or obs.queue_length > 2000:
            if obs.pending_scale_ups < 2:
                return ActionChoice(
                    action=CloudScaleAction(scale_delta=2), label="emergency_scale_up"
                )
        return ActionChoice(action=CloudScaleAction(scale_delta=0), label="noop_fallback")

    return ActionChoice(action=CloudScaleAction(scale_delta=0), label="default_noop")


class HybridPolicy:
    """Class wrapper for run_baseline script compatibility."""
    def __call__(self, obs: CloudScaleObservation) -> CloudScaleAction:
        return choose_heuristic("hybrid", obs)

class ThresholdCpuPolicy:
    """Class wrapper for run_baseline script compatibility."""
    def __call__(self, obs: CloudScaleObservation) -> CloudScaleAction:
        return choose_heuristic("threshold_cpu", obs)

class LatencyQueuePolicy:
    """Class wrapper for run_baseline script compatibility."""
    def __call__(self, obs: CloudScaleObservation) -> CloudScaleAction:
        return choose_heuristic("latency_queue", obs)

class NoopPolicy:
    """Class wrapper for run_baseline script compatibility."""
    def __call__(self, obs: CloudScaleObservation) -> CloudScaleAction:
        return choose_heuristic("noop", obs)

POLICIES = {
    "threshold_cpu": ThresholdCpuPolicy,
    "latency_queue": LatencyQueuePolicy,
    "hybrid": HybridPolicy,
    "noop": NoopPolicy,
}

def get_policy(name: str = "hybrid"):
    """Return an instantiated policy by name."""
    cls = POLICIES.get(name, HybridPolicy)
    return cls()
