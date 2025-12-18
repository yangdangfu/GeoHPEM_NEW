from __future__ import annotations

from typing import Any

from geohpem.app.precheck import PrecheckIssue, precheck_request_mesh
from geohpem.contract.errors import ContractError
from geohpem.contract.validate import validate_request_basic, validate_request_jsonschema_if_available


def validate_inputs(
    request: dict[str, Any],
    mesh: dict[str, Any],
    *,
    capabilities: dict[str, Any] | None = None,
) -> list[PrecheckIssue]:
    """
    Validate inputs for GUI and batch tooling.

    This returns a list of PrecheckIssue (ERROR/WARN/INFO) that can be rendered in dialogs.
    It is best-effort and should never raise.
    """
    issues: list[PrecheckIssue] = []

    try:
        validate_request_basic(request)
    except ContractError as exc:
        issues.append(PrecheckIssue(severity="ERROR", code="CONTRACT", message=str(exc)))
    except Exception as exc:
        issues.append(PrecheckIssue(severity="ERROR", code="CONTRACT", message=f"Contract validation failed: {exc}"))

    try:
        validate_request_jsonschema_if_available(request)
    except Exception as exc:
        issues.append(PrecheckIssue(severity="ERROR", code="SCHEMA", message=f"Schema validation failed: {exc}"))

    try:
        issues.extend(precheck_request_mesh(request, mesh, capabilities=capabilities))
    except Exception as exc:
        issues.append(PrecheckIssue(severity="ERROR", code="PRECHECK", message=f"Pre-check failed: {exc}"))

    # De-duplicate while preserving order.
    seen: set[tuple[str, str, str]] = set()
    deduped: list[PrecheckIssue] = []
    for it in issues:
        key = (it.severity, it.code, it.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped


def has_errors(issues: list[PrecheckIssue]) -> bool:
    return any(i.severity == "ERROR" for i in issues)

