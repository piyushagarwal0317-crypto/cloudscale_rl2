# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Grader for CloudScaleRL / AutoScaleOps.

Calculates a normalized score [0, 1] based on service reliability,
efficiency, and stability.
"""

from typing import Dict, Any

def grade_episode(metrics: Dict[str, Any]) -> Dict[str, float]:
    """
    Grades an episode based on cumulative metrics.
    
    Expected metrics:
    - total_steps
    - total_sla_violations
    - average_latency_ms
    - average_pods
    - total_dropped_requests
    - sla_target_ms
    """
    
    total_steps = metrics.get("total_steps", 1)
    sla_violations = metrics.get("total_sla_violations", 0)
    avg_latency = metrics.get("average_latency_ms", 0)
    avg_pods = metrics.get("average_pods", 0)
    dropped = metrics.get("total_dropped_requests", 0)
    sla_target = metrics.get("sla_target_ms", 250)
    
    # 1. SLA Score (Service Reliability)
    # Higher is better. 1.0 if no violations.
    sla_compliance = 1.0 - (sla_violations / total_steps)
    sla_compliance = max(0.0, sla_compliance)
    
    # 2. Efficiency Score (Cost/Resource Usage)
    # We want to minimize pods while keeping SLA.
    # Baseline pods might be say 10.
    efficiency = max(0.0, 1.0 - (avg_pods / 20.0))
    
    # 3. Latency Score
    # Bonus for being well under SLA.
    latency_score = max(0.0, 1.0 - (avg_latency / (sla_target * 2.0)))
    
    # 4. Dropped Requests Penalty
    dropped_penalty = 1.0 if dropped == 0 else max(0.0, 1.0 - (dropped / 1000.0))
    
    # Combined score
    # SLA is most important (50%), efficiency (30%), latency (10%), dropped (10%)
    final_score = (
        0.50 * sla_compliance +
        0.30 * efficiency +
        0.10 * latency_score +
        0.10 * dropped_penalty
    )
    
    return {
        "score": round(final_score, 3),
        "sla_compliance": round(sla_compliance, 3),
        "efficiency": round(efficiency, 3),
        "latency_score": round(latency_score, 3),
        "dropped_penalty": round(dropped_penalty, 3)
    }
