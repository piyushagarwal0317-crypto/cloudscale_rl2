from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Optional
from uuid import uuid4
import math
import random

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import (
        CloudScaleAction,
        CloudScaleObservation,
        PendingScaleEvent,
        TrafficSnapshot,
    )
except (ImportError, ModuleNotFoundError):
    from models import (
        CloudScaleAction,
        CloudScaleObservation,
        PendingScaleEvent,
        TrafficSnapshot,
    )


# ---------------------------------------------------------------------------
# Scenario configuration
# ---------------------------------------------------------------------------

@dataclass
class ScenarioConfig:
    task_id: str
    horizon: int
    initial_pods: int
    min_pods: int
    max_pods: int
    base_seed: int
    # --- traffic ---
    base_request_rate: float          # mean requests/sec at baseline
    traffic_amplitude: float          # sinusoidal amplitude
    traffic_noise_std: float          # Gaussian noise std-dev
    burst_probability: float          # chance of a random traffic spike per step
    burst_multiplier: float           # how much a burst inflates traffic
    morning_peak_multiplier: float    # multiplier during morning peak
    afternoon_peak_multiplier: float  # multiplier during afternoon peak
    # --- capacity ---
    pod_capacity: float               # max req/s each pod can serve
    max_queue: int                    # max queue depth before drops
    # --- provisioning ---
    provision_delay_mean: int         # mean steps for a pod to come online
    provision_delay_std: float        # std-dev for provisioning delay
    deprovision_delay: int            # steps for pod termination
    cold_start_latency_ms: float     # extra latency for a newly active pod
    cold_start_steps: int             # how many steps the cold-start lasts
    # --- latency model ---
    base_latency_ms: float            # baseline per-request latency
    queue_latency_factor: float       # ms added per queued request (normalised)
    cpu_latency_factor: float         # ms added at high CPU utilisation
    # --- SLA ---
    sla_latency_ms: int               # target p50 latency
    # --- reward weights ---
    w_sla_bonus: float
    w_sla_penalty: float
    w_cost: float
    w_queue: float
    w_oscillation: float
    w_invalid: float
    w_idle_pod: float


SCENARIOS: dict[str, ScenarioConfig] = {
    "easy": ScenarioConfig(
        task_id="easy",
        horizon=180,
        initial_pods=3,
        min_pods=1,
        max_pods=15,
        base_seed=101,
        base_request_rate=1000.0,
        traffic_amplitude=200.0,
        traffic_noise_std=50.0,
        burst_probability=0.02,
        burst_multiplier=1.6,
        morning_peak_multiplier=1.20,
        afternoon_peak_multiplier=1.15,
        pod_capacity=500.0,
        max_queue=3000,
        provision_delay_mean=3,
        provision_delay_std=0.5,
        deprovision_delay=2,
        cold_start_latency_ms=30.0,
        cold_start_steps=3,
        base_latency_ms=40.0,
        queue_latency_factor=150.0,
        cpu_latency_factor=80.0,
        sla_latency_ms=250,
        w_sla_bonus=2.0,
        w_sla_penalty=0.03,
        w_cost=0.08,
        w_queue=0.005,
        w_oscillation=0.4,
        w_invalid=5.0,
        w_idle_pod=0.003,
    ),
    "medium": ScenarioConfig(
        task_id="medium",
        horizon=240,
        initial_pods=4,
        min_pods=1,
        max_pods=20,
        base_seed=202,
        base_request_rate=1500.0,
        traffic_amplitude=500.0,
        traffic_noise_std=150.0,
        burst_probability=0.05,
        burst_multiplier=1.8,
        morning_peak_multiplier=1.40,
        afternoon_peak_multiplier=1.50,
        pod_capacity=500.0,
        max_queue=4000,
        provision_delay_mean=5,
        provision_delay_std=1.0,
        deprovision_delay=3,
        cold_start_latency_ms=45.0,
        cold_start_steps=4,
        base_latency_ms=45.0,
        queue_latency_factor=180.0,
        cpu_latency_factor=100.0,
        sla_latency_ms=180,
        w_sla_bonus=2.0,
        w_sla_penalty=0.04,
        w_cost=0.10,
        w_queue=0.008,
        w_oscillation=0.5,
        w_invalid=5.0,
        w_idle_pod=0.003,
    ),
    "hard": ScenarioConfig(
        task_id="hard",
        horizon=300,
        initial_pods=4,
        min_pods=1,
        max_pods=25,
        base_seed=303,
        base_request_rate=2000.0,
        traffic_amplitude=1000.0,
        traffic_noise_std=300.0,
        burst_probability=0.10,
        burst_multiplier=2.0,
        morning_peak_multiplier=1.65,
        afternoon_peak_multiplier=1.90,
        pod_capacity=500.0,
        max_queue=5000,
        provision_delay_mean=8,
        provision_delay_std=2.0,
        deprovision_delay=4,
        cold_start_latency_ms=60.0,
        cold_start_steps=5,
        base_latency_ms=50.0,
        queue_latency_factor=200.0,
        cpu_latency_factor=120.0,
        sla_latency_ms=120,
        w_sla_bonus=2.0,
        w_sla_penalty=0.05,
        w_cost=0.12,
        w_queue=0.01,
        w_oscillation=0.6,
        w_invalid=5.0,
        w_idle_pod=0.003,
    ),
}


# ---------------------------------------------------------------------------
# Internal simulation state
# ---------------------------------------------------------------------------

@dataclass
class Pod:
    pod_id: str
    status: str = "active"           # active | provisioning | terminating
    created_step: int = 0
    active_step: int = 0             # step when pod became active
    cold_start_remaining: int = 0    # steps of cold-start penalty left
    requests_served: int = 0
    idle_steps: int = 0


@dataclass
class ScaleEvent:
    """In-flight scaling operation tracked internally."""
    direction: str                   # "up" | "down"
    pods_count: int
    remaining_steps: int
    pod_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class CloudScaleEnvironment(Environment):
    """Cloud autoscaling simulation.

    The agent acts as an SRE deciding how many pods to add or remove each
    time-step.  Traffic is stochastic with daily patterns and random bursts.
    Scaling decisions are subject to provisioning delay.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task: str = "easy"):
        self.task = task if task in SCENARIOS else "easy"
        self.config = SCENARIOS[self.task]
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._rng = random.Random(self.config.base_seed)

        # simulation state (will be initialised in _setup_episode)
        self._step_idx: int = 0
        self._pods: dict[str, Pod] = {}
        self._pending_events: list[ScaleEvent] = []
        self._queue_length: int = 0
        self._next_pod_id: int = 1

        # counters
        self._cumulative_reward: float = 0.0
        self._step_reward: float = 0.0
        self._total_requests_processed: int = 0
        self._total_requests_dropped: int = 0
        self._total_sla_violations: int = 0
        self._latency_history: list[float] = []
        self._request_rate_history: list[float] = []
        self._action_history: list[int] = []

        # current-step metrics (set in _advance)
        self._current_cpu: float = 0.0
        self._current_latency: float = 0.0
        self._current_request_rate: float = 0.0
        self._step_processed: int = 0
        self._step_dropped: int = 0

        self._setup_episode(seed=self.config.base_seed)

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self, task: Optional[str] = None) -> CloudScaleObservation:
        if task and task in SCENARIOS:
            self.task = task
            self.config = SCENARIOS[task]
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._setup_episode(seed=self.config.base_seed)
        return self._build_observation(done=False)

    def step(self, action: CloudScaleAction) -> CloudScaleObservation:  # type: ignore[override]
        self._state.step_count += 1
        self._step_reward = 0.0

        self._apply_action(action)
        self._advance_one_step()

        done = self._step_idx >= self.config.horizon
        return self._build_observation(done=done)

    @property
    def state(self) -> State:
        return self._state

    # ------------------------------------------------------------------
    # Episode bootstrap
    # ------------------------------------------------------------------

    def _setup_episode(self, seed: int):
        self._rng = random.Random(seed)
        self._step_idx = 0
        self._pods = {}
        self._pending_events = []
        self._queue_length = 0
        self._next_pod_id = 1

        self._cumulative_reward = 0.0
        self._step_reward = 0.0
        self._total_requests_processed = 0
        self._total_requests_dropped = 0
        self._total_sla_violations = 0
        self._latency_history = []
        self._request_rate_history = []
        self._action_history = []

        self._current_cpu = 0.0
        self._current_latency = 0.0
        self._current_request_rate = 0.0
        self._step_processed = 0
        self._step_dropped = 0

        # spawn initial pods (already active, no cold-start)
        for _ in range(self.config.initial_pods):
            pid = self._new_pod_id()
            self._pods[pid] = Pod(
                pod_id=pid,
                status="active",
                created_step=0,
                active_step=0,
                cold_start_remaining=0,
            )

    # ------------------------------------------------------------------
    # Observation builder
    # ------------------------------------------------------------------

    def _build_observation(self, done: bool) -> CloudScaleObservation:
        active_pods = self._active_pod_count()

        # pending events → public view
        pending_views = [
            PendingScaleEvent(
                direction=evt.direction,
                pods=evt.pods_count,
                remaining_steps=evt.remaining_steps,
            )
            for evt in self._pending_events
        ]
        pending_ups = sum(
            evt.pods_count for evt in self._pending_events if evt.direction == "up"
        )
        pending_downs = sum(
            evt.pods_count for evt in self._pending_events if evt.direction == "down"
        )

        # traffic snapshot
        recent = self._request_rate_history[-10:] if self._request_rate_history else [0.0]
        avg_rate = mean(recent)
        peak_rate = max(recent)
        trend = self._compute_trend(recent)
        traffic_snapshot = TrafficSnapshot(
            recent_avg_request_rate=round(avg_rate, 2),
            recent_peak_request_rate=round(peak_rate, 2),
            trend=trend,
        )

        avg_latency = mean(self._latency_history) if self._latency_history else 0.0

        self._cumulative_reward += self._step_reward

        return CloudScaleObservation(
            task_id=self.task,
            time_step=self._step_idx,
            horizon=self.config.horizon,
            cpu_utilization=round(self._current_cpu, 4),
            latency_ms=round(self._current_latency, 2),
            request_rate=round(self._current_request_rate, 2),
            queue_length=self._queue_length,
            active_pods=active_pods,
            pending_scale_ups=pending_ups,
            pending_scale_downs=pending_downs,
            pending_events=pending_views,
            traffic_snapshot=traffic_snapshot,
            total_requests_processed=self._total_requests_processed,
            total_requests_dropped=self._total_requests_dropped,
            total_sla_violations=self._total_sla_violations,
            average_latency_ms=round(avg_latency, 2),
            reward=round(self._step_reward, 4),
            cumulative_reward=round(self._cumulative_reward, 4),
            done=done,
            metadata={
                "version": "2.0",
                "seed": self.config.base_seed,
                "step_processed": self._step_processed,
                "step_dropped": self._step_dropped,
                "traffic_multiplier": round(
                    self._time_of_day_multiplier(self._step_idx), 3
                ),
            },
        )

    # ------------------------------------------------------------------
    # Action processing
    # ------------------------------------------------------------------

    def _apply_action(self, action: CloudScaleAction):
        delta = action.scale_delta
        self._action_history.append(delta)

        active = self._active_pod_count()
        pending_up = sum(
            e.pods_count for e in self._pending_events if e.direction == "up"
        )
        pending_down = sum(
            e.pods_count for e in self._pending_events if e.direction == "down"
        )
        projected = active + pending_up - pending_down + delta

        # clamp to [min_pods, max_pods] — penalise the part that was clamped
        if projected < self.config.min_pods:
            wasted = self.config.min_pods - projected
            delta += wasted
            self._step_reward -= self.config.w_invalid * (wasted > 0)
        elif projected > self.config.max_pods:
            wasted = projected - self.config.max_pods
            delta -= wasted
            self._step_reward -= self.config.w_invalid * (wasted > 0)

        if delta == 0:
            return

        if delta > 0:
            # schedule scale-up
            delay = max(
                1,
                int(
                    round(
                        self._rng.gauss(
                            self.config.provision_delay_mean,
                            self.config.provision_delay_std,
                        )
                    )
                ),
            )
            pod_ids: list[str] = []
            for _ in range(delta):
                pid = self._new_pod_id()
                self._pods[pid] = Pod(
                    pod_id=pid,
                    status="provisioning",
                    created_step=self._step_idx,
                )
                pod_ids.append(pid)
            self._pending_events.append(
                ScaleEvent(
                    direction="up",
                    pods_count=delta,
                    remaining_steps=delay,
                    pod_ids=pod_ids,
                )
            )
        else:
            # schedule scale-down (pick pods with fewest requests served)
            abs_delta = abs(delta)
            active_pods_list = sorted(
                [p for p in self._pods.values() if p.status == "active"],
                key=lambda p: p.requests_served,
            )
            to_remove = active_pods_list[:abs_delta]
            pod_ids_down = [p.pod_id for p in to_remove]
            for p in to_remove:
                p.status = "terminating"
            self._pending_events.append(
                ScaleEvent(
                    direction="down",
                    pods_count=abs_delta,
                    remaining_steps=self.config.deprovision_delay,
                    pod_ids=pod_ids_down,
                )
            )

    # ------------------------------------------------------------------
    # Simulation tick
    # ------------------------------------------------------------------

    def _advance_one_step(self):
        # 1. Resolve pending scaling events
        still_pending: list[ScaleEvent] = []
        for evt in self._pending_events:
            evt.remaining_steps -= 1
            if evt.remaining_steps <= 0:
                if evt.direction == "up":
                    for pid in evt.pod_ids:
                        pod = self._pods.get(pid)
                        if pod and pod.status == "provisioning":
                            pod.status = "active"
                            pod.active_step = self._step_idx
                            pod.cold_start_remaining = self.config.cold_start_steps
                else:
                    for pid in evt.pod_ids:
                        if pid in self._pods:
                            del self._pods[pid]
            else:
                still_pending.append(evt)
        self._pending_events = still_pending

        # 2. Tick cold-start counters
        for pod in self._pods.values():
            if pod.cold_start_remaining > 0:
                pod.cold_start_remaining -= 1

        # 3. Generate traffic
        request_rate = self._generate_traffic(self._step_idx)
        self._current_request_rate = request_rate
        self._request_rate_history.append(request_rate)

        # 4. Process requests
        active_pods = [p for p in self._pods.values() if p.status == "active"]
        num_active = len(active_pods)

        if num_active == 0:
            # no pods — everything queues/drops
            self._queue_length += int(request_rate)
            total_capacity = 0
        else:
            # pods under cold-start have reduced capacity
            total_capacity = 0.0
            for pod in active_pods:
                if pod.cold_start_remaining > 0:
                    total_capacity += self.config.pod_capacity * 0.5
                else:
                    total_capacity += self.config.pod_capacity

            available = request_rate + self._queue_length
            processed = min(available, total_capacity)
            remaining = available - processed

            self._queue_length = int(remaining)
            self._step_processed = int(processed)
            self._total_requests_processed += int(processed)

            # distribute processed requests across pods for accounting
            per_pod = int(processed) // max(1, num_active)
            for pod in active_pods:
                pod.requests_served += per_pod

        # 5. Drop excess queue
        if self._queue_length > self.config.max_queue:
            dropped = self._queue_length - self.config.max_queue
            self._queue_length = self.config.max_queue
            self._step_dropped = dropped
            self._total_requests_dropped += dropped
        else:
            self._step_dropped = 0

        # 6. Calculate CPU utilisation
        if total_capacity > 0:
            cpu_util = min(1.0, (request_rate + max(0, self._queue_length - request_rate * 0.1)) / total_capacity)
        else:
            cpu_util = 1.0
        self._current_cpu = cpu_util

        # 7. Calculate latency
        latency = self._compute_latency(cpu_util, num_active, total_capacity)
        self._current_latency = latency
        self._latency_history.append(latency)

        if latency > self.config.sla_latency_ms:
            self._total_sla_violations += 1

        # 8. Idle pod accounting
        for pod in active_pods:
            if cpu_util < 0.15:
                pod.idle_steps += 1

        # 9. Compute step reward
        self._compute_reward(latency, cpu_util, num_active)

        # 10. Advance clock
        self._step_idx += 1

    # ------------------------------------------------------------------
    # Traffic generation
    # ------------------------------------------------------------------

    def _generate_traffic(self, step: int) -> float:
        """Stochastic traffic with sinusoidal base, daily pattern, noise, bursts."""
        period = 60  # steps for a full cycle
        base = self.config.base_request_rate
        amp = self.config.traffic_amplitude
        noise_std = self.config.traffic_noise_std

        sinusoidal = base + amp * math.sin(2 * math.pi * step / period)
        noise = self._rng.gauss(0, noise_std)
        time_mult = self._time_of_day_multiplier(step)

        rate = (sinusoidal + noise) * time_mult

        # random burst
        if self._rng.random() < self.config.burst_probability:
            rate *= self.config.burst_multiplier

        return max(0.0, rate)

    def _time_of_day_multiplier(self, step: int) -> float:
        """Simulate morning and afternoon peaks (like lunch/dinner for food delivery)."""
        # Treat step 0 as 08:00, each step ≈ 1 minute
        hour = 8 + (step / 60.0)
        multiplier = 1.0
        # morning peak: 10-12
        if 10 <= hour <= 12:
            multiplier *= self.config.morning_peak_multiplier
        # afternoon peak: 14-17
        if 14 <= hour <= 17:
            multiplier *= self.config.afternoon_peak_multiplier
        return multiplier

    # ------------------------------------------------------------------
    # Latency model
    # ------------------------------------------------------------------

    def _compute_latency(
        self, cpu_util: float, num_active: int, total_capacity: float
    ) -> float:
        """Realistic latency: base + queue pressure + CPU saturation + cold-start."""
        base = self.config.base_latency_ms

        # queue pressure
        if total_capacity > 0:
            queue_pressure = (self._queue_length / total_capacity) * self.config.queue_latency_factor
        else:
            queue_pressure = self.config.queue_latency_factor * 2.0

        # CPU saturation (exponential near 1.0)
        cpu_pressure = (cpu_util ** 3) * self.config.cpu_latency_factor

        # cold-start penalty
        cold_pods = sum(
            1 for p in self._pods.values()
            if p.status == "active" and p.cold_start_remaining > 0
        )
        cold_penalty = 0.0
        if num_active > 0:
            cold_ratio = cold_pods / num_active
            cold_penalty = cold_ratio * self.config.cold_start_latency_ms

        latency = base + queue_pressure + cpu_pressure + cold_penalty

        # add a small amount of noise
        latency += self._rng.gauss(0, 3.0)
        return max(0.0, latency)

    # ------------------------------------------------------------------
    # Reward
    # ------------------------------------------------------------------

    def _compute_reward(self, latency: float, cpu_util: float, num_active: int):
        cfg = self.config

        # SLA compliance
        if latency <= cfg.sla_latency_ms:
            self._step_reward += cfg.w_sla_bonus
        else:
            late_ms = latency - cfg.sla_latency_ms
            self._step_reward += 0.8
            self._step_reward -= cfg.w_sla_penalty * late_ms

        # cost penalty (per active pod)
        self._step_reward -= cfg.w_cost * num_active

        # queue backlog penalty
        self._step_reward -= cfg.w_queue * self._queue_length

        # drops penalty
        if self._step_dropped > 0:
            self._step_reward -= 1.2

        # oscillation penalty (look at last 3 actions)
        if len(self._action_history) >= 3:
            last3 = self._action_history[-3:]
            # penalise sign changes (e.g. +1, -1, +1)
            sign_changes = sum(
                1 for i in range(1, len(last3))
                if last3[i] * last3[i - 1] < 0
            )
            self._step_reward -= cfg.w_oscillation * sign_changes

        # idle pod penalty
        idle_count = sum(
            1 for p in self._pods.values()
            if p.status == "active" and cpu_util < 0.15
        )
        self._step_reward -= cfg.w_idle_pod * idle_count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _active_pod_count(self) -> int:
        return sum(1 for p in self._pods.values() if p.status == "active")

    def _new_pod_id(self) -> str:
        pid = f"P{self._next_pod_id:04d}"
        self._next_pod_id += 1
        return pid

    @staticmethod
    def _compute_trend(recent: list[float]) -> str:
        if len(recent) < 5:
            return "stable"
        if recent[-1] > recent[-5] * 1.1:
            return "rising"
        elif recent[-1] < recent[-5] * 0.9:
            return "falling"
        return "stable"
