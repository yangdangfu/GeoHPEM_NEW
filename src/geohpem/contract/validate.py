from __future__ import annotations

from typing import Any

from geohpem.contract.errors import ContractError


def validate_request_basic(request: dict[str, Any]) -> None:
    schema_version = request.get("schema_version")
    if schema_version not in ("0.1", "0.2"):
        raise ContractError("request.schema_version must be '0.1' or '0.2'")

    model = request.get("model")
    if not isinstance(model, dict):
        raise ContractError("request.model must be an object")
    if model.get("dimension") != 2:
        raise ContractError("request.model.dimension must be 2")
    if schema_version == "0.1":
        if model.get("mode") not in ("plane_strain", "axisymmetric"):
            raise ContractError("request.model.mode must be 'plane_strain' or 'axisymmetric'")
    else:
        if model.get("mode") not in ("plane_strain", "plane_stress", "axisymmetric"):
            raise ContractError("request.model.mode must be 'plane_strain' or 'plane_stress' or 'axisymmetric'")

    stages = request.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ContractError("request.stages must be a non-empty list")


def validate_request_jsonschema_if_available(request: dict[str, Any]) -> None:
    """
    Optional validation using jsonschema (if installed).
    This is intended for developer tooling and CI, not for hard runtime dependency.
    """
    try:
        import jsonschema  # type: ignore
    except Exception:
        return

    from importlib.resources import files

    schema_text = (files("geohpem.contract.schemas") / "request.schema.json").read_text(encoding="utf-8")
    schema = __import__("json").loads(schema_text)
    jsonschema.validate(instance=request, schema=schema)
