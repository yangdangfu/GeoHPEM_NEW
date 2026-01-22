from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from geohpem.contract.io import read_case_folder, read_result_folder
from geohpem.project.normalize import ensure_request_ids
from geohpem.project.types import ProjectData


def load_case_folder(case_dir: str | Path) -> ProjectData:
    case_path = Path(case_dir)
    request, mesh = read_case_folder(case_path)
    ensure_request_ids(request, mesh)

    result_meta: dict[str, Any] | None = None
    result_arrays: dict[str, np.ndarray] | None = None
    out_dir = case_path / "out"
    if out_dir.exists():
        try:
            result_meta, result_arrays = read_result_folder(out_dir)
        except Exception:
            result_meta, result_arrays = None, None

    return ProjectData(
        request=request, mesh=mesh, result_meta=result_meta, result_arrays=result_arrays
    )
