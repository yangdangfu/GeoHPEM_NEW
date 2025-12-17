from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ImportReport:
    points: int
    cells: dict[str, int]
    node_sets: dict[str, int]
    edge_sets: dict[str, int]
    element_sets: dict[str, int]


def _safe_name(name: str) -> str:
    out = []
    for ch in name:
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out).strip("_")
    return s or "set"


def _unique_name(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    i = 2
    while f"{base}_{i}" in used:
        i += 1
    name = f"{base}_{i}"
    used.add(name)
    return name


def meshio_to_contract(mesh) -> tuple[dict[str, Any], ImportReport]:  # noqa: ANN001
    """
    Convert a meshio.Mesh into GeoHPEM Contract mesh dict (NPZ).

    Supports:
    - points -> points (N,2)
    - triangle -> cells_tri3
    - quad -> cells_quad4
    - physical groups (gmsh:physical) -> node_set__/edge_set__/elem_set__
    """
    points = np.asarray(mesh.points, dtype=float)
    if points.ndim != 2 or points.shape[1] < 2:
        raise ValueError("mesh.points must be (N,>=2)")
    points2 = points[:, :2].copy()

    out: dict[str, Any] = {"points": points2}

    # Field data: name -> (id, dim)
    field_data = getattr(mesh, "field_data", {}) or {}
    phys_id_to_name_dim: dict[int, tuple[str, int]] = {}
    used_set_names: set[str] = set()
    for raw_name, arr in field_data.items():
        try:
            pid = int(arr[0])
            dim = int(arr[1])
        except Exception:
            continue
        safe = _safe_name(str(raw_name))
        safe = _unique_name(safe, used_set_names)
        phys_id_to_name_dim[pid] = (safe, dim)

    # cell_data: list of dicts aligned with mesh.cells
    cell_data = getattr(mesh, "cell_data", []) or []

    def get_phys_tags(block_index: int) -> np.ndarray | None:
        if block_index >= len(cell_data):
            return None
        data = cell_data[block_index]
        if not isinstance(data, dict):
            return None
        tags = data.get("gmsh:physical") or data.get("gmsh:geometrical")
        if tags is None:
            return None
        return np.asarray(tags, dtype=np.int64).reshape(-1)

    node_sets: dict[str, np.ndarray] = {}
    edge_sets: dict[str, np.ndarray] = {}
    elem_sets: dict[str, dict[str, np.ndarray]] = {}  # name -> cell_type -> indices

    cells_count: dict[str, int] = {}

    tri_conns: list[np.ndarray] = []
    tri_tags_list: list[np.ndarray | None] = []
    quad_conns: list[np.ndarray] = []
    quad_tags_list: list[np.ndarray | None] = []

    line_conns: list[np.ndarray] = []
    line_tags_list: list[np.ndarray | None] = []

    vertex_conns: list[np.ndarray] = []
    vertex_tags_list: list[np.ndarray | None] = []

    for bi, block in enumerate(mesh.cells):
        ctype = block.type
        conn = np.asarray(block.data, dtype=np.int32)
        cells_count[ctype] = cells_count.get(ctype, 0) + int(conn.shape[0])
        tags = get_phys_tags(bi)

        if ctype == "triangle":
            tri_conns.append(conn)
            tri_tags_list.append(tags)
            continue

        if ctype == "quad":
            quad_conns.append(conn)
            quad_tags_list.append(tags)
            continue

        if ctype == "line":
            line_conns.append(conn)
            line_tags_list.append(tags)
            continue

        if ctype == "vertex":
            vertex_conns.append(conn)
            vertex_tags_list.append(tags)
            continue

    def name_for_pid(pid: int, expected_dim: int) -> str:
        if pid in phys_id_to_name_dim:
            nm, dim = phys_id_to_name_dim[pid]
            if dim == expected_dim:
                return nm
        return _unique_name(f"phys_{pid}", used_set_names)

    if tri_conns:
        cells_tri3 = np.vstack(tri_conns).astype(np.int32)
        out["cells_tri3"] = cells_tri3

        offset = 0
        for conn, tags in zip(tri_conns, tri_tags_list, strict=True):
            if tags is None:
                offset += conn.shape[0]
                continue
            for pid in np.unique(tags):
                pid_i = int(pid)
                nm, dim = phys_id_to_name_dim.get(pid_i, (None, None))  # type: ignore[assignment]
                if nm is None:
                    nm = name_for_pid(pid_i, 2)
                    dim = 2
                if dim != 2:
                    continue
                idx = (np.nonzero(tags == pid)[0] + offset).astype(np.int32)
                elem_sets.setdefault(nm, {}).setdefault("tri3", np.zeros((0,), dtype=np.int32))
                elem_sets[nm]["tri3"] = np.concatenate([elem_sets[nm]["tri3"], idx])
            offset += conn.shape[0]

    if quad_conns:
        cells_quad4 = np.vstack(quad_conns).astype(np.int32)
        out["cells_quad4"] = cells_quad4

        offset = 0
        for conn, tags in zip(quad_conns, quad_tags_list, strict=True):
            if tags is None:
                offset += conn.shape[0]
                continue
            for pid in np.unique(tags):
                pid_i = int(pid)
                nm, dim = phys_id_to_name_dim.get(pid_i, (None, None))  # type: ignore[assignment]
                if nm is None:
                    nm = name_for_pid(pid_i, 2)
                    dim = 2
                if dim != 2:
                    continue
                idx = (np.nonzero(tags == pid)[0] + offset).astype(np.int32)
                elem_sets.setdefault(nm, {}).setdefault("quad4", np.zeros((0,), dtype=np.int32))
                elem_sets[nm]["quad4"] = np.concatenate([elem_sets[nm]["quad4"], idx])
            offset += conn.shape[0]

    if line_conns:
        for conn, tags in zip(line_conns, line_tags_list, strict=True):
            if tags is None:
                continue
            for pid in np.unique(tags):
                pid_i = int(pid)
                nm, dim = phys_id_to_name_dim.get(pid_i, (None, None))  # type: ignore[assignment]
                if nm is None:
                    nm = name_for_pid(pid_i, 1)
                    dim = 1
                if dim != 1:
                    continue
                edges = conn[np.nonzero(tags == pid)[0], :2].astype(np.int32)
                if nm in edge_sets:
                    edge_sets[nm] = np.vstack([edge_sets[nm], edges])
                else:
                    edge_sets[nm] = edges

    if vertex_conns:
        for conn, tags in zip(vertex_conns, vertex_tags_list, strict=True):
            if tags is None:
                continue
            for pid in np.unique(tags):
                pid_i = int(pid)
                nm, dim = phys_id_to_name_dim.get(pid_i, (None, None))  # type: ignore[assignment]
                if nm is None:
                    nm = name_for_pid(pid_i, 0)
                    dim = 0
                if dim != 0:
                    continue
                nodes = conn[np.nonzero(tags == pid)[0], 0].astype(np.int32)
                if nm in node_sets:
                    node_sets[nm] = np.unique(np.concatenate([node_sets[nm], nodes])).astype(np.int32)
                else:
                    node_sets[nm] = np.unique(nodes).astype(np.int32)

    # Write sets into NPZ keys
    for name, arr in node_sets.items():
        out[f"node_set__{name}"] = np.asarray(arr, dtype=np.int32).reshape(-1)
    for name, arr in edge_sets.items():
        out[f"edge_set__{name}"] = np.asarray(arr, dtype=np.int32).reshape(-1, 2)
    for name, by_type in elem_sets.items():
        for cell_type, idx in by_type.items():
            out[f"elem_set__{name}__{cell_type}"] = np.asarray(idx, dtype=np.int32).reshape(-1)

    report = ImportReport(
        points=int(points2.shape[0]),
        cells=cells_count,
        node_sets={k: int(v.size) for k, v in node_sets.items()},
        edge_sets={k: int(v.shape[0]) for k, v in edge_sets.items()},
        element_sets={
            k: int(sum(int(v.size) for v in by_type.values())) for k, by_type in elem_sets.items()
        },
    )
    return out, report
