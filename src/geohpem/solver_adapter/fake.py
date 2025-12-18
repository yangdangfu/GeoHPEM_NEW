from __future__ import annotations

import time
from typing import Any

import numpy as np


class FakeSolver:
    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "fake",
            "contract": {"min": "0.1", "max": "0.1"},
            "modes": ["plane_strain", "axisymmetric"],
            "analysis_types": ["static", "dynamic", "seepage_transient", "consolidation_u_p"],
            "fields": ["u", "p"],
            "results": ["u", "p", "stress", "strain", "vm"],
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from geohpem.app.errors import CancelledError

        points = np.asarray(mesh["points"])
        n = points.shape[0]
        n_tri = int(np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64))).shape[0])
        n_quad = int(np.asarray(mesh.get("cells_quad4", np.zeros((0, 4), dtype=np.int64))).shape[0])
        n_cells = n_tri + n_quad

        # Precompute centroids per cell in the same order as vtk_convert (tri3 then quad4)
        def centroids_for(conn: np.ndarray) -> np.ndarray:
            if conn.size == 0:
                return np.zeros((0, 2), dtype=float)
            pts = points[np.asarray(conn, dtype=np.int64)]
            return np.mean(pts[:, :, :2], axis=1)

        tri_conn = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64)), dtype=np.int64)
        quad_conn = np.asarray(mesh.get("cells_quad4", np.zeros((0, 4), dtype=np.int64)), dtype=np.int64)
        cent_tri = centroids_for(tri_conn)
        cent_quad = centroids_for(quad_conn)
        cent = np.vstack([cent_tri, cent_quad]) if (cent_tri.size or cent_quad.size) else np.zeros((0, 2), dtype=float)

        def cb_progress(p: float, msg: str, stage_id: str, step: int) -> None:
            if callbacks and (fn := callbacks.get("on_progress")):
                fn(p, msg, stage_id, step)

        def should_cancel() -> bool:
            if callbacks and (fn := callbacks.get("should_cancel")):
                try:
                    return bool(fn())
                except Exception:
                    return False
            return False

        stages = request["stages"]
        total_steps = sum(int(s.get("num_steps", 1)) for s in stages)
        total_steps = max(total_steps, 1)

        arrays: dict[str, Any] = {}
        stage_infos: list[dict[str, Any]] = []
        global_steps: list[dict[str, Any]] = []
        step_counter = 0

        for si, stage in enumerate(stages):
            stage_id = stage.get("id", f"stage_{si+1}")
            num_steps = int(stage.get("num_steps", 1))
            times = []
            for step in range(num_steps):
                if should_cancel():
                    raise CancelledError("Cancelled by user")
                step_counter += 1
                p = step_counter / total_steps
                cb_progress(p, "fake solving...", stage_id, step)
                time.sleep(0.01)

                disp = np.zeros((n, 2), dtype=float)
                disp[:, 0] = 1e-3 * p
                disp[:, 1] = -1e-3 * p
                pore = np.full((n,), 10.0 * p, dtype=float)
                # Element scalar field (e.g. von Mises-like placeholder) to exercise element plots/picking/history.
                vm = None
                if n_cells > 0:
                    # Create a smooth field varying with depth and time.
                    y = cent[:, 1] if cent.shape[0] == n_cells else np.zeros((n_cells,), dtype=float)
                    vm = (50.0 * p) + (5.0 * y)

                step_key = f"{step_counter:06d}"
                arrays[f"nodal__u__step{step_key}"] = disp
                arrays[f"nodal__p__step{step_key}"] = pore
                if vm is not None:
                    arrays[f"elem__vm__step{step_key}"] = np.asarray(vm, dtype=float)
                times.append(float(stage.get("dt", 1.0)) * (step + 1))
                global_steps.append(
                    {
                        "id": int(step_counter),
                        "stage_id": str(stage_id),
                        "stage_step": int(step),
                        "time": float(times[-1]),
                    }
                )

            stage_infos.append({"id": stage_id, "num_steps": num_steps, "times": times})

        meta = {
            "schema_version": "0.1",
            "status": "success",
            "solver_info": {"name": "fake", "note": "placeholder solver for platform bring-up"},
            "stages": stage_infos,
            "global_steps": global_steps,
            "warnings": [],
            "errors": [],
            "registry": [
                {
                    "name": "u",
                    "location": "node",
                    "shape": "vector2",
                    "unit": request.get("unit_system", {}).get("length", "m"),
                    "npz_pattern": "nodal__u__step{step:06d}",
                },
                {
                    "name": "p",
                    "location": "node",
                    "shape": "scalar",
                    "unit": request.get("unit_system", {}).get("pressure", "kPa"),
                    "npz_pattern": "nodal__p__step{step:06d}",
                },
                {
                    "name": "vm",
                    "location": "element",
                    "shape": "scalar",
                    "unit": request.get("unit_system", {}).get("pressure", "kPa"),
                    "npz_pattern": "elem__vm__step{step:06d}",
                },
            ],
        }
        return meta, arrays
