from __future__ import annotations

from typing import Any

import numpy as np

from geohpem.viz.vtk_convert import (
    available_steps_from_arrays,
    contract_mesh_to_pyvista,
    get_array_for,
    vector_magnitude,
)


class OutputWorkspace:
    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (
            QCheckBox,
            QComboBox,
            QFormLayout,
            QLabel,
            QListWidget,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

        self._Qt = Qt
        self._QMessageBox = QMessageBox

        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        # Left panel: result browser
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.registry_list = QListWidget()
        left_layout.addWidget(QLabel("Registry"))
        left_layout.addWidget(self.registry_list, 1)

        self.step = QSpinBox()
        self.step.setRange(0, 0)
        self.step.setEnabled(False)
        left_layout.addWidget(QLabel("Step"))
        left_layout.addWidget(self.step)

        self.field_mode = QComboBox()
        self.field_mode.addItem("Auto", "auto")
        self.field_mode.addItem("Magnitude (vector)", "mag")
        self.field_mode.setEnabled(False)
        left_layout.addWidget(QLabel("Field mode"))
        left_layout.addWidget(self.field_mode)

        self.warp = QCheckBox("Warp by displacement u")
        self.warp.setEnabled(False)
        left_layout.addWidget(self.warp)

        self.warp_scale = QSpinBox()
        self.warp_scale.setRange(0, 1_000_000)
        self.warp_scale.setValue(100)
        self.warp_scale.setEnabled(False)
        left_layout.addWidget(QLabel("Warp scale"))
        left_layout.addWidget(self.warp_scale)

        self.btn_reset = QPushButton("Reset view")
        self.btn_reset.setEnabled(False)
        left_layout.addWidget(self.btn_reset)

        splitter.addWidget(left)

        # Right panel: viewer + probe readout
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self._right_layout = right_layout
        self.probe = QLabel("Probe: (click a point to read value)")
        right_layout.addWidget(self.probe)

        self._viewer = None  # QtInteractor
        self._viewer_host = QWidget()
        self._viewer_host_layout = QVBoxLayout(self._viewer_host)
        self._viewer_host_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._viewer_host, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        self._meta: dict[str, Any] | None = None
        self._arrays: dict[str, Any] | None = None
        self._mesh: dict[str, Any] | None = None
        self._steps: list[int] = []
        self._reg_items: list[dict[str, Any]] = []

        self.registry_list.currentRowChanged.connect(self._render)
        self.step.valueChanged.connect(self._render)
        self.field_mode.currentIndexChanged.connect(self._render)
        self.warp.stateChanged.connect(self._render)
        self.warp_scale.valueChanged.connect(self._render)
        self.btn_reset.clicked.connect(self._reset_view)

    def set_result(self, meta: dict[str, Any], arrays: dict[str, Any], mesh: dict[str, Any] | None = None) -> None:
        self._meta = meta
        self._arrays = arrays
        self._mesh = mesh

        self._reg_items = [i for i in meta.get("registry", []) if isinstance(i, dict)]
        self.registry_list.clear()
        for item in self._reg_items:
            name = item.get("name", "<unnamed>")
            loc = item.get("location", "?")
            self.registry_list.addItem(f"{name} ({loc})")

        self._steps = available_steps_from_arrays(arrays)
        if self._steps:
            self.step.setEnabled(True)
            self.step.setRange(0, len(self._steps) - 1)
            self.step.setValue(len(self._steps) - 1)
        else:
            self.step.setEnabled(False)
            self.step.setRange(0, 0)

        self._ensure_viewer()
        self._render()

    def _ensure_viewer(self) -> None:
        if self._viewer is not None:
            return
        try:
            from pyvistaqt import QtInteractor  # type: ignore
        except Exception:
            from PySide6.QtWidgets import QLabel  # type: ignore

            self._viewer_host_layout.addWidget(QLabel("PyVistaQt not installed. Install pyvista + pyvistaqt."))
            return

        self._viewer = QtInteractor(self._viewer_host)
        self._viewer_host_layout.addWidget(self._viewer)

        # probe picking
        def on_pick(point):  # noqa: ANN001
            self._on_probe(point)

        self._viewer.enable_point_picking(callback=on_pick, show_message=False, use_mesh=True, show_point=True)
        self._viewer.set_background("white")
        self.btn_reset.setEnabled(True)

    def _reset_view(self) -> None:
        if self._viewer is None:
            return
        self._viewer.reset_camera()
        self._viewer.render()

    def _selected_reg(self) -> dict[str, Any] | None:
        idx = self.registry_list.currentRow()
        if idx < 0 or idx >= len(self._reg_items):
            return None
        return self._reg_items[idx]

    def _selected_step_id(self) -> int | None:
        if not self._steps:
            return None
        i = int(self.step.value())
        if i < 0 or i >= len(self._steps):
            return None
        return self._steps[i]

    def _render(self) -> None:
        if self._viewer is None:
            return
        if not self._meta or self._arrays is None:
            return
        if self._mesh is None:
            self.probe.setText("Mesh not available (open project/case with output).")
            return

        reg = self._selected_reg()
        step_id = self._selected_step_id()
        if reg is None or step_id is None:
            return

        location = reg.get("location", "node")
        name = reg.get("name", "")
        if not isinstance(name, str) or not name:
            return

        # Build mesh grid
        vtk_mesh = contract_mesh_to_pyvista(self._mesh)
        grid = vtk_mesh.grid.copy()

        # Load field array
        arr = get_array_for(arrays=self._arrays, location=location, name=name, step=step_id)
        if arr is None:
            self.probe.setText(f"Missing array for {name} ({location}) step {step_id:06d}")
            return

        scalar_name = name
        mode = self.field_mode.currentData()
        if arr.ndim == 2 and mode in ("auto", "mag"):
            scalar = vector_magnitude(arr)
            scalar_name = f"{name}_mag"
        else:
            scalar = np.asarray(arr).reshape(-1)

        # Attach scalars to points/cells
        if location in ("node", "nodal"):
            if scalar.shape[0] != grid.n_points:
                self.probe.setText(f"Array size mismatch: {scalar.shape[0]} vs n_points {grid.n_points}")
                return
            grid.point_data.clear()
            grid.point_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "point"}
        elif location in ("element", "elem"):
            if scalar.shape[0] != grid.n_cells:
                self.probe.setText(f"Array size mismatch: {scalar.shape[0]} vs n_cells {grid.n_cells}")
                return
            grid.cell_data.clear()
            grid.cell_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "cell"}
        else:
            self.probe.setText(f"Unsupported location for plotting: {location}")
            return

        # Warp by displacement (if available)
        self.warp.setEnabled(True)
        self.warp_scale.setEnabled(True)
        if self.warp.isChecked():
            u = get_array_for(arrays=self._arrays, location="node", name="u", step=step_id)
            if u is not None and u.ndim == 2 and u.shape[0] == grid.n_points:
                u3 = np.zeros((grid.n_points, 3), dtype=float)
                u3[:, : min(2, u.shape[1])] = u[:, : min(2, u.shape[1])]
                grid.point_data["u_vec"] = u3
                grid = grid.warp_by_vector("u_vec", factor=float(self.warp_scale.value()))

        # Render
        self._viewer.clear()
        self._viewer.add_mesh(grid, show_edges=True, cmap="viridis", **scalars_kwargs)
        self._viewer.add_scalar_bar(title=f"{scalar_name} (step {step_id:06d})")
        self._viewer.reset_camera()
        self._viewer.render()

        # Enable field mode if vector
        self.field_mode.setEnabled(bool(arr.ndim == 2))

        # Cache last grid for probing
        self._last_grid = grid  # type: ignore[attr-defined]
        self._last_scalar = scalar_name  # type: ignore[attr-defined]
        self._last_pref = scalars_kwargs.get("preference", "point")  # type: ignore[attr-defined]

    def _on_probe(self, point) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        grid = getattr(self, "_last_grid", None)
        scalar_name = getattr(self, "_last_scalar", None)
        pref = getattr(self, "_last_pref", "point")
        if grid is None or not scalar_name:
            return
        try:
            # Find closest point
            pid = int(grid.find_closest_point(point))
            val = None
            if pref == "point" and scalar_name in grid.point_data:
                val = float(grid.point_data[scalar_name][pid])
            self.probe.setText(f"Probe: x={point[0]:.4g}, y={point[1]:.4g} -> {scalar_name}={val}")
        except Exception as exc:
            self.probe.setText(f"Probe failed: {exc}")
