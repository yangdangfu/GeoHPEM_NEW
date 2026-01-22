from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Project:
    """
    Platform-side project root.

    Note: this is intentionally lightweight for bring-up; the stable boundary is
    the Contract (request.json + mesh.npz).
    """

    request: dict[str, Any]
    mesh: dict[str, Any]
