from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class TriangleQualityStats:
    count: int
    min_angle_deg_min: float
    min_angle_deg_p50: float
    min_angle_deg_p95: float
    aspect_ratio_max: float


def _triangle_angles_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    # edges opposite vertices A,B,C: a=|BC|, b=|CA|, c=|AB|
    # angle at A opposite a: cosA = (b^2 + c^2 - a^2)/(2bc)
    eps = 1e-30
    cosA = (b * b + c * c - a * a) / (2.0 * np.maximum(b * c, eps))
    cosB = (c * c + a * a - b * b) / (2.0 * np.maximum(c * a, eps))
    cosC = (a * a + b * b - c * c) / (2.0 * np.maximum(a * b, eps))
    cosA = np.clip(cosA, -1.0, 1.0)
    cosB = np.clip(cosB, -1.0, 1.0)
    cosC = np.clip(cosC, -1.0, 1.0)
    A = np.degrees(np.arccos(cosA))
    B = np.degrees(np.arccos(cosB))
    C = np.degrees(np.arccos(cosC))
    return np.stack([A, B, C], axis=1)


def triangle_quality(
    points: np.ndarray, tri3: np.ndarray
) -> tuple[np.ndarray, np.ndarray, TriangleQualityStats]:
    """
    Returns:
    - min_angle_deg: (M,) minimum interior angle per triangle
    - aspect_ratio: (M,) max_edge / min_edge per triangle
    - stats: summary
    """
    pts = np.asarray(points, dtype=float)
    tri = np.asarray(tri3, dtype=np.int64)
    if tri.size == 0:
        stats = TriangleQualityStats(
            count=0,
            min_angle_deg_min=float("nan"),
            min_angle_deg_p50=float("nan"),
            min_angle_deg_p95=float("nan"),
            aspect_ratio_max=float("nan"),
        )
        return np.zeros((0,), dtype=float), np.zeros((0,), dtype=float), stats

    p0 = pts[tri[:, 0], :2]
    p1 = pts[tri[:, 1], :2]
    p2 = pts[tri[:, 2], :2]

    e0 = np.linalg.norm(p1 - p0, axis=1)  # |AB| (c)
    e1 = np.linalg.norm(p2 - p1, axis=1)  # |BC| (a)
    e2 = np.linalg.norm(p0 - p2, axis=1)  # |CA| (b)

    # Opposite lengths: a=|BC|, b=|CA|, c=|AB|
    angles = _triangle_angles_deg(a=e1, b=e2, c=e0)
    min_angle = np.min(angles, axis=1)

    edges = np.stack([e0, e1, e2], axis=1)
    min_edge = np.min(edges, axis=1)
    max_edge = np.max(edges, axis=1)
    aspect = np.where(min_edge > 0, max_edge / min_edge, float("inf"))

    stats = TriangleQualityStats(
        count=int(tri.shape[0]),
        min_angle_deg_min=float(np.nanmin(min_angle)),
        min_angle_deg_p50=float(np.nanpercentile(min_angle, 50)),
        min_angle_deg_p95=float(np.nanpercentile(min_angle, 95)),
        aspect_ratio_max=float(np.nanmax(aspect)),
    )
    return min_angle, aspect, stats
