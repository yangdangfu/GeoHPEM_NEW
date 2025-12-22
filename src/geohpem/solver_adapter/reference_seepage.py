from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class _MatDarcy:
    k: float  # isotropic permeability


def _as_float2(v: Any, *, name: str) -> tuple[float, float]:
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return float(v[0]), float(v[1])
    raise ValueError(f"Expected {name} as [x,y]")


def _nodes_from_set(mesh: dict[str, Any], set_name: str) -> np.ndarray:
    k_node = f"node_set__{set_name}"
    if k_node in mesh:
        return np.asarray(mesh[k_node], dtype=np.int64).reshape(-1)
    k_edge = f"edge_set__{set_name}"
    if k_edge in mesh:
        e = np.asarray(mesh[k_edge], dtype=np.int64).reshape(-1, 2)
        if e.size == 0:
            return np.zeros((0,), dtype=np.int64)
        return np.unique(e.reshape(-1))
    raise KeyError(f"Missing set: node_set__{set_name} (or edge_set__{set_name})")


def _edges_from_set(mesh: dict[str, Any], set_name: str) -> np.ndarray:
    k_edge = f"edge_set__{set_name}"
    if k_edge not in mesh:
        raise KeyError(f"Missing edge set: {k_edge}")
    return np.asarray(mesh[k_edge], dtype=np.int64).reshape(-1, 2)


def _tri_grad_area(xy: np.ndarray) -> tuple[np.ndarray, float]:
    x1, y1 = float(xy[0, 0]), float(xy[0, 1])
    x2, y2 = float(xy[1, 0]), float(xy[1, 1])
    x3, y3 = float(xy[2, 0]), float(xy[2, 1])
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    A = 0.5 * det
    if A == 0.0:
        raise ValueError("Degenerate tri3 (zero area)")
    b1 = y2 - y3
    b2 = y3 - y1
    b3 = y1 - y2
    c1 = x3 - x2
    c2 = x1 - x3
    c3 = x2 - x1
    d = 1.0 / (2.0 * A)
    dNdx = np.array([b1, b2, b3], dtype=float) * d
    dNdy = np.array([c1, c2, c3], dtype=float) * d
    grads = np.vstack([dNdx, dNdy]).T  # (3,2)
    return grads, abs(A)


def _quad_shape_derivs(xi: float, eta: float) -> tuple[np.ndarray, np.ndarray]:
    dN_dxi = 0.25 * np.array([-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)], dtype=float)
    dN_deta = 0.25 * np.array([-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)], dtype=float)
    return dN_dxi, dN_deta


class ReferenceSeepageSolver:
    """
    Reference solver: steady seepage (Poisson/Darcy), scalar p on nodes.
    """

    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "reference_seepage",
            "contract": {"min": "0.2", "max": "0.2"},
            "modes": ["plane_strain", "plane_stress"],
            "analysis_types": ["seepage_steady"],
            "materials": ["darcy"],
            "bcs": ["p"],
            "loads": ["flux"],
            "fields": ["p"],
            "results": ["p"],
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from scipy.sparse import coo_matrix  # type: ignore
        from scipy.sparse.linalg import spsolve  # type: ignore

        def cb_progress(p: float, msg: str, stage_id: str, step: int) -> None:
            if callbacks and (fn := callbacks.get("on_progress")):
                fn(float(p), str(msg), str(stage_id), int(step))

        def cb_frame(frame_meta: dict[str, Any], *, mesh_out: dict[str, Any] | None = None, arrays_out: dict[str, Any] | None = None) -> None:
            if callbacks and (fn := callbacks.get("on_frame")):
                try:
                    fn(frame_meta, mesh=mesh_out, arrays=arrays_out)
                except TypeError:
                    fn(frame_meta)

        def should_cancel() -> bool:
            if callbacks and (fn := callbacks.get("should_cancel")):
                try:
                    return bool(fn())
                except Exception:
                    return False
            return False

        points = np.asarray(mesh["points"], dtype=float)
        xy = points[:, :2]
        n_nodes = int(xy.shape[0])

        tri = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64)), dtype=np.int64)
        quad = np.asarray(mesh.get("cells_quad4", np.zeros((0, 4), dtype=np.int64)), dtype=np.int64)

        materials = request.get("materials", {})
        if not isinstance(materials, dict):
            materials = {}
        assignments = request.get("assignments", [])
        if not isinstance(assignments, list):
            assignments = []

        mats: list[_MatDarcy] = []
        mat_index: dict[str, int] = {}

        def get_mat(mid: str) -> int:
            if mid in mat_index:
                return mat_index[mid]
            m = materials.get(mid)
            if not isinstance(m, dict):
                raise ValueError(f"Unknown material_id: {mid}")
            if str(m.get("model_name")) != "darcy":
                raise ValueError(f"reference_seepage supports only darcy, got {m.get('model_name')}")
            pars = m.get("parameters")
            if not isinstance(pars, dict):
                raise ValueError(f"material.parameters must be object for {mid}")
            k = float(pars.get("k"))
            mats.append(_MatDarcy(k=k))
            mat_index[mid] = len(mats) - 1
            return mat_index[mid]

        tri_mat = np.full((tri.shape[0],), -1, dtype=np.int32)
        quad_mat = np.full((quad.shape[0],), -1, dtype=np.int32)
        for a in assignments:
            if not isinstance(a, dict):
                continue
            ct = str(a.get("cell_type", "")).strip()
            es = str(a.get("element_set", "")).strip()
            mid = str(a.get("material_id", "")).strip()
            if not ct or not es or not mid:
                continue
            idx = get_mat(mid)
            key = f"elem_set__{es}__{ct}"
            if key not in mesh:
                raise KeyError(f"Missing element set for assignment: {key}")
            ids = np.asarray(mesh[key], dtype=np.int64).reshape(-1)
            if ct == "tri3":
                tri_mat[ids] = idx
            elif ct == "quad4":
                quad_mat[ids] = idx
            else:
                raise ValueError(f"Unsupported cell_type: {ct}")

        if tri_mat.size and np.any(tri_mat < 0):
            raise ValueError("Unassigned tri3 elements (assignments missing)")
        if quad_mat.size and np.any(quad_mat < 0):
            raise ValueError("Unassigned quad4 elements (assignments missing)")

        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []

        def add_ke(conn: np.ndarray, ke: np.ndarray) -> None:
            for a, na in enumerate(conn):
                ra = int(na)
                for b, nb in enumerate(conn):
                    rows.append(ra)
                    cols.append(int(nb))
                    data.append(float(ke[a, b]))

        for eid, conn in enumerate(tri):
            k = mats[int(tri_mat[eid])].k if tri_mat.size else 1.0
            grads, A = _tri_grad_area(xy[np.asarray(conn, dtype=np.int64)])
            ke = np.zeros((3, 3), dtype=float)
            for i in range(3):
                for j in range(3):
                    ke[i, j] = float(k) * float(np.dot(grads[i], grads[j])) * A
            add_ke(np.asarray(conn, dtype=np.int64), ke)

        gp = 1.0 / np.sqrt(3.0)
        pts = [(-gp, -gp), (gp, -gp), (gp, gp), (-gp, gp)]
        for eid, conn in enumerate(quad):
            k = mats[int(quad_mat[eid])].k if quad_mat.size else 1.0
            conn_i = np.asarray(conn, dtype=np.int64)
            xy_e = xy[conn_i]
            ke = np.zeros((4, 4), dtype=float)
            for xi, eta in pts:
                dN_dxi, dN_deta = _quad_shape_derivs(float(xi), float(eta))
                J = np.zeros((2, 2), dtype=float)
                J[0, 0] = float(np.dot(dN_dxi, xy_e[:, 0]))
                J[0, 1] = float(np.dot(dN_dxi, xy_e[:, 1]))
                J[1, 0] = float(np.dot(dN_deta, xy_e[:, 0]))
                J[1, 1] = float(np.dot(dN_deta, xy_e[:, 1]))
                detJ = float(np.linalg.det(J))
                invJ = np.linalg.inv(J)
                grads = np.vstack([dN_dxi, dN_deta]).T @ invJ.T  # (4,2)
                for i in range(4):
                    for j in range(4):
                        ke[i, j] += float(k) * float(np.dot(grads[i], grads[j])) * detJ
            add_ke(conn_i, ke)

        K = coo_matrix((np.asarray(data, dtype=float), (np.asarray(rows), np.asarray(cols))), shape=(n_nodes, n_nodes)).tocsr()

        def accumulate_bcs(stages_upto: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
            fixed: dict[int, float] = {}
            for st in stages_upto:
                for bc in st.get("bcs", []) if isinstance(st.get("bcs"), list) else []:
                    if not isinstance(bc, dict) or str(bc.get("type", "")) != "p":
                        continue
                    set_name = str(bc.get("set", "")).strip()
                    if not set_name:
                        continue
                    nodes = _nodes_from_set(mesh, set_name)
                    val = float(bc.get("value"))
                    for nid in nodes:
                        fixed[int(nid)] = val
            if not fixed:
                return np.zeros((0,), dtype=np.int64), np.zeros((0,), dtype=float)
            dofs = np.fromiter(fixed.keys(), dtype=np.int64)
            vals = np.asarray([fixed[int(d)] for d in dofs], dtype=float)
            return dofs, vals

        def accumulate_flux_loads(stages_upto: list[dict[str, Any]], scale_current: float) -> np.ndarray:
            F = np.zeros((n_nodes,), dtype=float)
            for si, st in enumerate(stages_upto):
                is_current = si == (len(stages_upto) - 1)
                fac = float(scale_current) if is_current else 1.0
                loads = st.get("loads", [])
                if not isinstance(loads, list):
                    continue
                for ld in loads:
                    if not isinstance(ld, dict) or str(ld.get("type", "")) != "flux":
                        continue
                    set_name = str(ld.get("set", "")).strip()
                    if not set_name:
                        continue
                    qn = float(ld.get("value")) * fac
                    edges = _edges_from_set(mesh, set_name)
                    for n1, n2 in edges:
                        p1 = xy[int(n1)]
                        p2 = xy[int(n2)]
                        L = float(np.linalg.norm(p2 - p1))
                        F[int(n1)] += qn * (L / 2.0)
                        F[int(n2)] += qn * (L / 2.0)
            return F

        stages = request.get("stages", [])
        if not isinstance(stages, list) or not stages:
            raise ValueError("request.stages must be a non-empty list")

        global_outreq = request.get("output_requests", [])
        if not isinstance(global_outreq, list):
            global_outreq = []

        def requested_outputs(stage: dict[str, Any]) -> tuple[set[str], int]:
            reqs: list[dict[str, Any]] = []
            for src in (global_outreq, stage.get("output_requests", [])):
                if isinstance(src, list):
                    for it in src:
                        if isinstance(it, dict):
                            reqs.append(it)
            names: set[str] = set()
            strides: list[int] = []
            for it in reqs:
                nm = it.get("name")
                if isinstance(nm, str) and nm.strip():
                    names.add(nm.strip())
                en = it.get("every_n", 1)
                try:
                    en_i = int(en)
                except Exception:
                    en_i = 1
                if en_i >= 1:
                    strides.append(en_i)
            supported = {"p"}
            names = {n for n in names if n in supported}
            if not names:
                names = set(supported)
            every_n = min(strides) if strides else 1
            every_n = max(int(every_n), 1)
            return names, every_n

        def stage_output_steps(num_steps: int, every_n: int) -> list[int]:
            idx = sorted({i for i in range(max(int(num_steps), 1)) if (i % max(int(every_n), 1) == 0) or (i == int(num_steps) - 1)})
            return idx or [int(num_steps) - 1]

        total_frames = 0
        for st in stages:
            if not isinstance(st, dict):
                continue
            ns = int(st.get("num_steps", 1) or 1)
            _names, ev = requested_outputs(st)
            total_frames += len(stage_output_steps(ns, ev))
        total_frames = max(int(total_frames), 1)

        arrays: dict[str, Any] = {}
        stage_infos: list[dict[str, Any]] = []
        global_steps: list[dict[str, Any]] = []
        step_counter = 0
        t_acc = 0.0

        for si, st in enumerate(stages):
            if not isinstance(st, dict):
                continue
            stage_id = str(st.get("id") or st.get("uid") or st.get("name") or f"stage_{si+1}")
            num_steps = int(st.get("num_steps", 1) or 1)
            dt = float(st.get("dt", 1.0) or 1.0)
            want, every_n = requested_outputs(st)
            out_steps = stage_output_steps(num_steps, every_n)
            times: list[float] = []
            stage_step_ids: list[int] = []
            t_stage0 = float(t_acc)

            for sstep in out_steps:
                if should_cancel():
                    from geohpem.app.errors import CancelledError

                    raise CancelledError("Cancelled by user")
                step_counter += 1
                fac = float(sstep + 1) / float(num_steps)
                pprog = float(step_counter) / float(total_frames)
                cb_progress(pprog, "reference_seepage solving...", stage_id, sstep)

                active_stages = [ss for ss in stages[: si + 1] if isinstance(ss, dict)]
                F = accumulate_flux_loads(active_stages, fac)
                fixed_dofs, fixed_vals = accumulate_bcs(active_stages)

                p = np.zeros((n_nodes,), dtype=float)
                if fixed_dofs.size:
                    p[fixed_dofs] = fixed_vals
                rhs = F - K @ p
                free = np.ones((n_nodes,), dtype=bool)
                free[fixed_dofs] = False
                Kff = K[free][:, free]
                pff = spsolve(Kff, rhs[free])
                p[free] = np.asarray(pff, dtype=float).reshape(-1)

                step_key = f"{step_counter:06d}"
                arrays_out: dict[str, Any] = {}
                if "p" in want:
                    arrays[f"nodal__p__step{step_key}"] = p.reshape(-1)
                    arrays_out[f"nodal__p__step{step_key}"] = arrays[f"nodal__p__step{step_key}"]

                t = t_stage0 + float(sstep + 1) * float(dt)
                times.append(float(t))
                stage_step_ids.append(int(sstep))
                global_steps.append({"id": int(step_counter), "stage_id": stage_id, "stage_step": int(sstep), "time": float(t)})

                cb_frame(
                    {
                        "id": int(step_counter),
                        "time": float(t),
                        "stage_id": str(stage_id),
                        "stage_step": int(sstep),
                        "substep": None,
                        "events": [],
                    },
                    mesh_out=None,
                    arrays_out=arrays_out,
                )

            t_acc = t_stage0 + float(num_steps) * float(dt)
            stage_infos.append({"id": stage_id, "num_steps": int(num_steps), "output_every_n": int(every_n), "output_stage_steps": stage_step_ids, "times": list(times)})

        unit_p = request.get("unit_system", {}).get("pressure", "Pa")
        present = any(k.startswith("nodal__p__step") for k in arrays.keys())
        meta = {
            "schema_version": "0.2",
            "status": "success",
            "solver_info": {"name": "reference_seepage", "note": "steady seepage reference solver (scipy.sparse)"},
            "stages": stage_infos,
            "global_steps": global_steps,
            "warnings": [],
            "errors": [],
            "registry": ([{"name": "p", "location": "node", "shape": "scalar", "unit": unit_p, "npz_pattern": "nodal__p__step{step:06d}"}] if present else []),
        }
        return meta, arrays


def get_solver() -> ReferenceSeepageSolver:
    return ReferenceSeepageSolver()
