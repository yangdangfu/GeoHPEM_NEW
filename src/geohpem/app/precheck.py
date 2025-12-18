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


def _parse_version(v: Any) -> tuple[int, ...] | None:
    if not isinstance(v, str) or not v.strip():
        return None
    parts = v.strip().split(".")
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except Exception:
            return None
    return tuple(out)


def _version_in_range(v: str, vmin: str | None, vmax: str | None) -> bool:
    tv = _parse_version(v)
    if tv is None:
        return True
    if vmin:
        tmin = _parse_version(vmin)
        if tmin is not None and tv < tmin:
            return False
    if vmax:
        tmax = _parse_version(vmax)
        if tmax is not None and tv > tmax:
            return False
    return True


def _allowed_output_names(capabilities: dict[str, Any] | None) -> set[str] | None:
    if not capabilities:
        return None
    names: set[str] = set()
    for key in ("results", "fields"):
        v = capabilities.get(key)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, str) and it:
                    names.add(it)
    return names or None


def precheck_request_mesh(
    request: dict[str, Any],
    mesh: dict[str, Any],
    *,
    capabilities: dict[str, Any] | None = None,
) -> list[PrecheckIssue]:
    issues: list[PrecheckIssue] = []

    if request.get("schema_version") != "0.1":
        issues.append(_issue("ERROR", "REQ_SCHEMA", "request.schema_version must be '0.1'"))

    if capabilities:
        contract = capabilities.get("contract")
        if isinstance(contract, dict):
            vmin = contract.get("min")
            vmax = contract.get("max")
            if isinstance(vmin, str) or isinstance(vmax, str):
                if not _version_in_range(str(request.get("schema_version", "")), str(vmin) if isinstance(vmin, str) else None, str(vmax) if isinstance(vmax, str) else None):
                    issues.append(
                        _issue(
                            "ERROR",
                            "CAP_CONTRACT",
                            f"Solver contract range {vmin}-{vmax} does not accept request.schema_version={request.get('schema_version')}",
                        )
                    )

    model = request.get("model")
    if not isinstance(model, dict):
        issues.append(_issue("ERROR", "REQ_MODEL", "request.model must be an object"))
    else:
        if model.get("dimension") != 2:
            issues.append(_issue("ERROR", "REQ_DIM", "request.model.dimension must be 2"))
        if model.get("mode") not in ("plane_strain", "axisymmetric"):
            issues.append(_issue("ERROR", "REQ_MODE", "request.model.mode must be 'plane_strain' or 'axisymmetric'"))
        if capabilities:
            modes = capabilities.get("modes")
            if isinstance(modes, list) and modes:
                allowed = {str(x) for x in modes if isinstance(x, str)}
                if allowed and str(model.get("mode")) not in allowed:
                    issues.append(
                        _issue(
                            "ERROR",
                            "CAP_MODE_UNSUPPORTED",
                            f"Solver does not support mode '{model.get('mode')}'. Supported: {sorted(allowed)}",
                        )
                    )

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
    allowed_outputs = _allowed_output_names(capabilities)

    # Check stage references to sets (bcs/loads).
    for si, stage in enumerate(stages):
        if not isinstance(stage, dict):
            issues.append(_issue("ERROR", "STAGE_TYPE", f"Stage[{si}] must be an object"))
            continue
        stage_id = stage.get("id", f"stage_{si+1}")

        if capabilities:
            ats = capabilities.get("analysis_types")
            if isinstance(ats, list) and ats:
                allowed = {str(x) for x in ats if isinstance(x, str)}
                at = str(stage.get("analysis_type", "static"))
                if allowed and at not in allowed:
                    issues.append(
                        _issue(
                            "ERROR",
                            "CAP_ANALYSIS_UNSUPPORTED",
                            f"{stage_id}: analysis_type '{at}' not supported by solver. Supported: {sorted(allowed)}",
                        )
                    )

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

        # Check output request names against capabilities (best-effort, WARN).
        if allowed_outputs:
            out_reqs = stage.get("output_requests", [])
            if isinstance(out_reqs, list):
                for oi, o in enumerate(out_reqs):
                    if not isinstance(o, dict):
                        continue
                    name = o.get("name")
                    if isinstance(name, str) and name and name not in allowed_outputs:
                        issues.append(
                            _issue(
                                "WARN",
                                "CAP_OUTPUT_UNSUPPORTED",
                                f"{stage_id}: output_requests[{oi}] name '{name}' not in solver capabilities",
                            )
                        )

    # Check assignments -> element sets
    assignments = request.get("assignments", [])
    if isinstance(assignments, list):
        for ai, a in enumerate(assignments):
            if not isinstance(a, dict):
                continue
            es = _as_set_name(a.get("element_set"))
            if es and es not in set_names:
                issues.append(_issue("ERROR", "ASSIGN_SET_MISSING", f"Assignment[{ai}] references missing set '{es}'"))

    # Check global output_requests names (best-effort, WARN).
    if allowed_outputs:
        out_reqs2 = request.get("output_requests", [])
        if isinstance(out_reqs2, list):
            for oi, o in enumerate(out_reqs2):
                if not isinstance(o, dict):
                    continue
                name = o.get("name")
                if isinstance(name, str) and name and name not in allowed_outputs:
                    issues.append(
                        _issue(
                            "WARN",
                            "CAP_OUTPUT_UNSUPPORTED",
                            f"request.output_requests[{oi}] name '{name}' not in solver capabilities",
                        )
                    )

    return issues


def summarize_issues(issues: Iterable[PrecheckIssue]) -> tuple[int, int, int]:
    e = sum(1 for i in issues if i.severity == "ERROR")
    w = sum(1 for i in issues if i.severity == "WARN")
    info = sum(1 for i in issues if i.severity == "INFO")
    return e, w, info
