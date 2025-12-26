from __future__ import annotations

from pathlib import Path
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
        from PySide6.QtCore import QObject, Qt, Signal  # type: ignore
        from PySide6.QtGui import QCursor, QKeySequence, QShortcut  # type: ignore
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
            QCheckBox,
            QComboBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMenu,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QSpinBox,
            QSplitter,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )  # type: ignore
        from geohpem.util.ids import new_uid

        class _Signals(QObject):
            ui_state_changed = Signal()

        self._signals = _Signals()
        self.ui_state_changed = self._signals.ui_state_changed

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QDoubleSpinBox = QDoubleSpinBox
        self._QMenu = QMenu
        self._QCursor = QCursor
        self._new_uid = new_uid
        self._is_2d_view = True
        self._color_range_cache: dict[tuple[str, str, str, str], tuple[float, float]] = {}

        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)

        status = QWidget()
        sl = QHBoxLayout(status)
        sl.setContentsMargins(10, 6, 10, 6)
        self._lbl_output = QLabel("Output: (none)")
        self._lbl_output.setStyleSheet("font-weight: 600;")
        self._lbl_solver = QLabel("Solver: -")
        self._lbl_solver.setStyleSheet("color: #4b5563;")
        self._lbl_field = QLabel("Field: -")
        self._lbl_step = QLabel("Step: -")
        sl.addWidget(self._lbl_output)
        sl.addWidget(self._lbl_solver)
        sl.addWidget(self._lbl_field)
        sl.addWidget(self._lbl_step)
        sl.addStretch(1)
        layout.addWidget(status, 0)

        # Shortcuts (Output workspace scope)
        try:
            self._sc_esc = QShortcut(QKeySequence("Esc"), self.widget)
            self._sc_esc.activated.connect(self._cancel_active_mode)
        except Exception:
            self._sc_esc = None

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        # Left panel: controls
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left.setMinimumWidth(320)

        # --- Field panel (always visible) ---
        gb_field = QGroupBox("Field")
        fld = QVBoxLayout(gb_field)

        self.registry_list = QListWidget()
        fld.addWidget(QLabel("Registry"))
        fld.addWidget(self.registry_list, 1)

        step_row = QWidget()
        step_rl = QHBoxLayout(step_row)
        step_rl.setContentsMargins(0, 0, 0, 0)
        step_rl.addWidget(QLabel("Step"))
        self.step = QSpinBox()
        self.step.setRange(0, 0)
        self.step.setEnabled(False)
        step_rl.addWidget(self.step, 1)
        fld.addWidget(step_row)

        self.step_info = QLabel("")
        self.step_info.setWordWrap(True)
        fld.addWidget(self.step_info)

        fm_row = QWidget()
        fm_rl = QHBoxLayout(fm_row)
        fm_rl.setContentsMargins(0, 0, 0, 0)
        fm_rl.addWidget(QLabel("Field mode"))
        self.field_mode = QComboBox()
        self.field_mode.addItem("Auto", "auto")
        self.field_mode.addItem("Magnitude (vector)", "mag")
        self.field_mode.setEnabled(False)
        fm_rl.addWidget(self.field_mode, 1)
        fld.addWidget(fm_row)

        cr_row = QWidget()
        cr_rl = QHBoxLayout(cr_row)
        cr_rl.setContentsMargins(0, 0, 0, 0)
        cr_rl.addWidget(QLabel("Color range"))
        self.color_range = QComboBox()
        self.color_range.addItem("Auto (per step)", "auto")
        self.color_range.addItem("Global (fixed)", "global")
        self.color_range.addItem("Manual", "manual")
        try:
            self.color_range.setCurrentIndex(int(self.color_range.findData("global")))
        except Exception:
            pass
        cr_rl.addWidget(self.color_range, 1)
        fld.addWidget(cr_row)

        manual_row = QWidget()
        mr = QHBoxLayout(manual_row)
        mr.setContentsMargins(0, 0, 0, 0)
        self.color_min = QLineEdit()
        self.color_min.setPlaceholderText("min (e.g. 0, -1e5)")
        self.color_max = QLineEdit()
        self.color_max.setPlaceholderText("max (e.g. 1e5)")
        mr.addWidget(QLabel("min"))
        mr.addWidget(self.color_min, 1)
        mr.addWidget(QLabel("max"))
        mr.addWidget(self.color_max, 1)
        fld.addWidget(manual_row)

        self.color_range_info = QLabel("")
        self.color_range_info.setWordWrap(True)
        fld.addWidget(self.color_range_info)

        self.warp = QCheckBox("Warp by displacement u")
        self.warp.setEnabled(False)
        fld.addWidget(self.warp)

        ws_row = QWidget()
        ws_rl = QHBoxLayout(ws_row)
        ws_rl.setContentsMargins(0, 0, 0, 0)
        ws_rl.addWidget(QLabel("Warp scale"))
        self.warp_scale = QSpinBox()
        self.warp_scale.setRange(0, 1_000_000)
        self.warp_scale.setValue(100)
        self.warp_scale.setEnabled(False)
        ws_rl.addWidget(self.warp_scale, 1)
        fld.addWidget(ws_row)

        actions_row = QWidget()
        ar = QHBoxLayout(actions_row)
        ar.setContentsMargins(0, 0, 0, 0)
        self.btn_reset = QPushButton("Reset view")
        self.btn_reset.setEnabled(False)
        self.btn_export_img = QPushButton("Export image...")
        self.btn_export_img.setEnabled(False)
        ar.addWidget(self.btn_reset)
        ar.addWidget(self.btn_export_img)
        fld.addWidget(actions_row)

        self.btn_export_steps = QPushButton("Export steps -> PNG...")
        self.btn_export_steps.setEnabled(False)
        fld.addWidget(self.btn_export_steps)

        left_layout.addWidget(gb_field, 3)

        gb_probe = QGroupBox("Probe")
        probe_layout = QVBoxLayout(gb_probe)
        probe_layout.setContentsMargins(6, 6, 6, 6)
        self.probe = QPlainTextEdit()
        self.probe.setReadOnly(True)
        self.probe.setMinimumHeight(90)
        self.probe.setPlainText("Probe: left-click in the viewport to read value.")
        probe_layout.addWidget(self.probe, 1)
        left_layout.addWidget(gb_probe, 1)

        # --- Tools panel (profiles/pins) ---
        tabs = QTabWidget()
        self._tabs = tabs
        self._tab_profiles = 0
        self._tab_pins = 1

        # Profiles tab
        tab_profiles = QWidget()
        pl = QVBoxLayout(tab_profiles)
        self.btn_profile = QPushButton("Profile line...")
        self.btn_profile.setEnabled(False)
        self.btn_profile_pick = QPushButton("Pick 2 points (viewport)")
        self.btn_profile_pick.setEnabled(False)
        top_p = QWidget()
        top_pl = QHBoxLayout(top_p)
        top_pl.setContentsMargins(0, 0, 0, 0)
        top_pl.addWidget(self.btn_profile, 1)
        top_pl.addWidget(self.btn_profile_pick, 1)
        pl.addWidget(top_p)

        self.profile_list = QListWidget()
        self.profile_list.setEnabled(False)
        pl.addWidget(self.profile_list, 1)

        row_prof_actions = QWidget()
        rpa = QHBoxLayout(row_prof_actions)
        rpa.setContentsMargins(0, 0, 0, 0)
        self.btn_profile_plot = QPushButton("Plot")
        self.btn_profile_plot.setEnabled(False)
        self.btn_profile_edit = QPushButton("Edit (drag)")
        self.btn_profile_edit.setEnabled(False)
        self.btn_profile_remove = QPushButton("Remove")
        self.btn_profile_remove.setEnabled(False)
        rpa.addWidget(self.btn_profile_plot)
        rpa.addWidget(self.btn_profile_edit)
        rpa.addWidget(self.btn_profile_remove)
        pl.addWidget(row_prof_actions)

        row_prof_edit = QWidget()
        rpe = QHBoxLayout(row_prof_edit)
        rpe.setContentsMargins(0, 0, 0, 0)
        self.btn_profile_edit_finish = QPushButton("Finish edit")
        self.btn_profile_edit_finish.setEnabled(False)
        self.btn_profile_edit_cancel = QPushButton("Cancel edit")
        self.btn_profile_edit_cancel.setEnabled(False)
        rpe.addWidget(self.btn_profile_edit_finish)
        rpe.addWidget(self.btn_profile_edit_cancel)
        pl.addWidget(row_prof_edit)

        tabs.addTab(tab_profiles, "Profiles")

        # Pins tab
        tab_pins = QWidget()
        pil = QVBoxLayout(tab_pins)

        row_pin_top = QWidget()
        rpt = QHBoxLayout(row_pin_top)
        rpt.setContentsMargins(0, 0, 0, 0)
        self.btn_history = QPushButton("Time history...")
        self.btn_history.setEnabled(False)
        pil.addWidget(self.btn_history)

        self.btn_pin_node = QPushButton("Pin last probe (node)")
        self.btn_pin_node.setEnabled(False)
        self.btn_pin_elem = QPushButton("Pin last cell (element)")
        self.btn_pin_elem.setEnabled(False)
        rpt.addWidget(self.btn_pin_node)
        rpt.addWidget(self.btn_pin_elem)
        pil.addWidget(row_pin_top)

        self.pin_list = QListWidget()
        self.pin_list.setEnabled(False)
        pil.addWidget(self.pin_list, 1)

        self.btn_pin_remove = QPushButton("Remove pin")
        self.btn_pin_remove.setEnabled(False)
        pil.addWidget(self.btn_pin_remove)

        tabs.addTab(tab_pins, "Pins")

        left_layout.addWidget(tabs, 2)

        splitter.addWidget(left)

        # Right panel: viewer
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

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
        self._source_path: Path | None = None
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
        self.field_mode.currentIndexChanged.connect(self._clear_color_cache)
        self.color_range.currentIndexChanged.connect(self._on_color_range_changed)
        self.color_min.editingFinished.connect(self._render)
        self.color_max.editingFinished.connect(self._render)
        self.warp.stateChanged.connect(self._render)
        self.warp_scale.valueChanged.connect(self._render)
        self.btn_reset.clicked.connect(self._reset_view)
        self.btn_profile.clicked.connect(self._on_profile_line)
        self.btn_history.clicked.connect(self._on_time_history)
        self.btn_export_img.clicked.connect(self._on_export_image)
        self.btn_export_steps.clicked.connect(self._on_export_steps_png)
        self.btn_profile_pick.clicked.connect(self._start_profile_pick_mode)
        self.btn_profile_plot.clicked.connect(self._plot_selected_profile)
        self.btn_profile_remove.clicked.connect(self._remove_selected_profile)
        self.btn_profile_edit.clicked.connect(self._start_profile_edit)
        self.btn_profile_edit_finish.clicked.connect(self._finish_profile_edit)
        self.btn_profile_edit_cancel.clicked.connect(self._cancel_profile_edit)
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
        self._profile_widget = None
        self._profile_edit_backup: dict[str, Any] | None = None
        self._pins: list[dict[str, Any]] = []
        self._ui_state: dict[str, Any] | None = None
        self._on_color_range_changed()
        self._refresh_status()

    def set_unit_context(self, units) -> None:  # noqa: ANN001
        """
        Set a UnitContext for display conversion (cloud map / probe readout).
        """
        self._units = units
        self._clear_color_cache()
        self._render()

    def set_source_path(self, path: Path | None) -> None:
        self._source_path = path
        self._refresh_status()

    def set_result(self, meta: dict[str, Any], arrays: dict[str, Any], mesh: dict[str, Any] | None = None) -> None:
        self._meta = meta
        self._arrays = arrays
        self._mesh = mesh
        self._clear_color_cache()
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
        self.btn_export_steps.setEnabled(True)
        self.profile_list.setEnabled(True)
        self.btn_profile_pick.setEnabled(True)
        self._refresh_profile_list()
        self.pin_list.setEnabled(True)
        self.btn_pin_node.setEnabled(True)
        self.btn_pin_elem.setEnabled(True)
        self._refresh_pin_list()
        self._apply_ui_state_if_ready()
        self._refresh_status()

    def _clear_color_cache(self) -> None:
        try:
            self._color_range_cache.clear()
        except Exception:
            pass

    def _on_color_range_changed(self) -> None:
        mode = str(self.color_range.currentData())
        is_manual = mode == "manual"
        try:
            self.color_min.setEnabled(bool(is_manual))
            self.color_max.setEnabled(bool(is_manual))
        except Exception:
            pass
        if mode == "global":
            self.color_range_info.setText("Global range is computed from all available steps (may take a moment).")
        elif mode == "manual":
            self.color_range_info.setText("Manual range uses min/max above (values are in display units).")
        else:
            self.color_range_info.setText("")
        self._render()

    def _refresh_status(self) -> None:
        label = "(none)"
        if isinstance(self._source_path, Path):
            label = self._source_path.name or str(self._source_path)
            try:
                self._lbl_output.setToolTip(str(self._source_path))
            except Exception:
                pass
        self._lbl_output.setText(f"Output: {label}")

        solver = "-"
        if isinstance(self._meta, dict):
            solver_info = self._meta.get("solver_info", {})
            if isinstance(solver_info, dict):
                solver = str(solver_info.get("name") or solver_info.get("id") or solver or "-")
        self._lbl_solver.setText(f"Solver: {solver}")

        field = "-"
        try:
            idx = int(self.registry_list.currentRow())
        except Exception:
            idx = -1
        if 0 <= idx < len(self._reg_items):
            reg = self._reg_items[idx]
            name = str(reg.get("name", "-"))
            loc = str(reg.get("location", ""))
            field = f"{name} ({loc})" if loc else name
        self._lbl_field.setText(f"Field: {field}")

        step_label = "-"
        try:
            if self._steps:
                idx = int(self.step.value())
                if 0 <= idx < len(self._steps):
                    step_label = str(int(self._steps[idx]))
        except Exception:
            pass
        self._lbl_step.setText(f"Step: {step_label}")

    def _parse_float(self, text: str) -> float | None:
        s = str(text or "").strip()
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None

    def _manual_clim(self) -> tuple[float, float] | None:
        a = self._parse_float(self.color_min.text())
        b = self._parse_float(self.color_max.text())
        if a is None or b is None:
            return None
        if not np.isfinite(a) or not np.isfinite(b):
            return None
        if a == b:
            return None
        lo, hi = (a, b) if a < b else (b, a)
        return (float(lo), float(hi))

    def _scalar_for_reg_step(self, reg: dict[str, Any], step_id: int) -> tuple[np.ndarray, str, str | None]:
        """
        Return (scalar_values_1d, scalar_name, unit_display_label) for the current field_mode.
        Uses the same unit conversion logic as rendering.
        """
        if self._arrays is None:
            raise RuntimeError("Missing arrays")
        location = str(reg.get("location", "node"))
        name = str(reg.get("name", ""))
        unit_base = reg.get("unit")
        if not isinstance(unit_base, str) or not unit_base:
            unit_base = None
        if not name:
            raise RuntimeError("Invalid registry entry")

        arr = get_array_for(arrays=self._arrays, location=location, name=name, step=int(step_id))
        if arr is None:
            raise RuntimeError(f"Missing array for {name} ({location}) step {int(step_id):06d}")

        scalar_name = name
        mode = self.field_mode.currentData()
        arr2 = np.asarray(arr)
        is_vector = bool(arr2.ndim == 2)
        if is_vector and mode in ("auto", "mag"):
            scalar = vector_magnitude(arr2)
            scalar_name = f"{name}_mag"
        else:
            scalar = arr2.reshape(-1)

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

        return np.asarray(scalar, dtype=float).reshape(-1), scalar_name, unit_display

    def _global_clim(self, reg: dict[str, Any]) -> tuple[float, float] | None:
        if not self._steps:
            return None
        name = str(reg.get("name", ""))
        loc = str(reg.get("location", ""))
        mode = str(self.field_mode.currentData() or "auto")
        unit = ""
        try:
            _scalar, _sname, unit = self._scalar_for_reg_step(reg, int(self._steps[-1]))
        except Exception:
            unit = ""
        key = (loc, name, mode, unit or "")
        if key in self._color_range_cache:
            return self._color_range_cache[key]

        vmin: float | None = None
        vmax: float | None = None
        for sid in self._steps:
            try:
                s, _sname, _unit = self._scalar_for_reg_step(reg, int(sid))
            except Exception:
                continue
            s = np.asarray(s, dtype=float).reshape(-1)
            mask = np.isfinite(s)
            if not np.any(mask):
                continue
            lo = float(np.min(s[mask]))
            hi = float(np.max(s[mask]))
            vmin = lo if vmin is None else min(vmin, lo)
            vmax = hi if vmax is None else max(vmax, hi)

        if vmin is None or vmax is None or vmin == vmax:
            return None
        self._color_range_cache[key] = (float(vmin), float(vmax))
        try:
            suf = f" {unit}" if unit else ""
            self.color_range_info.setText(f"Global range: {vmin:.6g}{suf} .. {vmax:.6g}{suf}")
        except Exception:
            pass
        return self._color_range_cache[key]

    def _get_color_clim(self, reg: dict[str, Any]) -> tuple[float, float] | None:
        mode = str(self.color_range.currentData())
        if mode == "manual":
            clim = self._manual_clim()
            if clim is None:
                try:
                    self.color_range_info.setText("Manual range: invalid min/max (leave blank to use Auto).")
                except Exception:
                    pass
            return clim
        if mode == "global":
            return self._global_clim(reg)
        return None

    def set_ui_state(self, ui_state: dict[str, Any]) -> None:
        """
        Load per-project UI state (profiles/pins/view preferences) into this workspace.
        Safe to call before/after set_result().
        """
        self._ui_state = ui_state if isinstance(ui_state, dict) else {}
        self._apply_ui_state_if_ready()

    def get_ui_state(self) -> dict[str, Any]:
        """
        Return a JSON-serializable UI state dict to be persisted in ProjectData.ui_state.
        """
        def _clean_profile(p: dict[str, Any]) -> dict[str, Any]:
            out: dict[str, Any] = {}
            for k in ("uid", "name", "p1", "p2", "reg", "step_id"):
                if k in p:
                    out[k] = p[k]
            return out

        def _clean_pin(pin: dict[str, Any]) -> dict[str, Any]:
            out: dict[str, Any] = {}
            for k in ("uid", "kind", "name", "pid", "x", "y", "cell_id", "cell_type", "local_id", "label"):
                if k in pin:
                    out[k] = pin[k]
            return out

        return {
            "output": {
                "profiles": [_clean_profile(p) for p in self._profiles if isinstance(p, dict)],
                "pins": [_clean_pin(p) for p in self._pins if isinstance(p, dict)],
            }
        }

    def _apply_ui_state_if_ready(self) -> None:
        """
        Apply cached ui_state to widgets; best-effort.
        """
        if self._ui_state is None:
            return
        out = self._ui_state.get("output") if isinstance(self._ui_state, dict) else None
        if not isinstance(out, dict):
            return
        profs = out.get("profiles")
        pins = out.get("pins")
        if isinstance(profs, list):
            self._profiles = [p for p in profs if isinstance(p, dict)]
            try:
                # Ensure uids exist
                for p in self._profiles:
                    if not p.get("uid"):
                        p["uid"] = self._new_uid("profile")
            except Exception:
                pass
            self._refresh_profile_list()
        if isinstance(pins, list):
            self._pins = [p for p in pins if isinstance(p, dict)]
            try:
                for p in self._pins:
                    if not p.get("uid"):
                        p["uid"] = self._new_uid("pin")
                    # Back-fill name/x/y for older ui_state.
                    kind = str(p.get("kind", ""))
                    if kind == "node":
                        if not p.get("name"):
                            p["name"] = f"node_{len([pp for pp in self._pins if isinstance(pp, dict) and pp.get('kind')=='node'])}"
                        if (p.get("x") is None or p.get("y") is None) and self._mesh is not None:
                            try:
                                pid = int(p.get("pid"))
                                pts = np.asarray(self._mesh.get("points"), dtype=float)
                                if 0 <= pid < pts.shape[0]:
                                    p["x"] = float(pts[pid, 0])
                                    p["y"] = float(pts[pid, 1])
                            except Exception:
                                pass
                    elif kind == "element":
                        if not p.get("name"):
                            p["name"] = f"elem_{len([pp for pp in self._pins if isinstance(pp, dict) and pp.get('kind')=='element'])}"
            except Exception:
                pass
            self._refresh_pin_list()
        # Re-render overlays if we already have a view.
        try:
            self._render()
        except Exception:
            pass

    def _infer_steps(self, meta: dict[str, Any], arrays: dict[str, Any]) -> tuple[list[int], dict[int, dict[str, Any]]]:
        """
        Prefer meta['frames'] when available (PFEM/HPEM), otherwise meta['global_steps'],
        otherwise fall back to parsing array keys.
        Returns (sorted_step_ids, step_info_by_id).
        """
        infos: dict[int, dict[str, Any]] = {}
        frames = meta.get("frames")
        if isinstance(frames, list) and frames:
            step_ids: list[int] = []
            for it in frames:
                if not isinstance(it, dict):
                    continue
                sid = it.get("id")
                try:
                    sid_i = int(sid)
                except Exception:
                    continue
                step_ids.append(sid_i)
                info = dict(it)
                info["_kind"] = "frame"
                infos[sid_i] = info
            step_ids = sorted(set(step_ids))
            if step_ids:
                return step_ids, infos
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
        self._apply_2d_view()
        # Prefer Qt's context menu signal over VTK right-click callbacks (more reliable across versions).
        try:
            self._viewer.setContextMenuPolicy(self._Qt.ContextMenuPolicy.CustomContextMenu)
            self._viewer.customContextMenuRequested.connect(self._on_viewer_context_menu_requested)
        except Exception:
            pass

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
        # Element picking: support Shift+LeftClick for cell selection (avoids conflict with node probe).
        self._install_shift_cell_picker()
        # Some picking helpers may reset the interactor style; enforce our 2D interaction again.
        self._apply_2d_view()
        self._viewer.set_background("white")
        self.btn_reset.setEnabled(True)
        self.btn_export_img.setEnabled(True)

    def _install_shift_cell_picker(self) -> None:
        """
        Install a VTK observer to pick cells on Shift+LeftClick.

        This works reliably even when point-picking is enabled on LeftClick.
        """
        if getattr(self, "_shift_cell_pick_installed", False) and getattr(self, "_qt_shift_cell_pick_installed", False):
            return
        v = self._viewer
        if v is None:
            return
        try:
            iren = getattr(v, "iren", None)
            vtk_iren = getattr(iren, "interactor", iren)
        except Exception:
            return
        if vtk_iren is None or not hasattr(vtk_iren, "AddObserver"):
            return
        try:
            import vtk  # type: ignore

            self._vtk_cell_picker = vtk.vtkCellPicker()  # type: ignore[attr-defined]
            try:
                # Slightly larger tolerance makes picking usable when zoomed out.
                self._vtk_cell_picker.SetTolerance(0.02)  # type: ignore[misc]
            except Exception:
                pass
        except Exception:
            return

        def on_left_press(obj, _evt):  # noqa: ANN001
            # Only when Shift is pressed, and not in profile-pick/edit modes.
            try:
                if getattr(self, "_mode", "normal") != "normal":
                    return
                if int(getattr(obj, "GetShiftKey")()) != 1:
                    return
            except Exception:
                return
            grid = getattr(self, "_last_grid", None)
            if grid is None or self._viewer is None:
                return
            try:
                x, y = obj.GetEventPosition()
            except Exception:
                return
            try:
                ren = None
                # Prefer VTK poked renderer if available.
                try:
                    if hasattr(obj, "FindPokedRenderer"):
                        ren = obj.FindPokedRenderer(int(x), int(y))  # type: ignore[misc]
                except Exception:
                    ren = None
                # Fall back to PyVista helper (requires style._parent compatibility).
                if ren is None:
                    try:
                        ren = self._viewer.iren.get_poked_renderer()  # type: ignore[attr-defined]
                    except Exception:
                        ren = None
                if ren is None:
                    rw = obj.GetRenderWindow()
                    rens = rw.GetRenderers() if rw is not None else None
                    ren = rens.GetFirstRenderer() if rens is not None else None
                if ren is None:
                    return

                # Restrict picker to the mesh actor when possible (avoids scalarbar/overlays).
                try:
                    act = getattr(self, "_mesh_actor", None)
                    if act is not None and hasattr(self._vtk_cell_picker, "PickFromListOn"):
                        self._vtk_cell_picker.PickFromListOn()  # type: ignore[misc]
                        if hasattr(self._vtk_cell_picker, "InitializePickList"):
                            self._vtk_cell_picker.InitializePickList()  # type: ignore[misc]
                        if hasattr(self._vtk_cell_picker, "AddPickList"):
                            self._vtk_cell_picker.AddPickList(act)  # type: ignore[misc]
                except Exception:
                    pass
                self._vtk_cell_picker.Pick(float(x), float(y), 0.0, ren)  # type: ignore[misc]
                cid = int(self._vtk_cell_picker.GetCellId())  # type: ignore[misc]
                if cid < 0:
                    # Fallback: map pick position to closest cell.
                    try:
                        pos = self._vtk_cell_picker.GetPickPosition()  # type: ignore[misc]
                        if hasattr(grid, "find_closest_cell"):
                            cid = int(grid.find_closest_cell(pos))  # type: ignore[misc]
                    except Exception:
                        cid = -1
                if cid >= 0:
                    self._on_cell_pick((int(cid),), {})
            except Exception:
                return

        if not getattr(self, "_shift_cell_pick_installed", False):
            try:
                # Use high priority to run before other LeftButtonPress observers.
                vtk_iren.AddObserver("LeftButtonPressEvent", on_left_press, 1.0)  # type: ignore[misc]
                self._shift_cell_pick_installed = True
            except Exception:
                # Even if VTK observer fails, try Qt-level fallback below.
                pass

        # Qt-level fallback (more reliable modifier detection in some setups)
        if getattr(self, "_qt_shift_cell_pick_installed", False):
            return
        try:
            from PySide6.QtCore import QObject, QEvent  # type: ignore

            outer = self

            class _ShiftPickFilter(QObject):
                def eventFilter(self, _obj, event):  # noqa: ANN001,N802
                    try:
                        if event.type() != QEvent.MouseButtonPress:
                            return False
                        if int(event.button()) != int(outer._Qt.LeftButton):
                            return False
                        if int(event.modifiers()) & int(outer._Qt.ShiftModifier) == 0:
                            return False
                        if getattr(outer, "_mode", "normal") != "normal":
                            return False
                        # Qt uses top-left origin; VTK often uses bottom-left. Try both.
                        try:
                            pos = event.position()
                            xq = float(pos.x())
                            yq = float(pos.y())
                        except Exception:
                            p = event.pos()
                            xq = float(p.x())
                            yq = float(p.y())
                        outer._pick_cell_from_display_pos(xq, yq)
                        return True  # consume: avoid node probe on Shift-click
                    except Exception:
                        return False

            self._qt_shift_pick_filter = _ShiftPickFilter(self.widget)
            iren_w = getattr(self._viewer, "iren", None)
            iren_widget = getattr(iren_w, "interactor", iren_w)
            qt_target = iren_w if hasattr(iren_w, "installEventFilter") else None
            if qt_target is None and hasattr(iren_widget, "installEventFilter"):
                qt_target = iren_widget
            if qt_target is not None:
                qt_target.installEventFilter(self._qt_shift_pick_filter)  # type: ignore[misc]
                self._qt_shift_cell_pick_installed = True
        except Exception:
            return

    def _pick_cell_from_display_pos(self, xq: float, yq: float) -> None:
        """
        Pick a cell using display coordinates (Qt mouse position), best-effort.
        """
        grid = getattr(self, "_last_grid", None)
        if grid is None or self._viewer is None:
            return
        picker = getattr(self, "_vtk_cell_picker", None)
        if picker is None:
            return
        try:
            iren = getattr(self._viewer, "iren", None)
            vtk_iren = getattr(iren, "interactor", iren)
        except Exception:
            vtk_iren = None
        if vtk_iren is None:
            return
        try:
            h = float(getattr(vtk_iren, "GetSize")()[1])  # type: ignore[misc]
        except Exception:
            try:
                h = float(getattr(self._viewer, "height")())
            except Exception:
                h = float(yq + 1.0)

        candidates = [(int(xq), int(h - yq)), (int(xq), int(yq))]

        # Restrict picker to the mesh actor when possible.
        try:
            act = getattr(self, "_mesh_actor", None)
            if act is not None and hasattr(picker, "PickFromListOn"):
                picker.PickFromListOn()  # type: ignore[misc]
                if hasattr(picker, "InitializePickList"):
                    picker.InitializePickList()  # type: ignore[misc]
                if hasattr(picker, "AddPickList"):
                    picker.AddPickList(act)  # type: ignore[misc]
        except Exception:
            pass

        for x, y in candidates:
            try:
                ren = None
                try:
                    if hasattr(vtk_iren, "FindPokedRenderer"):
                        ren = vtk_iren.FindPokedRenderer(int(x), int(y))  # type: ignore[misc]
                except Exception:
                    ren = None
                if ren is None:
                    rw = vtk_iren.GetRenderWindow()
                    rens = rw.GetRenderers() if rw is not None else None
                    ren = rens.GetFirstRenderer() if rens is not None else None
                if ren is None:
                    continue
                picker.Pick(float(x), float(y), 0.0, ren)  # type: ignore[misc]
                cid = int(picker.GetCellId())  # type: ignore[misc]
                if cid < 0:
                    try:
                        pos = picker.GetPickPosition()  # type: ignore[misc]
                        if hasattr(grid, "find_closest_cell"):
                            cid = int(grid.find_closest_cell(pos))  # type: ignore[misc]
                    except Exception:
                        cid = -1
                if cid >= 0:
                    self._on_cell_pick((int(cid),), {})
                    return
            except Exception:
                continue
        try:
            self.probe.setPlainText("Cell pick: nothing (try Shift+click inside an element).")
        except Exception:
            pass

    def _apply_2d_view(self) -> None:
        """
        Configure the VTK viewer for 2D-only interaction (pan/zoom, no rotation).
        """
        if not self._is_2d_view or self._viewer is None:
            return
        plotter = getattr(self._viewer, "plotter", self._viewer)
        try:
            from geohpem.viz.vtk_interaction import apply_2d_interaction

            apply_2d_interaction(plotter, on_right_click=self._open_viewer_context_menu)
        except Exception:
            return

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

    def _cancel_active_mode(self) -> None:
        """
        Cancel an active interactive mode (best-effort).

        Esc is intended as the universal "get me out of this mode" key.
        """
        if getattr(self, "_mode", "normal") == "profile_edit":
            try:
                self._cancel_profile_edit()
            except Exception:
                pass
            return

    def _open_viewer_context_menu(self, _pos=None) -> None:  # noqa: ANN001
        """
        Right-click context menu for the Output VTK viewer.
        Called from the VTK interactor style (so we use current cursor position).
        """
        try:
            menu = self._QMenu(self.widget)

            header = menu.addAction("Output Viewer")
            header.setEnabled(False)
            menu.addSeparator()

            act_reset = menu.addAction("Reset view")
            act_reset.setEnabled(self._viewer is not None)
            act_reset.triggered.connect(self._reset_view)

            menu.addSeparator()

            act_export = menu.addAction("Export image...")
            act_export.setEnabled(self._viewer is not None)
            act_export.triggered.connect(self._on_export_image)

            act_export_steps = menu.addAction("Export steps -> PNG...")
            act_export_steps.setEnabled(self._viewer is not None)
            act_export_steps.triggered.connect(self._on_export_steps_png)

            menu.addSeparator()

            act_profile = menu.addAction("Profile line...")
            act_profile.setEnabled(self._viewer is not None)
            act_profile.triggered.connect(self._on_profile_line)

            act_history = menu.addAction("Time history...")
            act_history.setEnabled(self._viewer is not None)
            act_history.triggered.connect(self._on_time_history)

            menu.addSeparator()

            act_pin_node = menu.addAction("Pin last probe (node)")
            act_pin_node.setEnabled(self._last_probe_pid is not None)
            act_pin_node.triggered.connect(self._pin_last_probe)

            act_pin_elem = menu.addAction("Pin last cell (element)")
            act_pin_elem.setEnabled(self._last_cell_id is not None)
            act_pin_elem.triggered.connect(self._pin_last_cell)

            if getattr(self, "_mode", "normal") != "normal":
                menu.addSeparator()
                act_cancel = menu.addAction("Cancel edit (Esc)")
                act_cancel.triggered.connect(self._cancel_active_mode)

            menu.exec(_pos if _pos is not None else self._QCursor.pos())
        except Exception:
            pass

    def _on_viewer_context_menu_requested(self, pos) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        try:
            gpos = self._viewer.mapToGlobal(pos)
        except Exception:
            gpos = None
        self._open_viewer_context_menu(gpos)

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
        if self._mode == "profile_edit":
            # Avoid clearing/rebuilding the plotter while a VTK widget is active.
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

        # Apply color range policy (auto/global/manual)
        try:
            clim = self._get_color_clim(reg)
            if clim is not None:
                scalars_kwargs = dict(scalars_kwargs)
                scalars_kwargs["clim"] = tuple(clim)
        except Exception:
            pass

        # Render
        self._viewer.clear()
        self._mesh_actor = self._viewer.add_mesh(grid, show_edges=True, cmap="viridis", **scalars_kwargs)
        try:
            if self._mesh_actor is not None and hasattr(self._mesh_actor, "SetPickable"):
                self._mesh_actor.SetPickable(True)  # type: ignore[misc]
        except Exception:
            pass
        if unit_display:
            title = f"{scalar_name} [{unit_display}] (step {step_id:06d})"
        elif unit_base:
            title = f"{scalar_name} [{unit_base}] (step {step_id:06d})"
        else:
            title = f"{scalar_name} (step {step_id:06d})"
        self._viewer.add_scalar_bar(title=title)
        self._add_particle_overlay(step_id)
        self._add_profile_overlays()
        self._add_pin_overlays(grid)
        if not bool(getattr(self, "_export_keep_camera", False)):
            self._viewer.reset_camera()
        self._viewer.render()

        # Enable field mode if vector
        self.field_mode.setEnabled(bool(is_vector))

        # Cache last grid for probing
        self._last_grid = grid  # type: ignore[attr-defined]
        self._last_scalar = scalar_name  # type: ignore[attr-defined]
        self._last_pref = scalars_kwargs.get("preference", "point")  # type: ignore[attr-defined]

    def _add_profile_overlays(self) -> None:
        """
        Draw all profile lines as view overlays (best-effort).
        """
        if self._viewer is None:
            return
        try:
            import pyvista as pv  # type: ignore

            selected = self._selected_profile()
            selected_uid = selected.get("uid") if isinstance(selected, dict) else None
            for p in self._profiles:
                if not isinstance(p, dict):
                    continue
                p1 = tuple(float(x) for x in (p.get("p1") or [0.0, 0.0, 0.0])[:3])
                p2 = tuple(float(x) for x in (p.get("p2") or [0.0, 0.0, 0.0])[:3])
                uid = p.get("uid")
                color = "red" if (uid and uid == selected_uid) else "#555555"
                line = pv.Line(p1, p2, resolution=1)
                self._viewer.add_mesh(line, color=color, line_width=3 if color == "red" else 2, pickable=False)
        except Exception:
            return

    def _add_pin_overlays(self, grid) -> None:  # noqa: ANN001
        """
        Draw pinned nodes/cells as view overlays (best-effort).
        """
        if self._viewer is None:
            return
        try:
            import pyvista as pv  # type: ignore
        except Exception:
            return

        selected = self._selected_pin()
        selected_uid = selected.get("uid") if isinstance(selected, dict) else None

        # Node pins (screen-sized points)
        for p in self._pins:
            try:
                if not isinstance(p, dict) or str(p.get("kind", "")) != "node":
                    continue
                x = p.get("x")
                y = p.get("y")
                if x is None or y is None:
                    pid = p.get("pid")
                    try:
                        pid_i = int(pid)
                        if 0 <= pid_i < int(getattr(grid, "n_points", 0)):
                            pt3 = np.asarray(grid.points[pid_i], dtype=float).ravel()
                            x = float(pt3[0])
                            y = float(pt3[1])
                    except Exception:
                        x, y = None, None
                if x is None or y is None:
                    continue
                x = float(x)
                y = float(y)
                uid = p.get("uid")
                is_sel = bool(uid and uid == selected_uid)
                pt = pv.PolyData(np.asarray([[x, y, 0.0]], dtype=float))
                self._viewer.add_mesh(
                    pt,
                    color=("red" if is_sel else "#4444aa"),
                    point_size=(14 if is_sel else 10),
                    render_points_as_spheres=True,
                    pickable=False,
                )
            except Exception:
                continue

        # Element pins (cell highlight)
        for p in self._pins:
            try:
                if not isinstance(p, dict) or str(p.get("kind", "")) != "element":
                    continue
                cid = int(p.get("cell_id"))
                if cid < 0 or cid >= int(getattr(grid, "n_cells", 0)):
                    continue
                uid = p.get("uid")
                is_sel = bool(uid and uid == selected_uid)
                cell = grid.extract_cells([cid])
                # Draw as boundary edges to avoid z-fighting under the (opaque) colormap mesh.
                try:
                    surf = cell.extract_surface()
                except Exception:
                    surf = cell

                # Z-offset to avoid z-fighting with the base colormap mesh.
                try:
                    dx = float(grid.bounds[1] - grid.bounds[0])
                    dy = float(grid.bounds[3] - grid.bounds[2])
                    z_off = 1e-6 * max(dx, dy, 1.0)
                except Exception:
                    z_off = 1e-6

                # When selected, also add a translucent face fill (more readable than edges-only).
                if is_sel:
                    try:
                        fill = surf
                        if hasattr(fill, "translate"):
                            fill = fill.translate((0.0, 0.0, z_off), inplace=False)
                        self._viewer.add_mesh(
                            fill,
                            color="#ff3333",
                            opacity=0.18,
                            show_edges=False,
                            lighting=False,
                            pickable=False,
                        )
                    except Exception:
                        pass
                try:
                    edges = surf.extract_feature_edges(
                        boundary_edges=True,
                        feature_edges=False,
                        manifold_edges=False,
                        non_manifold_edges=False,
                    )
                except Exception:
                    edges = surf
                try:
                    if hasattr(edges, "translate"):
                        edges = edges.translate((0.0, 0.0, z_off), inplace=False)
                except Exception:
                    pass
                self._viewer.add_mesh(
                    edges,
                    color=("red" if is_sel else "#aa4444"),
                    line_width=(6 if is_sel else 3),
                    render_lines_as_tubes=True,
                    pickable=False,
                )
            except Exception:
                continue

        # Last picked cell (not necessarily pinned): show subtle highlight for feedback.
        try:
            last_cid = getattr(self, "_last_cell_id", None)
            if isinstance(last_cid, int) and 0 <= int(last_cid) < int(getattr(grid, "n_cells", 0)):
                # Skip if already pinned (avoid duplicate highlight noise).
                pinned_ids = {int(pp.get("cell_id")) for pp in self._pins if isinstance(pp, dict) and str(pp.get("kind", "")) == "element" and "cell_id" in pp}
                if int(last_cid) not in pinned_ids:
                    cell = grid.extract_cells([int(last_cid)])
                    try:
                        surf = cell.extract_surface()
                    except Exception:
                        surf = cell
                    # Z-offset to avoid z-fighting with the base colormap mesh.
                    try:
                        dx = float(grid.bounds[1] - grid.bounds[0])
                        dy = float(grid.bounds[3] - grid.bounds[2])
                        z_off = 1e-6 * max(dx, dy, 1.0)
                    except Exception:
                        z_off = 1e-6
                    try:
                        edges = surf.extract_feature_edges(
                            boundary_edges=True,
                            feature_edges=False,
                            manifold_edges=False,
                            non_manifold_edges=False,
                        )
                    except Exception:
                        edges = surf
                    try:
                        if hasattr(edges, "translate"):
                            edges = edges.translate((0.0, 0.0, z_off), inplace=False)
                    except Exception:
                        pass
                    self._viewer.add_mesh(
                        edges,
                        color="#ff9900",
                        line_width=2,
                        render_lines_as_tubes=True,
                        pickable=False,
                    )
        except Exception:
            pass
        self._refresh_status()

    def _rerender_preserve_camera(self) -> None:
        """
        Re-render while preserving camera (used for overlay/selection changes).
        """
        if self._viewer is None:
            return
        if getattr(self, "_mode", "normal") == "profile_edit":
            return
        try:
            cam = getattr(self._viewer, "camera_position", None)
        except Exception:
            cam = None
        try:
            self._export_keep_camera = True  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self._render()
            try:
                if cam is not None and hasattr(self._viewer, "camera_position"):
                    self._viewer.camera_position = cam  # type: ignore[attr-defined]
                    self._viewer.render()
            except Exception:
                pass
        finally:
            try:
                self._export_keep_camera = False  # type: ignore[attr-defined]
            except Exception:
                pass

    def _schedule_rerender_preserve_camera(self) -> None:
        """
        Schedule a camera-preserving re-render on the Qt event loop.

        This avoids re-entrancy issues when called from VTK picking callbacks.
        """
        try:
            from PySide6.QtCore import QTimer  # type: ignore

            QTimer.singleShot(0, self._rerender_preserve_camera)
        except Exception:
            try:
                self._rerender_preserve_camera()
            except Exception:
                pass

    def _update_step_info(self, step_id: int) -> None:
        info = self._step_infos.get(int(step_id))
        if not isinstance(info, dict):
            self.step_info.setText(f"global_step_id={step_id:06d}")
            return
        label = "global_step_id"
        if str(info.get("_kind")) == "frame":
            label = "frame_id"
        parts = [f"{label}={int(step_id):06d}"]
        if "stage_id" in info:
            parts.append(f"stage={info.get('stage_id')}")
        if "stage_step" in info:
            try:
                parts.append(f"stage_step={int(info.get('stage_step'))}")
            except Exception:
                pass
        if "substep" in info:
            try:
                parts.append(f"substep={int(info.get('substep'))}")
            except Exception:
                pass
        if "dt" in info:
            try:
                parts.append(f"dt={float(info.get('dt')):.6g}")
            except Exception:
                pass
        if "events" in info and isinstance(info.get("events"), list):
            try:
                parts.append(f"events={len(info.get('events'))}")
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
            self._last_cell_info = None

        # Update highlight overlays immediately (last-picked cell orange outline).
        self._schedule_rerender_preserve_camera()

    def _fill_cells_from_base(self, mesh: dict[str, Any], pts: np.ndarray) -> dict[str, Any]:
        base = self._mesh or {}
        if pts.ndim != 2:
            return mesh
        n_pts = int(pts.shape[0])
        for cell_type in ("tri3", "quad4"):
            key = f"cells_{cell_type}"
            if key in mesh:
                continue
            if key not in base:
                continue
            try:
                arr = np.asarray(base[key], dtype=np.int64)
            except Exception:
                continue
            if arr.size == 0:
                mesh[key] = arr
                continue
            try:
                if int(arr.max()) < n_pts:
                    mesh[key] = arr
            except Exception:
                continue
        return mesh

    def _mesh_for_step(self, step_id: int) -> dict[str, Any]:
        if self._mesh is None or self._arrays is None:
            raise RuntimeError("Missing mesh/results")
        arrays = self._arrays
        sid = int(step_id)
        for tag in ("frame", "step"):
            key_points = f"mesh__points__{tag}{sid:06d}"
            if key_points in arrays:
                pts = np.asarray(arrays[key_points], dtype=float)
                mesh: dict[str, Any] = {"points": pts}
                for cell_type in ("tri3", "quad4"):
                    key_cells = f"mesh__cells_{cell_type}__{tag}{sid:06d}"
                    if key_cells in arrays:
                        mesh[f"cells_{cell_type}"] = np.asarray(arrays[key_cells], dtype=np.int64)
                return self._fill_cells_from_base(mesh, pts)
        return self._mesh

    def _particle_points_for_step(self, step_id: int) -> np.ndarray | None:
        if self._arrays is None:
            return None
        arrays = self._arrays
        sid = int(step_id)
        for tag in ("frame", "step"):
            key_pts = f"particles__points__{tag}{sid:06d}"
            if key_pts in arrays:
                pts = np.asarray(arrays[key_pts], dtype=float)
                if pts.ndim == 2 and pts.shape[1] >= 2:
                    if pts.shape[1] == 2:
                        z = np.zeros((pts.shape[0], 1), dtype=float)
                        return np.hstack([pts[:, :2], z])
                    return pts[:, :3]
            kx = f"particles__x__{tag}{sid:06d}"
            ky = f"particles__y__{tag}{sid:06d}"
            kz = f"particles__z__{tag}{sid:06d}"
            if kx in arrays and ky in arrays:
                x = np.asarray(arrays[kx], dtype=float).reshape(-1)
                y = np.asarray(arrays[ky], dtype=float).reshape(-1)
                if x.size != y.size:
                    continue
                if kz in arrays:
                    z = np.asarray(arrays[kz], dtype=float).reshape(-1)
                    if z.size != x.size:
                        z = np.zeros_like(x)
                else:
                    z = np.zeros_like(x)
                return np.stack([x, y, z], axis=1)
        return None

    def _add_particle_overlay(self, step_id: int) -> None:
        if self._viewer is None:
            return
        pts = self._particle_points_for_step(step_id)
        if pts is None or pts.size == 0:
            return
        try:
            import pyvista as pv  # type: ignore

            cloud = pv.PolyData(np.asarray(pts, dtype=float))
            self._viewer.add_mesh(
                cloud,
                color="#333333",
                point_size=5,
                render_points_as_spheres=True,
                pickable=False,
            )
        except Exception:
            return

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

        mesh = self._mesh_for_step(step_id)
        vtk_mesh = contract_mesh_to_pyvista(mesh)
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
            grid.point_data[scalar_name] = scalar
            scalars_kwargs = {"scalars": scalar_name, "preference": "point"}
        elif location in ("element", "elem"):
            if scalar.shape[0] != grid.n_cells:
                raise RuntimeError(f"Array size mismatch: {scalar.shape[0]} vs n_cells {grid.n_cells}")
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
            try:
                if getattr(self, "_tabs", None) is not None:
                    self._tabs.setCurrentIndex(int(getattr(self, "_tab_profiles", 0)))
            except Exception:
                pass
            self._plot_profile(prof)
            try:
                self.ui_state_changed.emit()
            except Exception:
                pass
            try:
                self._render()
            except Exception:
                pass
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
        self.btn_profile_edit.setEnabled(bool(ok) and self._mode == "normal")
        self.btn_profile_edit_finish.setEnabled(False)
        self.btn_profile_edit_cancel.setEnabled(False)
        # Update viewport highlight immediately (selected profile line in red).
        if self._viewer is not None:
            self._rerender_preserve_camera()

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
        try:
            self.ui_state_changed.emit()
        except Exception:
            pass

    def _plot_profile(self, prof: dict[str, Any]) -> None:
        from geohpem.gui.dialogs.plot_dialog import PlotDialog, PlotSeries

        dist = np.asarray(prof.get("dist", []), dtype=float).ravel()
        vals = np.asarray(prof.get("vals", []), dtype=float).ravel()
        if dist.size == 0 or vals.size == 0:
            try:
                dist, vals, scalar_name2, unit2 = self._recompute_profile_series(prof)
                prof["dist"] = dist
                prof["vals"] = vals
                if scalar_name2:
                    prof["scalar_name"] = scalar_name2
                if unit2:
                    prof["unit"] = unit2
            except Exception:
                pass
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

    def _recompute_profile_series(self, prof: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, str | None, str | None]:
        """
        Re-sample the result field over the profile line.
        Returns (dist, vals, scalar_name, unit_label).
        """
        if self._arrays is None or self._mesh is None:
            raise RuntimeError("No result loaded")
        reg_ref = prof.get("reg") if isinstance(prof.get("reg"), dict) else {}
        location = str(reg_ref.get("location", "node"))
        name = str(reg_ref.get("name", ""))
        if not name:
            raise RuntimeError("Profile missing reg.name")
        step_id = int(prof.get("step_id", 0))
        p1 = tuple(float(x) for x in (prof.get("p1") or [0.0, 0.0, 0.0])[:3])
        p2 = tuple(float(x) for x in (prof.get("p2") or [0.0, 0.0, 0.0])[:3])

        reg = None
        if self._meta is not None:
            for it in self._meta.get("registry", []):
                if not isinstance(it, dict):
                    continue
                if str(it.get("location", "")) == location and str(it.get("name", "")) == name:
                    reg = it
                    break
        if reg is None:
            reg = {"location": location, "name": name}

        grid, scalar_name, _scalars_kwargs, unit_label, _is_vec = self._build_grid_with_scalars(reg, step_id, warp=False)
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
        return dist, vals, scalar_name, unit_label

    def _start_profile_edit(self) -> None:
        if self._viewer is None:
            return
        if self._mode != "normal":
            return
        prof = self._selected_profile()
        if prof is None:
            return
        p1 = tuple(float(x) for x in (prof.get("p1") or [0.0, 0.0, 0.0])[:3])
        p2 = tuple(float(x) for x in (prof.get("p2") or [0.0, 0.0, 0.0])[:3])
        self._profile_edit_backup = {"uid": prof.get("uid"), "p1": list(p1), "p2": list(p2)}

        self._mode = "profile_edit"
        try:
            self.probe.setPlainText("Profile edit: drag the two endpoints, then click Finish/Cancel.")
        except Exception:
            pass
        try:
            self.registry_list.setEnabled(False)
            self.step.setEnabled(False)
            self.field_mode.setEnabled(False)
            self.warp.setEnabled(False)
            self.warp_scale.setEnabled(False)
            self.btn_profile_edit.setEnabled(False)
            self.btn_profile_edit_finish.setEnabled(True)
            self.btn_profile_edit_cancel.setEnabled(True)
        except Exception:
            pass

        def _as_point3(pt) -> list[float] | None:  # noqa: ANN001
            try:
                if isinstance(pt, np.ndarray):
                    pt = pt.tolist()
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x = float(pt[0])
                    y = float(pt[1])
                    z = float(pt[2]) if len(pt) >= 3 else 0.0
                    return [x, y, z]
            except Exception:
                return None
            return None

        def _get_widget_points(widget) -> tuple[list[float], list[float]] | None:  # noqa: ANN001
            """
            Best-effort extraction of (p1, p2) from various VTK line widget types.
            """
            try:
                if hasattr(widget, "GetPoint1") and hasattr(widget, "GetPoint2"):
                    a = _as_point3(widget.GetPoint1())  # type: ignore[misc]
                    b = _as_point3(widget.GetPoint2())  # type: ignore[misc]
                    if a and b:
                        return a, b
            except Exception:
                pass
            try:
                rep = widget.GetRepresentation() if hasattr(widget, "GetRepresentation") else None  # type: ignore[misc]
                if rep is not None:
                    for m1, m2 in (
                        ("GetPoint1WorldPosition", "GetPoint2WorldPosition"),
                        ("GetPoint1DisplayPosition", "GetPoint2DisplayPosition"),
                    ):
                        if hasattr(rep, m1) and hasattr(rep, m2):
                            a = _as_point3(getattr(rep, m1)())  # type: ignore[misc]
                            b = _as_point3(getattr(rep, m2)())  # type: ignore[misc]
                            if a and b:
                                return a, b
            except Exception:
                pass
            return None

        def _set_widget_points(widget, a: tuple[float, float, float], b: tuple[float, float, float]) -> None:
            try:
                if hasattr(widget, "SetPoint1"):
                    widget.SetPoint1(*a)  # type: ignore[misc]
                if hasattr(widget, "SetPoint2"):
                    widget.SetPoint2(*b)  # type: ignore[misc]
                return
            except Exception:
                pass
            try:
                rep = widget.GetRepresentation() if hasattr(widget, "GetRepresentation") else None  # type: ignore[misc]
                if rep is None:
                    return
                if hasattr(rep, "SetPoint1WorldPosition") and hasattr(rep, "SetPoint2WorldPosition"):
                    rep.SetPoint1WorldPosition(a)  # type: ignore[misc]
                    rep.SetPoint2WorldPosition(b)  # type: ignore[misc]
            except Exception:
                return

        def _update_prof_from_points(a, b) -> None:  # noqa: ANN001
            pa = _as_point3(a)
            pb = _as_point3(b)
            if pa is None or pb is None:
                return
            prof["p1"] = pa
            prof["p2"] = pb
            prof["dist"] = []
            prof["vals"] = []

        def cb(*args, **kwargs):  # noqa: ANN001
            """
            PyVista versions differ:
            - callback(point_a, point_b)
            - callback(widget) when pass_widget=True (or unsupported kwargs fall back)
            Keep this callback resilient.
            """
            # 1) explicit kwargs
            for k1, k2 in (("pointa", "pointb"), ("point1", "point2"), ("p1", "p2")):
                if k1 in kwargs and k2 in kwargs:
                    _update_prof_from_points(kwargs[k1], kwargs[k2])
                    return
            # 2) positional points
            if len(args) >= 2:
                _update_prof_from_points(args[0], args[1])
                return
            # 3) widget
            if len(args) == 1:
                pts = _get_widget_points(args[0])
                if pts is not None:
                    _update_prof_from_points(pts[0], pts[1])
                return

        try:
            plotter = getattr(self._viewer, "plotter", self._viewer)
            self._profile_widget = plotter.add_line_widget(  # type: ignore[misc]
                cb,
                use_vertices=False,
                pass_widget=True,
                interaction_event="end",
                color="red",
            )
            try:
                _set_widget_points(self._profile_widget, p1, p2)
            except Exception:
                pass
        except Exception as exc:
            self._mode = "normal"
            self._profile_widget = None
            self._profile_edit_backup = None
            self._QMessageBox.critical(self.widget, "Profile Edit Failed", str(exc))
            try:
                self._render()
            except Exception:
                pass

    def _finish_profile_edit(self) -> None:
        if self._mode != "profile_edit":
            return
        # Snapshot current widget endpoints in case callback wasn't invoked (version differences / event timing).
        try:
            backup = self._profile_edit_backup if isinstance(self._profile_edit_backup, dict) else None
            uid = backup.get("uid") if backup else None
            w = self._profile_widget
            if uid and w is not None:
                pts = None
                try:
                    # Local helper mirroring _start_profile_edit's widget extraction.
                    rep = w.GetRepresentation() if hasattr(w, "GetRepresentation") else None  # type: ignore[misc]
                    if hasattr(w, "GetPoint1") and hasattr(w, "GetPoint2"):
                        pts = (w.GetPoint1(), w.GetPoint2())  # type: ignore[misc]
                    elif rep is not None and hasattr(rep, "GetPoint1WorldPosition") and hasattr(rep, "GetPoint2WorldPosition"):
                        pts = (rep.GetPoint1WorldPosition(), rep.GetPoint2WorldPosition())  # type: ignore[misc]
                except Exception:
                    pts = None
                if pts is not None:
                    a = pts[0]
                    b = pts[1]
                    try:
                        if isinstance(a, np.ndarray):
                            a = a.tolist()
                        if isinstance(b, np.ndarray):
                            b = b.tolist()
                        p1 = [float(a[0]), float(a[1]), float(a[2]) if len(a) >= 3 else 0.0]
                        p2 = [float(b[0]), float(b[1]), float(b[2]) if len(b) >= 3 else 0.0]
                        for p in self._profiles:
                            if isinstance(p, dict) and p.get("uid") == uid:
                                p["p1"] = p1
                                p["p2"] = p2
                                p["dist"] = []
                                p["vals"] = []
                                break
                    except Exception:
                        pass
        except Exception:
            pass
        self._teardown_profile_widget()
        self._mode = "normal"
        self._profile_edit_backup = None
        try:
            self.ui_state_changed.emit()
        except Exception:
            pass
        try:
            self.registry_list.setEnabled(True)
            self.step.setEnabled(True)
            self.warp.setEnabled(True)
            self.warp_scale.setEnabled(True)
        except Exception:
            pass
        try:
            self._render()
        except Exception:
            pass
        self._on_profile_selection_changed(self.profile_list.currentRow())

    def _cancel_profile_edit(self) -> None:
        if self._mode != "profile_edit":
            return
        backup = self._profile_edit_backup
        self._teardown_profile_widget()
        self._mode = "normal"
        if isinstance(backup, dict):
            uid = backup.get("uid")
            for p in self._profiles:
                if isinstance(p, dict) and p.get("uid") == uid:
                    p["p1"] = backup.get("p1")
                    p["p2"] = backup.get("p2")
                    break
        self._profile_edit_backup = None
        try:
            self.registry_list.setEnabled(True)
            self.step.setEnabled(True)
            self.warp.setEnabled(True)
            self.warp_scale.setEnabled(True)
        except Exception:
            pass
        try:
            self._render()
        except Exception:
            pass
        self._on_profile_selection_changed(self.profile_list.currentRow())

    def _teardown_profile_widget(self) -> None:
        w = self._profile_widget
        self._profile_widget = None
        if w is None:
            return
        try:
            if hasattr(w, "Off"):
                w.Off()  # type: ignore[misc]
            elif hasattr(w, "SetEnabled"):
                w.SetEnabled(0)  # type: ignore[misc]
        except Exception:
            pass

    def _refresh_pin_list(self, *, select_uid: str | None = None) -> None:
        self.pin_list.clear()

        def fmt_num(v) -> str:  # noqa: ANN001
            try:
                if v is None:
                    return "?"
                return f"{float(v):.4g}"
            except Exception:
                return "?"

        for p in self._pins:
            kind = str(p.get("kind", ""))
            if kind == "node":
                pid = p.get("pid")
                x, y = p.get("x"), p.get("y")
                label = f"{p.get('name','node')}  (pid={pid} x={fmt_num(x)} y={fmt_num(y)})"
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
        # Update viewport highlight immediately (selected pin in red).
        if self._viewer is not None:
            self._rerender_preserve_camera()

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
        try:
            if getattr(self, "_tabs", None) is not None:
                self._tabs.setCurrentIndex(int(getattr(self, "_tab_pins", 1)))
        except Exception:
            pass
        try:
            self.ui_state_changed.emit()
        except Exception:
            pass

    def _pin_last_cell(self) -> None:
        if self._last_cell_id is None or not isinstance(self._last_cell_info, dict):
            self._QMessageBox.information(self.widget, "Pin", "Pick a cell first (click on mesh).")
            return
        info = dict(self._last_cell_info)
        uid = self._new_uid("pin")
        pin = {"uid": uid, "kind": "element", "name": f"elem_{len([p for p in self._pins if p.get('kind')=='element'])+1}", **info}
        self._pins.append(pin)
        self._refresh_pin_list(select_uid=uid)
        try:
            if getattr(self, "_tabs", None) is not None:
                self._tabs.setCurrentIndex(int(getattr(self, "_tab_pins", 1)))
        except Exception:
            pass
        try:
            self.ui_state_changed.emit()
        except Exception:
            pass

    def _remove_selected_pin(self) -> None:
        row = int(self.pin_list.currentRow())
        if row < 0 or row >= len(self._pins):
            return
        del self._pins[row]
        self._refresh_pin_list()
        try:
            self.ui_state_changed.emit()
        except Exception:
            pass

    def _step_time_map(self) -> dict[int, float]:
        """
        Best-effort mapping from global step id -> time (float).
        For fake solver, meta["stages"][*]["times"] exists and steps are sequential.
        """
        if not self._meta:
            return {}
        frames = self._meta.get("frames")
        if isinstance(frames, list) and frames:
            out: dict[int, float] = {}
            for it in frames:
                if not isinstance(it, dict):
                    continue
                try:
                    fid = int(it.get("id"))
                    t = float(it.get("time"))
                except Exception:
                    continue
                out[fid] = t
            if out:
                return out
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

    def _on_export_steps_png(self) -> None:
        """
        Export the currently selected field over all steps as a PNG sequence.
        """
        if self._viewer is None or self._meta is None or self._arrays is None or self._mesh is None:
            return
        ctx = self._current_field_context()
        if ctx is None:
            self._QMessageBox.information(self.widget, "Export Steps", "Select a field and render a step first.")
            return
        _reg, _step_id, scalar_name, _pref, _unit_label = ctx

        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import QFileDialog, QInputDialog, QProgressDialog  # type: ignore

        folder = QFileDialog.getExistingDirectory(self.widget, "Export Steps (PNG)", "")
        if not folder:
            return

        prefix, ok = QInputDialog.getText(self.widget, "Export Steps", "Filename prefix", text=str(scalar_name or "field"))
        if not ok:
            return
        prefix = (prefix or "field").strip() or "field"

        cam = None
        try:
            cam = getattr(self._viewer, "camera_position", None)
        except Exception:
            cam = None

        prog = QProgressDialog("Exporting PNG sequence...", "Cancel", 0, max(len(self._steps), 1), self.widget)
        prog.setWindowModality(Qt.WindowModality.ApplicationModal)
        prog.setMinimumDuration(0)
        prog.show()

        old_idx = int(self.step.value())
        self._export_keep_camera = True  # type: ignore[attr-defined]
        try:
            # prevent user interaction changing the view while exporting
            self.registry_list.setEnabled(False)
            self.step.setEnabled(False)
            self.field_mode.setEnabled(False)
            self.warp.setEnabled(False)
            self.warp_scale.setEnabled(False)

            self.step.blockSignals(True)
            for i, step_id in enumerate(self._steps):
                prog.setValue(i)
                prog.setLabelText(f"step {int(step_id):06d} ({i+1}/{len(self._steps)})")
                if prog.wasCanceled():
                    break
                self.step.setValue(int(i))
                self._render()
                try:
                    if cam is not None and hasattr(self._viewer, "camera_position"):
                        self._viewer.camera_position = cam  # type: ignore[attr-defined]
                        self._viewer.render()
                except Exception:
                    pass
                out = Path(folder) / f"{prefix}_step{int(step_id):06d}.png"
                v = self._viewer
                if hasattr(v, "screenshot"):
                    v.screenshot(str(out))  # type: ignore[misc]
                else:
                    plotter = getattr(v, "plotter", None)
                    if plotter is None or not hasattr(plotter, "screenshot"):
                        raise RuntimeError("Viewer does not support screenshot()")
                    plotter.screenshot(str(out))  # type: ignore[misc]
        except Exception as exc:
            self._QMessageBox.critical(self.widget, "Export Steps Failed", str(exc))
        finally:
            try:
                self.step.blockSignals(False)
            except Exception:
                pass
            try:
                self._export_keep_camera = False  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                self.registry_list.setEnabled(True)
                self.step.setEnabled(True)
                self.warp.setEnabled(True)
                self.warp_scale.setEnabled(True)
            except Exception:
                pass
            try:
                self.step.setValue(old_idx)
            except Exception:
                pass
            try:
                self._render()
            except Exception:
                pass
            try:
                prog.close()
            except Exception:
                pass

    def _on_profile_line(self) -> None:
        if self._viewer is None:
            return
        try:
            if getattr(self, "_tabs", None) is not None:
                self._tabs.setCurrentIndex(int(getattr(self, "_tab_profiles", 0)))
        except Exception:
            pass
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

        chk_save = QCheckBox("Save to Profiles list")
        chk_save.setChecked(True)
        form.addRow("", chk_save)

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

            # Persist into Profiles list (recommended), so user can later edit/plot/export repeatedly.
            prof = None
            if chk_save.isChecked():
                uid = self._new_uid("profile")
                prof = {
                    "uid": uid,
                    "name": f"profile_{len(self._profiles)+1}",
                    "p1": [float(p1[0]), float(p1[1]), float(p1[2])],
                    "p2": [float(p2[0]), float(p2[1]), float(p2[2])],
                    "reg": {"location": reg.get("location"), "name": reg.get("name")},
                    "step_id": int(step_id),
                    "scalar_name": scalar_name,
                    "unit": unit_label,
                    "dist": dist,
                    "vals": vals,
                }
                self._profiles.append(prof)
                self._refresh_profile_list(select_uid=uid)
                try:
                    self.ui_state_changed.emit()
                except Exception:
                    pass

                # Update viewport overlay without resetting camera.
                if chk_overlay.isChecked():
                    try:
                        cam = getattr(self._viewer, "camera_position", None)
                    except Exception:
                        cam = None
                    try:
                        self._export_keep_camera = True  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:
                        self._render()
                        if cam is not None and hasattr(self._viewer, "camera_position"):
                            self._viewer.camera_position = cam  # type: ignore[attr-defined]
                            self._viewer.render()
                    finally:
                        try:
                            self._export_keep_camera = False  # type: ignore[attr-defined]
                        except Exception:
                            pass
            elif chk_overlay.isChecked():
                # Temporary overlay only (not saved).
                try:
                    line = pv.Line(p1, p2, resolution=1)
                    self._viewer.add_mesh(line, color="red", line_width=3, pickable=False)
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
        try:
            if getattr(self, "_tabs", None) is not None:
                self._tabs.setCurrentIndex(int(getattr(self, "_tab_pins", 1)))
        except Exception:
            pass
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
