from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(slots=True)
class ProjectData:
    request: dict[str, Any]
    mesh: dict[str, np.ndarray]
    result_meta: dict[str, Any] | None = None
    result_arrays: dict[str, np.ndarray] | None = None
    manifest: dict[str, Any] | None = None

