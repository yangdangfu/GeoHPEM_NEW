from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Polygon2D:
    vertices: list[tuple[float, float]]
    edge_groups: list[str]
    region_name: str = "domain"
    vertex_ids: list[str] | None = None
    edge_ids: list[str] | None = None

    def validate(self) -> None:
        if len(self.vertices) < 3:
            raise ValueError("Polygon must have at least 3 vertices")
        if len(self.edge_groups) not in (0, len(self.vertices)):
            raise ValueError("edge_groups must be empty or have the same length as vertices")
        if self.vertex_ids is not None and len(self.vertex_ids) != len(self.vertices):
            raise ValueError("vertex_ids must have the same length as vertices")
        if self.edge_ids is not None and len(self.edge_ids) != len(self.vertices):
            raise ValueError("edge_ids must have the same length as vertices")

    def normalized_edge_groups(self) -> list[str]:
        if not self.edge_groups:
            return [f"edge_{i+1}" for i in range(len(self.vertices))]
        return list(self.edge_groups)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        out = {
            "type": "polygon2d",
            "vertices": [[float(x), float(y)] for x, y in self.vertices],
            "edge_groups": list(self.normalized_edge_groups()),
            "region_name": self.region_name,
        }
        if self.vertex_ids is not None:
            out["vertex_ids"] = list(self.vertex_ids)
        if self.edge_ids is not None:
            out["edge_ids"] = list(self.edge_ids)
        return out

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Polygon2D":
        if data.get("type") != "polygon2d":
            raise ValueError("geometry.type must be 'polygon2d'")
        verts_raw = data.get("vertices", [])
        if not isinstance(verts_raw, list):
            raise ValueError("geometry.vertices must be a list")
        vertices: list[tuple[float, float]] = []
        for v in verts_raw:
            if not isinstance(v, (list, tuple)) or len(v) < 2:
                raise ValueError("Each vertex must be [x,y]")
            vertices.append((float(v[0]), float(v[1])))
        edge_groups = data.get("edge_groups", [])
        if edge_groups is None:
            edge_groups = []
        if not isinstance(edge_groups, list):
            raise ValueError("geometry.edge_groups must be a list")
        region_name = str(data.get("region_name", "domain"))
        v_ids = data.get("vertex_ids")
        e_ids = data.get("edge_ids")
        if v_ids is not None and not isinstance(v_ids, list):
            raise ValueError("geometry.vertex_ids must be a list")
        if e_ids is not None and not isinstance(e_ids, list):
            raise ValueError("geometry.edge_ids must be a list")
        poly = Polygon2D(
            vertices=vertices,
            edge_groups=[str(s) for s in edge_groups],
            region_name=region_name,
            vertex_ids=[str(s) for s in v_ids] if isinstance(v_ids, list) else None,
            edge_ids=[str(s) for s in e_ids] if isinstance(e_ids, list) else None,
        )
        poly.validate()
        return poly


def get_polygon_from_request(request: dict[str, Any]) -> Polygon2D | None:
    geo = request.get("geometry")
    if not isinstance(geo, dict):
        return None
    if geo.get("type") != "polygon2d":
        return None
    return Polygon2D.from_dict(geo)


def set_polygon_in_request(request: dict[str, Any], poly: Polygon2D | None) -> dict[str, Any]:
    req = dict(request)
    if poly is None:
        req.pop("geometry", None)
        return req
    # Preserve existing ids if caller didn't provide them.
    existing = request.get("geometry")
    if (
        isinstance(existing, dict)
        and existing.get("type") == "polygon2d"
        and poly.vertex_ids is None
        and poly.edge_ids is None
    ):
        try:
            ex = Polygon2D.from_dict(existing)
        except Exception:
            ex = None
        if ex is not None and len(ex.vertices) == len(poly.vertices):
            poly = Polygon2D(
                vertices=poly.vertices,
                edge_groups=poly.edge_groups,
                region_name=poly.region_name,
                vertex_ids=ex.vertex_ids,
                edge_ids=ex.edge_ids,
            )
    req["geometry"] = poly.to_dict()
    return req
