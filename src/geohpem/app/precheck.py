from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class PrecheckIssue:
    severity: str  # "ERROR" | "WARN" | "INFO"
    code: str
    message: str
    jump: dict[str, Any] | None = None


def _issue(
    severity: str, code: str, message: str, *, jump: dict[str, Any] | None = None
) -> PrecheckIssue:
    return PrecheckIssue(severity=severity, code=code, message=message, jump=jump)


def _as_set_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _mesh_has_cells(mesh: dict[str, Any]) -> bool:
    return any(
        k.startswith("cells_") and getattr(mesh.get(k), "shape", None) is not None
        for k in mesh.keys()
    )


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


def _collect_element_set_names(mesh: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for k in mesh.keys():
        if k.startswith("elem_set__"):
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

    schema_version = str(request.get("schema_version", ""))
    if schema_version not in ("0.1", "0.2"):
        issues.append(
            _issue(
                "ERROR",
                "REQ_SCHEMA",
                "request.schema_version must be '0.1' or '0.2'",
                jump={"type": "project"},
            )
        )

    if capabilities:
        contract = capabilities.get("contract")
        if isinstance(contract, dict):
            vmin = contract.get("min")
            vmax = contract.get("max")
            if isinstance(vmin, str) or isinstance(vmax, str):
                if not _version_in_range(
                    str(request.get("schema_version", "")),
                    str(vmin) if isinstance(vmin, str) else None,
                    str(vmax) if isinstance(vmax, str) else None,
                ):
                    issues.append(
                        _issue(
                            "ERROR",
                            "CAP_CONTRACT",
                            f"Solver contract range {vmin}-{vmax} does not accept request.schema_version={request.get('schema_version')}",
                            jump={"type": "project"},
                        )
                    )

    model = request.get("model")
    if not isinstance(model, dict):
        issues.append(
            _issue(
                "ERROR",
                "REQ_MODEL",
                "request.model must be an object",
                jump={"type": "model"},
            )
        )
    else:
        if model.get("dimension") != 2:
            issues.append(
                _issue(
                    "ERROR",
                    "REQ_DIM",
                    "request.model.dimension must be 2",
                    jump={"type": "model"},
                )
            )
        allowed_modes = (
            ("plane_strain", "axisymmetric")
            if schema_version == "0.1"
            else ("plane_strain", "plane_stress", "axisymmetric")
        )
        if model.get("mode") not in allowed_modes:
            issues.append(
                _issue(
                    "ERROR",
                    "REQ_MODE",
                    f"request.model.mode must be one of {list(allowed_modes)}",
                    jump={"type": "model"},
                )
            )
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
                            jump={"type": "model"},
                        )
                    )

    stages = request.get("stages")
    if not isinstance(stages, list) or not stages:
        issues.append(
            _issue(
                "ERROR",
                "REQ_STAGES",
                "request.stages must be a non-empty list",
                jump={"type": "stages"},
            )
        )
        stages = []

    if "points" not in mesh:
        issues.append(
            _issue(
                "ERROR",
                "MESH_POINTS",
                "mesh.npz must contain 'points'",
                jump={"type": "mesh"},
            )
        )
    else:
        pts = mesh.get("points")
        try:
            npts = int(getattr(pts, "shape")[0])
        except Exception:
            npts = -1
        if npts == 0:
            issues.append(
                _issue(
                    "WARN",
                    "MESH_EMPTY",
                    "Mesh has 0 points (empty mesh).",
                    jump={"type": "mesh"},
                )
            )

    if not _mesh_has_cells(mesh):
        issues.append(
            _issue(
                "ERROR",
                "MESH_CELLS",
                "mesh.npz must contain at least one 'cells_*' array",
                jump={"type": "mesh"},
            )
        )

    set_names = _collect_set_names(mesh)
    elem_set_names = _collect_element_set_names(mesh)
    allowed_outputs = _allowed_output_names(capabilities)

    if _mesh_has_cells(mesh) and not elem_set_names:
        issues.append(
            _issue(
                "ERROR",
                "ELEM_SET_MISSING",
                "No element sets found. Create element sets before assigning materials.",
                jump={"type": "sets"},
            )
        )

    # Check stage references to sets (bcs/loads).
    for si, stage in enumerate(stages):
        if not isinstance(stage, dict):
            issues.append(
                _issue(
                    "ERROR",
                    "STAGE_TYPE",
                    f"Stage[{si}] must be an object",
                    jump={"type": "stages"},
                )
            )
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
                            jump={
                                "type": "stage",
                                "index": si,
                                "uid": stage.get("uid", ""),
                            },
                        )
                    )

        if (
            not stage.get("bcs")
            and not stage.get("loads")
            and not stage.get("output_requests")
        ):
            issues.append(
                _issue(
                    "WARN",
                    "STAGE_EMPTY",
                    f"{stage_id}: stage has no BCs/Loads/Outputs configured",
                    jump={"type": "stage", "index": si, "uid": stage.get("uid", "")},
                )
            )

        for bc in stage.get("bcs", []) if isinstance(stage.get("bcs"), list) else []:
            if not isinstance(bc, dict):
                continue
            set_name = _as_set_name(bc.get("set"))
            if set_name and set_name not in set_names:
                issues.append(
                    _issue(
                        "ERROR",
                        "BC_SET_MISSING",
                        f"{stage_id}: BC references missing set '{set_name}'",
                        jump={"type": "sets"},
                    )
                )

        for load in (
            stage.get("loads", []) if isinstance(stage.get("loads"), list) else []
        ):
            if not isinstance(load, dict):
                continue
            set_name = _as_set_name(load.get("set"))
            if set_name and set_name not in set_names:
                issues.append(
                    _issue(
                        "ERROR",
                        "LOAD_SET_MISSING",
                        f"{stage_id}: Load references missing set '{set_name}'",
                        jump={"type": "sets"},
                    )
                )

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
                                jump={
                                    "type": "stage",
                                    "index": si,
                                    "uid": stage.get("uid", ""),
                                },
                            )
                        )

    # Check assignments -> element sets
    assignments = request.get("assignments", [])
    materials = request.get("materials", {})
    if _mesh_has_cells(mesh) and elem_set_names and not assignments:
        issues.append(
            _issue(
                "ERROR",
                "ASSIGN_EMPTY",
                "No assignments found. Map element sets to materials.",
                jump={"type": "assignments"},
            )
        )
    if isinstance(materials, dict) and not materials and assignments:
        issues.append(
            _issue(
                "ERROR",
                "MATERIALS_EMPTY",
                "Assignments exist but no materials are defined.",
                jump={"type": "materials"},
            )
        )
    if isinstance(assignments, list):
        for ai, a in enumerate(assignments):
            if not isinstance(a, dict):
                continue
            es = _as_set_name(a.get("element_set"))
            if es and es not in elem_set_names and elem_set_names:
                issues.append(
                    _issue(
                        "ERROR",
                        "ASSIGN_SET_MISSING",
                        f"Assignment[{ai}] references missing set '{es}'",
                        jump={"type": "assignments"},
                    )
                )
            mid = _as_set_name(a.get("material_id"))
            if (
                mid
                and isinstance(materials, dict)
                and materials
                and mid not in materials
            ):
                issues.append(
                    _issue(
                        "ERROR",
                        "ASSIGN_MATERIAL_MISSING",
                        f"Assignment[{ai}] references missing material '{mid}'",
                        jump={"type": "materials"},
                    )
                )

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
                            jump={"type": "global_output_requests"},
                        )
                    )

    return issues


def summarize_issues(issues: Iterable[PrecheckIssue]) -> tuple[int, int, int]:
    e = sum(1 for i in issues if i.severity == "ERROR")
    w = sum(1 for i in issues if i.severity == "WARN")
    info = sum(1 for i in issues if i.severity == "INFO")
    return e, w, info
