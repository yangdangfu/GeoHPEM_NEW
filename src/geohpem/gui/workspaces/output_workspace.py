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
            QDoubleSpinBox,
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
        from geohpem.util.ids import new_uid

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QDoubleSpinBox = QDoubleSpinBox
        self._new_uid = new_uid

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
        self.step_info = QLabel("")
        self.step_info.setWordWrap(True)
        left_layout.addWidget(self.step_info)

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

        self.btn_profile = QPushButton("Profile line...")
        self.btn_profile.setEnabled(False)
        left_layout.addWidget(self.btn_profile)

        self.btn_history = QPushButton("Time history...")
        self.btn_history.setEnabled(False)
        left_layout.addWidget(self.btn_history)

        self.btn_export_img = QPushButton("Export image...")
        self.btn_export_img.setEnabled(False)
        left_layout.addWidget(self.btn_export_img)

        left_layout.addWidget(QLabel("Profiles"))
        self.profile_list = QListWidget()
        self.profile_list.setEnabled(False)
        left_layout.addWidget(self.profile_list, 1)

        self.btn_profile_pick = QPushButton("Pick 2 points (viewport)")
        self.btn_profile_pick.setEnabled(False)
        left_layout.addWidget(self.btn_profile_pick)
        self.btn_profile_plot = QPushButton("Plot selected")
        self.btn_profile_plot.setEnabled(False)
        left_layout.addWidget(self.btn_profile_plot)
        self.btn_profile_remove = QPushButton("Remove selected")
        self.btn_profile_remove.setEnabled(False)
        left_layout.addWidget(self.btn_profile_remove)

        left_layout.addWidget(QLabel("Pins"))
        self.pin_list = QListWidget()
        self.pin_list.setEnabled(False)
        left_layout.addWidget(self.pin_list, 1)

        self.btn_pin_node = QPushButton("Pin last probe (node)")
        self.btn_pin_node.setEnabled(False)
        left_layout.addWidget(self.btn_pin_node)
        self.btn_pin_elem = QPushButton("Pin last cell (element)")
        self.btn_pin_elem.setEnabled(False)
        left_layout.addWidget(self.btn_pin_elem)
        self.btn_pin_remove = QPushButton("Remove pin")
        self.btn_pin_remove.setEnabled(False)
        left_layout.addWidget(self.btn_pin_remove)

        splitter.addWidget(left)

        # Right panel: viewer + probe readout (resizable)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self._right_layout = right_layout

        v_split = QSplitter(self._Qt.Vertical)
        right_layout.addWidget(v_split, 1)

        probe_host = QWidget()
        probe_layout = QVBoxLayout(probe_host)
        probe_layout.setContentsMargins(0, 0, 0, 0)
        self.probe = QPlainTextEdit()
        self.probe.setReadOnly(True)
        self.probe.setMinimumHeight(70)
        self.probe.setPlainText("Probe: left-click in the viewport to read value.")
        probe_layout.addWidget(self.probe)
        v_split.addWidget(probe_host)

        self._viewer = None  # QtInteractor
        self._viewer_host = QWidget()
        self._viewer_host_layout = QVBoxLayout(self._viewer_host)
        self._viewer_host_layout.setContentsMargins(0, 0, 0, 0)
        v_split.addWidget(self._viewer_host)
        try:
            v_split.setStretchFactor(0, 0)
            v_split.setStretchFactor(1, 1)
            v_split.setSizes([90, 1000])
        except Exception:
            pass
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        self._meta: dict[str, Any] | None = None
        self._arrays: dict[str, Any] | None = None
        self._mesh: dict[str, Any] | None = None
        self._units = None  # UnitContext | None
        self._steps: list[int] = []
        self._step_infos: dict[int, dict[str, Any]] = {}
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
        self.btn_profile.clicked.connect(self._on_profile_line)
        self.btn_history.clicked.connect(self._on_time_history)
        self.btn_export_img.clicked.connect(self._on_export_image)
        self.btn_profile_pick.clicked.connect(self._start_profile_pick_mode)
        self.btn_profile_plot.clicked.connect(self._plot_selected_profile)
        self.btn_profile_remove.clicked.connect(self._remove_selected_profile)
        self.profile_list.currentRowChanged.connect(self._on_profile_selection_changed)
        self.profile_list.itemDoubleClicked.connect(lambda *_: self._plot_selected_profile())
        self.pin_list.currentRowChanged.connect(self._on_pin_selection_changed)
        self.btn_pin_node.clicked.connect(self._pin_last_probe)
        self.btn_pin_elem.clicked.connect(self._pin_last_cell)
        self.btn_pin_remove.clicked.connect(self._remove_selected_pin)

        self._probe_history: list[dict[str, Any]] = []
        self._last_probe_pid: int | None = None
        self._last_cell_id: int | None = None
        self._last_probe_xyz: tuple[float, float, float] | None = None
        self._last_cell_info: dict[str, Any] | None = None

        self._mode: str = "normal"  # normal|profile_pick
        self._profile_pick_points: list[tuple[float, float, float]] = []
        self._profiles: list[dict[str, Any]] = []
        self._profile_actor = None
        self._pins: list[dict[str, Any]] = []

    def set_unit_context(self, units) -> None:  # noqa: ANN001
        """
        Set a UnitContext for display conversion (cloud map / probe readout).
        """
        self._units = units
        self._render()

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

        self._steps, self._step_infos = self._infer_steps(meta, arrays)
        if self._steps:
            self.step.setEnabled(True)
            self.step.setRange(0, len(self._steps) - 1)
            self.step.setValue(len(self._steps) - 1)
        else:
            self.step.setEnabled(False)
            self.step.setRange(0, 0)

        self._ensure_viewer()
        self._render()
        self.btn_profile.setEnabled(True)
        self.btn_history.setEnabled(True)
        self.btn_export_img.setEnabled(True)
        self.profile_list.setEnabled(True)
        self.btn_profile_pick.setEnabled(True)
        self._refresh_profile_list()
        self.pin_list.setEnabled(True)
        self.btn_pin_node.setEnabled(True)
        self.btn_pin_elem.setEnabled(True)
        self._refresh_pin_list()

    def _infer_steps(self, meta: dict[str, Any], arrays: dict[str, Any]) -> tuple[list[int], dict[int, dict[str, Any]]]:
        """
        Prefer meta['global_steps'] when available, otherwise fall back to parsing array keys.
        Returns (sorted_step_ids, step_info_by_id).
        """
        infos: dict[int, dict[str, Any]] = {}
        gs = meta.get("global_steps")
        if isinstance(gs, list) and gs:
            step_ids: list[int] = []
            for it in gs:
                if not isinstance(it, dict):
                    continue
                sid = it.get("id")
                try:
                    sid_i = int(sid)
                except Exception:
                    continue
                step_ids.append(sid_i)
                infos[sid_i] = dict(it)
            step_ids = sorted(set(step_ids))
            if step_ids:
                return step_ids, infos
        steps = available_steps_from_arrays(arrays)
        return steps, infos

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
        self.btn_export_img.setEnabled(True)

    def shutdown(self) -> None:
        """
        Best-effort teardown for VTK/Qt resources to avoid noisy OpenGL context errors on app exit (Windows).
        """
        v = self._viewer
        if v is None:
            return
        # Suppress VTK warnings during teardown (OpenGL context may already be invalid while Qt is closing).
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
            # Detach from Qt hierarchy and delete later.
            if hasattr(v, "setParent"):
                v.setParent(None)
            if hasattr(v, "deleteLater"):
                v.deleteLater()
        except Exception:
            pass
        self._viewer = None

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
        self._update_step_info(step_id)

        location = reg.get("location", "node")
        name = reg.get("name", "")
        unit_base = reg.get("unit")
        if not isinstance(unit_base, str) or not unit_base:
            unit_base = None
        if not isinstance(name, str) or not name:
            return

        try:
            grid, scalar_name, scalars_kwargs, unit_display, is_vector = self._build_grid_with_scalars(
                reg, step_id, warp=bool(self.warp.isChecked())
            )
        except Exception as exc:
            self.probe.setText(str(exc))
            return

        # Render
        self._viewer.clear()
        self._viewer.add_mesh(grid, show_edges=True, cmap="viridis", **scalars_kwargs)
        if unit_display:
            title = f"{scalar_name} [{unit_display}] (step {step_id:06d})"
        elif unit_base:
            title = f"{scalar_name} [{unit_base}] (step {step_id:06d})"
        else:
            title = f"{scalar_name} (step {step_id:06d})"
        self._viewer.add_scalar_bar(title=title)
        self._viewer.reset_camera()
        self._viewer.render()

        # Enable field mode if vector
        self.field_mode.setEnabled(bool(is_vector))

        # Cache last grid for probing
        self._last_grid = grid  # type: ignore[attr-defined]
        self._last_scalar = scalar_name  # type: ignore[attr-defined]
        self._last_pref = scalars_kwargs.get("preference", "point")  # type: ignore[attr-defined]

    def _update_step_info(self, step_id: int) -> None:
        info = self._step_infos.get(int(step_id))
        if not isinstance(info, dict):
            self.step_info.setText(f"global_step_id={step_id:06d}")
            return
        parts = [f"global_step_id={int(step_id):06d}"]
        if "stage_id" in info:
            parts.append(f"stage={info.get('stage_id')}")
        if "stage_step" in info:
            try:
                parts.append(f"stage_step={int(info.get('stage_step'))}")
            except Exception:
                pass
        if "time" in info:
            try:
                parts.append(f"time={float(info.get('time')):.6g}")
            except Exception:
                pass
        self.step_info.setText("  ".join(parts))

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
            self._last_probe_pid = pid
            self._last_probe_xyz = (px, py, pz)
            self._probe_history.append({"x": px, "y": py, "z": pz, "pid": pid})
            self._probe_history = self._probe_history[-10:]
            if self._mode == "profile_pick":
                self._capture_profile_pick_point(px, py, pz)
            node_sets = self._node_set_membership.get(pid, [])
            sets_txt = f" node_sets={node_sets}" if node_sets else ""
            if self._units is not None:
                ux = self._units.convert_base_to_display("length", px)
                uy = self._units.convert_base_to_display("length", py)
                u = self._units.display_unit("length", "") or ""
                suf = f" {u}" if u else ""
                pos_txt = f"x={ux:.6g}{suf}, y={uy:.6g}{suf}"
            else:
                pos_txt = f"x={px:.6g}, y={py:.6g}"
            self.probe.setPlainText(
                f"Probe:\n"
                f"  pid={pid}\n"
                f"  {pos_txt}\n"
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
        self._last_cell_id = int(cell_id)

        try:
            ctype_code = int(grid.cell_data["__cell_type_code"][cell_id])
            local_id = int(grid.cell_data["__cell_local_id"][cell_id])
            ctype = cell_type_code_to_name(ctype_code) or str(ctype_code)
            elem_sets = self._elem_set_membership.get(ctype, {}).get(local_id, [])
            self._last_cell_info = {"cell_id": int(cell_id), "cell_type": str(ctype), "local_id": int(local_id), "elem_sets": list(elem_sets)}
            self.probe.setPlainText(
                "Cell pick:\n"
                f"  cell_id={cell_id}\n"
                f"  type={ctype}\n"
                f"  local_id={local_id}\n"
                f"  elem_sets={elem_sets}"
            )
        except Exception as exc:
            self.probe.setPlainText(f"Cell pick failed: {exc}")

    def _build_grid_with_scalars(
        self,
        reg: dict[str, Any],
        step_id: int,
        *,
        warp: bool,
    ) -> tuple[Any, str, dict[str, Any], str | None, bool]:
        """
        Build a pyvista grid with the selected scalar attached.
        Returns (grid, scalar_name, scalars_kwargs, unit_display_label).
        """
        if self._mesh is None or self._arrays is None:
            raise RuntimeError("Missing mesh/results")

        location = str(reg.get("location", "node"))
        name = str(reg.get("name", ""))
        unit_base = reg.get("unit")
        if not isinstance(unit_base, str) or not unit_base:
            unit_base = None
        if not name:
            raise RuntimeError("Invalid registry entry")

        vtk_mesh = contract_mesh_to_pyvista(self._mesh)
        grid = vtk_mesh.grid.copy()

        arr = get_array_for(arrays=self._arrays, location=location, name=name, step=int(step_id))
        if arr is None:
            raise RuntimeError(f"Missing array for {name} ({location}) step {int(step_id):06d}")

        scalar_name = name
        mode = self.field_mode.currentData()
        arr2 = np.asarray(arr)
        is_vector = bool(arr2.ndim == 2)
        if is_vector and mode in ("auto", "mag"):
            scalar = vector_magnitude(arr)
            scalar_name = f"{name}_mag"
        else:
            scalar = arr2.reshape(-1)

        # Display unit conversion (scale values only; geometry remains in base units)
        unit_display: str | None = None
        if unit_base and self._units is not None:
            from geohpem.units import conversion_factor, infer_kind_from_unit

            kind = infer_kind_from_unit(unit_base)
            if name == "u":
                kind = "length"
            if kind:
                unit_display = self._units.display_unit(kind, unit_base)
                if unit_display and unit_display != unit_base:
                    scalar = scalar.astype(float, copy=False) * conversion_factor(unit_base, unit_display)
        elif name == "u" and self._units is not None:
            ub = self._units.base_unit("length", None)
            ud = self._units.display_unit("length", None)
            if ub and ud and ub != ud:
                from geohpem.units import conversion_factor

                scalar = scalar.astype(float, copy=False) * conversion_factor(ub, ud)
                unit_display = ud

        if location in ("node", "nodal"):
            if scalar.shape[0] != grid.n_points:
                raise RuntimeError(f"Array size mismatch: {scalar.shape[0]} vs n_points {grid.n_points}")
            grid.point_data.clear()
            grid.point_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "point"}
        elif location in ("element", "elem"):
            if scalar.shape[0] != grid.n_cells:
                raise RuntimeError(f"Array size mismatch: {scalar.shape[0]} vs n_cells {grid.n_cells}")
            grid.cell_data.clear()
            grid.cell_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "cell"}
        else:
            raise RuntimeError(f"Unsupported location for plotting: {location}")

        if warp:
            u = get_array_for(arrays=self._arrays, location="node", name="u", step=int(step_id))
            if u is not None and np.asarray(u).ndim == 2 and u.shape[0] == grid.n_points:
                u3 = np.zeros((grid.n_points, 3), dtype=float)
                u3[:, : min(2, u.shape[1])] = np.asarray(u)[:, : min(2, u.shape[1])]
                grid.point_data["u_vec"] = u3
                grid = grid.warp_by_vector("u_vec", factor=float(self.warp_scale.value()))

        return grid, scalar_name, scalars_kwargs, unit_display or unit_base, is_vector

    def _start_profile_pick_mode(self) -> None:
        if self._viewer is None:
            return
        if self._meta is None:
            return
        if self._mode == "profile_pick":
            # Toggle off
            self._mode = "normal"
            self._profile_pick_points = []
            try:
                self.btn_profile_pick.setText("Pick 2 points (viewport)")
            except Exception:
                pass
            self.probe.setPlainText("Profile pick canceled.")
            return
        self._mode = "profile_pick"
        self._profile_pick_points = []
        try:
            self.btn_profile_pick.setText("Cancel pick mode")
        except Exception:
            pass
        self.probe.setPlainText(
            "Profile pick mode:\n"
            "  1) Left-click first point in viewport\n"
            "  2) Left-click second point\n"
            "  -> will create a profile and plot automatically.\n"
            "Tip: click this button again to cancel."
        )

    def _capture_profile_pick_point(self, x: float, y: float, z: float) -> None:
        if self._mode != "profile_pick":
            return
        self._profile_pick_points.append((float(x), float(y), float(z)))
        if len(self._profile_pick_points) == 1:
            self.probe.setPlainText("Profile pick mode: first point set, pick second point...")
            return
        if len(self._profile_pick_points) >= 2:
            p1 = self._profile_pick_points[0]
            p2 = self._profile_pick_points[1]
            self._mode = "normal"
            self._profile_pick_points = []
            try:
                self.btn_profile_pick.setText("Pick 2 points (viewport)")
            except Exception:
                pass
            self._create_profile_from_points(p1, p2)

    def _create_profile_from_points(self, p1: tuple[float, float, float], p2: tuple[float, float, float]) -> None:
        ctx = self._current_field_context()
        if ctx is None:
            self._QMessageBox.information(self.widget, "Profile", "Select a field and render a step first.")
            return
        reg, step_id, scalar_name, _pref, unit_label = ctx

        try:
            grid, scalar_name2, _scalars_kwargs, unit_label2, _is_vec = self._build_grid_with_scalars(reg, step_id, warp=False)
            scalar_name = scalar_name2
            unit_label = unit_label2
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Profile Failed", str(exc))
            return

        try:
            import pyvista as pv  # type: ignore

            sampled = grid.sample_over_line(p1, p2, resolution=200)
            dist = None
            for key in ("Distance", "distance"):
                if key in sampled.point_data:
                    dist = np.asarray(sampled.point_data[key], dtype=float).ravel()
                    break
            if dist is None:
                pts = np.asarray(sampled.points, dtype=float)
                dist = np.sqrt(np.sum((pts[:, :3] - pts[0, :3]) ** 2, axis=1))

            if scalar_name in sampled.point_data:
                vals = np.asarray(sampled.point_data[scalar_name], dtype=float).ravel()
            elif scalar_name in sampled.cell_data:
                vals = np.asarray(sampled.cell_data[scalar_name], dtype=float).ravel()
            else:
                raise RuntimeError(f"Sampled data missing '{scalar_name}'")

            # Overlay line
            try:
                line = pv.Line(p1, p2, resolution=1)
                if self._profile_actor is not None:
                    try:
                        self._viewer.remove_actor(self._profile_actor)
                    except Exception:
                        pass
                self._profile_actor = self._viewer.add_mesh(line, color="red", line_width=3)
                self._viewer.render()
            except Exception:
                pass

            uid = self._new_uid("profile")
            prof = {
                "uid": uid,
                "name": f"profile_{len(self._profiles)+1}",
                "p1": list(p1),
                "p2": list(p2),
                "reg": {"location": reg.get("location"), "name": reg.get("name")},
                "step_id": int(step_id),
                "scalar_name": scalar_name,
                "unit": unit_label,
                "dist": dist,
                "vals": vals,
            }
            self._profiles.append(prof)
            self._refresh_profile_list(select_uid=uid)
            self._plot_profile(prof)
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Profile Failed", str(exc))

    def _refresh_profile_list(self, *, select_uid: str | None = None) -> None:
        self.profile_list.clear()
        for p in self._profiles:
            nm = str(p.get("name", "profile"))
            step_id = int(p.get("step_id", 0))
            reg = p.get("reg", {}) if isinstance(p.get("reg"), dict) else {}
            label = f"{nm}  ({reg.get('name')}@{reg.get('location')} step {step_id:06d})"
            self.profile_list.addItem(label)
        self._on_profile_selection_changed(self.profile_list.currentRow())
        if select_uid:
            for i, p in enumerate(self._profiles):
                if p.get("uid") == select_uid:
                    self.profile_list.setCurrentRow(i)
                    break

    def _on_profile_selection_changed(self, row: int) -> None:
        ok = 0 <= int(row) < len(self._profiles)
        self.btn_profile_plot.setEnabled(bool(ok))
        self.btn_profile_remove.setEnabled(bool(ok))

    def _selected_profile(self) -> dict[str, Any] | None:
        row = int(self.profile_list.currentRow())
        if row < 0 or row >= len(self._profiles):
            return None
        p = self._profiles[row]
        return p if isinstance(p, dict) else None

    def _plot_selected_profile(self) -> None:
        p = self._selected_profile()
        if p is None:
            return
        self._plot_profile(p)

    def _remove_selected_profile(self) -> None:
        row = int(self.profile_list.currentRow())
        if row < 0 or row >= len(self._profiles):
            return
        del self._profiles[row]
        self._refresh_profile_list()

    def _plot_profile(self, prof: dict[str, Any]) -> None:
        # Overlay line for selected profile (best-effort).
        if self._viewer is not None:
            try:
                import pyvista as pv  # type: ignore

                p1 = tuple(float(x) for x in (prof.get("p1") or [0.0, 0.0, 0.0])[:3])
                p2 = tuple(float(x) for x in (prof.get("p2") or [0.0, 0.0, 0.0])[:3])
                line = pv.Line(p1, p2, resolution=1)
                if self._profile_actor is not None:
                    try:
                        self._viewer.remove_actor(self._profile_actor)
                    except Exception:
                        pass
                self._profile_actor = self._viewer.add_mesh(line, color="red", line_width=3)
                self._viewer.render()
            except Exception:
                pass

        from geohpem.gui.dialogs.plot_dialog import PlotDialog, PlotSeries

        dist = np.asarray(prof.get("dist", []), dtype=float).ravel()
        vals = np.asarray(prof.get("vals", []), dtype=float).ravel()
        scalar_name = str(prof.get("scalar_name", "value"))
        unit = prof.get("unit")
        step_id = int(prof.get("step_id", 0))
        title = f"Profile: {scalar_name} (step {step_id:06d})"
        ylabel = scalar_name
        if isinstance(unit, str) and unit:
            ylabel = f"{scalar_name} [{unit}]"

        dlg = PlotDialog(
            self.widget,
            title=title,
            xlabel="Distance",
            ylabel=ylabel,
            series=[PlotSeries(x=dist, y=vals, label=None)],
            default_csv_name=f"profile_{scalar_name}_step{step_id:06d}.csv",
            default_png_name=f"profile_{scalar_name}_step{step_id:06d}.png",
        )
        dlg.exec()

    def _refresh_pin_list(self, *, select_uid: str | None = None) -> None:
        self.pin_list.clear()
        for p in self._pins:
            kind = str(p.get("kind", ""))
            if kind == "node":
                pid = p.get("pid")
                x, y = p.get("x"), p.get("y")
                label = f"{p.get('name','node')}  (pid={pid} x={x:.4g} y={y:.4g})"
            else:
                cid = p.get("cell_id")
                ct = p.get("cell_type", "")
                lid = p.get("local_id")
                label = f"{p.get('name','elem')}  (cell_id={cid} {ct} local_id={lid})"
            self.pin_list.addItem(label)
        self._on_pin_selection_changed(self.pin_list.currentRow())
        if select_uid:
            for i, p in enumerate(self._pins):
                if p.get("uid") == select_uid:
                    self.pin_list.setCurrentRow(i)
                    break

    def _on_pin_selection_changed(self, row: int) -> None:
        ok = 0 <= int(row) < len(self._pins)
        self.btn_pin_remove.setEnabled(bool(ok))

    def _selected_pin(self) -> dict[str, Any] | None:
        row = int(self.pin_list.currentRow())
        if row < 0 or row >= len(self._pins):
            return None
        p = self._pins[row]
        return p if isinstance(p, dict) else None

    def _pin_last_probe(self) -> None:
        if self._last_probe_pid is None or self._last_probe_xyz is None:
            self._QMessageBox.information(self.widget, "Pin", "Probe a point first (left-click).")
            return
        px, py, _pz = self._last_probe_xyz
        uid = self._new_uid("pin")
        pin = {"uid": uid, "kind": "node", "name": f"node_{len([p for p in self._pins if p.get('kind')=='node'])+1}", "pid": int(self._last_probe_pid), "x": float(px), "y": float(py)}
        self._pins.append(pin)
        self._refresh_pin_list(select_uid=uid)

    def _pin_last_cell(self) -> None:
        if self._last_cell_id is None or not isinstance(self._last_cell_info, dict):
            self._QMessageBox.information(self.widget, "Pin", "Pick a cell first (click on mesh).")
            return
        info = dict(self._last_cell_info)
        uid = self._new_uid("pin")
        pin = {"uid": uid, "kind": "element", "name": f"elem_{len([p for p in self._pins if p.get('kind')=='element'])+1}", **info}
        self._pins.append(pin)
        self._refresh_pin_list(select_uid=uid)

    def _remove_selected_pin(self) -> None:
        row = int(self.pin_list.currentRow())
        if row < 0 or row >= len(self._pins):
            return
        del self._pins[row]
        self._refresh_pin_list()

    def _step_time_map(self) -> dict[int, float]:
        """
        Best-effort mapping from global step id -> time (float).
        For fake solver, meta["stages"][*]["times"] exists and steps are sequential.
        """
        if not self._meta:
            return {}
        # Preferred: explicit mapping from meta['global_steps'].
        gs = self._meta.get("global_steps")
        if isinstance(gs, list) and gs:
            out: dict[int, float] = {}
            for it in gs:
                if not isinstance(it, dict):
                    continue
                try:
                    sid = int(it.get("id"))
                    t = float(it.get("time"))
                except Exception:
                    continue
                out[sid] = t
            if out:
                return out
        stages = self._meta.get("stages", [])
        if not isinstance(stages, list) or not stages:
            return {}
        out: dict[int, float] = {}
        step_counter = 0
        for st in stages:
            if not isinstance(st, dict):
                continue
            times = st.get("times", [])
            if not isinstance(times, list):
                continue
            for t in times:
                step_counter += 1
                try:
                    out[int(step_counter)] = float(t)
                except Exception:
                    continue
        return out

    def _current_field_context(self) -> tuple[dict[str, Any], int, str, str, str | None] | None:
        """
        Returns (reg, step_id, scalar_name, preference, unit_label_for_plot).
        """
        reg = self._selected_reg()
        step_id = self._selected_step_id()
        if reg is None or step_id is None:
            return None
        scalar_name = getattr(self, "_last_scalar", None)
        pref = getattr(self, "_last_pref", None)
        if not isinstance(scalar_name, str) or not scalar_name:
            return None
        if not isinstance(pref, str) or not pref:
            return None

        unit_label = self._field_unit_label(reg, str(reg.get("name", "")))
        return reg, int(step_id), str(scalar_name), str(pref), unit_label

    def _field_unit_label(self, reg: dict[str, Any], field_name: str) -> str | None:
        """
        Best-effort unit label consistent with the viewer (display units when configured).
        """
        unit_base = reg.get("unit")
        if not isinstance(unit_base, str) or not unit_base:
            unit_base = None

        # Follow the same convention as _render for displacement.
        if field_name == "u" and self._units is not None:
            ud = self._units.display_unit("length", None)
            return ud or unit_base

        if unit_base and self._units is not None:
            try:
                from geohpem.units import infer_kind_from_unit

                kind = infer_kind_from_unit(unit_base)
                if kind:
                    return self._units.display_unit(kind, unit_base) or unit_base
            except Exception:
                return unit_base
        return unit_base

    def _on_export_image(self) -> None:
        if self._viewer is None:
            return
        from PySide6.QtWidgets import QFileDialog  # type: ignore

        file, _ = QFileDialog.getSaveFileName(self.widget, "Export Image", "view.png", "PNG (*.png);;All Files (*)")
        if not file:
            return
        try:
            v = self._viewer
            # QtInteractor may expose screenshot() directly or via .plotter
            if hasattr(v, "screenshot"):
                v.screenshot(file)  # type: ignore[misc]
            else:
                plotter = getattr(v, "plotter", None)
                if plotter is None or not hasattr(plotter, "screenshot"):
                    raise RuntimeError("Viewer does not support screenshot()")
                plotter.screenshot(file)  # type: ignore[misc]
            self._QMessageBox.information(self.widget, "Export Image", f"Saved:\n{file}")
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Export Image Failed", str(exc))

    def _on_profile_line(self) -> None:
        if self._viewer is None:
            return
        ctx = self._current_field_context()
        if ctx is None:
            self._QMessageBox.information(self.widget, "Profile Line", "Select a field and render a step first.")
            return
        reg, step_id, scalar_name, pref, unit_label = ctx
        grid = getattr(self, "_last_grid", None)
        if grid is None:
            return

        from PySide6.QtWidgets import (  # type: ignore
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QSpinBox,
            QVBoxLayout,
            QWidget,
        )

        dialog = QDialog(self.widget)
        dialog.setWindowTitle("Profile Line")
        dialog.resize(520, 260)
        layout = QVBoxLayout(dialog)

        note = QLabel("Tip: use two point picks (left-click) then 'Use last two picks'.")
        layout.addWidget(note)

        form = QFormLayout()
        layout.addLayout(form)

        def spin() -> Any:
            s = self._QDoubleSpinBox()
            s.setDecimals(6)
            s.setRange(-1e12, 1e12)
            s.setSingleStep(0.1)
            return s

        x1 = spin()
        y1 = spin()
        x2 = spin()
        y2 = spin()
        form.addRow("x1", x1)
        form.addRow("y1", y1)
        form.addRow("x2", x2)
        form.addRow("y2", y2)

        samples = QSpinBox()
        samples.setRange(2, 5000)
        samples.setValue(200)
        form.addRow("samples", samples)

        chk_overlay = QCheckBox("Show line overlay in viewport")
        chk_overlay.setChecked(True)
        form.addRow("", chk_overlay)

        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        btn_last2 = QPushButton("Use last two picks")
        bl.addWidget(btn_last2)
        bl.addStretch(1)
        layout.addWidget(btn_row)

        def apply_last2() -> None:
            if len(self._probe_history) < 2:
                return
            a = self._probe_history[-2]
            b = self._probe_history[-1]
            x1.setValue(float(a.get("x", 0.0)))
            y1.setValue(float(a.get("y", 0.0)))
            x2.setValue(float(b.get("x", 0.0)))
            y2.setValue(float(b.get("y", 0.0)))

        btn_last2.clicked.connect(apply_last2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return

        p1 = (float(x1.value()), float(y1.value()), 0.0)
        p2 = (float(x2.value()), float(y2.value()), 0.0)
        n = int(samples.value())

        try:
            import pyvista as pv  # type: ignore

            sampled = grid.sample_over_line(p1, p2, resolution=max(n - 1, 1))
            # VTK usually provides 'Distance' array for sample_over_line
            dist = None
            for key in ("Distance", "distance"):
                if key in sampled.point_data:
                    dist = np.asarray(sampled.point_data[key], dtype=float).ravel()
                    break
            if dist is None:
                pts = np.asarray(sampled.points, dtype=float)
                dist = np.zeros((pts.shape[0],), dtype=float)
                if pts.shape[0] > 1:
                    d = np.sqrt(np.sum((pts[:, :3] - pts[0, :3]) ** 2, axis=1))
                    dist = d

            if scalar_name in sampled.point_data:
                vals = np.asarray(sampled.point_data[scalar_name], dtype=float).ravel()
            elif scalar_name in sampled.cell_data:
                vals = np.asarray(sampled.cell_data[scalar_name], dtype=float).ravel()
            else:
                raise RuntimeError(f"Sampled data missing '{scalar_name}'")

            if chk_overlay.isChecked():
                line = pv.Line(p1, p2, resolution=1)
                try:
                    if hasattr(self, "_profile_actor") and getattr(self, "_profile_actor") is not None:
                        try:
                            self._viewer.remove_actor(getattr(self, "_profile_actor"))
                        except Exception:
                            pass
                    actor = self._viewer.add_mesh(line, color="red", line_width=3)
                    self._profile_actor = actor
                    self._viewer.render()
                except Exception:
                    pass

            # Plot
            from geohpem.gui.dialogs.plot_dialog import PlotDialog, PlotSeries

            ylabel = scalar_name
            if unit_label:
                ylabel = f"{scalar_name} [{unit_label}]"
            dlg = PlotDialog(
                self.widget,
                title=f"Profile: {scalar_name} (step {step_id:06d})",
                xlabel="Distance",
                ylabel=ylabel,
                series=[PlotSeries(x=dist, y=vals, label=None)],
                default_csv_name=f"profile_{scalar_name}_step{step_id:06d}.csv",
                default_png_name=f"profile_{scalar_name}_step{step_id:06d}.png",
            )
            dlg.exec()
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Profile Line Failed", str(exc))

    def _on_time_history(self) -> None:
        if self._mesh is None or self._arrays is None:
            return
        reg = self._selected_reg()
        if reg is None:
            self._QMessageBox.information(self.widget, "Time History", "Select a field first.")
            return

        location = str(reg.get("location", "node"))
        name = str(reg.get("name", ""))
        if not name:
            return

        # Select source (last pick vs pinned)
        src = self._select_history_source(location=location)
        if src is None:
            return

        # Choose index for sampling
        if location in ("node", "nodal"):
            pid = int(src["pid"])
        elif location in ("element", "elem"):
            cid = int(src["cell_id"])
        else:
            self._QMessageBox.information(self.widget, "Time History", f"Unsupported location: {location}")
            return

        # Build time axis (best-effort)
        time_map = self._step_time_map()
        xs: list[float] = []
        ys: list[float] = []

        unit_label = self._field_unit_label(reg, name)

        for step_id in self._steps:
            arr = get_array_for(arrays=self._arrays, location=location, name=name, step=step_id)
            if arr is None:
                continue
            mode = self.field_mode.currentData()
            if np.asarray(arr).ndim == 2 and mode in ("auto", "mag"):
                scalar = vector_magnitude(arr)
                scalar_name = f"{name}_mag"
            else:
                scalar = np.asarray(arr).reshape(-1)
                scalar_name = name

            # unit conversion consistent with viewer
            if unit_label and self._units is not None:
                # If reg provides base unit, try convert to display.
                base = reg.get("unit") if isinstance(reg.get("unit"), str) else None
                if isinstance(base, str) and base and base != unit_label:
                    try:
                        from geohpem.units import conversion_factor

                        scalar = scalar.astype(float, copy=False) * conversion_factor(base, unit_label)
                    except Exception:
                        pass

            try:
                if location in ("node", "nodal"):
                    v = float(np.asarray(scalar)[int(pid)])  # type: ignore[arg-type]
                else:
                    v = float(np.asarray(scalar)[int(cid)])  # type: ignore[arg-type]
            except Exception:
                continue

            xs.append(float(time_map.get(int(step_id), float(step_id))))
            ys.append(v)

        if not xs:
            self._QMessageBox.information(self.widget, "Time History", "No data available for this field.")
            return

        from geohpem.gui.dialogs.plot_dialog import PlotDialog, PlotSeries

        xlabel = "Time" if any(k in time_map for k in self._steps) else "Step"
        ylabel = scalar_name
        if unit_label:
            ylabel = f"{scalar_name} [{unit_label}]"
        dlg = PlotDialog(
            self.widget,
            title=f"Time history: {scalar_name}",
            xlabel=xlabel,
            ylabel=ylabel,
            series=[PlotSeries(x=np.asarray(xs, dtype=float), y=np.asarray(ys, dtype=float), label=None)],
            default_csv_name=f"history_{scalar_name}.csv",
            default_png_name=f"history_{scalar_name}.png",
        )
        dlg.exec()

    def _select_history_source(self, *, location: str) -> dict[str, Any] | None:
        """
        Pick a source for time history:
        - node: last probe pid or pinned node
        - element: last cell pick or pinned element
        """
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QLabel,
            QRadioButton,
            QVBoxLayout,
        )

        want = "node" if location in ("node", "nodal") else "element"

        dlg = QDialog(self.widget)
        dlg.setWindowTitle("Time History Source")
        dlg.resize(520, 220)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(f"Field location: {want}"))

        rb_last = QRadioButton("Use last picked")
        rb_pin = QRadioButton("Use pinned")
        rb_last.setChecked(True)
        layout.addWidget(rb_last)
        layout.addWidget(rb_pin)

        form = QFormLayout()
        layout.addLayout(form)
        combo = QComboBox()
        form.addRow("Pinned", combo)

        pins = [p for p in self._pins if isinstance(p, dict) and p.get("kind") == want]
        for p in pins:
            if want == "node":
                combo.addItem(f"{p.get('name')} (pid={p.get('pid')})", p.get("uid"))
            else:
                combo.addItem(f"{p.get('name')} (cell_id={p.get('cell_id')} {p.get('cell_type')})", p.get("uid"))
        combo.setEnabled(False)

        def sync() -> None:
            combo.setEnabled(bool(rb_pin.isChecked()))

        rb_last.toggled.connect(sync)
        rb_pin.toggled.connect(sync)
        sync()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() != QDialog.Accepted:
            return None

        if rb_last.isChecked():
            if want == "node":
                if self._last_probe_pid is None:
                    self._QMessageBox.information(self.widget, "Time History", "Probe a point first (left-click) or pin one.")
                    return None
                return {"kind": "node", "pid": int(self._last_probe_pid)}
            if self._last_cell_id is None:
                self._QMessageBox.information(self.widget, "Time History", "Pick a cell first or pin one.")
                return None
            return {"kind": "element", "cell_id": int(self._last_cell_id)}

        if not pins:
            self._QMessageBox.information(self.widget, "Time History", "No pinned items available.")
            return None

        uid = combo.currentData()
        for p in pins:
            if p.get("uid") == uid:
                return dict(p)
        return dict(pins[0])
