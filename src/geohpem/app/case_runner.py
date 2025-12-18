from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from geohpem.app.diagnostics import build_diagnostics_zip
from geohpem.app.errors import CancelledError
from geohpem.app.run_case import run_case
from geohpem.contract.io import read_result_folder


@dataclass(frozen=True, slots=True)
class CaseRunRecord:
    case_dir: Path
    status: str  # success|failed|canceled|skipped
    solver_selector: str
    elapsed_s: float
    rss_start_mb: float | None
    rss_end_mb: float | None
    out_dir: Path | None
    error: str | None
    diagnostics_zip: Path | None
    compare: dict[str, Any] | None


def discover_case_folders(root: Path) -> list[Path]:
    """
    Find immediate subfolders under root that look like case folders.
    """
    root = Path(root)
    if not root.exists():
        return []
    if (root / "request.json").exists() and (root / "mesh.npz").exists():
        return [root]
    out: list[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if (p / "request.json").exists() and (p / "mesh.npz").exists():
            out.append(p)
    return out


def _compare_out_dirs(out_a: Path, out_b: Path) -> dict[str, Any]:
    """
    Minimal numeric comparison (final-step arrays only).
    """
    meta_a, arr_a = read_result_folder(out_a)
    meta_b, arr_b = read_result_folder(out_b)
    reg_a = [r for r in meta_a.get("registry", []) if isinstance(r, dict)]
    reg_b = [r for r in meta_b.get("registry", []) if isinstance(r, dict)]
    idx_b = {(r.get("location"), r.get("name")): r for r in reg_b}

    # infer last step id from arrays keys
    def last_step(arrs: dict[str, Any]) -> int | None:
        steps: list[int] = []
        for k in arrs.keys():
            if "step" in k:
                try:
                    s = int(k.split("step", 1)[1])
                    steps.append(s)
                except Exception:
                    continue
        return max(steps) if steps else None

    sa = last_step(arr_a)
    sb = last_step(arr_b)
    step = sa if (sa is not None and sa == sb) else (sa or sb)

    import numpy as np

    diffs: list[dict[str, Any]] = []
    for r in reg_a:
        key = (r.get("location"), r.get("name"))
        if key not in idx_b:
            continue
        patt_a = r.get("npz_pattern")
        patt_b = idx_b[key].get("npz_pattern")
        if not isinstance(patt_a, str) or not isinstance(patt_b, str) or step is None:
            continue
        ka = patt_a.format(step=step)
        kb = patt_b.format(step=step)
        if ka not in arr_a or kb not in arr_b:
            continue
        xa = np.asarray(arr_a[ka]).astype(float, copy=False)
        xb = np.asarray(arr_b[kb]).astype(float, copy=False)
        if xa.shape != xb.shape:
            diffs.append({"location": key[0], "name": key[1], "shape_a": list(xa.shape), "shape_b": list(xb.shape), "status": "shape_mismatch"})
            continue
        d = xa - xb
        diffs.append(
            {
                "location": key[0],
                "name": key[1],
                "step": step,
                "l2": float(np.linalg.norm(d.ravel())),
                "linf": float(np.max(np.abs(d))) if d.size else 0.0,
                "status": "ok",
            }
        )
    return {"step": step, "diffs": diffs}


def run_cases(
    case_dirs: Iterable[Path],
    *,
    solver_selector: str,
    baseline_root: Path | None = None,
    on_progress: Callable[[int, int, Path, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[CaseRunRecord]:
    """
    Run many case folders sequentially and collect a summary.

    baseline_root: if provided, compare each case's out/ against baseline_root/<case_name>/out
    """
    dirs = [Path(p) for p in case_dirs]
    total = max(len(dirs), 1)
    records: list[CaseRunRecord] = []

    for i, case_dir in enumerate(dirs, start=1):
        if should_cancel and should_cancel():
            break
        t0 = time.perf_counter()
        rss0: float | None = None
        rss1: float | None = None
        out_dir: Path | None = None
        diag: Path | None = None
        cmp: dict[str, Any] | None = None
        err: str | None = None
        status = "success"
        try:
            try:
                import psutil  # type: ignore

                rss0 = float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
            except Exception:
                rss0 = None
            if on_progress:
                on_progress(i, total, case_dir, "running")
            callbacks = {"should_cancel": (should_cancel or (lambda: False))}
            out_dir = run_case(str(case_dir), solver_selector=solver_selector, callbacks=callbacks)
            if baseline_root is not None:
                base_out = Path(baseline_root) / case_dir.name / "out"
                if base_out.exists():
                    cmp = _compare_out_dirs(out_dir, base_out)
            try:
                import psutil  # type: ignore

                rss1 = float(psutil.Process().memory_info().rss) / (1024.0 * 1024.0)
            except Exception:
                rss1 = None
        except CancelledError as exc:
            status = "canceled"
            err = str(exc)
            try:
                diag = build_diagnostics_zip(case_dir, solver_selector=solver_selector, error=err, tb=None, logs=None).zip_path
            except Exception:
                diag = None
        except Exception as exc:
            status = "failed"
            err = str(exc)
            try:
                diag = build_diagnostics_zip(case_dir, solver_selector=solver_selector, error=err, tb=None, logs=None).zip_path
            except Exception:
                diag = None
        elapsed = float(time.perf_counter() - t0)
        records.append(
            CaseRunRecord(
                case_dir=case_dir,
                status=status,
                solver_selector=solver_selector,
                elapsed_s=elapsed,
                rss_start_mb=rss0,
                rss_end_mb=rss1,
                out_dir=out_dir,
                error=err,
                diagnostics_zip=diag,
                compare=cmp,
            )
        )
        if on_progress:
            on_progress(i, total, case_dir, status)

    return records


def write_case_run_report(records: list[CaseRunRecord], out_path: Path) -> Path:
    out_path = Path(out_path)
    payload = []
    for r in records:
        payload.append(
            {
                "case_dir": str(r.case_dir),
                "status": r.status,
                "solver_selector": r.solver_selector,
                "elapsed_s": r.elapsed_s,
                "rss_start_mb": r.rss_start_mb,
                "rss_end_mb": r.rss_end_mb,
                "out_dir": str(r.out_dir) if r.out_dir else None,
                "error": r.error,
                "diagnostics_zip": str(r.diagnostics_zip) if r.diagnostics_zip else None,
                "compare": r.compare,
            }
        )
    out_path.write_text(json.dumps({"records": payload}, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
