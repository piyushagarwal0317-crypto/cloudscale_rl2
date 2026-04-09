# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
FastAPI application for the CloudScaleRL / AutoScaleOps Environment.
"""

from fastapi import Body, HTTPException
from typing import Dict, Any

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import CloudScaleAction, CloudScaleObservation
    from .cloudscale_rl_environment import CloudScaleEnvironment, SCENARIOS
    from .grader import grade_episode
except (ModuleNotFoundError, ImportError):
    from models import CloudScaleAction, CloudScaleObservation
    from server.cloudscale_rl_environment import CloudScaleEnvironment, SCENARIOS
    from server.grader import grade_episode


# Create the app with web interface
app = create_app(
    CloudScaleEnvironment,
    CloudScaleAction,
    CloudScaleObservation,
    env_name="cloudscale_rl",
    max_concurrent_envs=10,
)

@app.get("/tasks")
async def get_tasks():
    """Returns the list of available scaling tasks."""
    return {
        "tasks": [
            {
                "id": cfg.task_id,
                "horizon": cfg.horizon,
                "sla_latency_ms": cfg.sla_latency_ms,
                "initial_pods": cfg.initial_pods,
            }
            for cfg in SCENARIOS.values()
        ]
    }

@app.post("/grader")
async def post_grader(metrics: Dict[str, Any] = Body(...)):
    """Calculates the score for a finished episode."""
    try:
        results = grade_episode(metrics)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "environment": "cloudscale_rl"}

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)
