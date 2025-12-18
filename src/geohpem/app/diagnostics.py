from __future__ import annotations

import json
import os
import platform
import sys
import time
import traceback
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DiagnosticsInfo:
    zip_path: Path


def _safe_read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        return data[:limit]
    except Exception:
        return ""


def _safe_read_bytes(path: Path, limit: int = 50_000_000) -> bytes:
    try:
        data = path.read_bytes()
        return data[:limit]
    except Exception:
        return b""


def build_diagnostics_zip(
    case_dir: Path,
    *,
    solver_selector: str,
    capabilities: dict[str, Any] | None = None,
    error: str | None = None,
    tb: str | None = None,
    logs: list[str] | None = None,
    include_out: bool = True,
) -> DiagnosticsInfo:
    """
    Create a self-contained diagnostics zip for sharing with solver/platform teams.
    """
    case_dir = Path(case_dir)
    diag_dir = case_dir / "_diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    zip_path = diag_dir / f"diag_{ts}.zip"

    meta: dict[str, Any] = {
        "time": ts,
        "solver_selector": solver_selector,
        "python": sys.version,
        "platform": {"system": platform.system(), "release": platform.release(), "version": platform.version()},
        "cwd": os.getcwd(),
    }
    if capabilities is not None:
        meta["capabilities"] = capabilities
    if error:
        meta["error"] = error
    if tb:
        meta["traceback"] = tb
    if logs:
        meta["logs"] = logs[-5000:]

    def add_file(z: zipfile.ZipFile, src: Path, arc: str) -> None:
        if not src.exists() or not src.is_file():
            return
        # Avoid huge accidental zips.
        size = src.stat().st_size
        if size > 200_000_000:  # 200MB
            return
        z.write(src, arcname=arc)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("diag/meta.json", json.dumps(meta, indent=2, ensure_ascii=False))

        # Inputs
        add_file(z, case_dir / "request.json", "case/request.json")
        add_file(z, case_dir / "mesh.npz", "case/mesh.npz")

        # Optional outputs (if present)
        if include_out:
            out_dir = case_dir / "out"
            if out_dir.exists() and out_dir.is_dir():
                add_file(z, out_dir / "result.json", "case/out/result.json")
                add_file(z, out_dir / "result.npz", "case/out/result.npz")

        # Convenience: include readable copies of request/result (limited)
        req_txt = _safe_read_text(case_dir / "request.json")
        if req_txt:
            z.writestr("diag/request_preview.json", req_txt)
        res_txt = _safe_read_text(case_dir / "out" / "result.json")
        if res_txt:
            z.writestr("diag/result_preview.json", res_txt)

        # Attach a short package list (best-effort)
        try:
            import importlib.metadata as md

            pkgs = []
            for dist in md.distributions():
                try:
                    name = dist.metadata["Name"]
                    ver = dist.version
                    if name:
                        pkgs.append(f"{name}=={ver}")
                except Exception:
                    continue
            pkgs = sorted(set(pkgs))
            z.writestr("diag/pip_freeze.txt", "\n".join(pkgs)[:2_000_000])
        except Exception:
            pass

    return DiagnosticsInfo(zip_path=zip_path)

