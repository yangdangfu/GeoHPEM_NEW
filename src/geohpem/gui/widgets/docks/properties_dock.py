from __future__ import annotations

import json
from typing import Any, Callable


class PropertiesDock:
    """
    Minimal form-based property editor for MVP.
    """

    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (
            QComboBox,
            QDockWidget,
            QDoubleSpinBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QScrollArea,
            QPushButton,
            QPlainTextEdit,
            QSpinBox,
            QStackedWidget,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

        self._Qt = Qt
        self.dock = QDockWidget("Properties")
        self.dock.setObjectName("dock_properties")

        self._stack = QStackedWidget()
        self.dock.setWidget(self._stack)

        # Page: empty
        self._page_empty = QWidget()
        empty_layout = QVBoxLayout(self._page_empty)
        empty_layout.addWidget(QLabel("Select an item in Project Explorer."))
        empty_layout.addStretch(1)
        self._stack.addWidget(self._page_empty)

        # Page: info
        self._page_info = QWidget()
        info_layout = QVBoxLayout(self._page_info)
        self._info_title = QLabel("Info")
        self._info_title.setStyleSheet("font-weight: 600;")
        info_layout.addWidget(self._info_title)
        self._info_details = QLabel("")
        self._info_details.setWordWrap(True)
        self._info_details.setStyleSheet("color: #4b5563;")
        info_layout.addWidget(self._info_details)
        self._info_cards = QWidget()
        self._info_cards_layout = QHBoxLayout(self._info_cards)
        self._info_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._info_cards_layout.setSpacing(8)
        info_layout.addWidget(self._info_cards)
        self._info_section = QLabel("Details")
        self._info_section.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 600;")
        info_layout.addWidget(self._info_section)
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_container = QWidget()
        self._info_form = QFormLayout(info_container)
        self._info_form.setContentsMargins(6, 6, 6, 6)
        info_scroll.setWidget(info_container)
        info_layout.addWidget(info_scroll, 1)
        self._stack.addWidget(self._page_info)

        # Page: model
        self._page_model = QWidget()
        model_layout = QVBoxLayout(self._page_model)
        self._cap_hint_model = QLabel("")
        self._cap_hint_model.setStyleSheet("color: #b45309;")  # amber-ish
        model_layout.addWidget(self._cap_hint_model)
        model_form = QFormLayout()
        model_layout.addLayout(model_form)

        self._mode = QComboBox()
        self._mode.addItem("Plane strain", "plane_strain")
        self._mode.addItem("Plane stress", "plane_stress")
        self._mode.addItem("Axisymmetric", "axisymmetric")
        model_form.addRow("Mode", self._mode)

        self._gx = QDoubleSpinBox()
        self._gx.setRange(-1e6, 1e6)
        self._gx.setDecimals(6)
        self._gy = QDoubleSpinBox()
        self._gy.setRange(-1e6, 1e6)
        self._gy.setDecimals(6)
        model_form.addRow("Gravity X", self._gx)
        model_form.addRow("Gravity Y", self._gy)

        self._btn_apply_model = QPushButton("Apply")
        model_layout.addWidget(self._btn_apply_model)
        model_layout.addStretch(1)
        self._stack.addWidget(self._page_model)

        # Page: stage
        self._page_stage = QWidget()
        stage_layout = QVBoxLayout(self._page_stage)
        self._cap_hint_stage = QLabel("")
        self._cap_hint_stage.setStyleSheet("color: #b45309;")  # amber-ish
        stage_layout.addWidget(self._cap_hint_stage)
        stage_form = QFormLayout()
        stage_layout.addLayout(stage_form)

        self._stage_id = QLineEdit()
        self._stage_id.setReadOnly(True)
        stage_form.addRow("Stage ID", self._stage_id)

        self._analysis_type = QComboBox()
        for v in ("static", "dynamic", "seepage_steady", "seepage_transient", "consolidation_u_p", "pfem"):
            self._analysis_type.addItem(v, v)
        stage_form.addRow("Analysis Type", self._analysis_type)

        self._num_steps = QSpinBox()
        self._num_steps.setRange(1, 10_000_000)
        stage_form.addRow("Num Steps", self._num_steps)

        self._dt = QDoubleSpinBox()
        self._dt.setRange(0.0, 1e9)
        self._dt.setDecimals(9)
        stage_form.addRow("dt", self._dt)

        from geohpem.gui.widgets.output_requests_editor import OutputRequestsEditor

        self._cap_hint_outputs = QLabel("")
        self._cap_hint_outputs.setStyleSheet("color: #b45309;")  # amber-ish
        stage_layout.addWidget(self._cap_hint_outputs)

        self._stage_out_editor = OutputRequestsEditor(self._page_stage, title="Stage output_requests")
        stage_layout.addWidget(self._stage_out_editor.widget, 1)

        from geohpem.gui.widgets.stage_table_editor import StageItemTableConfig, StageItemTableEditor

        self._available_sets: list[str] = []
        self._bcs_editor = StageItemTableEditor(
            self._page_stage,
            config=StageItemTableConfig(kind="bc", uid_prefix="bc", title="Stage BCs", default_field="u", default_type="dirichlet"),
        )
        stage_layout.addWidget(self._bcs_editor.widget, 1)

        self._loads_editor = StageItemTableEditor(
            self._page_stage,
            config=StageItemTableConfig(kind="load", uid_prefix="load", title="Stage Loads", default_field="p", default_type="neumann"),
        )
        stage_layout.addWidget(self._loads_editor.widget, 1)

        self._btn_apply_stage = QPushButton("Apply")
        stage_layout.addWidget(self._btn_apply_stage)
        self._stack.addWidget(self._page_stage)

        # Page: material
        self._page_material = QWidget()
        mat_layout = QVBoxLayout(self._page_material)
        mat_form = QFormLayout()
        mat_layout.addLayout(mat_form)

        self._mat_id = QLineEdit()
        self._mat_id.setReadOnly(True)
        mat_form.addRow("Material ID", self._mat_id)

        self._mat_model_name = QLineEdit()
        mat_form.addRow("Model Name", self._mat_model_name)

        self._mat_params = QPlainTextEdit()
        self._mat_params.setPlaceholderText("{ ... }")
        mat_layout.addWidget(QLabel("Parameters (JSON object)"))
        mat_layout.addWidget(self._mat_params)

        self._btn_apply_material = QPushButton("Apply")
        mat_layout.addWidget(self._btn_apply_material)
        self._stack.addWidget(self._page_material)

        # Page: assignments
        from geohpem.gui.widgets.assignments_editor import AssignmentsEditor, AssignmentOptions

        self._page_assignments = QWidget()
        asg_layout = QVBoxLayout(self._page_assignments)
        self._assign_hint = QLabel("")
        self._assign_hint.setStyleSheet("color: #b45309;")
        asg_layout.addWidget(self._assign_hint)
        self._assign_editor = AssignmentsEditor(self._page_assignments)
        asg_layout.addWidget(self._assign_editor.widget, 1)
        self._btn_apply_assign = QPushButton("Apply")
        asg_layout.addWidget(self._btn_apply_assign)
        self._stack.addWidget(self._page_assignments)

        # Page: global output requests
        from geohpem.gui.widgets.output_requests_editor import OutputRequestsEditor

        self._page_global_out = QWidget()
        g_layout = QVBoxLayout(self._page_global_out)
        g_layout.addWidget(QLabel("Global output_requests (optional)"))
        self._global_out_editor = OutputRequestsEditor(self._page_global_out, title="Global output_requests")
        g_layout.addWidget(self._global_out_editor.widget, 1)
        self._btn_apply_global_out = QPushButton("Apply")
        g_layout.addWidget(self._btn_apply_global_out)
        self._stack.addWidget(self._page_global_out)

        # Callbacks configured by MainWindow
        self._apply_model_cb: Callable[[str, float, float], None] | None = None
        self._apply_stage_cb: Callable[[str, dict[str, Any]], None] | None = None
        self._apply_material_cb: Callable[[str, str, dict[str, Any]], None] | None = None
        self._apply_assignments_cb: Callable[[list[dict[str, Any]]], None] | None = None
        self._apply_global_output_requests_cb: Callable[[list[dict[str, Any]]], None] | None = None

        self._current_stage_index: int | None = None
        self._current_stage_uid: str | None = None
        self._solver_caps: dict[str, Any] | None = None
        self._current_material_id: str | None = None

        self._btn_apply_model.clicked.connect(self._on_apply_model)
        self._btn_apply_stage.clicked.connect(self._on_apply_stage)
        self._btn_apply_material.clicked.connect(self._on_apply_material)
        self._btn_apply_assign.clicked.connect(self._on_apply_assignments)
        self._btn_apply_global_out.clicked.connect(self._on_apply_global_output_requests)

        self.show_empty()

    def set_available_sets(self, names: list[str]) -> None:
        self._available_sets = list(names)
        try:
            self._bcs_editor.set_set_options(self._available_sets)
            self._loads_editor.set_set_options(self._available_sets)
        except Exception:
            pass

    def set_solver_capabilities(self, caps: dict[str, Any] | None) -> None:
        """
        Update UI availability based on solver capabilities (best-effort).
        """
        self._solver_caps = caps
        # Refresh enable/disable state for current pages.
        self._apply_capabilities_to_model_combo()
        self._apply_capabilities_to_stage_combo()
        # Stage BC/Load helper options (best-effort).
        try:
            bc_types = caps.get("bcs") if isinstance(caps, dict) else None
            ld_types = caps.get("loads") if isinstance(caps, dict) else None
            bc_list = [str(x) for x in (bc_types or []) if isinstance(x, str) and x.strip()]
            ld_list = [str(x) for x in (ld_types or []) if isinstance(x, str) and x.strip()]
            self._bcs_editor.set_type_options(bc_list)
            self._loads_editor.set_type_options(ld_list)

            # Fields are optional in v0.2; keep a small common set and let presets auto-fill.
            field_opts: list[str] = []
            if "displacement" in bc_list or "traction" in ld_list or "gravity" in ld_list:
                field_opts.append("u")
            if "p" in bc_list or "flux" in ld_list:
                field_opts.append("p")
            if not field_opts:
                field_opts = ["u", "p"]
            self._bcs_editor.set_field_options(field_opts)
            self._loads_editor.set_field_options(field_opts)

            # Type -> (field,value) presets for better UX.
            self._bcs_editor.set_type_presets(
                {
                    "displacement": {"field": "u", "value": {"ux": 0.0, "uy": 0.0}},
                    "p": {"field": "p", "value": 0.0},
                }
            )
            self._loads_editor.set_type_presets(
                {
                    "traction": {"field": "u", "value": [0.0, -1.0e5]},
                    "gravity": {"field": "u", "value": [0.0, -9.81]},
                    "flux": {"field": "p", "value": -1.0e-6},
                }
            )
        except Exception:
            pass
        try:
            self._stage_out_editor.set_options(self._outreq_options())
            self._global_out_editor.set_options(self._outreq_options())
        except Exception:
            pass

    def _set_combo_item_enabled(self, combo, index: int, enabled: bool) -> None:  # noqa: ANN001
        try:
            model = combo.model()
            if hasattr(model, "item"):
                item = model.item(index)
                if item is not None:
                    item.setEnabled(bool(enabled))
                    return
        except Exception:
            pass
        try:
            from PySide6.QtCore import Qt  # type: ignore

            role = int(Qt.ItemDataRole.UserRole) - 1
            if enabled:
                flags = int(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            else:
                flags = int(Qt.ItemFlag.ItemIsSelectable)
            combo.setItemData(index, flags, role)
        except Exception:
            # Not all models allow per-item enabled control; ignore.
            return

    def _apply_capabilities_to_model_combo(self) -> None:
        caps = self._solver_caps or {}
        allowed = caps.get("modes")
        if not isinstance(allowed, list) or not allowed:
            self._cap_hint_model.setText("")
            for i in range(self._mode.count()):
                self._set_combo_item_enabled(self._mode, i, True)
            return
        allow = {str(x) for x in allowed if isinstance(x, str)}
        for i in range(self._mode.count()):
            v = str(self._mode.itemData(i))
            self._set_combo_item_enabled(self._mode, i, v in allow)
        cur = str(self._mode.currentData())
        if cur and cur not in allow:
            self._cap_hint_model.setText(f"Current mode '{cur}' is not supported by selected solver.")
        else:
            self._cap_hint_model.setText("")

    def _apply_capabilities_to_stage_combo(self) -> None:
        caps = self._solver_caps or {}
        allowed = caps.get("analysis_types")
        if not isinstance(allowed, list) or not allowed:
            self._cap_hint_stage.setText("")
            for i in range(self._analysis_type.count()):
                self._set_combo_item_enabled(self._analysis_type, i, True)
            return
        allow = {str(x) for x in allowed if isinstance(x, str)}
        for i in range(self._analysis_type.count()):
            v = str(self._analysis_type.itemData(i))
            self._set_combo_item_enabled(self._analysis_type, i, v in allow)
        cur = str(self._analysis_type.currentData())
        if cur and cur not in allow:
            self._cap_hint_stage.setText(f"Current analysis_type '{cur}' is not supported by selected solver.")
        else:
            self._cap_hint_stage.setText("")

    def _allowed_output_names(self) -> set[str] | None:
        caps = self._solver_caps or {}
        names: set[str] = set()
        for key in ("results", "fields"):
            v = caps.get(key)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, str) and it:
                        names.add(it)
        return names or None

    def _outreq_options(self):
        from geohpem.gui.widgets.output_requests_editor import OutputRequestOptions

        allowed = self._allowed_output_names() or set()
        return OutputRequestOptions(names=sorted(allowed))

    def _validate_stage_outputs(self) -> None:
        allowed = self._allowed_output_names()
        if not allowed:
            self._cap_hint_outputs.setText("")
            return
        bad: list[str] = []
        for it in self._stage_out_editor.requests():
            if not isinstance(it, dict):
                continue
            name = it.get("name")
            if isinstance(name, str) and name and name not in allowed:
                bad.append(name)
        if bad:
            self._cap_hint_outputs.setText(f"Some outputs are not supported by selected solver: {sorted(set(bad))}")
        else:
            self._cap_hint_outputs.setText("")

    def bind_apply_model(self, cb: Callable[[str, float, float], None]) -> None:
        self._apply_model_cb = cb

    def bind_apply_stage(self, cb: Callable[[str, dict[str, Any]], None]) -> None:
        self._apply_stage_cb = cb

    def bind_apply_material(self, cb: Callable[[str, str, dict[str, Any]], None]) -> None:
        self._apply_material_cb = cb

    def bind_apply_assignments(self, cb: Callable[[list[dict[str, Any]]], None]) -> None:
        self._apply_assignments_cb = cb

    def bind_apply_global_output_requests(self, cb: Callable[[list[dict[str, Any]]], None]) -> None:
        self._apply_global_output_requests_cb = cb

    def show_empty(self) -> None:
        self._stack.setCurrentWidget(self._page_empty)

    def show_info(
        self,
        title: str,
        fields: list[tuple[str, str]],
        details: str | None = None,
        cards: list[tuple[str, str]] | None = None,
    ) -> None:
        self._info_title.setText(title or "Info")
        self._info_details.setText(details or "")
        self._clear_form(self._info_form)
        self._clear_layout(self._info_cards_layout)
        if cards:
            for key, value in cards:
                self._info_cards_layout.addWidget(self._make_info_card(key, value))
            self._info_cards_layout.addStretch(1)
        self._info_cards.setVisible(bool(cards))
        if not fields:
            self._add_form_row(self._info_form, "Info", "(no details)")
        else:
            for key, value in fields:
                self._add_form_row(self._info_form, key, value)
        self._stack.setCurrentWidget(self._page_info)

    def _clear_layout(self, layout) -> None:  # noqa: ANN001
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _clear_form(self, form: QFormLayout) -> None:
        while form.rowCount():
            form.removeRow(0)

    def _make_info_card(self, title: str, value: str) -> QWidget:
        from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout  # type: ignore

        card = QFrame()
        card.setStyleSheet(
            "QFrame { border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px; }"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 6, 8, 6)
        lab_title = QLabel(str(title))
        lab_title.setStyleSheet("color: #6b7280; font-size: 11px;")
        lab_val = QLabel(str(value))
        lab_val.setStyleSheet("font-weight: 600; font-size: 12px;")
        lay.addWidget(lab_title)
        lay.addWidget(lab_val)
        return card

    def _add_form_row(self, form: QFormLayout, key: str, value: str) -> None:
        from PySide6.QtWidgets import QLabel  # type: ignore

        key_label = QLabel(str(key))
        key_label.setStyleSheet("color: #374151; font-weight: 600;")
        val_label = QLabel(str(value))
        val_label.setTextInteractionFlags(self._Qt.TextSelectableByMouse)
        val_label.setWordWrap(True)
        form.addRow(key_label, val_label)

    def show_model(self, request: dict[str, Any]) -> None:
        model = request.get("model", {}) if isinstance(request.get("model"), dict) else {}
        mode = model.get("mode", "plane_strain")
        idx = self._mode.findData(mode)
        if idx >= 0:
            self._mode.setCurrentIndex(idx)
        self._apply_capabilities_to_model_combo()
        gravity = model.get("gravity", [0.0, -9.81])
        try:
            gx, gy = float(gravity[0]), float(gravity[1])
        except Exception:
            gx, gy = 0.0, -9.81
        self._gx.setValue(gx)
        self._gy.setValue(gy)
        self._stack.setCurrentWidget(self._page_model)

    def show_stage(self, stage_index: int, stage: dict[str, Any]) -> None:
        self._current_stage_index = stage_index
        self._current_stage_uid = str(stage.get("uid", "")) if isinstance(stage, dict) else None
        self._stage_id.setText(str(stage.get("id", f"stage_{stage_index+1}")))
        at = stage.get("analysis_type", "static")
        idx = self._analysis_type.findData(at)
        if idx >= 0:
            self._analysis_type.setCurrentIndex(idx)
        self._apply_capabilities_to_stage_combo()
        self._num_steps.setValue(int(stage.get("num_steps", 1)))
        self._dt.setValue(float(stage.get("dt", 1.0)))

        self._stage_out_editor.set_options(self._outreq_options())
        out_req = stage.get("output_requests", [])
        self._stage_out_editor.set_requests(out_req if isinstance(out_req, list) else [])
        self._validate_stage_outputs()

        self._bcs_editor.set_set_options(self._available_sets)
        self._loads_editor.set_set_options(self._available_sets)
        bcs = stage.get("bcs", [])
        self._bcs_editor.set_items(bcs if isinstance(bcs, list) else [])
        loads = stage.get("loads", [])
        self._loads_editor.set_items(loads if isinstance(loads, list) else [])

        self._stack.setCurrentWidget(self._page_stage)

    def show_material(self, material_id: str, material: dict[str, Any]) -> None:
        self._current_material_id = material_id
        self._mat_id.setText(material_id)
        self._mat_model_name.setText(str(material.get("model_name", "")))
        params = material.get("parameters", {})
        try:
            self._mat_params.setPlainText(json.dumps(params, indent=2, ensure_ascii=False))
        except Exception:
            self._mat_params.setPlainText("{}")
        self._stack.setCurrentWidget(self._page_material)

    def show_assignments(self, request: dict[str, Any]) -> None:
        assigns = request.get("assignments", [])
        self._assign_editor.set_options(self._assign_options())
        self._assign_editor.set_assignments(assigns if isinstance(assigns, list) else [])
        self._validate_assignments()
        self._stack.setCurrentWidget(self._page_assignments)

    def show_global_output_requests(self, request: dict[str, Any]) -> None:
        self._global_out_editor.set_options(self._outreq_options())
        out = request.get("output_requests", [])
        self._global_out_editor.set_requests(out if isinstance(out, list) else [])
        self._stack.setCurrentWidget(self._page_global_out)

    def _on_apply_model(self) -> None:
        if not self._apply_model_cb:
            return
        self._apply_model_cb(str(self._mode.currentData()), float(self._gx.value()), float(self._gy.value()))

    def _on_apply_stage(self) -> None:
        if not self._current_stage_uid or not self._apply_stage_cb:
            return
        out_req = self._stage_out_editor.requests()

        bcs = self._bcs_editor.items()
        loads = self._loads_editor.items()
        patch = {
            "analysis_type": str(self._analysis_type.currentData()),
            "num_steps": int(self._num_steps.value()),
            "dt": float(self._dt.value()),
            "output_requests": out_req,
            "bcs": bcs,
            "loads": loads,
        }
        self._apply_stage_cb(self._current_stage_uid, patch)
        self._validate_stage_outputs()

    def _on_apply_material(self) -> None:
        if self._current_material_id is None or not self._apply_material_cb:
            return
        model_name = self._mat_model_name.text().strip()
        try:
            params = json.loads(self._mat_params.toPlainText() or "{}")
            if not isinstance(params, dict):
                raise ValueError("parameters must be an object")
        except Exception:
            params = {}
        self._apply_material_cb(self._current_material_id, model_name, params)

    def _assign_options(self):
        from geohpem.gui.widgets.assignments_editor import AssignmentOptions

        return AssignmentOptions(element_sets=getattr(self, "_element_sets", []), materials=sorted(list((getattr(self, "_materials", set()) or set()))))

    def set_available_element_sets(self, pairs: list[tuple[str, str]]) -> None:
        self._element_sets = list(pairs)
        try:
            self._assign_editor.set_options(self._assign_options())
        except Exception:
            pass

    def set_available_materials(self, materials: list[str]) -> None:
        self._materials = set(materials)
        try:
            self._assign_editor.set_options(self._assign_options())
        except Exception:
            pass

    def _validate_assignments(self) -> None:
        # Best-effort hints for missing references.
        opts = self._assign_options()
        es_names = {n for n, _ct in opts.element_sets}
        es_pairs = set(opts.element_sets)
        mats = set(opts.materials)
        bad_es: set[str] = set()
        bad_mat: set[str] = set()
        bad_pair: set[str] = set()
        for a in self._assign_editor.assignments():
            es = a.get("element_set")
            mid = a.get("material_id")
            ct = a.get("cell_type")
            if isinstance(es, str) and es and es not in es_names and es_names:
                bad_es.add(es)
            if isinstance(es, str) and isinstance(ct, str) and es and ct and es_pairs and (es, ct) not in es_pairs:
                bad_pair.add(f"{es}:{ct}")
            if isinstance(mid, str) and mid and mid not in mats and mats:
                bad_mat.add(mid)
        parts = []
        if bad_es:
            parts.append(f"Missing element_set: {sorted(bad_es)}")
        if bad_pair:
            parts.append(f"cell_type mismatch: {sorted(bad_pair)}")
        if bad_mat:
            parts.append(f"Missing material_id: {sorted(bad_mat)}")
        self._assign_hint.setText(" | ".join(parts))

    def _on_apply_assignments(self) -> None:
        if not self._apply_assignments_cb:
            return
        assigns = self._assign_editor.assignments()
        self._apply_assignments_cb(assigns)
        self._validate_assignments()

    def _on_apply_global_output_requests(self) -> None:
        if not self._apply_global_output_requests_cb:
            return
        self._apply_global_output_requests_cb(self._global_out_editor.requests())
