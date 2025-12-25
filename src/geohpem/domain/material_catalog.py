from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MaterialModel:
    name: str
    label: str
    behavior: str
    defaults: dict[str, Any]
    description: str = ""


_MODELS: list[MaterialModel] = [
    MaterialModel(
        name="linear_elastic",
        label="Linear Elastic",
        behavior="elastic",
        defaults={"E": 3.0e7, "nu": 0.3, "rho": 1800.0},
        description="Small-strain linear elasticity.",
    ),
    MaterialModel(
        name="mohr_coulomb",
        label="Mohr-Coulomb",
        behavior="plastic",
        defaults={
            "elastic": {"E": 3.0e7, "nu": 0.3, "rho": 1800.0},
            "strength": {"phi": 30.0, "c": 5.0e3, "psi": 0.0},
            "tension_cutoff": {"enabled": False, "ft": 0.0},
        },
        description="Classic elasto-plastic soil model.",
    ),
    MaterialModel(
        name="drucker_prager",
        label="Drucker-Prager",
        behavior="plastic",
        defaults={
            "elastic": {"E": 3.0e7, "nu": 0.3, "rho": 1800.0},
            "plastic": {"alpha": 0.1, "k": 1.0e5},
        },
        description="Smooth cone yield surface (pressure-dependent).",
    ),
    MaterialModel(
        name="cam_clay",
        label="Modified Cam-Clay",
        behavior="plastic",
        defaults={
            "elastic": {"kappa": 0.02, "lambda": 0.1, "nu": 0.3},
            "critical": {"M": 1.2},
            "state": {"e0": 0.8, "p0": 1.0e5},
        },
        description="Critical state model for clays.",
    ),
    MaterialModel(
        name="biot_poroelastic",
        label="Biot Poroelastic",
        behavior="poroelastic",
        defaults={
            "solid": {"E": 3.0e7, "nu": 0.3, "rho": 1800.0},
            "fluid": {"rho": 1000.0, "mu": 1.0e-3},
            "permeability": {"kx": 1.0e-6, "ky": 1.0e-6},
            "porosity": 0.35,
            "biot": {"alpha": 0.8, "M": 1.0e8},
        },
        description="Coupled solid-fluid response (u-p).",
    ),
    MaterialModel(
        name="darcy",
        label="Darcy Flow",
        behavior="seepage",
        defaults={
            "permeability": {"kx": 1.0e-6, "ky": 1.0e-6},
            "fluid": {"rho": 1000.0, "mu": 1.0e-3},
        },
        description="Steady/Transient seepage model.",
    ),
]


_BEHAVIORS: dict[str, str] = {
    "elastic": "Elastic",
    "plastic": "Elasto-plastic",
    "poroelastic": "Poroelastic",
    "seepage": "Seepage",
    "custom": "Custom/Other",
}


def behavior_options() -> list[tuple[str, str]]:
    return list(_BEHAVIORS.items())


def models_for_behavior(behavior: str) -> list[MaterialModel]:
    if behavior == "custom":
        return []
    return [m for m in _MODELS if m.behavior == behavior]


def all_models() -> list[MaterialModel]:
    return list(_MODELS)


def behavior_for_model(model_name: str) -> str | None:
    for m in _MODELS:
        if m.name == model_name:
            return m.behavior
    return None


def model_by_name(model_name: str) -> MaterialModel | None:
    for m in _MODELS:
        if m.name == model_name:
            return m
    return None


def model_defaults(model_name: str) -> dict[str, Any] | None:
    m = model_by_name(model_name)
    return dict(m.defaults) if m is not None else None
