from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class PrecheckIssue:
    severity: str  # "ERROR" | "WARN" | "INFO"
    code: str
    message: str


def _issue(severity: str, code: str, message: str) -> PrecheckIssue:
    return PrecheckIssue(severity=severity, code=code, message=message)


def _as_set_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _mesh_has_cells(mesh: dict[str, Any]) -> bool:
    return any(k.startswith("cells_") and getattr(mesh.get(k), "shape", None) is not None for k in mesh.keys())


def _collect_set_names(mesh: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for k in mesh.keys():
        if k.startswith("node_set__"):
            names.add(k.split("__", 1)[1])
        if k.startswith("edge_set__"):
            names.add(k.split("__", 1)[1])
        if k.startswith("elem_set__"):
            # elem_set__NAME__tri3
            rest = k.split("__", 1)[1]
            names.add(rest.split("__", 1)[0])
    return names


def precheck_request_mesh(request: dict[str, Any], mesh: dict[str, Any]) -> list[PrecheckIssue]:
    issues: list[PrecheckIssue] = []

    if request.get("schema_version") != "0.1":
        issues.append(_issue("ERROR", "REQ_SCHEMA", "request.schema_version must be '0.1'"))

    model = request.get("model")
    if not isinstance(model, dict):
        issues.append(_issue("ERROR", "REQ_MODEL", "request.model must be an object"))
    else:
        if model.get("dimension") != 2:
            issues.append(_issue("ERROR", "REQ_DIM", "request.model.dimension must be 2"))
        if model.get("mode") not in ("plane_strain", "axisymmetric"):
            issues.append(_issue("ERROR", "REQ_MODE", "request.model.mode must be 'plane_strain' or 'axisymmetric'"))

    stages = request.get("stages")
    if not isinstance(stages, list) or not stages:
        issues.append(_issue("ERROR", "REQ_STAGES", "request.stages must be a non-empty list"))
        stages = []

    if "points" not in mesh:
        issues.append(_issue("ERROR", "MESH_POINTS", "mesh.npz must contain 'points'"))
    else:
        pts = mesh.get("points")
        try:
            npts = int(getattr(pts, "shape")[0])
        except Exception:
            npts = -1
        if npts == 0:
            issues.append(_issue("WARN", "MESH_EMPTY", "Mesh has 0 points (empty mesh)."))

    if not _mesh_has_cells(mesh):
        issues.append(_issue("ERROR", "MESH_CELLS", "mesh.npz must contain at least one 'cells_*' array"))

    set_names = _collect_set_names(mesh)

    # Check stage references to sets (bcs/loads).
    for si, stage in enumerate(stages):
        if not isinstance(stage, dict):
            issues.append(_issue("ERROR", "STAGE_TYPE", f"Stage[{si}] must be an object"))
            continue
        stage_id = stage.get("id", f"stage_{si+1}")

        for bc in stage.get("bcs", []) if isinstance(stage.get("bcs"), list) else []:
            if not isinstance(bc, dict):
                continue
            set_name = _as_set_name(bc.get("set"))
            if set_name and set_name not in set_names:
                issues.append(_issue("ERROR", "BC_SET_MISSING", f"{stage_id}: BC references missing set '{set_name}'"))

        for load in stage.get("loads", []) if isinstance(stage.get("loads"), list) else []:
            if not isinstance(load, dict):
                continue
            set_name = _as_set_name(load.get("set"))
            if set_name and set_name not in set_names:
                issues.append(_issue("ERROR", "LOAD_SET_MISSING", f"{stage_id}: Load references missing set '{set_name}'"))

    # Check assignments -> element sets
    assignments = request.get("assignments", [])
    if isinstance(assignments, list):
        for ai, a in enumerate(assignments):
            if not isinstance(a, dict):
                continue
            es = _as_set_name(a.get("element_set"))
            if es and es not in set_names:
                issues.append(_issue("ERROR", "ASSIGN_SET_MISSING", f"Assignment[{ai}] references missing set '{es}'"))

    return issues


def summarize_issues(issues: Iterable[PrecheckIssue]) -> tuple[int, int, int]:
    e = sum(1 for i in issues if i.severity == "ERROR")
    w = sum(1 for i in issues if i.severity == "WARN")
    info = sum(1 for i in issues if i.severity == "INFO")
    return e, w, info

