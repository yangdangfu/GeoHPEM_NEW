from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from geohpem import __version__
from geohpem.contract.errors import ContractError
from geohpem.contract.validate import validate_request_basic
from geohpem.project.migrations import migrate_manifest, migrate_request, migrate_result
from geohpem.project.normalize import ensure_request_ids
from geohpem.project.types import ProjectData


DEFAULT_EXT = ".geohpem"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_project_path(path: str | Path) -> Path:
    p = Path(path)
    if p.suffix.lower() != DEFAULT_EXT:
        p = p.with_suffix(DEFAULT_EXT)
    return p


def make_manifest(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "created_at": _utc_now_iso(),
        "app": {"name": "geohpem", "version": __version__},
        "contract": {"request": "0.1", "result": "0.1"},
    }
    if extra:
        manifest.update(extra)
    return manifest


def save_geohpem(path: str | Path, project: ProjectData) -> Path:
    out_path = normalize_project_path(path)
    ensure_request_ids(project.request, project.mesh)
    validate_request_basic(project.request)

    manifest = project.manifest or make_manifest()
    if manifest.get("schema_version") != "0.1":
        raise ContractError("manifest.schema_version must be '0.1'")

    mesh_buf = io.BytesIO()
    np.savez_compressed(mesh_buf, **project.mesh)
    mesh_bytes = mesh_buf.getvalue()

    result_json_bytes: bytes | None = None
    result_npz_bytes: bytes | None = None
    if project.result_meta is not None and project.result_arrays is not None:
        result_json_bytes = json.dumps(project.result_meta, indent=2, ensure_ascii=False).encode("utf-8")
        result_buf = io.BytesIO()
        np.savez_compressed(result_buf, **project.result_arrays)
        result_npz_bytes = result_buf.getvalue()

    ui_state_bytes: bytes | None = None
    if project.ui_state is not None:
        ui_state_bytes = json.dumps(project.ui_state, indent=2, ensure_ascii=False).encode("utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))
        zf.writestr("request.json", json.dumps(project.request, indent=2, ensure_ascii=False).encode("utf-8"))
        zf.writestr("mesh.npz", mesh_bytes)

        if ui_state_bytes is not None:
            zf.writestr("ui_state.json", ui_state_bytes)

        if result_json_bytes is not None and result_npz_bytes is not None:
            zf.writestr("out/result.json", result_json_bytes)
            zf.writestr("out/result.npz", result_npz_bytes)

    return out_path


def load_geohpem(path: str | Path) -> ProjectData:
    in_path = Path(path)
    if not in_path.exists():
        raise FileNotFoundError(in_path)

    with zipfile.ZipFile(in_path, "r") as zf:
        manifest = migrate_manifest(json.loads(zf.read("manifest.json").decode("utf-8")))
        request = migrate_request(json.loads(zf.read("request.json").decode("utf-8")))
        validate_request_basic(request)

        mesh_npz_bytes = zf.read("mesh.npz")
        mesh_npz = np.load(io.BytesIO(mesh_npz_bytes), allow_pickle=False)
        mesh = {k: mesh_npz[k] for k in mesh_npz.files}
        ensure_request_ids(request, mesh)

        result_meta = None
        result_arrays = None
        ui_state: dict[str, Any] | None = None
        try:
            ui_state = json.loads(zf.read("ui_state.json").decode("utf-8"))
            if not isinstance(ui_state, dict):
                ui_state = None
        except KeyError:
            ui_state = None
        except Exception:
            ui_state = None
        try:
            result_json_bytes = zf.read("out/result.json")
            result_npz_bytes = zf.read("out/result.npz")
        except KeyError:
            result_json_bytes = None
            result_npz_bytes = None

        if result_json_bytes and result_npz_bytes:
            result_meta = migrate_result(json.loads(result_json_bytes.decode("utf-8")))
            result_npz = np.load(io.BytesIO(result_npz_bytes), allow_pickle=False)
            result_arrays = {k: result_npz[k] for k in result_npz.files}

    return ProjectData(
        request=request,
        mesh=mesh,
        result_meta=result_meta,
        result_arrays=result_arrays,
        manifest=manifest,
        ui_state=ui_state,
    )
