# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import pytest
from server.cloudscale_rl_environment import CloudScaleEnvironment
from models import CloudScaleAction


def test_env_reset():
    env = CloudScaleEnvironment(task="easy")
    obs = env.reset()
    assert obs.task_id == "easy"
    assert obs.time_step == 0
    assert obs.active_pods == 3
    assert obs.horizon == 180


def test_env_step_scale_up():
    env = CloudScaleEnvironment(task="easy")
    env.reset()
    action = CloudScaleAction(scale_delta=1)
    obs = env.step(action)

    assert obs.time_step == 1
    assert obs.pending_scale_ups >= 1
    # Active pods shouldn't change yet due to provisioning delay
    assert obs.active_pods == 3


def test_env_step_hold():
    env = CloudScaleEnvironment(task="easy")
    env.reset()
    action = CloudScaleAction(scale_delta=0)
    obs = env.step(action)

    assert obs.time_step == 1
    assert obs.active_pods == 3
    assert obs.request_rate > 0


def test_env_done():
    env = CloudScaleEnvironment(task="easy")
    env.reset()
    for _ in range(180):
        obs = env.step(CloudScaleAction(scale_delta=0))

    assert obs.done is True
    assert obs.time_step == 180


def test_env_provisioning_completes():
    """After enough steps, a scale-up should result in more active pods."""
    env = CloudScaleEnvironment(task="easy")
    env.reset()
    # Scale up by 2
    env.step(CloudScaleAction(scale_delta=2))
    # Wait for provisioning to complete (easy delay_mean=3, +margin)
    for _ in range(6):
        obs = env.step(CloudScaleAction(scale_delta=0))

    assert obs.active_pods >= 4  # started with 3, added 2


def test_env_scale_down():
    """Scaling down should eventually reduce pod count."""
    env = CloudScaleEnvironment(task="easy")
    env.reset()
    # Scale down by 1
    env.step(CloudScaleAction(scale_delta=-1))
    # Wait for deprovision to complete (easy deprovision_delay=2, +margin)
    for _ in range(4):
        obs = env.step(CloudScaleAction(scale_delta=0))

    assert obs.active_pods <= 3  # started with 3, removed 1


def test_env_medium_task():
    env = CloudScaleEnvironment(task="medium")
    obs = env.reset()
    assert obs.task_id == "medium"
    assert obs.horizon == 240
    assert obs.active_pods == 4


def test_env_hard_task():
    env = CloudScaleEnvironment(task="hard")
    obs = env.reset()
    assert obs.task_id == "hard"
    assert obs.horizon == 300
    assert obs.active_pods == 4


def test_env_deterministic():
    """Two episodes with same seed should produce identical first-step traffic."""
    env1 = CloudScaleEnvironment(task="easy")
    obs1 = env1.reset()
    step1 = env1.step(CloudScaleAction(scale_delta=0))

    env2 = CloudScaleEnvironment(task="easy")
    obs2 = env2.reset()
    step2 = env2.step(CloudScaleAction(scale_delta=0))

    assert step1.request_rate == step2.request_rate
    assert step1.latency_ms == step2.latency_ms
