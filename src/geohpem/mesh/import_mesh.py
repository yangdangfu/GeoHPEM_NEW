from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from geohpem.mesh.convert import ImportReport, meshio_to_contract


def _report_from_contract_mesh(mesh: dict[str, Any]) -> ImportReport:
    points = int(np.asarray(mesh.get("points", np.zeros((0, 2)))).shape[0])

    cells: dict[str, int] = {}
    node_sets: dict[str, int] = {}
    edge_sets: dict[str, int] = {}
    elem_sets: dict[str, int] = {}

    for k, v in mesh.items():
        if not isinstance(k, str):
            continue
        if k.startswith("cells_"):
            a = np.asarray(v)
            try:
                cells[k.split("_", 1)[1]] = int(a.shape[0])
            except Exception:
                cells[k.split("_", 1)[1]] = int(a.size)
        elif k.startswith("node_set__"):
            name = k.split("__", 1)[1]
            a = np.asarray(v)
            node_sets[name] = int(a.size)
        elif k.startswith("edge_set__"):
            name = k.split("__", 1)[1]
            a = np.asarray(v)
            edge_sets[name] = int(a.reshape(-1, 2).shape[0]) if a.size else 0
        elif k.startswith("elem_set__"):
            # elem_set__NAME__tri3/quad4
            rest = k.split("__", 1)[1]
            parts = rest.split("__")
            if not parts:
                continue
            name = parts[0]
            a = np.asarray(v)
            elem_sets[name] = elem_sets.get(name, 0) + int(a.size)

    return ImportReport(
        points=points,
        cells=cells,
        node_sets=node_sets,
        edge_sets=edge_sets,
        element_sets=elem_sets,
    )


def import_contract_npz_report(path: str | Path) -> tuple[dict[str, Any], ImportReport]:
    """
    Import a Contract mesh.npz directly (no meshio conversion).

    This is useful when users already have Contract-format meshes (e.g. from other tools or exported case folders).
    """
    p = Path(path)
    data = np.load(str(p), allow_pickle=True)
    mesh: dict[str, Any] = {k: data[k] for k in data.files}
    report = _report_from_contract_mesh(mesh)
    return mesh, report


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
    p = Path(path)
    if p.suffix.lower() == ".npz":
        return import_contract_npz_report(p)

    try:
        import meshio  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("meshio is required: pip install geohpem[mesh]") from exc

    mesh = meshio.read(str(p))
    return meshio_to_contract(mesh)
