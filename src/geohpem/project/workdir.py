from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from geohpem.contract.io import write_case_folder, write_result_folder
from geohpem.project.types import ProjectData


def materialize_to_workdir(project: ProjectData) -> Path:
    """
    Create a temporary case folder on disk for solver runs (request.json + mesh.npz [+ out]).
    """
    root = Path(tempfile.mkdtemp(prefix="geohpem_case_"))
    write_case_folder(root, project.request, project.mesh)
    if project.result_meta is not None and project.result_arrays is not None:
        write_result_folder(root / "out", project.result_meta, project.result_arrays)
    return root


def update_project_from_workdir(project: ProjectData, case_dir: Path) -> ProjectData:
    """
    Pull back `out/` results (if any) after a solver run.
    """
    out_dir = case_dir / "out"
    if not out_dir.exists():
        return project
    from geohpem.contract.io import read_result_folder

    meta, arrays = read_result_folder(out_dir)
    return ProjectData(
        request=project.request,
        mesh=project.mesh,
        result_meta=meta,
        result_arrays={k: np.asarray(v) for k, v in arrays.items()},
        manifest=project.manifest,
    )

