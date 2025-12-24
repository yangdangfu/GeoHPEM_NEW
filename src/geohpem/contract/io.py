from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from geohpem.contract.errors import ContractError
from geohpem.contract.validate import validate_request_basic


def read_case_folder(case_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    request_path = case_dir / "request.json"
    mesh_path = case_dir / "mesh.npz"
    if not request_path.exists():
        raise FileNotFoundError(request_path)
    if not mesh_path.exists():
        raise FileNotFoundError(mesh_path)

    # Accept UTF-8 with BOM (common on Windows editors).
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    validate_request_basic(request)

    mesh_npz = np.load(mesh_path, allow_pickle=False)
    mesh = {k: mesh_npz[k] for k in mesh_npz.files}
    return request, mesh


def write_case_folder(case_dir: Path, request: dict[str, Any], mesh: dict[str, Any]) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    validate_request_basic(request)
    (case_dir / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    np.savez_compressed(case_dir / "mesh.npz", **mesh)


def write_result_folder(out_dir: Path, result_meta: dict[str, Any], result_arrays: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(
        json.dumps(result_meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    np.savez_compressed(out_dir / "result.npz", **result_arrays)


def read_result_folder(out_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    meta_path = out_dir / "result.json"
    arrays_path = out_dir / "result.npz"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    if not arrays_path.exists():
        raise FileNotFoundError(arrays_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    arrays_npz = np.load(arrays_path, allow_pickle=False)
    arrays = {k: arrays_npz[k] for k in arrays_npz.files}
    return meta, arrays


def safe_npz_key(name: str) -> str:
    if not name or any(ch.isspace() for ch in name):
        raise ContractError(f"Invalid npz key: {name!r}")
    return name
