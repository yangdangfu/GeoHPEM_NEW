from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import sys

import numpy as np


def _ensure_src_on_path() -> None:
    """
    Allow running this script without installing the package.
    """
    try:
        import geohpem  # noqa: F401

        return
    except Exception:
        pass
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if src.exists():
        sys.path.insert(0, str(src))


def structured_rect_mesh(
    *,
    width: float,
    height: float,
    nx: int,
    ny: int,
    with_tris: bool = True,
) -> dict[str, Any]:
    """
    Build a structured quad mesh on [0,width]x[0,height], optionally split into tri3.
    Returns Contract mesh dict suitable for mesh.npz.
    """
    xs = np.linspace(0.0, float(width), int(nx) + 1, dtype=float)
    ys = np.linspace(0.0, float(height), int(ny) + 1, dtype=float)

    points = np.array([(x, y) for y in ys for x in xs], dtype=float)

    def nid(i: int, j: int) -> int:
        return j * (nx + 1) + i

    # quad4 cells
    quads: list[tuple[int, int, int, int]] = []
    for j in range(ny):
        for i in range(nx):
            n0 = nid(i, j)
            n1 = nid(i + 1, j)
            n2 = nid(i + 1, j + 1)
            n3 = nid(i, j + 1)
            quads.append((n0, n1, n2, n3))
    cells_quad4 = np.asarray(quads, dtype=np.int64)

    # tri3 cells (split each quad into two triangles, consistent ordering)
    tris: list[tuple[int, int, int]] = []
    if with_tris:
        for (n0, n1, n2, n3) in quads:
            tris.append((n0, n1, n2))
            tris.append((n0, n2, n3))
    cells_tri3 = np.asarray(tris, dtype=np.int64)

    # node sets (by coordinate)
    tol = 1e-12
    x = points[:, 0]
    y = points[:, 1]

    node_left = np.where(np.abs(x - 0.0) <= tol)[0]
    node_right = np.where(np.abs(x - float(width)) <= tol)[0]
    node_bottom = np.where(np.abs(y - 0.0) <= tol)[0]
    node_top = np.where(np.abs(y - float(height)) <= tol)[0]

    node_bl = np.array([nid(0, 0)], dtype=np.int64)
    node_br = np.array([nid(nx, 0)], dtype=np.int64)
    node_tl = np.array([nid(0, ny)], dtype=np.int64)
    node_tr = np.array([nid(nx, ny)], dtype=np.int64)

    # edge sets (node pairs along boundaries)
    def edge_pairs_h(j: int) -> np.ndarray:
        return np.asarray([(nid(i, j), nid(i + 1, j)) for i in range(nx)], dtype=np.int64)

    def edge_pairs_v(i: int) -> np.ndarray:
        return np.asarray([(nid(i, j), nid(i, j + 1)) for j in range(ny)], dtype=np.int64)

    edge_bottom = edge_pairs_h(0)
    edge_top = edge_pairs_h(ny)
    edge_left = edge_pairs_v(0)
    edge_right = edge_pairs_v(nx)

    # element sets: all + a soft zone subset
    n_elem_quad = cells_quad4.shape[0]
    elem_all_quad = np.arange(n_elem_quad, dtype=np.int64)

    # soft zone: x in [0.35W, 0.65W], y in [0, 0.4H]
    soft_ids: list[int] = []
    for eid, (n0, n1, n2, n3) in enumerate(cells_quad4):
        cx = float(np.mean(points[[n0, n1, n2, n3], 0]))
        cy = float(np.mean(points[[n0, n1, n2, n3], 1]))
        if (0.35 * width) <= cx <= (0.65 * width) and 0.0 <= cy <= (0.4 * height):
            soft_ids.append(eid)
    elem_soft_quad = np.asarray(soft_ids, dtype=np.int64)

    # For tri3, element ids are local to tri3 list
    elem_all_tri = np.arange(cells_tri3.shape[0], dtype=np.int64) if with_tris else np.zeros((0,), dtype=np.int64)
    elem_soft_tri: np.ndarray
    if with_tris:
        # map quad soft ids to corresponding 2 tri ids (2 per quad)
        tri_soft: list[int] = []
        for qid in soft_ids:
            tri_soft.extend([2 * qid, 2 * qid + 1])
        elem_soft_tri = np.asarray(tri_soft, dtype=np.int64)
    else:
        elem_soft_tri = np.zeros((0,), dtype=np.int64)

    mesh: dict[str, Any] = {
        "points": points,
        "cells_quad4": cells_quad4,
        # include tri3 as well (better coverage: mesh quality, multi-cell types)
        "cells_tri3": cells_tri3,
        # node sets
        "node_set__left": node_left.astype(np.int64),
        "node_set__right": node_right.astype(np.int64),
        "node_set__bottom": node_bottom.astype(np.int64),
        "node_set__top": node_top.astype(np.int64),
        "node_set__corner_bl": node_bl,
        "node_set__corner_br": node_br,
        "node_set__corner_tl": node_tl,
        "node_set__corner_tr": node_tr,
        # edge sets
        "edge_set__bottom": edge_bottom,
        "edge_set__top": edge_top,
        "edge_set__left": edge_left,
        "edge_set__right": edge_right,
        # element sets
        "elem_set__soil__quad4": elem_all_quad,
        "elem_set__soft_zone__quad4": elem_soft_quad,
        "elem_set__soil__tri3": elem_all_tri,
        "elem_set__soft_zone__tri3": elem_soft_tri,
    }
    return mesh


def make_request(*, mode: str) -> dict[str, Any]:
    def bc(uid: str, set_name: str, ux: Any = None, uy: Any = None) -> dict[str, Any]:
        out: dict[str, Any] = {"uid": uid, "set": set_name, "type": "displacement"}
        if ux is not None:
            out["ux"] = ux
        if uy is not None:
            out["uy"] = uy
        return out

    def load(uid: str, set_name: str, kind: str, value: float) -> dict[str, Any]:
        return {"uid": uid, "set": set_name, "type": kind, "value": float(value)}

    def outreq(uid: str, name: str, location: str, every_n: int = 1) -> dict[str, Any]:
        return {"uid": uid, "name": name, "location": location, "every_n": int(every_n)}

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "unit_system": {"length": "m", "pressure": "kPa"},
        "model": {"dimension": 2, "mode": mode, "gravity": [0.0, -9.81]},
        "materials": {
            "Soil_Stiff": {"model": "LinearElastic", "parameters": {"E": 30000.0, "nu": 0.30}},
            "Soil_Soft": {"model": "LinearElastic", "parameters": {"E": 15000.0, "nu": 0.35}},
        },
        "assignments": [
            {"element_set": "soil", "cell_type": "quad4", "material_id": "Soil_Stiff"},
            {"element_set": "soft_zone", "cell_type": "quad4", "material_id": "Soil_Soft"},
            {"element_set": "soil", "cell_type": "tri3", "material_id": "Soil_Stiff"},
            {"element_set": "soft_zone", "cell_type": "tri3", "material_id": "Soil_Soft"},
        ],
        "stages": [
            {
                "id": "S1_Initial",
                "analysis_type": "static",
                "num_steps": 5,
                "dt": 1.0,
                "bcs": [
                    bc("bc_bottom_fix", "bottom", ux=0.0, uy=0.0),
                    bc("bc_left_ux", "left", ux=0.0),
                ],
                "loads": [],
                "output_requests": [
                    outreq("or_u", "u", "node", 1),
                    outreq("or_p", "p", "node", 1),
                    outreq("or_vm", "vm", "element", 1),
                ],
            },
            {
                "id": "S2_Surcharge",
                "analysis_type": "static",
                "num_steps": 10,
                "dt": 0.5,
                "bcs": [
                    bc("bc_bottom_fix2", "bottom", ux=0.0, uy=0.0),
                    bc("bc_left_ux2", "left", ux=0.0),
                ],
                "loads": [
                    load("ld_top_surcharge", "top", "traction_y", value=-50.0),
                ],
                "output_requests": [
                    outreq("or_u2", "u", "node", 1),
                    outreq("or_p2", "p", "node", 1),
                    outreq("or_vm2", "vm", "element", 1),
                ],
            },
            {
                "id": "S3_Dynamic",
                "analysis_type": "dynamic",
                "num_steps": 20,
                "dt": 0.1,
                "bcs": [
                    bc("bc_bottom_fix3", "bottom", ux=0.0, uy=0.0),
                    bc("bc_left_ux3", "left", ux=0.0),
                ],
                "loads": [
                    load("ld_right_push", "right", "traction_x", value=20.0),
                ],
                "output_requests": [
                    outreq("or_u3", "u", "node", 1),
                    outreq("or_p3", "p", "node", 1),
                    outreq("or_vm3", "vm", "element", 1),
                ],
            },
        ],
        "output_requests": [
            outreq("gor_u", "u", "node", 1),
            outreq("gor_vm", "vm", "element", 1),
        ],
    }
    return request


def main() -> int:
    _ensure_src_on_path()
    root = Path("_Projects") / "cases" / "realistic_case_01"
    root.mkdir(parents=True, exist_ok=True)

    request = make_request(mode="plane_strain")
    mesh = structured_rect_mesh(width=20.0, height=10.0, nx=40, ny=20, with_tris=True)

    (root / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(root / "mesh.npz", **mesh)

    # Precompute outputs using the fake solver for convenience.
    try:
        from geohpem.solver_adapter.fake import FakeSolver
        from geohpem.contract.io import write_result_folder

        solver = FakeSolver()
        meta, arrays = solver.solve(request, mesh, callbacks=None)
        write_result_folder(root / "out", meta, arrays)
        try:
            (root / "out_build_failed.txt").unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
    except Exception as exc:
        (root / "out_build_failed.txt").write_text(str(exc), encoding="utf-8")

    (root / "README.md").write_text(
        "\n".join(
            [
                "# realistic_case_01",
                "",
                "A richer local test case to exercise GeoHPEM GUI features:",
                "- Import-mesh route (case folder: request.json + mesh.npz)",
                "- Multiple stages + BCs/loads/output_requests",
                "- Node/edge/element sets (soil + soft_zone)",
                "- Fake solver precomputed outputs (out/): nodal u/p + element vm + global_steps",
                "",
                "Open in GUI:",
                "- `python main.py --open _Projects/cases/realistic_case_01`",
                "",
                "Suggested checks:",
                "- `Tools -> Validate Inputs...` should be clean",
                "- `Solve -> Run (fake)` should run and write out/ again",
                "- Output: profile/time history (node + element), export image, probe, cell pick",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
