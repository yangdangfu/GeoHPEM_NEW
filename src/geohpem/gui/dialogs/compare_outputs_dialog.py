from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from geohpem.app.compare_outputs import FieldKey, common_fields, common_steps, diff_stats_for, load_outputs, step_curve_for
from geohpem.viz.vtk_convert import contract_mesh_to_pyvista, get_array_for, vector_magnitude


class CompareOutputsDialog:
    def __init__(self, parent) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QSplitter,
            QPlainTextEdit,
            QVBoxLayout,
            QWidget,
        )

        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Compare Outputs")
        self._dialog.resize(1100, 720)

        root = QVBoxLayout(self._dialog)

        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        self._path_a = QLabel("A: (not selected)")
        self._path_b = QLabel("B: (not selected)")
        btn_a = QPushButton("Open A...")
        btn_b = QPushButton("Open B...")
        top_l.addWidget(btn_a)
        top_l.addWidget(btn_b)
        top_l.addWidget(self._path_a, 1)
        top_l.addWidget(self._path_b, 1)
        root.addWidget(top)

        splitter = QSplitter()
        root.addWidget(splitter, 1)

        # Left panel
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.addWidget(QLabel("Fields (intersection)"))
        self._fields = QListWidget()
        left_l.addWidget(self._fields, 1)

        form = QFormLayout()
        left_l.addLayout(form)
        self._mode = QComboBox()
        self._mode.addItem("Diff (A - B)", "diff")
        self._mode.addItem("A", "a")
        self._mode.addItem("B", "b")
        form.addRow("View", self._mode)

        self._step = QSpinBox()
        self._step.setEnabled(False)
        self._step.setRange(0, 0)
        form.addRow("Step", self._step)

        self._field_mode = QComboBox()
        self._field_mode.addItem("Auto", "auto")
        self._field_mode.addItem("Magnitude (vector)", "mag")
        self._field_mode.setEnabled(False)
        form.addRow("Field mode", self._field_mode)

        btn_export = QPushButton("Export step-curve CSV...")
        left_l.addWidget(btn_export)

        splitter.addWidget(left)

        # Right panel: viewer + stats
        right = QWidget()
        right_l = QVBoxLayout(right)
        self._stats = QPlainTextEdit()
        self._stats.setReadOnly(True)
        self._stats.setMaximumHeight(170)
        self._stats.setPlainText("Select A, B and a field to compare.")
        right_l.addWidget(self._stats)

        self._viewer = None
        self._viewer_host = QWidget()
        self._viewer_host_l = QVBoxLayout(self._viewer_host)
        self._viewer_host_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(self._viewer_host, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        root.addWidget(buttons)
        buttons.rejected.connect(self._dialog.reject)
        self._dialog.finished.connect(lambda *_: self._shutdown_viewer())

        # State
        self._meta_a: dict[str, Any] | None = None
        self._arr_a: dict[str, Any] | None = None
        self._meta_b: dict[str, Any] | None = None
        self._arr_b: dict[str, Any] | None = None
        self._mesh: dict[str, Any] | None = None
        self._steps: list[int] = []
        self._field_keys: list[FieldKey] = []

        btn_a.clicked.connect(lambda: self._open_side("a"))
        btn_b.clicked.connect(lambda: self._open_side("b"))
        self._fields.currentRowChanged.connect(self._render)
        self._mode.currentIndexChanged.connect(self._render)
        self._step.valueChanged.connect(self._render)
        self._field_mode.currentIndexChanged.connect(self._render)
        btn_export.clicked.connect(self._export_curve)

    def exec(self) -> int:
        return int(self._dialog.exec())

    def _shutdown_viewer(self) -> None:
        v = self._viewer
        if v is None:
            return
        try:
            import vtk  # type: ignore

            vtk.vtkObject.GlobalWarningDisplayOff()
        except Exception:
            pass
        try:
            plotter = getattr(v, "plotter", None)
            if plotter is not None and hasattr(plotter, "close"):
                plotter.close()
        except Exception:
            pass
        try:
            if hasattr(v, "close"):
                v.close()
        except Exception:
            pass
        try:
            if hasattr(v, "setParent"):
                v.setParent(None)
            if hasattr(v, "deleteLater"):
                v.deleteLater()
        except Exception:
            pass
        self._viewer = None

    def _ensure_viewer(self) -> None:
        if self._viewer is not None:
            return
        try:
            from pyvistaqt import QtInteractor  # type: ignore
        except Exception:
            from PySide6.QtWidgets import QLabel  # type: ignore

            self._viewer_host_l.addWidget(QLabel("PyVistaQt not installed. Install pyvista + pyvistaqt."))
            return
        self._viewer = QtInteractor(self._viewer_host)
        self._viewer_host_l.addWidget(self._viewer)
        self._viewer.set_background("white")

    def _open_side(self, which: str) -> None:
        folder = self._QFileDialog.getExistingDirectory(self._dialog, f"Select {'A' if which=='a' else 'B'} output or case folder")
        if not folder:
            return
        p = Path(folder)
        try:
            meta, arrays = load_outputs(p)
        except Exception as exc:
            self._QMessageBox.critical(self._dialog, "Compare Outputs", str(exc))
            return

        if which == "a":
            self._meta_a, self._arr_a = meta, arrays
            self._path_a.setText(f"A: {p}")
        else:
            self._meta_b, self._arr_b = meta, arrays
            self._path_b.setText(f"B: {p}")

        # Try load mesh from sibling mesh.npz (prefer A then B)
        if self._mesh is None:
            candidate = p.parent if (p / "result.json").exists() else p
            mesh_path = candidate / "mesh.npz"
            if mesh_path.exists():
                try:
                    import numpy as np

                    self._mesh = dict(np.load(mesh_path, allow_pickle=True))
                except Exception:
                    self._mesh = None

        self._refresh_fields_and_steps()

    def _refresh_fields_and_steps(self) -> None:
        if not self._meta_a or not self._meta_b or self._arr_a is None or self._arr_b is None:
            return
        self._field_keys = common_fields(self._meta_a, self._meta_b)
        self._fields.clear()
        for k in self._field_keys:
            self._fields.addItem(f"{k.name} ({k.location})")

        self._steps = common_steps(self._arr_a, self._arr_b)
        if self._steps:
            self._step.setEnabled(True)
            self._step.setRange(0, len(self._steps) - 1)
            self._step.setValue(len(self._steps) - 1)
        else:
            self._step.setEnabled(False)
            self._step.setRange(0, 0)
        self._render()

    def _selected_field(self) -> FieldKey | None:
        i = self._fields.currentRow()
        if i < 0 or i >= len(self._field_keys):
            return None
        return self._field_keys[i]

    def _selected_step_id(self) -> int | None:
        if not self._steps:
            return None
        i = int(self._step.value())
        if i < 0 or i >= len(self._steps):
            return None
        return self._steps[i]

    def _render(self) -> None:
        self._ensure_viewer()
        if self._viewer is None:
            return
        if not self._meta_a or not self._meta_b or self._arr_a is None or self._arr_b is None:
            return
        if self._mesh is None:
            self._stats.setPlainText("Mesh not found. Open a case folder (with mesh.npz) or place mesh.npz next to outputs.")
            return
        field = self._selected_field()
        step = self._selected_step_id()
        if field is None or step is None:
            return

        # Read arrays
        a = get_array_for(arrays=self._arr_a, location=field.location, name=field.name, step=step)
        b = get_array_for(arrays=self._arr_b, location=field.location, name=field.name, step=step)
        if a is None or b is None:
            self._stats.setPlainText("Missing arrays for selected field/step.")
            return

        view = str(self._mode.currentData())
        mode = str(self._field_mode.currentData())
        is_vec = np.asarray(a).ndim == 2
        self._field_mode.setEnabled(bool(is_vec))

        if is_vec and mode in ("auto", "mag"):
            sa = vector_magnitude(a)
            sb = vector_magnitude(b)
            scalar_name = f"{field.name}_mag"
        else:
            sa = np.asarray(a).reshape(-1).astype(float, copy=False)
            sb = np.asarray(b).reshape(-1).astype(float, copy=False)
            scalar_name = field.name

        if sa.shape != sb.shape:
            self._stats.setPlainText(f"Shape mismatch: A{list(sa.shape)} vs B{list(sb.shape)}")
            return

        if view == "a":
            scalar = sa
            title = f"A: {scalar_name} step {step:06d}"
        elif view == "b":
            scalar = sb
            title = f"B: {scalar_name} step {step:06d}"
        else:
            scalar = sa - sb
            title = f"Diff (A-B): {scalar_name} step {step:06d}"

        # Stats
        st = diff_stats_for(meta_a=self._meta_a, arrays_a=self._arr_a, meta_b=self._meta_b, arrays_b=self._arr_b, field=field, step=step)
        if st is None:
            self._stats.setPlainText("Stats unavailable (missing arrays or mismatch).")
        else:
            self._stats.setPlainText(
                f"Field: {field.name} ({field.location})\n"
                f"Step: {step:06d}\n"
                f"Diff stats (A-B scalar): min={st.min:.6g}, max={st.max:.6g}, mean={st.mean:.6g}, L2={st.l2:.6g}, Linf={st.linf:.6g}\n"
                f"View: {view}"
            )

        vtk_mesh = contract_mesh_to_pyvista(self._mesh)
        grid = vtk_mesh.grid.copy()

        # Attach scalars
        if field.location in ("node", "nodal"):
            if scalar.shape[0] != grid.n_points:
                self._stats.setPlainText(f"Array size mismatch: {scalar.shape[0]} vs n_points {grid.n_points}")
                return
            grid.point_data.clear()
            grid.point_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "point"}
        else:
            if scalar.shape[0] != grid.n_cells:
                self._stats.setPlainText(f"Array size mismatch: {scalar.shape[0]} vs n_cells {grid.n_cells}")
                return
            grid.cell_data.clear()
            grid.cell_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "cell"}

        self._viewer.clear()
        self._viewer.add_mesh(grid, show_edges=True, cmap="coolwarm", **scalars_kwargs)
        self._viewer.add_scalar_bar(title=title)
        self._viewer.reset_camera()
        self._viewer.render()

    def _export_curve(self) -> None:
        if not self._meta_a or not self._meta_b or self._arr_a is None or self._arr_b is None:
            return
        field = self._selected_field()
        if field is None or not self._steps:
            return
        path, _ = self._QFileDialog.getSaveFileName(self._dialog, "Export CSV", "", "CSV (*.csv);;All Files (*)")
        if not path:
            return
        steps = list(self._steps)
        curve_a = step_curve_for(arrays=self._arr_a, field=field, steps=steps)
        curve_b = step_curve_for(arrays=self._arr_b, field=field, steps=steps)
        try:
            import csv

            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["step", "A_min", "A_max", "A_mean", "B_min", "B_max", "B_mean", "diff_mean"])
                for s, a, b in zip(steps, curve_a, curve_b):
                    diff_mean = float(a["mean"] - b["mean"]) if (np.isfinite(a["mean"]) and np.isfinite(b["mean"])) else float("nan")
                    w.writerow([f"{s:06d}", a["min"], a["max"], a["mean"], b["min"], b["max"], b["mean"], diff_mean])
            self._QMessageBox.information(self._dialog, "Export CSV", f"Wrote: {path}")
        except Exception as exc:
            self._QMessageBox.critical(self._dialog, "Export CSV", str(exc))
