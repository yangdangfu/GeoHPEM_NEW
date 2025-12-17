from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


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
    points = np.asarray(mesh.points[:, :2], dtype=float)
    out: dict[str, Any] = {"points": points}

    for cell_block in mesh.cells:
        if cell_block.type == "triangle":
            out["cells_tri3"] = np.asarray(cell_block.data, dtype=np.int32)
        elif cell_block.type == "quad":
            out["cells_quad4"] = np.asarray(cell_block.data, dtype=np.int32)
        # extend as needed

    return out

