from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from geohpem.mesh.convert import ImportReport, meshio_to_contract

def import_with_meshio(path: str | Path) -> dict[str, Any]:
    """
    Import a mesh via meshio (optional dependency) and convert into the Contract NPZ mesh dict.

    This is a placeholder for the future "导入现成网格" workflow.
    """
    try:
        import meshio  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("meshio is required: pip install geohpem[mesh]") from exc

    mesh = meshio.read(str(path))
    out, _report = meshio_to_contract(mesh)
    return out


def import_with_meshio_report(path: str | Path) -> tuple[dict[str, Any], ImportReport]:
    try:
        import meshio  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("meshio is required: pip install geohpem[mesh]") from exc

    mesh = meshio.read(str(path))
    return meshio_to_contract(mesh)
