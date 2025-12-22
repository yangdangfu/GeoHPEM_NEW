from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from geohpem.geometry.polygon2d import Polygon2D
from geohpem.mesh.convert import ImportReport, meshio_to_contract


@dataclass(frozen=True, slots=True)
class PygmshConfig:
    mesh_size: float = 0.1


def _sanitize_set_name(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return "domain"
    out: list[str] = []
    for ch in s:
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s2 = "".join(out).strip("_")
    return s2 or "domain"


def generate_from_polygon(poly: Polygon2D, config: PygmshConfig | None = None) -> tuple[dict[str, Any], ImportReport]:
    """
    Generate a 2D triangular mesh from a polygon using pygmsh/gmsh.

    - Edge physical groups are created from poly.edge_groups (or default edge_i).
    - Surface physical group is created from poly.region_name.
    """
    cfg = config or PygmshConfig()
    poly.validate()

    try:
        import pygmsh  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pygmsh is required: install dependencies (e.g. conda env geohpem)") from exc

    points = [(float(x), float(y), 0.0) for x, y in poly.vertices]
    edge_groups = poly.normalized_edge_groups()

    with pygmsh.geo.Geometry() as geom:
        polygon = geom.add_polygon(points, mesh_size=cfg.mesh_size)

        # Physical groups
        # - boundary edges: individual line entities
        for name, line in zip(edge_groups, polygon.lines):
            geom.add_physical(line, label=str(name))
        # - surface/region
        geom.add_physical(polygon.surface, label=str(poly.region_name))

        mesh = geom.generate_mesh(dim=2)

    mesh_dict, report = meshio_to_contract(mesh)

    # Fallback: some gmsh/pygmsh/meshio combinations may produce gmsh:physical tags=0
    # even though we created physical groups. Ensure we always have at least one
    # element_set for material assignments in the GUI.
    if not any(k.startswith("elem_set__") for k in mesh_dict.keys()):
        region = _sanitize_set_name(str(poly.region_name))
        if "cells_tri3" in mesh_dict:
            n = int(getattr(mesh_dict["cells_tri3"], "shape", [0])[0])
            if n > 0:
                mesh_dict[f"elem_set__{region}__tri3"] = np.arange(n, dtype=np.int32)
        if "cells_quad4" in mesh_dict:
            n = int(getattr(mesh_dict["cells_quad4"], "shape", [0])[0])
            if n > 0:
                mesh_dict[f"elem_set__{region}__quad4"] = np.arange(n, dtype=np.int32)

        element_sets = dict(report.element_sets)
        # Report counts are per set-name; keep it simple: total elements in fallback region.
        total = 0
        if "cells_tri3" in mesh_dict:
            total += int(getattr(mesh_dict["cells_tri3"], "shape", [0])[0])
        if "cells_quad4" in mesh_dict:
            total += int(getattr(mesh_dict["cells_quad4"], "shape", [0])[0])
        element_sets[region] = int(total)
        report = ImportReport(
            points=report.points,
            cells=report.cells,
            node_sets=report.node_sets,
            edge_sets=report.edge_sets,
            element_sets=element_sets,
        )

    return mesh_dict, report
