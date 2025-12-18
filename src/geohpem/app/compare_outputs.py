from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from geohpem.contract.io import read_result_folder
from geohpem.viz.vtk_convert import available_steps_from_arrays, get_array_for, vector_magnitude


@dataclass(frozen=True, slots=True)
class FieldKey:
    location: str
    name: str


@dataclass(frozen=True, slots=True)
class FieldStats:
    min: float
    max: float
    mean: float
    l2: float
    linf: float


def _as_scalar(arr: Any) -> np.ndarray:
    a = np.asarray(arr)
    if a.ndim == 2:
        return vector_magnitude(a)
    return a.reshape(-1).astype(float, copy=False)


def common_fields(meta_a: dict[str, Any], meta_b: dict[str, Any]) -> list[FieldKey]:
    reg_a = [r for r in meta_a.get("registry", []) if isinstance(r, dict)]
    reg_b = [r for r in meta_b.get("registry", []) if isinstance(r, dict)]
    set_b = {(str(r.get("location", "")), str(r.get("name", ""))) for r in reg_b}
    keys: list[FieldKey] = []
    for r in reg_a:
        loc = str(r.get("location", ""))
        name = str(r.get("name", ""))
        if not loc or not name:
            continue
        if (loc, name) in set_b:
            keys.append(FieldKey(location=loc, name=name))
    # stable sort
    keys = sorted({(k.location, k.name) for k in keys})
    return [FieldKey(location=loc, name=name) for loc, name in keys]


def common_steps(arrays_a: dict[str, Any], arrays_b: dict[str, Any]) -> list[int]:
    sa = set(available_steps_from_arrays(arrays_a))
    sb = set(available_steps_from_arrays(arrays_b))
    return sorted(sa.intersection(sb))


def diff_stats_for(
    *,
    meta_a: dict[str, Any],
    arrays_a: dict[str, Any],
    meta_b: dict[str, Any],
    arrays_b: dict[str, Any],
    field: FieldKey,
    step: int,
) -> FieldStats | None:
    a = get_array_for(arrays=arrays_a, location=field.location, name=field.name, step=step)
    b = get_array_for(arrays=arrays_b, location=field.location, name=field.name, step=step)
    if a is None or b is None:
        return None
    sa = _as_scalar(a)
    sb = _as_scalar(b)
    if sa.shape != sb.shape:
        return None
    d = sa - sb
    if d.size == 0:
        return FieldStats(min=0.0, max=0.0, mean=0.0, l2=0.0, linf=0.0)
    return FieldStats(
        min=float(np.min(d)),
        max=float(np.max(d)),
        mean=float(np.mean(d)),
        l2=float(np.linalg.norm(d.ravel())),
        linf=float(np.max(np.abs(d))),
    )


def step_curve_for(
    *,
    arrays: dict[str, Any],
    field: FieldKey,
    steps: list[int],
) -> list[dict[str, float]]:
    """
    Returns a list of per-step scalar stats: min/max/mean.
    """
    out: list[dict[str, float]] = []
    for s in steps:
        a = get_array_for(arrays=arrays, location=field.location, name=field.name, step=s)
        if a is None:
            out.append({"min": float("nan"), "max": float("nan"), "mean": float("nan")})
            continue
        sc = _as_scalar(a)
        if sc.size == 0:
            out.append({"min": 0.0, "max": 0.0, "mean": 0.0})
            continue
        out.append({"min": float(np.min(sc)), "max": float(np.max(sc)), "mean": float(np.mean(sc))})
    return out


def load_outputs(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Accept either an out folder (containing result.json/result.npz) or a case folder (containing out/).
    """
    p = Path(path)
    if p.is_dir() and (p / "result.json").exists():
        return read_result_folder(p)
    if p.is_dir() and (p / "out").is_dir():
        return read_result_folder(p / "out")
    raise FileNotFoundError(f"Not an output folder or case folder: {p}")

