from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def firestore_logging_enabled() -> bool:
    return _is_truthy(os.getenv("FIRESTORE_LOGGING_ENABLED", "false"))


@lru_cache(maxsize=1)
def _firestore_client() -> Any | None:
    try:
        from google.cloud import firestore
    except Exception:
        return None

    project = (
        os.getenv("FIRESTORE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
    )

    try:
        if project:
            return firestore.Client(project=project)
        return firestore.Client()
    except Exception:
        return None


def log_scale_advice_event(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    source: str = "api",
) -> bool:
    """Write recommendation event to Firestore when enabled.

    Returns True when persisted, False otherwise.
    """
    if not firestore_logging_enabled():
        return False

    client = _firestore_client()
    if client is None:
        return False

    collection_name = os.getenv("FIRESTORE_COLLECTION", "scale_advice_events")
    event = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "request": request_payload,
        "response": response_payload,
    }

    try:
        client.collection(collection_name).add(event)
        return True
    except Exception:
        return False


def fetch_recent_scale_advice_events(limit: int = 20) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    if not firestore_logging_enabled():
        return []

    client = _firestore_client()
    if client is None:
        return []

    collection_name = os.getenv("FIRESTORE_COLLECTION", "scale_advice_events")

    try:
        from google.cloud import firestore as firestore_module

        query = (
            client.collection(collection_name)
            .order_by("created_at", direction=firestore_module.Query.DESCENDING)
            .limit(limit)
        )
        events: list[dict[str, Any]] = []
        for doc in query.stream():
            item = doc.to_dict() or {}
            item["id"] = doc.id
            events.append(item)
        return events
    except Exception:
        return []