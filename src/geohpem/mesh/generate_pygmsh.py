from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from geohpem.geometry.polygon2d import Polygon2D
from geohpem.mesh.convert import ImportReport, meshio_to_contract


@dataclass(frozen=True, slots=True)
class PygmshConfig:
    mesh_size: float = 0.1


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
    return mesh_dict, report
