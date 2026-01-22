from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

_UNIT_TO_SI: dict[str, tuple[str, float]] = {
    # length
    "m": ("length", 1.0),
    "mm": ("length", 1e-3),
    "cm": ("length", 1e-2),
    "km": ("length", 1e3),
    # force
    "N": ("force", 1.0),
    "kN": ("force", 1e3),
    "MN": ("force", 1e6),
    # time
    "s": ("time", 1.0),
    "min": ("time", 60.0),
    "h": ("time", 3600.0),
    # pressure
    "Pa": ("pressure", 1.0),
    "kPa": ("pressure", 1e3),
    "MPa": ("pressure", 1e6),
    "GPa": ("pressure", 1e9),
}


def _kind_of(unit: str) -> str | None:
    rec = _UNIT_TO_SI.get(unit)
    return rec[0] if rec else None


def conversion_factor(unit_from: str, unit_to: str) -> float:
    """
    Multiply a value in `unit_from` by this factor to convert into `unit_to`.
    """
    if unit_from == unit_to:
        return 1.0
    a = _UNIT_TO_SI.get(unit_from)
    b = _UNIT_TO_SI.get(unit_to)
    if not a or not b:
        raise KeyError(f"Unknown unit(s): {unit_from!r} -> {unit_to!r}")
    if a[0] != b[0]:
        raise ValueError(
            f"Incompatible units: {unit_from!r} ({a[0]}) -> {unit_to!r} ({b[0]})"
        )
    # value_to = value_from * (from_to_SI / to_to_SI)
    return float(a[1]) / float(b[1])


def convert_value(value: float, unit_from: str, unit_to: str) -> float:
    return float(value) * conversion_factor(unit_from, unit_to)


def convert_array(arr: Any, unit_from: str, unit_to: str) -> np.ndarray:
    a = np.asarray(arr)
    factor = conversion_factor(unit_from, unit_to)
    if factor == 1.0:
        return a
    return a.astype(float, copy=False) * factor


def request_unit_system(request: dict[str, Any]) -> dict[str, str]:
    """
    Returns the project's declared unit system (engineering units).

    v0.1 policy: treat request.unit_system as the unit system of the stored numbers.
    """
    raw = request.get("unit_system")
    if isinstance(raw, dict):
        out: dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, str) and v:
                out[k] = v
        return out
    return {}


@dataclass(frozen=True, slots=True)
class UnitContext:
    """
    Unit conversion context:
    - base: units used by stored numbers (typically request.unit_system)
    - display: user-selected display units (subset override); fallback to base
    """

    base: dict[str, str]
    display: dict[str, str]

    def base_unit(self, kind: str, default: str | None = None) -> str | None:
        u = self.base.get(kind)
        return u or default

    def display_unit(self, kind: str, default: str | None = None) -> str | None:
        u = self.display.get(kind) or self.base.get(kind)
        return u or default

    def factor_base_to_display(self, kind: str) -> float:
        ub = self.base_unit(kind)
        ud = self.display_unit(kind)
        if not ub or not ud:
            return 1.0
        return conversion_factor(ub, ud)

    def format_value(
        self, kind: str, value: float | None, *, precision: int = 6
    ) -> str:
        if value is None:
            return "None"
        ub = self.base_unit(kind)
        ud = self.display_unit(kind)
        if not ub or not ud:
            return f"{value:.{precision}g}"
        v = convert_value(float(value), ub, ud)
        return f"{v:.{precision}g} {ud}"

    def convert_base_to_display(self, kind: str, value: float) -> float:
        ub = self.base_unit(kind)
        ud = self.display_unit(kind)
        if not ub or not ud:
            return float(value)
        return convert_value(float(value), ub, ud)

    def convert_display_to_base(self, kind: str, value: float) -> float:
        ub = self.base_unit(kind)
        ud = self.display_unit(kind)
        if not ub or not ud:
            return float(value)
        return convert_value(float(value), ud, ub)


def available_units_for_kind(kind: str) -> list[str]:
    items: list[str] = []
    for u, (k, _) in _UNIT_TO_SI.items():
        if k == kind:
            items.append(u)
    # keep a stable, intuitive order
    preferred: list[str] = []
    for u in (
        "mm",
        "cm",
        "m",
        "km",
        "Pa",
        "kPa",
        "MPa",
        "GPa",
        "N",
        "kN",
        "MN",
        "s",
        "min",
        "h",
    ):
        if u in items:
            preferred.append(u)
    rest = sorted([u for u in items if u not in preferred])
    return preferred + rest


def infer_kind_from_unit(unit: str) -> str | None:
    return _kind_of(unit)


def normalize_unit_system(unit_system: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kind, unit in unit_system.items():
        if not isinstance(kind, str) or not isinstance(unit, str) or not unit:
            continue
        if unit in _UNIT_TO_SI:
            out[kind] = unit
    return out


def merge_display_units(
    base: dict[str, str],
    overrides: dict[str, str] | None,
    *,
    allowed_kinds: Iterable[str] = ("length", "pressure", "force", "time"),
) -> dict[str, str]:
    """
    Returns a cleaned display-unit dict. Unknown kinds/units are ignored.
    """
    allow = set(allowed_kinds)
    out: dict[str, str] = {}
    if overrides:
        for k, u in overrides.items():
            if k not in allow:
                continue
            if not isinstance(u, str) or not u:
                continue
            # allow "project" sentinel to mean fallback to base
            if u == "project":
                continue
            if u in _UNIT_TO_SI and _kind_of(u) == k:
                out[k] = u
    # If base has unknown unit, display override must still be compatible; we keep out only.
    return out
