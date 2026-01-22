from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class VtkMesh:
    grid: Any  # pyvista.UnstructuredGrid
    n_points: int
    n_cells: int


def _ensure_3d_points(points2: np.ndarray) -> np.ndarray:
    pts = np.asarray(points2, dtype=float)
    if pts.ndim != 2 or pts.shape[1] < 2:
        raise ValueError("points must be (N,2) or (N,>=2)")
    z = np.zeros((pts.shape[0], 1), dtype=float)
    return np.hstack([pts[:, :2], z])


def _vtk_cells_from_conn(conn: np.ndarray) -> np.ndarray:
    conn = np.asarray(conn, dtype=np.int64)
    if conn.ndim != 2:
        raise ValueError("cell connectivity must be 2D")
    n = conn.shape[1]
    prefix = np.full((conn.shape[0], 1), n, dtype=np.int64)
    return np.hstack([prefix, conn]).ravel()


def contract_mesh_to_pyvista(mesh: dict[str, Any]) -> VtkMesh:
    """
    Convert Contract mesh dict (NPZ arrays) into pyvista.UnstructuredGrid.
    Supports:
    - cells_tri3
    - cells_quad4
    """
    try:
        import pyvista as pv  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pyvista is required: pip/conda install pyvista") from exc

    if "points" not in mesh:
        raise ValueError("mesh must contain 'points'")
    points3 = _ensure_3d_points(np.asarray(mesh["points"]))

    cells_parts: list[np.ndarray] = []
    celltypes_parts: list[np.ndarray] = []
    cell_type_code_parts: list[np.ndarray] = []
    cell_local_id_parts: list[np.ndarray] = []

    # VTK cell types
    VTK_TRIANGLE = 5
    VTK_QUAD = 9
    TYPE_TRI3 = 1
    TYPE_QUAD4 = 2

    if "cells_tri3" in mesh:
        tri = np.asarray(mesh["cells_tri3"], dtype=np.int64)
        if tri.size:
            cells_parts.append(_vtk_cells_from_conn(tri))
            celltypes_parts.append(
                np.full((tri.shape[0],), VTK_TRIANGLE, dtype=np.uint8)
            )
            cell_type_code_parts.append(
                np.full((tri.shape[0],), TYPE_TRI3, dtype=np.int32)
            )
            cell_local_id_parts.append(np.arange(tri.shape[0], dtype=np.int32))

    if "cells_quad4" in mesh:
        quad = np.asarray(mesh["cells_quad4"], dtype=np.int64)
        if quad.size:
            cells_parts.append(_vtk_cells_from_conn(quad))
            celltypes_parts.append(np.full((quad.shape[0],), VTK_QUAD, dtype=np.uint8))
            cell_type_code_parts.append(
                np.full((quad.shape[0],), TYPE_QUAD4, dtype=np.int32)
            )
            cell_local_id_parts.append(np.arange(quad.shape[0], dtype=np.int32))

    if not cells_parts:
        # empty grid
        grid = pv.UnstructuredGrid(
            np.array([], dtype=np.int64), np.array([], dtype=np.uint8), points3
        )
        return VtkMesh(grid=grid, n_points=int(points3.shape[0]), n_cells=0)

    cells = np.concatenate(cells_parts)
    celltypes = np.concatenate(celltypes_parts)
    grid = pv.UnstructuredGrid(cells, celltypes, points3)
    # Add mapping so we can map picked VTK cells back to Contract cell blocks.
    grid.cell_data["__cell_type_code"] = np.concatenate(cell_type_code_parts)
    grid.cell_data["__cell_local_id"] = np.concatenate(cell_local_id_parts)
    return VtkMesh(grid=grid, n_points=int(points3.shape[0]), n_cells=int(grid.n_cells))


def cell_type_code_to_name(code: int) -> str | None:
    return {1: "tri3", 2: "quad4"}.get(int(code))


def available_steps_from_arrays(arrays: dict[str, Any]) -> list[int]:
    """
    Extract integer step/frame ids from result array keys like 'nodal__p__step000010'
    or 'nodal__p__frame000010'.
    """
    steps: set[int] = set()
    for k in arrays.keys():
        if "__step" in k:
            try:
                s = k.split("__step", 1)[1]
                steps.add(int(s))
            except Exception:
                pass
        if "__frame" in k:
            try:
                s = k.split("__frame", 1)[1]
                steps.add(int(s))
            except Exception:
                pass
    return sorted(steps)


def get_array_for(
    *,
    arrays: dict[str, Any],
    location: str,
    name: str,
    step: int,
) -> np.ndarray | None:
    prefix = {"node": "nodal", "element": "elem", "ip": "ip", "global": "global"}.get(
        location, None
    )
    if not prefix:
        return None
    key = f"{prefix}__{name}__step{step:06d}"
    if key not in arrays:
        key = f"{prefix}__{name}__frame{step:06d}"
    if key not in arrays:
        return None
    return np.asarray(arrays[key])


def vector_magnitude(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    if v.ndim != 2:
        raise ValueError("vector must be 2D (N,dim)")
    return np.sqrt(np.sum(v * v, axis=1))
