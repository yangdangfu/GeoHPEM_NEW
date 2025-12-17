from __future__ import annotations

from typing import Any

from geohpem.contract.errors import ContractError


def validate_request_basic(request: dict[str, Any]) -> None:
    if request.get("schema_version") != "0.1":
        raise ContractError("request.schema_version must be '0.1'")

    model = request.get("model")
    if not isinstance(model, dict):
        raise ContractError("request.model must be an object")
    if model.get("dimension") != 2:
        raise ContractError("request.model.dimension must be 2")
    if model.get("mode") not in ("plane_strain", "axisymmetric"):
        raise ContractError("request.model.mode must be 'plane_strain' or 'axisymmetric'")

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

