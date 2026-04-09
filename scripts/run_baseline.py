"""
Run a baseline heuristic policy against the CloudScaleRL environment.

Usage:
    uv run python scripts/run_baseline.py --url http://localhost:8000 --task easy --policy hybrid
    uv run python scripts/run_baseline.py --url http://localhost:8000 --episodes 3
"""

from __future__ import annotations

import argparse
import json
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import CloudScaleEnv
from decision import get_policy, POLICIES
from models import CloudScaleAction


def run_episode(url: str, task: str, policy_name: str, episode: int) -> dict:
    policy = get_policy(policy_name)

    with CloudScaleEnv(base_url=url).sync() as env:
        result = env.reset(task=task)
        obs = result.observation
        total_reward = 0.0
        step = 0

        print(f"\n{'='*60}")
        print(f"Episode {episode} | Task: {task} | Policy: {policy_name}")
        print(f"{'='*60}")
        print(f"  Horizon: {obs.horizon} | Initial Pods: {obs.active_pods}")

        while not obs.done:
            action = policy(obs)
            result = env.step(action)
            obs = result.observation
            total_reward += float(result.reward or 0)
            step += 1

            if step % 20 == 0 or obs.latency_ms > 200:
                print(
                    f"  Step {obs.time_step:03d} | "
                    f"Act={action.scale_delta:+d} | "
                    f"Lat={obs.latency_ms:6.1f}ms | "
                    f"CPU={obs.cpu_utilization*100:4.1f}% | "
                    f"Pods={obs.active_pods:2d} | "
                    f"Queue={obs.queue_length:5d} | "
                    f"SLA_viol={obs.total_sla_violations}"
                )

        avg_lat = obs.average_latency_ms
        sla_rate = 1.0 - (obs.total_sla_violations / max(1, obs.time_step))

        print(f"\n  RESULTS:")
        print(f"    Steps:          {obs.time_step}")
        print(f"    Cumulative Rew: {total_reward:.2f}")
        print(f"    SLA Violations: {obs.total_sla_violations}/{obs.time_step}")
        print(f"    SLA Compliance: {sla_rate*100:.1f}%")
        print(f"    Avg Latency:    {avg_lat:.1f} ms")
        print(f"    Final Pods:     {obs.active_pods}")
        print(f"    Dropped:        {obs.total_requests_dropped}")

        return {
            "task": task,
            "policy": policy_name,
            "episode": episode,
            "steps": obs.time_step,
            "reward": round(total_reward, 2),
            "sla_violations": obs.total_sla_violations,
            "sla_compliance": round(sla_rate, 3),
            "avg_latency_ms": round(avg_lat, 1),
            "final_pods": obs.active_pods,
            "dropped": obs.total_requests_dropped,
        }


def main():
    parser = argparse.ArgumentParser(description="CloudScaleRL Baseline Runner")
    parser.add_argument("--url", type=str, default="http://localhost:8000")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--task", type=str, default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument(
        "--policy",
        type=str,
        default="hybrid",
        choices=list(POLICIES.keys()),
    )
    args = parser.parse_args()

    print(f"CloudScaleRL Baseline Evaluation")
    print(f"  Server:   {args.url}")
    print(f"  Task:     {args.task}")
    print(f"  Policy:   {args.policy}")
    print(f"  Episodes: {args.episodes}")

    results = []
    for ep in range(1, args.episodes + 1):
        r = run_episode(args.url, args.task, args.policy, ep)
        results.append(r)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
