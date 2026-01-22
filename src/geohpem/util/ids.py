from __future__ import annotations

import uuid


def new_uid(prefix: str) -> str:
    """
    Generate a stable unique id string for project objects.
    """
    p = (prefix or "id").strip().lower()
    return f"{p}_{uuid.uuid4().hex}"
