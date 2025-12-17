from __future__ import annotations

from typing import Any


def migrate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate manifest to the latest supported version.
    For now, only v0.1 is supported.
    """
    ver = manifest.get("schema_version", "0.1")
    if ver == "0.1":
        return manifest
    raise ValueError(f"Unsupported manifest schema_version: {ver!r}")


def migrate_request(request: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate request.json to the latest supported Contract version.
    For now, only v0.1 is supported.
    """
    ver = request.get("schema_version", "0.1")
    if ver == "0.1":
        return request
    raise ValueError(f"Unsupported request schema_version: {ver!r}")


def migrate_result(result_meta: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate result.json (meta) to the latest supported Contract version.
    For now, only v0.1 is supported.
    """
    ver = result_meta.get("schema_version", "0.1")
    if ver == "0.1":
        return result_meta
    raise ValueError(f"Unsupported result schema_version: {ver!r}")

