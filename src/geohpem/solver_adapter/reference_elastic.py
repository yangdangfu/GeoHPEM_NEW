from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class _MatElastic:
    E: float
    nu: float
    rho: float


def _as_float2(v: Any, *, name: str) -> tuple[float, float]:
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return float(v[0]), float(v[1])
    raise ValueError(f"Expected {name} as [x,y]")


def _plane_D(*, E: float, nu: float, mode: str) -> np.ndarray:
    E = float(E)
    nu = float(nu)
    if mode == "plane_stress":
        c = E / (1.0 - nu**2)
        return c * np.array([[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu) / 2.0]], dtype=float)
    if mode == "plane_strain":
        c = E / ((1.0 + nu) * (1.0 - 2.0 * nu))
        return c * np.array(
            [[1.0 - nu, nu, 0.0], [nu, 1.0 - nu, 0.0], [0.0, 0.0, (1.0 - 2.0 * nu) / 2.0]],
            dtype=float,
        )
    raise ValueError(f"Unsupported mode for reference_elastic: {mode}")


def _tri_B_area(xy: np.ndarray) -> tuple[np.ndarray, float]:
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
    B = np.zeros((3, 6), dtype=float)
    for i in range(3):
        B[0, 2 * i + 0] = dNdx[i]
        B[1, 2 * i + 1] = dNdy[i]
        B[2, 2 * i + 0] = dNdy[i]
        B[2, 2 * i + 1] = dNdx[i]
    return B, abs(A)


def _quad_shape_derivs(xi: float, eta: float) -> tuple[np.ndarray, np.ndarray]:
    # Node ordering: (-1,-1),(+1,-1),(+1,+1),(-1,+1)
    dN_dxi = 0.25 * np.array([-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)], dtype=float)
    dN_deta = 0.25 * np.array([-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)], dtype=float)
    return dN_dxi, dN_deta


def _quad_shape(xi: float, eta: float) -> np.ndarray:
    return 0.25 * np.array(
        [(1 - xi) * (1 - eta), (1 + xi) * (1 - eta), (1 + xi) * (1 + eta), (1 - xi) * (1 + eta)],
        dtype=float,
    )


def _quad_ke_fe(xy: np.ndarray, D: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # 2x2 Gauss points
    gp = 1.0 / np.sqrt(3.0)
    pts = [(-gp, -gp), (gp, -gp), (gp, gp), (-gp, gp)]
    ke = np.zeros((8, 8), dtype=float)
    fe = np.zeros((8,), dtype=float)
    for xi, eta in pts:
        dN_dxi, dN_deta = _quad_shape_derivs(float(xi), float(eta))
        J = np.zeros((2, 2), dtype=float)
        J[0, 0] = float(np.dot(dN_dxi, xy[:, 0]))
        J[0, 1] = float(np.dot(dN_dxi, xy[:, 1]))
        J[1, 0] = float(np.dot(dN_deta, xy[:, 0]))
        J[1, 1] = float(np.dot(dN_deta, xy[:, 1]))
        detJ = float(np.linalg.det(J))
        if detJ == 0.0:
            raise ValueError("Degenerate quad4 (zero Jacobian)")
        invJ = np.linalg.inv(J)
        grads = np.vstack([dN_dxi, dN_deta]).T @ invJ.T  # (4,2) => [dNdx,dNdy]
        B = np.zeros((3, 8), dtype=float)
        for i in range(4):
            dNdx = float(grads[i, 0])
            dNdy = float(grads[i, 1])
            B[0, 2 * i + 0] = dNdx
            B[1, 2 * i + 1] = dNdy
            B[2, 2 * i + 0] = dNdy
            B[2, 2 * i + 1] = dNdx
        ke += (B.T @ D @ B) * detJ

        N = _quad_shape(float(xi), float(eta))
        # fe = ∫ N^T * b dA (2 dof per node)
        for i in range(4):
            fe[2 * i + 0] += float(N[i]) * float(b[0]) * detJ
            fe[2 * i + 1] += float(N[i]) * float(b[1]) * detJ
    return ke, fe


def _tri_ke_fe(xy: np.ndarray, D: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    B, A = _tri_B_area(xy)
    ke = (B.T @ D @ B) * A
    # constant body force: fe = b * A/3 per node
    fe = np.zeros((6,), dtype=float)
    for i in range(3):
        fe[2 * i + 0] = float(b[0]) * A / 3.0
        fe[2 * i + 1] = float(b[1]) * A / 3.0
    return ke, fe


def _von_mises_2d(sig: np.ndarray) -> float:
    sx = float(sig[0])
    sy = float(sig[1])
    sxy = float(sig[2])
    return float(np.sqrt(sx * sx - sx * sy + sy * sy + 3.0 * sxy * sxy))


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
    e = np.asarray(mesh[k_edge], dtype=np.int64).reshape(-1, 2)
    return e


def _material_assignment(
    *,
    mesh: dict[str, Any],
    assignments: list[dict[str, Any]],
    materials: dict[str, Any],
) -> tuple[list[_MatElastic], np.ndarray, np.ndarray]:
    tri = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64)), dtype=np.int64)
    quad = np.asarray(mesh.get("cells_quad4", np.zeros((0, 4), dtype=np.int64)), dtype=np.int64)
    tri_mat = np.full((tri.shape[0],), -1, dtype=np.int32)
    quad_mat = np.full((quad.shape[0],), -1, dtype=np.int32)

    mats: list[_MatElastic] = []
    mat_index: dict[str, int] = {}

    def get_mat(mid: str) -> int:
        if mid in mat_index:
            return mat_index[mid]
        m = materials.get(mid)
        if not isinstance(m, dict):
            raise ValueError(f"Unknown material_id: {mid}")
        if str(m.get("model_name")) != "linear_elastic":
            raise ValueError(f"reference_elastic supports only linear_elastic, got {m.get('model_name')}")
        pars = m.get("parameters")
        if not isinstance(pars, dict):
            raise ValueError(f"material.parameters must be object for {mid}")
        E = float(pars.get("E"))
        nu = float(pars.get("nu"))
        rho = float(pars.get("rho", 0.0))
        mats.append(_MatElastic(E=E, nu=nu, rho=rho))
        mat_index[mid] = len(mats) - 1
        return mat_index[mid]

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
    return mats, tri_mat, quad_mat


class ReferenceElasticSolver:
    """
    Reference solver: small-strain linear elasticity (static).

    This is intended as an interface/example implementation for solver-team integration,
    not as a high-performance production solver.
    """

    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "reference_elastic",
            "contract": {"min": "0.2", "max": "0.2"},
            "modes": ["plane_strain", "plane_stress"],
            "analysis_types": ["static"],
            "materials": ["linear_elastic"],
            "bcs": ["displacement"],
            "loads": ["gravity", "traction"],
            "fields": ["u", "sx", "sy", "sxy", "vm"],
            "results": ["u", "stress", "vm"],
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from scipy.sparse import coo_matrix, csr_matrix  # type: ignore
        from scipy.sparse.linalg import spsolve  # type: ignore

        def cb_progress(p: float, msg: str, stage_id: str, step: int) -> None:
            if callbacks and (fn := callbacks.get("on_progress")):
                fn(float(p), str(msg), str(stage_id), int(step))

        def cb_frame(frame_meta: dict[str, Any], *, mesh_out: dict[str, Any] | None = None, arrays_out: dict[str, Any] | None = None) -> None:
            """
            Optional per-frame callback (PFEM/HPEM-friendly): can be used for streaming visualization/logging.
            Platform currently may ignore this; it is provided as a template for solver teams.
            """
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

        model = request.get("model", {}) if isinstance(request.get("model"), dict) else {}
        mode = str(model.get("mode", "plane_strain"))
        if mode not in ("plane_strain", "plane_stress"):
            raise ValueError(f"reference_elastic supports only plane_strain/plane_stress, got {mode}")

        points = np.asarray(mesh["points"], dtype=float)
        if points.ndim != 2 or points.shape[1] < 2:
            raise ValueError("mesh.points must be (N,2)")
        xy = points[:, :2]
        n_nodes = int(xy.shape[0])
        ndof = 2 * n_nodes

        tri = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64)), dtype=np.int64)
        quad = np.asarray(mesh.get("cells_quad4", np.zeros((0, 4), dtype=np.int64)), dtype=np.int64)

        assignments = request.get("assignments", [])
        if not isinstance(assignments, list):
            assignments = []
        materials = request.get("materials", {})
        if not isinstance(materials, dict):
            materials = {}
        mats, tri_mat, quad_mat = _material_assignment(mesh=mesh, assignments=assignments, materials=materials)

        # Assemble global K and base body force F (gravity)
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []
        F_body = np.zeros((ndof,), dtype=float)

        # gravity vector (force direction); actual body force = rho * g
        g = model.get("gravity", [0.0, 0.0])
        gx, gy = _as_float2(g, name="model.gravity")
        gvec = np.array([gx, gy], dtype=float)

        def add_ke_fe(conn: np.ndarray, ke: np.ndarray, fe: np.ndarray) -> None:
            dofs = np.empty((2 * conn.size,), dtype=np.int64)
            for i, nid in enumerate(conn):
                dofs[2 * i + 0] = 2 * int(nid) + 0
                dofs[2 * i + 1] = 2 * int(nid) + 1
            # stiffness
            for a in range(dofs.size):
                ra = int(dofs[a])
                for b in range(dofs.size):
                    rows.append(ra)
                    cols.append(int(dofs[b]))
                    data.append(float(ke[a, b]))
            # body force
            for a in range(dofs.size):
                F_body[int(dofs[a])] += float(fe[a])

        for eid, conn in enumerate(tri):
            midx = int(tri_mat[eid]) if tri_mat.size else 0
            m = mats[midx]
            D = _plane_D(E=m.E, nu=m.nu, mode=mode)
            b = m.rho * gvec
            ke, fe = _tri_ke_fe(xy[np.asarray(conn, dtype=np.int64)], D, b)
            add_ke_fe(np.asarray(conn, dtype=np.int64), ke, fe)

        for eid, conn in enumerate(quad):
            midx = int(quad_mat[eid]) if quad_mat.size else 0
            m = mats[midx]
            D = _plane_D(E=m.E, nu=m.nu, mode=mode)
            b = m.rho * gvec
            ke, fe = _quad_ke_fe(xy[np.asarray(conn, dtype=np.int64)], D, b)
            add_ke_fe(np.asarray(conn, dtype=np.int64), ke, fe)

        K = coo_matrix((np.asarray(data, dtype=float), (np.asarray(rows), np.asarray(cols))), shape=(ndof, ndof)).tocsr()

        # Helper: traction loads -> global F
        def traction_vector(load: dict[str, Any]) -> tuple[str, np.ndarray]:
            set_name = str(load.get("set", "")).strip()
            if not set_name:
                raise ValueError("traction.load.set is required")
            tx, ty = _as_float2(load.get("value"), name="traction.value")
            return set_name, np.array([tx, ty], dtype=float)

        def add_traction(F: np.ndarray, edges: np.ndarray, t: np.ndarray) -> None:
            for n1, n2 in np.asarray(edges, dtype=np.int64):
                p1 = xy[int(n1)]
                p2 = xy[int(n2)]
                L = float(np.linalg.norm(p2 - p1))
                f = t * (L / 2.0)  # per node, thickness=1
                F[2 * int(n1) + 0] += float(f[0])
                F[2 * int(n1) + 1] += float(f[1])
                F[2 * int(n2) + 0] += float(f[0])
                F[2 * int(n2) + 1] += float(f[1])

        # BCs: accumulate fixed dofs and prescribed values (later stages override earlier)
        def accumulate_bcs(stages_upto: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
            fixed: dict[int, float] = {}
            for st in stages_upto:
                for bc in st.get("bcs", []) if isinstance(st.get("bcs"), list) else []:
                    if not isinstance(bc, dict) or str(bc.get("type", "")) != "displacement":
                        continue
                    set_name = str(bc.get("set", "")).strip()
                    if not set_name:
                        continue
                    nodes = _nodes_from_set(mesh, set_name)
                    val = bc.get("value", {})
                    if not isinstance(val, dict):
                        continue
                    if "ux" in val:
                        ux = float(val["ux"])
                        for nid in nodes:
                            fixed[2 * int(nid) + 0] = ux
                    if "uy" in val:
                        uy = float(val["uy"])
                        for nid in nodes:
                            fixed[2 * int(nid) + 1] = uy
            if not fixed:
                return np.zeros((0,), dtype=np.int64), np.zeros((0,), dtype=float)
            dofs = np.fromiter(fixed.keys(), dtype=np.int64)
            vals = np.asarray([fixed[int(d)] for d in dofs], dtype=float)
            return dofs, vals

        # Loads: gravity override + traction (cumulative)
        def accumulate_loads(stages_upto: list[dict[str, Any]], scale_current: float) -> np.ndarray:
            F = np.array(F_body, copy=True)
            for si, st in enumerate(stages_upto):
                is_current = si == (len(stages_upto) - 1)
                fac = float(scale_current) if is_current else 1.0
                loads = st.get("loads", [])
                if not isinstance(loads, list):
                    continue
                for ld in loads:
                    if not isinstance(ld, dict):
                        continue
                    tp = str(ld.get("type", ""))
                    if tp == "gravity":
                        # override gravity vector for this stage (affects body force only)
                        gx2, gy2 = _as_float2(ld.get("value"), name="gravity.value")
                        g2 = np.array([gx2, gy2], dtype=float)
                        # recompute body force contribution per element with this gravity (scaled)
                        # For reference implementation simplicity: treat gravity as additional body load.
                        # Users can keep gravity only in model.gravity for deterministic behavior.
                        if np.linalg.norm(g2) > 0:
                            # add delta body force (rho*(g2-g)) scaled
                            dg = (g2 - gvec) * fac
                            if np.linalg.norm(dg) == 0:
                                continue
                            Fb = np.zeros_like(F)
                            for eid, conn in enumerate(tri):
                                midx = int(tri_mat[eid]) if tri_mat.size else 0
                                m = mats[midx]
                                D = _plane_D(E=m.E, nu=m.nu, mode=mode)
                                b = m.rho * dg
                                _ke, fe = _tri_ke_fe(xy[np.asarray(conn, dtype=np.int64)], D, b)
                                dofs = np.array([2 * int(n) for n in conn] + [2 * int(n) + 1 for n in conn], dtype=np.int64)
                                # fe is interleaved; map by loop
                                for i, nid in enumerate(conn):
                                    Fb[2 * int(nid) + 0] += float(fe[2 * i + 0])
                                    Fb[2 * int(nid) + 1] += float(fe[2 * i + 1])
                            for eid, conn in enumerate(quad):
                                midx = int(quad_mat[eid]) if quad_mat.size else 0
                                m = mats[midx]
                                D = _plane_D(E=m.E, nu=m.nu, mode=mode)
                                b = m.rho * dg
                                _ke, fe = _quad_ke_fe(xy[np.asarray(conn, dtype=np.int64)], D, b)
                                for i, nid in enumerate(conn):
                                    Fb[2 * int(nid) + 0] += float(fe[2 * i + 0])
                                    Fb[2 * int(nid) + 1] += float(fe[2 * i + 1])
                            F += Fb
                    elif tp == "traction":
                        set_name, t = traction_vector(ld)
                        edges = _edges_from_set(mesh, set_name)
                        add_traction(F, edges, t * fac)
            return F

        stages = request.get("stages", [])
        if not isinstance(stages, list) or not stages:
            raise ValueError("request.stages must be a non-empty list")

        total_steps = sum(int(st.get("num_steps", 1) or 1) for st in stages if isinstance(st, dict))
        total_steps = max(int(total_steps), 1)

        arrays: dict[str, Any] = {}
        stage_infos: list[dict[str, Any]] = []
        global_steps: list[dict[str, Any]] = []
        step_counter = 0
        t_acc = 0.0

        # Solve per stage-step (linear ramp of current-stage loads)
        for si, st in enumerate(stages):
            if not isinstance(st, dict):
                continue
            stage_id = str(st.get("id") or st.get("uid") or st.get("name") or f"stage_{si+1}")
            num_steps = int(st.get("num_steps", 1) or 1)
            dt = float(st.get("dt", 1.0) or 1.0)
            times: list[float] = []

            for sstep in range(num_steps):
                if should_cancel():
                    from geohpem.app.errors import CancelledError

                    raise CancelledError("Cancelled by user")
                step_counter += 1
                fac = float(sstep + 1) / float(num_steps)
                p = float(step_counter) / float(total_steps)
                cb_progress(p, "reference_elastic solving...", stage_id, sstep)

                active_stages = [ss for ss in stages[: si + 1] if isinstance(ss, dict)]
                F = accumulate_loads(active_stages, fac)
                fixed_dofs, fixed_vals = accumulate_bcs(active_stages)

                u = np.zeros((ndof,), dtype=float)
                if fixed_dofs.size:
                    u[fixed_dofs] = fixed_vals
                rhs = F - K @ u
                free = np.ones((ndof,), dtype=bool)
                free[fixed_dofs] = False
                Kff = K[free][:, free]
                uff = spsolve(Kff, rhs[free])
                u[free] = np.asarray(uff, dtype=float).reshape(-1)
                u_xy = u.reshape(n_nodes, 2)

                # stresses in VTK cell order: tri then quad
                sx_list: list[float] = []
                sy_list: list[float] = []
                sxy_list: list[float] = []
                vm_list: list[float] = []

                for eid, conn in enumerate(tri):
                    midx = int(tri_mat[eid]) if tri_mat.size else 0
                    m = mats[midx]
                    D = _plane_D(E=m.E, nu=m.nu, mode=mode)
                    B, _A = _tri_B_area(xy[np.asarray(conn, dtype=np.int64)])
                    ue = u[np.array([2 * int(n) + d for n in conn for d in (0, 1)], dtype=np.int64)]
                    eps = B @ ue
                    sig = D @ eps
                    sx_list.append(float(sig[0]))
                    sy_list.append(float(sig[1]))
                    sxy_list.append(float(sig[2]))
                    vm_list.append(_von_mises_2d(sig))

                for eid, conn in enumerate(quad):
                    midx = int(quad_mat[eid]) if quad_mat.size else 0
                    m = mats[midx]
                    D = _plane_D(E=m.E, nu=m.nu, mode=mode)
                    # average stress over Gauss points
                    gp = 1.0 / np.sqrt(3.0)
                    pts = [(-gp, -gp), (gp, -gp), (gp, gp), (-gp, gp)]
                    sigs: list[np.ndarray] = []
                    conn_i = np.asarray(conn, dtype=np.int64)
                    xy_e = xy[conn_i]
                    ue = u[np.array([2 * int(n) + d for n in conn_i for d in (0, 1)], dtype=np.int64)]
                    for xi, eta in pts:
                        dN_dxi, dN_deta = _quad_shape_derivs(float(xi), float(eta))
                        J = np.zeros((2, 2), dtype=float)
                        J[0, 0] = float(np.dot(dN_dxi, xy_e[:, 0]))
                        J[0, 1] = float(np.dot(dN_dxi, xy_e[:, 1]))
                        J[1, 0] = float(np.dot(dN_deta, xy_e[:, 0]))
                        J[1, 1] = float(np.dot(dN_deta, xy_e[:, 1]))
                        invJ = np.linalg.inv(J)
                        grads = np.vstack([dN_dxi, dN_deta]).T @ invJ.T
                        B = np.zeros((3, 8), dtype=float)
                        for i in range(4):
                            dNdx = float(grads[i, 0])
                            dNdy = float(grads[i, 1])
                            B[0, 2 * i + 0] = dNdx
                            B[1, 2 * i + 1] = dNdy
                            B[2, 2 * i + 0] = dNdy
                            B[2, 2 * i + 1] = dNdx
                        eps = B @ ue
                        sigs.append(D @ eps)
                    sig = np.mean(np.vstack(sigs), axis=0)
                    sx_list.append(float(sig[0]))
                    sy_list.append(float(sig[1]))
                    sxy_list.append(float(sig[2]))
                    vm_list.append(_von_mises_2d(sig))

                step_key = f"{step_counter:06d}"
                arrays[f"nodal__u__step{step_key}"] = u_xy
                arrays[f"elem__sx__step{step_key}"] = np.asarray(sx_list, dtype=float)
                arrays[f"elem__sy__step{step_key}"] = np.asarray(sy_list, dtype=float)
                arrays[f"elem__sxy__step{step_key}"] = np.asarray(sxy_list, dtype=float)
                arrays[f"elem__vm__step{step_key}"] = np.asarray(vm_list, dtype=float)

                t_acc += dt
                times.append(float(t_acc))
                global_steps.append({"id": int(step_counter), "stage_id": stage_id, "stage_step": int(sstep), "time": float(t_acc)})

                cb_frame(
                    {
                        "id": int(step_counter),
                        "time": float(t_acc),
                        "stage_id": str(stage_id),
                        "stage_step": int(sstep),
                        "substep": None,
                        "events": [],
                    },
                    mesh_out=None,
                    arrays_out={
                        f"nodal__u__step{step_key}": arrays[f"nodal__u__step{step_key}"],
                        f"elem__vm__step{step_key}": arrays[f"elem__vm__step{step_key}"],
                    },
                )

            stage_infos.append({"id": stage_id, "num_steps": int(num_steps), "times": list(times)})

        unit_len = request.get("unit_system", {}).get("length", "m")
        unit_p = request.get("unit_system", {}).get("pressure", "Pa")
        meta = {
            "schema_version": "0.1",
            "status": "success",
            "solver_info": {"name": "reference_elastic", "note": "linear elastic reference solver (scipy.sparse)"},
            "stages": stage_infos,
            "global_steps": global_steps,
            "warnings": [],
            "errors": [],
            "registry": [
                {"name": "u", "location": "node", "shape": "vector2", "unit": unit_len, "npz_pattern": "nodal__u__step{step:06d}"},
                {"name": "sx", "location": "element", "shape": "scalar", "unit": unit_p, "npz_pattern": "elem__sx__step{step:06d}"},
                {"name": "sy", "location": "element", "shape": "scalar", "unit": unit_p, "npz_pattern": "elem__sy__step{step:06d}"},
                {"name": "sxy", "location": "element", "shape": "scalar", "unit": unit_p, "npz_pattern": "elem__sxy__step{step:06d}"},
                {"name": "vm", "location": "element", "shape": "scalar", "unit": unit_p, "npz_pattern": "elem__vm__step{step:06d}"},
            ],
        }
        return meta, arrays


def get_solver() -> ReferenceElasticSolver:
    return ReferenceElasticSolver()
