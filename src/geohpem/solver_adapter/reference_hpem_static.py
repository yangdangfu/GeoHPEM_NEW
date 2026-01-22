from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass(frozen=True, slots=True)
class _SetMaps:
    node_ids: dict[str, int]
    edge_ids: dict[str, int]
    elem_ids: dict[str, int]


def _iter_set_names(mesh: dict[str, Any], *, prefix: str) -> list[str]:
    names: list[str] = []
    for key in mesh.keys():
        if not isinstance(key, str) or not key.startswith(prefix):
            continue
        names.append(key[len(prefix) :])
    return sorted(set(names))


def _collect_elem_sets(mesh: dict[str, Any]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for key, val in mesh.items():
        if not isinstance(key, str) or not key.startswith("elem_set__"):
            continue
        if "__tri3" not in key:
            continue
        name = key[len("elem_set__") : key.rfind("__tri3")]
        arr = np.asarray(val, dtype=np.int64).reshape(-1)
        out[name] = arr
    return out


def _compute_mesh_size(points: np.ndarray, tri: np.ndarray) -> float:
    if tri.size == 0:
        return 1.0
    p0 = points[tri[:, 0], :2]
    p1 = points[tri[:, 1], :2]
    p2 = points[tri[:, 2], :2]
    e01 = np.linalg.norm(p1 - p0, axis=1)
    e12 = np.linalg.norm(p2 - p1, axis=1)
    e20 = np.linalg.norm(p0 - p2, axis=1)
    sizes = np.concatenate([e01, e12, e20])
    sizes = sizes[np.isfinite(sizes)]
    if sizes.size == 0:
        return 1.0
    return float(np.median(sizes))


def _build_surface_set_from_edges(
    surfaces: np.ndarray, edges: np.ndarray
) -> np.ndarray:
    surf_map: dict[tuple[int, int], list[int]] = {}
    for idx, (a, b) in enumerate(np.asarray(surfaces, dtype=np.int64).reshape(-1, 2)):
        key = (int(min(a, b)), int(max(a, b)))
        surf_map.setdefault(key, []).append(int(idx))
    hits: list[int] = []
    for a, b in np.asarray(edges, dtype=np.int64).reshape(-1, 2):
        key = (int(min(a, b)), int(max(a, b)))
        hits.extend(surf_map.get(key, []))
    if not hits:
        return np.zeros((0,), dtype=np.int64)
    return np.unique(np.asarray(hits, dtype=np.int64))


def _as_vec2(val: Any) -> tuple[float, float]:
    if isinstance(val, dict):
        x = float(val.get("ux", val.get("x", 0.0)))
        y = float(val.get("uy", val.get("y", 0.0)))
        return x, y
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return float(val[0]), float(val[1])
    raise ValueError("Expected a 2D vector (dict or [x,y])")


def _load_reference_modules() -> Callable[..., Any]:
    import importlib.util
    import sys
    import types

    solver_root = Path(__file__).resolve().parents[1] / "solver"

    # Register solver subpackages to satisfy absolute imports inside FEMSimulation.
    for name in (
        "Command_Library",
        "Core_Library",
        "Coupling",
        "Element_Library",
        "Material_Library",
        "Mathematic_Library",
        "model",
        "Post_Processing",
        "Pressure_stabilization",
        "Pre_Processing",
    ):
        if name in sys.modules:
            continue
        pkg = types.ModuleType(name)
        pkg.__path__ = [str(solver_root / name)]
        pkg.__package__ = name
        sys.modules[name] = pkg

    module_path = solver_root / "FEMSimulation.py"
    spec = importlib.util.spec_from_file_location(
        "geohpem.solver.FEMSimulation", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load FEMSimulation from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.FEMSimulation  # type: ignore[attr-defined]


class ReferenceHPEMStaticSolver:
    """
    Adapter for GeoHPEM_reference FEMSimulation (static HPEM).

    Limitations:
    - tri3 meshes only
    - linear_elastic materials only
    - boundary/load types: displacement + pressure/surface_traction
    """

    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "reference_hpem_static",
            "contract": {"min": "0.2", "max": "0.2"},
            "modes": ["plane_strain", "plane_stress"],
            "analysis_types": ["static"],
            "materials": ["linear_elastic"],
            "bcs": ["displacement"],
            "loads": ["pressure", "surface_traction"],
            "fields": ["u_mag", "p"],
            "results": ["u_mag", "p"],
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        def cb_progress(p: float, msg: str, stage_id: str, step: int) -> None:
            if callbacks and (fn := callbacks.get("on_progress")):
                fn(float(p), str(msg), str(stage_id), int(step))

        def cb_frame(
            frame_meta: dict[str, Any], *, mesh_out=None, arrays_out=None
        ) -> None:  # noqa: ANN001
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

        stages = request.get("stages", [])
        if not isinstance(stages, list) or not stages:
            raise ValueError("request.stages is required for reference_hpem_static")
        stage = stages[0] if isinstance(stages[0], dict) else {}
        stage_id = str(stage.get("id", "S1"))
        num_steps = int(stage.get("num_steps", 1))
        dt = float(stage.get("dt", 1.0))

        points = np.asarray(mesh.get("points", []), dtype=float)
        if points.ndim != 2 or points.shape[1] < 2:
            raise ValueError("mesh.points must be (N,2)")
        tri = np.asarray(
            mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int64)), dtype=np.int64
        )
        if tri.ndim != 2 or tri.shape[1] != 3:
            raise ValueError("reference_hpem_static supports tri3 only")

        # Build meshio input for FEMSimulation
        import meshio  # type: ignore

        meshio_mesh = meshio.Mesh(
            points=points[:, :2].astype(np.float64),
            cells={"triangle": tri.astype(np.int32)},
        )
        mesh_size = _compute_mesh_size(points, tri)

        # Build explicit sets
        node_sets_raw = {
            name: np.asarray(mesh[f"node_set__{name}"], dtype=np.int64).reshape(-1)
            for name in _iter_set_names(mesh, prefix="node_set__")
        }
        edge_sets_raw = {
            name: np.asarray(mesh[f"edge_set__{name}"], dtype=np.int64).reshape(-1, 2)
            for name in _iter_set_names(mesh, prefix="edge_set__")
        }
        elem_sets_raw = _collect_elem_sets(mesh)

        node_ids = {name: i + 1 for i, name in enumerate(sorted(node_sets_raw.keys()))}
        edge_ids = {name: i + 1 for i, name in enumerate(sorted(edge_sets_raw.keys()))}
        elem_ids = {name: i + 1 for i, name in enumerate(sorted(elem_sets_raw.keys()))}
        set_maps = _SetMaps(node_ids=node_ids, edge_ids=edge_ids, elem_ids=elem_ids)

        # Materials -> FEMSimulation material_properties
        materials = request.get("materials", {})
        if not isinstance(materials, dict):
            materials = {}
        assignments = request.get("assignments", [])
        if not isinstance(assignments, list):
            assignments = []

        mat_ids: dict[str, int] = {}
        material_properties: dict[int, dict[str, Any]] = {}
        for idx, (mid, mat) in enumerate(materials.items(), start=1):
            if not isinstance(mat, dict):
                continue
            if str(mat.get("model_name")) != "linear_elastic":
                raise ValueError(
                    f"reference_hpem_static supports only linear_elastic, got {mat.get('model_name')}"
                )
            pars = mat.get("parameters", {})
            if not isinstance(pars, dict):
                raise ValueError(f"material.parameters must be object for {mid}")
            E = float(pars.get("E"))
            nu = float(pars.get("nu"))
            rho = float(pars.get("rho", 0.0))
            elasticity = {"parameter": [E, nu, rho]}
            elasticity["shear_modulus"] = E / 2.0 / (1.0 + nu)
            elasticity["bulk_modulus"] = E / 3.0 / (1.0 - 2.0 * nu)
            mat_ids[mid] = idx
            material_properties[idx] = {
                "Elasticity": elasticity,
                "Eset": [],
                "Pset": [],
            }

        for a in assignments:
            if not isinstance(a, dict):
                continue
            if str(a.get("cell_type", "")) != "tri3":
                continue
            es = str(a.get("element_set", "")).strip()
            mid = str(a.get("material_id", "")).strip()
            if not es or not mid or es not in set_maps.elem_ids:
                continue
            if mid not in mat_ids:
                raise ValueError(f"Unknown material_id: {mid}")
            midx = mat_ids[mid]
            material_properties[midx]["Eset"].append(set_maps.elem_ids[es])
            material_properties[midx]["Pset"].append(set_maps.elem_ids[es])

        # Boundary conditions and loads (single stage)
        bcs: list[dict[str, Any]] = []
        for i, bc in enumerate(
            stage.get("bcs", []) if isinstance(stage.get("bcs"), list) else [], start=1
        ):
            if not isinstance(bc, dict):
                continue
            if str(bc.get("type", "")) != "displacement":
                continue
            set_name = str(bc.get("set", "")).strip()
            val = bc.get("value", {})
            expr: list[Any] = []
            dirs: list[int] = []
            if isinstance(val, dict):
                if "ux" in val:
                    expr.append(val["ux"])
                    dirs.append(1)
                if "uy" in val:
                    expr.append(val["uy"])
                    dirs.append(2)
            if not expr:
                continue
            item: dict[str, Any] = {
                "id": i,
                "type": "displacement",
                "Expression": expr,
                "Direction": dirs,
            }
            if set_name in set_maps.node_ids:
                item["Nset"] = [set_maps.node_ids[set_name]]
            elif set_name in set_maps.edge_ids:
                item["Sset"] = [set_maps.edge_ids[set_name]]
            else:
                raise ValueError(f"BC set not found: {set_name}")
            bcs.append(item)

        loads: list[dict[str, Any]] = []
        for i, ld in enumerate(
            stage.get("loads", []) if isinstance(stage.get("loads"), list) else [],
            start=1,
        ):
            if not isinstance(ld, dict):
                continue
            set_name = str(ld.get("set", "")).strip()
            if not set_name:
                continue
            ltype = str(ld.get("type", "")).strip().lower()
            if ltype in ("traction", "surface_traction"):
                tp = "surface_traction"
            elif ltype in ("pressure",):
                tp = "pressure"
            else:
                continue
            item: dict[str, Any] = {"id": i, "type": tp}
            val = ld.get("value", 0.0)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                item["Expression"] = [float(val[0]), float(val[1])]
                item["Direction"] = [1, 2]
            else:
                item["Expression"] = [float(val)]
                item["Direction"] = [2]
            if set_name in set_maps.edge_ids:
                item["Sset"] = [set_maps.edge_ids[set_name]]
            elif set_name in set_maps.node_ids:
                item["Nset"] = [set_maps.node_ids[set_name]]
            else:
                raise ValueError(f"Load set not found: {set_name}")
            loads.append(item)

        # Build FEMSimulation with explicit sets
        FEMSimulation = _load_reference_modules()

        class _ExplicitSetSimulation(FEMSimulation):  # type: ignore
            def __init__(
                self, *, explicit_sets: dict[str, dict[int, np.ndarray]], **kwargs
            ):
                super().__init__(**kwargs)
                self._explicit_sets = explicit_sets

            def define_initial_sets(self, step=None):  # noqa: ANN001
                try:
                    self.Model["Set"]["node_set"] = self._explicit_sets.get(
                        "node_set", {}
                    )
                    self.Model["Set"]["surface_set"] = self._explicit_sets.get(
                        "surface_set", {}
                    )
                    self.Model["Set"]["element_set"] = self._explicit_sets.get(
                        "element_set", {}
                    )
                    self.Model["Set"]["particle_set"] = self._explicit_sets.get(
                        "particle_set", {}
                    )
                except Exception:
                    pass

            def define_single_sets(self, step=None, set_types=None):  # noqa: ANN001
                self.define_initial_sets(step)

        explicit_sets: dict[str, dict[int, np.ndarray]] = {
            "node_set": {
                sid: node_sets_raw[name] for name, sid in set_maps.node_ids.items()
            },
            "surface_set": {},
            "element_set": {
                sid: elem_sets_raw[name] for name, sid in set_maps.elem_ids.items()
            },
            "particle_set": {
                sid: np.zeros((0,), dtype=np.int64)
                for sid in set_maps.elem_ids.values()
            },
        }

        # Build surface sets after FEM mesh is available (need surfaces list)
        frames: list[dict[str, Any]] = []

        def on_frame(
            step: int,
            time: float,
            dt: float,
            p_verts,
            p_scalars,
            e_verts,
            e_inds,
            e_scalars,
        ):  # noqa: ANN001
            frames.append(
                {
                    "step": int(step),
                    "time": float(time),
                    "dt": float(dt),
                    "e_scalars": dict(e_scalars or {}),
                }
            )

        sim = _ExplicitSetSimulation(
            explicit_sets=explicit_sets,
            mesh_data=[meshio_mesh],
            mesh_size=mesh_size,
            num_steps=num_steps,
            material_properties=material_properties,
            tolerance={"Utol": 1e-5, "Ftol": 1e-5, "PCGtol": 1e-8, "MaxIterNum": 50},
            node_sets=[],
            surface_sets=[],
            element_sets=[],
            particle_sets=[],
            boundary_conditions=bcs,
            load_conditions=loads,
            GeometricNonlinear=False,
            implicit=False,
            T=float(num_steps) * float(dt),
            Theta=1.0,
            Coupling=False,
            output=False,
            on_frame=on_frame,
        )

        sim.initialize_model()
        surfaces = np.asarray(sim.Model["Mesh"]["surfaces"], dtype=np.int64).reshape(
            -1, 2
        )
        for name, sid in set_maps.edge_ids.items():
            edges = edge_sets_raw.get(name)
            if edges is None:
                continue
            explicit_sets["surface_set"][sid] = _build_surface_set_from_edges(
                surfaces, edges
            )

        # Run steps (step_once invokes on_frame)
        for step in range(num_steps + 1):
            if should_cancel():
                raise RuntimeError("Canceled")
            cb_progress(
                step / max(num_steps, 1), "HPEM static step", stage_id, int(step)
            )
            sim.step_once()

        arrays: dict[str, Any] = {}
        global_steps: list[dict[str, Any]] = []
        times: list[float] = []
        stage_steps: list[int] = []
        for frame in frames:
            step_id = int(frame["step"])
            t = float(frame["time"])
            global_steps.append(
                {"id": step_id, "stage_id": stage_id, "stage_step": step_id, "time": t}
            )
            stage_steps.append(step_id)
            times.append(t)
            scalars = frame["e_scalars"]
            if "u_mag" in scalars:
                arrays[f"nodal__u_mag__step{step_id:06d}"] = np.asarray(
                    scalars["u_mag"], dtype=np.float32
                ).reshape(-1)
            if "p" in scalars:
                arrays[f"nodal__p__step{step_id:06d}"] = np.asarray(
                    scalars["p"], dtype=np.float32
                ).reshape(-1)
            cb_frame(
                {
                    "id": int(step_id),
                    "time": float(t),
                    "stage_id": stage_id,
                    "stage_step": int(step_id),
                    "substep": None,
                    "events": [],
                },
                arrays_out=None,
            )

        unit_len = request.get("unit_system", {}).get("length", "m")
        unit_p = request.get("unit_system", {}).get("pressure", "Pa")
        registry: list[dict[str, Any]] = []
        if any(k.startswith("nodal__u_mag__step") for k in arrays.keys()):
            registry.append(
                {
                    "name": "u_mag",
                    "location": "node",
                    "shape": "scalar",
                    "unit": unit_len,
                    "npz_pattern": "nodal__u_mag__step{step:06d}",
                }
            )
        if any(k.startswith("nodal__p__step") for k in arrays.keys()):
            registry.append(
                {
                    "name": "p",
                    "location": "node",
                    "shape": "scalar",
                    "unit": unit_p,
                    "npz_pattern": "nodal__p__step{step:06d}",
                }
            )

        meta = {
            "schema_version": "0.2",
            "status": "success",
            "solver_info": {
                "name": "reference_hpem_static",
                "note": "GeoHPEM_reference FEMSimulation (static)",
            },
            "stages": [
                {
                    "id": stage_id,
                    "num_steps": int(num_steps),
                    "output_every_n": 1,
                    "output_stage_steps": stage_steps,
                    "times": times,
                }
            ],
            "global_steps": global_steps,
            "warnings": [],
            "errors": [],
            "registry": registry,
        }
        return meta, arrays


def get_solver() -> ReferenceHPEMStaticSolver:
    return ReferenceHPEMStaticSolver()
