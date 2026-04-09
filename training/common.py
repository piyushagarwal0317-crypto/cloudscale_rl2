"""
Common utilities for RL training.
"""
import numpy as np
from models import CloudScaleObservation

def extract_features(obs: CloudScaleObservation) -> np.ndarray:
    """Extract a flat feature vector from the observation."""
    features = [
        obs.cpu_utilization,
        obs.latency_ms / 1000.0,  # Normalize latency
        obs.request_rate / 2000.0, # Approximate max rate
        obs.queue_length / 5000.0, # Approximate max queue
        obs.active_pods / 25.0,    # Max pods
        obs.pending_scale_ups / 5.0, # Approximate
        obs.pending_scale_downs / 5.0, # Approximate
    ]

    if obs.traffic_snapshot:
        features.extend([
            obs.traffic_snapshot.recent_avg_request_rate / 2000.0,
            obs.traffic_snapshot.recent_peak_request_rate / 2000.0,
            1.0 if obs.traffic_snapshot.trend == "rising" else (
                -1.0 if obs.traffic_snapshot.trend == "falling" else 0.0
            )
        ])
    else:
        features.extend([0.0, 0.0, 0.0]) # Padding if no snapshot

    return np.array(features, dtype=np.float32)

def extract_action_mask(obs: CloudScaleObservation) -> list[int]:
    """
    Returns a mask for discrete actions (scale_delta):
    Indices map to: [-2, -1, 0, 1, 2] -> [0, 1, 2, 3, 4]
    """
    mask = [1, 1, 1, 1, 1]
    # Restrict actions based on pending scale events or extreme values
    # Could prevent -2 if pods < 3, etc., but keeping it simple for now.
    if obs.active_pods <= 1:
        mask[0] = 0 # Cannot scale down by 2
        mask[1] = 0 # Cannot scale down by 1
    elif obs.active_pods == 2:
        mask[0] = 0 # Cannot scale down by 2

    # Simple constraint against oscillating requests
    if obs.pending_scale_ups > 0:
        mask[0] = 0
        mask[1] = 0
    if obs.pending_scale_downs > 0:
        mask[3] = 0
        mask[4] = 0

    return mask

