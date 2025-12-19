from __future__ import annotations

from typing import Any

import numpy as np


def compute_boundary_edges(mesh: dict[str, Any]) -> np.ndarray:
    """
    Compute boundary edges from a 2D mesh connectivity.

    Boundary edges are those belonging to exactly one cell. Returned edges are
    unique and stored as node-id pairs (n,2) with each row sorted (min,max).
    """
    pts = np.asarray(mesh.get("points", np.zeros((0, 2))), dtype=float)
    if pts.ndim != 2 or pts.shape[1] < 2:
        return np.zeros((0, 2), dtype=np.int32)

    def boundary_for_edges(edges: np.ndarray) -> np.ndarray:
        edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
        if edges.size == 0:
            return np.zeros((0, 2), dtype=np.int32)
        edges = np.sort(edges, axis=1)
        n_points = int(pts.shape[0])
        ok = (edges[:, 0] >= 0) & (edges[:, 1] >= 0) & (edges[:, 0] < n_points) & (edges[:, 1] < n_points)
        edges = edges[ok]
        if edges.size == 0:
            return np.zeros((0, 2), dtype=np.int32)
        uniq, counts = np.unique(edges, axis=0, return_counts=True)
        return np.asarray(uniq[counts == 1], dtype=np.int32).reshape(-1, 2)

    boundary_parts: list[np.ndarray] = []

    tri = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3))), dtype=np.int64)
    if tri.ndim == 2 and tri.shape[1] == 3 and tri.shape[0] > 0:
        tri_edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]], axis=0)
        boundary_parts.append(boundary_for_edges(tri_edges))

    quad = np.asarray(mesh.get("cells_quad4", np.zeros((0, 4))), dtype=np.int64)
    if quad.ndim == 2 and quad.shape[1] == 4 and quad.shape[0] > 0:
        quad_edges = np.concatenate([quad[:, [0, 1]], quad[:, [1, 2]], quad[:, [2, 3]], quad[:, [3, 0]]], axis=0)
        boundary_parts.append(boundary_for_edges(quad_edges))

    if not boundary_parts:
        return np.zeros((0, 2), dtype=np.int32)

    # Union boundary edges across cell blocks.
    # Important: when a mesh contains multiple cell blocks that geometrically
    # overlap (e.g., tri3 subdivision + quad4), a global edge count will mark
    # boundary edges as "shared" and incorrectly drop them. Per-block boundary
    # detection + union avoids that.
    bd = np.concatenate([b for b in boundary_parts if b.size], axis=0) if any(b.size for b in boundary_parts) else np.zeros((0, 2), dtype=np.int32)
    if bd.size == 0:
        return np.zeros((0, 2), dtype=np.int32)
    bd = np.asarray(bd, dtype=np.int64).reshape(-1, 2)
    bd = np.sort(bd, axis=1)
    bd = np.unique(bd, axis=0)
    return np.asarray(bd, dtype=np.int32).reshape(-1, 2)


def classify_boundary_edges(
    mesh: dict[str, Any],
    *,
    edges: np.ndarray | None = None,
    tol_factor: float = 1e-6,
) -> dict[str, np.ndarray]:
    """
    Classify boundary edges into {all,bottom,top,left,right} by bounding box extremes.

    This is a best-effort helper intended for common engineering cases where the
    domain has clear min/max x/y boundaries.
    """
    pts = np.asarray(mesh.get("points", np.zeros((0, 2))), dtype=float)
    if pts.ndim != 2 or pts.shape[1] < 2:
        empty = np.zeros((0, 2), dtype=np.int32)
        return {"all": empty, "bottom": empty, "top": empty, "left": empty, "right": empty}

    bd = compute_boundary_edges(mesh) if edges is None else np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    bd = np.asarray(bd, dtype=np.int64).reshape(-1, 2)
    if bd.size == 0:
        empty = np.zeros((0, 2), dtype=np.int32)
        return {"all": empty, "bottom": empty, "top": empty, "left": empty, "right": empty}

    x = pts[:, 0]
    y = pts[:, 1]
    xmin = float(np.min(x))
    xmax = float(np.max(x))
    ymin = float(np.min(y))
    ymax = float(np.max(y))
    span_x = max(xmax - xmin, 1.0)
    span_y = max(ymax - ymin, 1.0)
    tol_x = max(1e-12, float(tol_factor) * span_x)
    tol_y = max(1e-12, float(tol_factor) * span_y)

    a = bd[:, 0]
    b = bd[:, 1]
    xa = x[a]
    xb = x[b]
    ya = y[a]
    yb = y[b]

    bottom = (np.maximum(ya, yb) <= (ymin + tol_y))
    top = (np.minimum(ya, yb) >= (ymax - tol_y))
    left = (np.maximum(xa, xb) <= (xmin + tol_x))
    right = (np.minimum(xa, xb) >= (xmax - tol_x))

    out: dict[str, np.ndarray] = {"all": np.asarray(bd, dtype=np.int32)}
    out["bottom"] = np.asarray(bd[bottom], dtype=np.int32)
    out["top"] = np.asarray(bd[top], dtype=np.int32)
    out["left"] = np.asarray(bd[left], dtype=np.int32)
    out["right"] = np.asarray(bd[right], dtype=np.int32)
    return out


def unique_nodes_from_edges(edges: np.ndarray) -> np.ndarray:
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    if edges.size == 0:
        return np.zeros((0,), dtype=np.int32)
    return np.asarray(np.unique(edges.reshape(-1)), dtype=np.int32).reshape(-1)
