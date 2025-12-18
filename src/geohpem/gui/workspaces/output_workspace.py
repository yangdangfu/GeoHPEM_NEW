from __future__ import annotations

from typing import Any

import numpy as np

from geohpem.viz.vtk_convert import (
    available_steps_from_arrays,
    cell_type_code_to_name,
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
            QPlainTextEdit,
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
        self.probe = QPlainTextEdit()
        self.probe.setReadOnly(True)
        self.probe.setMaximumHeight(110)
        self.probe.setPlainText("Probe: left-click in the viewport to read value.")
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
        self._node_set_membership: dict[int, list[str]] = {}
        self._elem_set_membership: dict[str, dict[int, list[str]]] = {}  # cell_type -> local_id -> names
        self._sets_label_by_key: dict[str, str] = {}

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
        self._build_set_membership()

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

    def _build_set_membership(self) -> None:
        self._node_set_membership = {}
        self._elem_set_membership = {}
        self._sets_label_by_key = {}
        if not self._mesh or not self._meta:
            return
        mesh = self._mesh
        # Optional request-provided label map via sets_meta (UI-only)
        # We don't have request here, so we use key itself as label.

        # Node sets
        for k, arr in mesh.items():
            if not k.startswith("node_set__"):
                continue
            name = k.split("__", 1)[1]
            nodes = np.asarray(arr, dtype=np.int64).reshape(-1)
            for nid in nodes:
                self._node_set_membership.setdefault(int(nid), []).append(name)

        # Element sets (per cell type)
        for k, arr in mesh.items():
            if not k.startswith("elem_set__"):
                continue
            rest = k.split("__", 1)[1]
            parts = rest.split("__")
            if len(parts) < 2:
                continue
            name = parts[0]
            cell_type = parts[1]
            ids = np.asarray(arr, dtype=np.int64).reshape(-1)
            by_id = self._elem_set_membership.setdefault(cell_type, {})
            for cid in ids:
                by_id.setdefault(int(cid), []).append(name)

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
        def on_pick(*args, **kwargs):  # noqa: ANN001
            # pyvista callback signature varies; we try to extract a point-like object.
            point = None
            if args:
                point = args[0]
            if point is None and "point" in kwargs:
                point = kwargs["point"]
            self._on_probe(point)

        # Avoid deprecated `use_mesh`; use_picker=True enables picker-based picking.
        try:
            self._viewer.enable_point_picking(
                callback=on_pick,
                show_message=False,
                left_clicking=True,
                use_picker=True,
                show_point=True,
            )
        except TypeError:
            # Backward compatibility with older pyvista versions
            self._viewer.enable_point_picking(
                callback=on_pick,
                show_message=False,
                left_clicking=True,
                show_point=True,
                use_mesh=True,  # deprecated in newer versions
            )

        # cell picking (extract cell id via picker when available)
        def on_cell_pick(*args, **kwargs):  # noqa: ANN001
            self._on_cell_pick(args, kwargs)

        try:
            self._viewer.enable_cell_picking(  # type: ignore[attr-defined]
                callback=on_cell_pick,
                show=False,
                through=False,
                show_message=False,
                start=True,
            )
        except Exception:
            # Some versions may not expose enable_cell_picking; point probe still works.
            pass
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
            if point is None:
                return
            # Normalize point into a 3-tuple
            if hasattr(point, "GetPickPosition"):
                point = point.GetPickPosition()
            if isinstance(point, np.ndarray):
                point = point.tolist()
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                px = float(point[0])
                py = float(point[1])
                pz = float(point[2]) if len(point) >= 3 else 0.0
            else:
                return
            # Find closest point
            pid = int(grid.find_closest_point((px, py, pz)))
            val = None
            if pref == "point" and scalar_name in grid.point_data:
                val = float(grid.point_data[scalar_name][pid])
            node_sets = self._node_set_membership.get(pid, [])
            sets_txt = f" node_sets={node_sets}" if node_sets else ""
            self.probe.setPlainText(
                f"Probe:\n"
                f"  pid={pid}\n"
                f"  x={px:.6g}, y={py:.6g}\n"
                f"  {scalar_name}={val}\n"
                f"  {sets_txt.strip() if sets_txt else 'node_sets=[]'}"
            )
        except Exception as exc:
            self.probe.setPlainText(f"Probe failed: {exc}")

    def _on_cell_pick(self, args, kwargs) -> None:  # noqa: ANN001
        grid = getattr(self, "_last_grid", None)
        if grid is None:
            return

        cell_id: int | None = None
        # Try various callback signatures and picker fields.
        for a in args:
            if isinstance(a, int):
                cell_id = int(a)
                break
            if hasattr(a, "cell_id"):
                try:
                    cell_id = int(getattr(a, "cell_id"))
                    break
                except Exception:
                    pass
        if cell_id is None and "cell_id" in kwargs:
            try:
                cell_id = int(kwargs["cell_id"])
            except Exception:
                cell_id = None

        # Try plotter picker
        if cell_id is None and self._viewer is not None:
            try:
                picker = getattr(self._viewer, "picker", None)
                if picker is not None and hasattr(picker, "GetCellId"):
                    cid = int(picker.GetCellId())
                    if cid >= 0:
                        cell_id = cid
            except Exception:
                cell_id = None

        if cell_id is None or cell_id < 0 or cell_id >= grid.n_cells:
            return

        try:
            ctype_code = int(grid.cell_data["__cell_type_code"][cell_id])
            local_id = int(grid.cell_data["__cell_local_id"][cell_id])
            ctype = cell_type_code_to_name(ctype_code) or str(ctype_code)
            elem_sets = self._elem_set_membership.get(ctype, {}).get(local_id, [])
            self.probe.setPlainText(
                "Cell pick:\n"
                f"  cell_id={cell_id}\n"
                f"  type={ctype}\n"
                f"  local_id={local_id}\n"
                f"  elem_sets={elem_sets}"
            )
        except Exception as exc:
            self.probe.setPlainText(f"Cell pick failed: {exc}")
