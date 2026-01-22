from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class PlotSeries:
    x: np.ndarray
    y: np.ndarray
    label: str | None = None


class PlotDialog:
    def __init__(
        self,
        parent,  # noqa: ANN001
        *,
        title: str,
        xlabel: str,
        ylabel: str,
        series: list[PlotSeries],
        note: str | None = None,
        default_csv_name: str = "data.csv",
        default_png_name: str = "plot.png",
    ) -> None:
        from matplotlib.backends.backend_qtagg import (
            FigureCanvasQTAgg as FigureCanvas,
        )  # type: ignore
        from matplotlib.backends.backend_qtagg import (
            NavigationToolbar2QT as NavigationToolbar,
        )  # type: ignore
        from matplotlib.figure import Figure  # type: ignore
        from PySide6.QtWidgets import (
            QDialog,
            QFileDialog,  # type: ignore
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )

        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox
        self._default_csv_name = default_csv_name
        self._default_png_name = default_png_name

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle(title)
        self._dialog.resize(900, 600)

        layout = QVBoxLayout(self._dialog)
        if note:
            layout.addWidget(QLabel(note))

        fig = Figure(constrained_layout=True)
        self._fig = fig
        self._canvas = FigureCanvas(fig)
        self._ax = fig.add_subplot(1, 1, 1)
        self._ax.set_xlabel(xlabel)
        self._ax.set_ylabel(ylabel)
        self._ax.grid(True, linestyle=":", linewidth=0.8)

        for s in series:
            x = np.asarray(s.x, dtype=float).ravel()
            y = np.asarray(s.y, dtype=float).ravel()
            if x.size != y.size:
                continue
            self._ax.plot(x, y, label=s.label or None)

        if any(s.label for s in series):
            self._ax.legend(loc="best")

        toolbar = NavigationToolbar(self._canvas, self._dialog)
        layout.addWidget(toolbar)
        layout.addWidget(self._canvas, 1)

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        self._btn_csv = QPushButton("Export CSV...")
        self._btn_png = QPushButton("Save Plot Image...")
        self._btn_close = QPushButton("Close")
        bl.addStretch(1)
        bl.addWidget(self._btn_csv)
        bl.addWidget(self._btn_png)
        bl.addWidget(self._btn_close)
        layout.addWidget(btns)

        self._btn_close.clicked.connect(self._dialog.accept)
        self._btn_csv.clicked.connect(
            lambda: self._export_csv(series, xlabel=xlabel, ylabel=ylabel)
        )
        self._btn_png.clicked.connect(self._save_plot_png)

    def exec(self) -> int:
        return int(self._dialog.exec())

    def _export_csv(
        self, series: list[PlotSeries], *, xlabel: str, ylabel: str
    ) -> None:
        file, _ = self._QFileDialog.getSaveFileName(
            self._dialog,
            "Export CSV",
            self._default_csv_name,
            "CSV (*.csv);;All Files (*)",
        )
        if not file:
            return
        path = Path(file)
        try:
            # Minimal wide format: x + y1..yn (assumes same x length; otherwise falls back to two-column per series).
            x0 = (
                np.asarray(series[0].x, dtype=float).ravel()
                if series
                else np.array([], dtype=float)
            )
            same_x = bool(series) and all(
                np.asarray(s.x).ravel().shape == x0.shape
                and np.allclose(np.asarray(s.x).ravel(), x0)
                for s in series
            )
            if same_x:
                cols = [x0]
                headers = [xlabel]
                for i, s in enumerate(series):
                    cols.append(np.asarray(s.y, dtype=float).ravel())
                    headers.append(s.label or f"{ylabel}_{i+1}")
                arr = np.column_stack(cols) if cols else np.zeros((0, 0))
                txt = ",".join(headers) + "\n"
                txt += "\n".join(",".join(f"{v:.12g}" for v in row) for row in arr)
                path.write_text(txt, encoding="utf-8")
            else:
                # Multi-block format.
                parts: list[str] = []
                for i, s in enumerate(series):
                    x = np.asarray(s.x, dtype=float).ravel()
                    y = np.asarray(s.y, dtype=float).ravel()
                    lab = s.label or f"series_{i+1}"
                    parts.append(f"# {lab}")
                    parts.append(f"{xlabel},{ylabel}")
                    parts.extend(
                        ",".join((f"{x[j]:.12g}", f"{y[j]:.12g}"))
                        for j in range(min(x.size, y.size))
                    )
                    parts.append("")
                path.write_text("\n".join(parts), encoding="utf-8")
        except Exception as exc:
            self._QMessageBox.critical(self._dialog, "Export CSV Failed", str(exc))

    def _save_plot_png(self) -> None:
        file, _ = self._QFileDialog.getSaveFileName(
            self._dialog,
            "Save Plot Image",
            self._default_png_name,
            "PNG (*.png);;All Files (*)",
        )
        if not file:
            return
        try:
            self._fig.savefig(str(file), dpi=200)
        except Exception as exc:
            self._QMessageBox.critical(self._dialog, "Save Plot Image Failed", str(exc))
