from __future__ import annotations

from typing import Any

import numpy as np

from geohpem.project.types import ProjectData


def new_empty_project(
    *,
    mode: str = "plane_strain",
    unit_system: dict[str, str] | None = None,
) -> ProjectData:
    if mode not in ("plane_strain", "axisymmetric"):
        raise ValueError("mode must be 'plane_strain' or 'axisymmetric'")

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "unit_system": unit_system or {"force": "kN", "length": "m", "time": "s", "pressure": "kPa"},
        "model": {"dimension": 2, "mode": mode, "gravity": [0.0, -9.81]},
        "materials": {},
        "assignments": [],
        "stages": [
            {
                "id": "stage_1",
                "analysis_type": "static",
                "num_steps": 1,
                "bcs": [],
                "loads": [],
                "output_requests": [],
            }
        ],
        "output_requests": [],
    }

    mesh = {
        "points": np.zeros((0, 2), dtype=float),
        "cells_tri3": np.zeros((0, 3), dtype=np.int32),
    }

    return ProjectData(request=request, mesh=mesh)


def new_sample_project(
    *,
    mode: str = "plane_strain",
    unit_system: dict[str, str] | None = None,
) -> ProjectData:
    if mode not in ("plane_strain", "axisymmetric"):
        raise ValueError("mode must be 'plane_strain' or 'axisymmetric'")

    points = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
        ],
        dtype=float,
    )
    cells_tri3 = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "unit_system": unit_system or {"force": "kN", "length": "m", "time": "s", "pressure": "kPa"},
        "model": {"dimension": 2, "mode": mode, "gravity": [0.0, -9.81]},
        "materials": {"soil_1": {"model_name": "placeholder", "parameters": {"note": "solver-owned"}}},
        "assignments": [{"element_set": "soil", "cell_type": "tri3", "material_id": "soil_1"}],
        "stages": [
            {
                "id": "stage_1",
                "analysis_type": "static",
                "num_steps": 5,
                "bcs": [{"field": "u", "type": "dirichlet", "set": "bottom", "value": [0.0, 0.0]}],
                "loads": [],
                "output_requests": [
                    {"name": "u", "location": "node", "every_n": 1},
                    {"name": "p", "location": "node", "every_n": 1},
                ],
            }
        ],
        "output_requests": [],
    }

    mesh = {
        "points": points,
        "cells_tri3": cells_tri3,
        "node_set__bottom": np.array([0, 1], dtype=np.int32),
        "edge_set__bottom": np.array([[0, 1]], dtype=np.int32),
        "elem_set__soil__tri3": np.array([0, 1], dtype=np.int32),
    }

    return ProjectData(request=request, mesh=mesh)

