from __future__ import annotations

from typing import Any


def _try_import_kratos():
    try:
        import KratosMultiphysics as km  # type: ignore
    except Exception as exc:
        raise ImportError(
            "KratosMultiphysics is not installed. Install Kratos or add it to PYTHONPATH."
        ) from exc
    return km


class KratosSolver:
    """
    Skeleton adapter for Kratos Multiphysics backend.
    """

    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "kratos",
            "contract": {"min": "0.2", "max": "0.2"},
            "modes": ["plane_strain", "plane_stress", "axisymmetric"],
            "analysis_types": ["static", "dynamic", "seepage_steady", "seepage_transient", "consolidation_u_p"],
            "materials": ["linear_elastic", "mohr_coulomb", "hardening_soil", "darcy"],
            "bcs": ["displacement", "p"],
            "loads": ["gravity", "traction", "flux"],
            "fields": ["u", "p", "stress", "strain", "vm", "plastic_strain"],
            "results": ["u", "p", "stress", "strain", "vm", "plastic_strain"],
            "backend": {"name": "kratos", "adapter": "skeleton"},
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _try_import_kratos()
        raise NotImplementedError(
            "Kratos adapter skeleton is not implemented yet. See docs/KRATOS_BACKEND_MAPPING.md."
        )


def get_solver() -> KratosSolver:
    return KratosSolver()
