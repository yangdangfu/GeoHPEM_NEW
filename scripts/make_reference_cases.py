from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _structured_tri_mesh(*, lx: float, ly: float, nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (points(N,2), cells_tri3(M,3)) for a rectangle [0,lx]x[0,ly].
    """
    xs = np.linspace(0.0, float(lx), int(nx) + 1)
    ys = np.linspace(0.0, float(ly), int(ny) + 1)
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    points = np.vstack([X.ravel(), Y.ravel()]).T

    def nid(i: int, j: int) -> int:
        return j * (nx + 1) + i

    tris: list[tuple[int, int, int]] = []
    for j in range(ny):
        for i in range(nx):
            n00 = nid(i, j)
            n10 = nid(i + 1, j)
            n01 = nid(i, j + 1)
            n11 = nid(i + 1, j + 1)
            # two triangles per quad
            tris.append((n00, n10, n11))
            tris.append((n00, n11, n01))
    cells_tri3 = np.asarray(tris, dtype=np.int64)
    return points.astype(float), cells_tri3


def _boundary_sets(*, nx: int, ny: int) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """
    Return (node_sets, edge_sets) for the structured mesh indexing.
    """
    def nid(i: int, j: int) -> int:
        return j * (nx + 1) + i

    bottom_nodes = np.array([nid(i, 0) for i in range(nx + 1)], dtype=np.int64)
    top_nodes = np.array([nid(i, ny) for i in range(nx + 1)], dtype=np.int64)
    left_nodes = np.array([nid(0, j) for j in range(ny + 1)], dtype=np.int64)
    right_nodes = np.array([nid(nx, j) for j in range(ny + 1)], dtype=np.int64)

    bottom_edges = np.array([[nid(i, 0), nid(i + 1, 0)] for i in range(nx)], dtype=np.int64)
    top_edges = np.array([[nid(i, ny), nid(i + 1, ny)] for i in range(nx)], dtype=np.int64)
    left_edges = np.array([[nid(0, j), nid(0, j + 1)] for j in range(ny)], dtype=np.int64)
    right_edges = np.array([[nid(nx, j), nid(nx, j + 1)] for j in range(ny)], dtype=np.int64)

    node_sets = {
        "node_set__bottom": bottom_nodes,
        "node_set__top": top_nodes,
        "node_set__left": left_nodes,
        "node_set__right": right_nodes,
    }
    edge_sets = {
        "edge_set__bottom": bottom_edges,
        "edge_set__top": top_edges,
        "edge_set__left": left_edges,
        "edge_set__right": right_edges,
    }
    return node_sets, edge_sets


def make_reference_elastic_case(case_dir: Path) -> None:
    lx, ly = 10.0, 4.0
    nx, ny = 30, 12
    points, tri = _structured_tri_mesh(lx=lx, ly=ly, nx=nx, ny=ny)
    node_sets, edge_sets = _boundary_sets(nx=nx, ny=ny)

    mesh: dict[str, np.ndarray] = {
        "points": points,
        "cells_tri3": tri,
        "elem_set__soil__tri3": np.arange(tri.shape[0], dtype=np.int64),
        **node_sets,
        **edge_sets,
    }

    request = {
        "schema_version": "0.2",
        "unit_system": {"length": "m", "pressure": "Pa"},
        "model": {"dimension": 2, "mode": "plane_strain", "gravity": [0.0, -9.81]},
        "materials": {
            "mat_soil": {"model_name": "linear_elastic", "parameters": {"E": 3.0e7, "nu": 0.30, "rho": 1800.0}}
        },
        "assignments": [{"uid": "as_soil", "cell_type": "tri3", "element_set": "soil", "material_id": "mat_soil"}],
        "stages": [
            {
                "id": "S1",
                "name": "S1_initial",
                "analysis_type": "static",
                "num_steps": 8,
                "dt": 1.0,
                "bcs": [
                    {"uid": "bc_bottom_fix", "type": "displacement", "set": "bottom", "value": {"ux": 0.0, "uy": 0.0}},
                    {"uid": "bc_left_ux", "type": "displacement", "set": "left", "value": {"ux": 0.0}},
                ],
                "loads": [
                    {"uid": "ld_top_trac", "type": "traction", "set": "top", "value": [0.0, -1.0e5]},
                ],
                "output_requests": [
                    {"uid": "or_u", "name": "u", "location": "node", "every_n": 1},
                    {"uid": "or_vm", "name": "vm", "location": "element", "every_n": 1},
                ],
            }
        ],
        "output_requests": [],
    }

    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(case_dir / "mesh.npz", **mesh)


def make_reference_seepage_case(case_dir: Path) -> None:
    lx, ly = 10.0, 4.0
    nx, ny = 30, 12
    points, tri = _structured_tri_mesh(lx=lx, ly=ly, nx=nx, ny=ny)
    node_sets, edge_sets = _boundary_sets(nx=nx, ny=ny)

    mesh: dict[str, np.ndarray] = {
        "points": points,
        "cells_tri3": tri,
        "elem_set__soil__tri3": np.arange(tri.shape[0], dtype=np.int64),
        **node_sets,
        **edge_sets,
    }

    request = {
        "schema_version": "0.2",
        "unit_system": {"length": "m", "pressure": "Pa"},
        "model": {"dimension": 2, "mode": "plane_strain", "gravity": [0.0, 0.0]},
        "materials": {"mat_k": {"model_name": "darcy", "parameters": {"k": 1.0e-6}}},
        "assignments": [{"uid": "as_k", "cell_type": "tri3", "element_set": "soil", "material_id": "mat_k"}],
        "stages": [
            {
                "id": "S1",
                "name": "S1_seepage",
                "analysis_type": "seepage_steady",
                "num_steps": 5,
                "dt": 1.0,
                "bcs": [{"uid": "bc_p_top", "type": "p", "set": "top", "value": 1.0e5}],
                "loads": [{"uid": "ld_flux_bottom", "type": "flux", "set": "bottom", "value": -1.0e-6}],
                "output_requests": [{"uid": "or_p", "name": "p", "location": "node", "every_n": 1}],
            }
        ],
        "output_requests": [],
    }

    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(case_dir / "mesh.npz", **mesh)


def main() -> int:
    root = Path("_Projects/cases")
    c1 = root / "reference_elastic_01"
    c2 = root / "reference_seepage_01"
    make_reference_elastic_case(c1)
    make_reference_seepage_case(c2)
    print(f"Wrote: {c1}")
    print(f"Wrote: {c2}")
    print("Now run:")
    print(f"  python geohpem_cli.py run {c1} --solver ref_elastic")
    print(f"  python geohpem_cli.py run {c2} --solver ref_seepage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
