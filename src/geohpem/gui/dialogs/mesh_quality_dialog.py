from __future__ import annotations

from typing import Any

import numpy as np

from geohpem.mesh.quality import triangle_quality


class MeshQualityDialog:
    def __init__(self, parent, mesh: dict[str, Any]) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (
            QDialog,
            QLabel,  # type: ignore
            QListWidget,
            QVBoxLayout,
        )

        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Mesh Quality")
        self.dialog.resize(800, 520)

        layout = QVBoxLayout(self.dialog)

        points = np.asarray(mesh.get("points", np.zeros((0, 2))))
        tri = np.asarray(mesh.get("cells_tri3", np.zeros((0, 3), dtype=np.int32)))

        if tri.size == 0:
            layout.addWidget(QLabel("No triangle cells found (cells_tri3)."))
            self.list = None
            return

        min_angle, aspect, stats = triangle_quality(points, tri)
        layout.addWidget(
            QLabel(
                f"Triangles: {stats.count}\n"
                f"Min angle (min/p50/p95): {stats.min_angle_deg_min:.3f} / {stats.min_angle_deg_p50:.3f} / {stats.min_angle_deg_p95:.3f}\n"
                f"Aspect ratio max: {stats.aspect_ratio_max:.3f}"
            )
        )

        self.list = QListWidget()
        layout.addWidget(
            QLabel("Worst triangles by min angle (index, min_angle_deg, aspect_ratio)")
        )
        layout.addWidget(self.list)

        worst = np.argsort(min_angle)[: min(50, min_angle.size)]
        for idx in worst:
            self.list.addItem(
                f"{int(idx)}\t{float(min_angle[idx]):.3f}\t{float(aspect[idx]):.3f}"
            )

    def exec(self) -> None:
        self.dialog.exec()
