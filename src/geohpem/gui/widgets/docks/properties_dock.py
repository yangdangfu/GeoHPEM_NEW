from __future__ import annotations

import json
from typing import Any, Callable

from PySide6.QtWidgets import QLabel, QWidget


class PropertiesDock:
    """
    Minimal form-based property editor for MVP.
    """

    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QAbstractItemView,
            QComboBox,
            QDockWidget,
            QDoubleSpinBox,
            QFormLayout,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QInputDialog,
            QLabel,
            QLineEdit,
            QPlainTextEdit,
            QPushButton,
            QSpinBox,
            QStackedWidget,
            QTabWidget,
            QTreeWidget,
            QVBoxLayout,
        )

        self._Qt = Qt
        self._QInputDialog = QInputDialog
        self._QAbstractItemView = QAbstractItemView
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
        self._apply_page_layout(info_layout)
        info_header, self._info_header_title, self._info_header_subtitle = self._build_header("Info", "")
        info_layout.addWidget(info_header)
        self._info_cards = QWidget()
        self._info_cards_layout = QHBoxLayout(self._info_cards)
        self._info_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._info_cards_layout.setSpacing(8)
        info_layout.addWidget(self._info_cards)
        self._info_tree = QTreeWidget()
        self._info_tree.setColumnCount(2)
        self._info_tree.setHeaderLabels(["Property", "Value"])
        self._info_tree.setAlternatingRowColors(True)
        self._info_tree.setRootIsDecorated(True)
        self._info_tree.setUniformRowHeights(True)
        header = self._info_tree.header()
        header.setStretchLastSection(True)
        try:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        except Exception:
            pass
        info_layout.addWidget(self._info_tree, 1)
        self._stack.addWidget(self._page_info)

        # Page: model
        self._page_model = QWidget()
        model_layout = QVBoxLayout(self._page_model)
        self._apply_page_layout(model_layout)
        model_header, self._model_header_title, self._model_header_subtitle = self._build_header(
            "Model",
            "Global analysis settings for the project.",
        )
        model_layout.addWidget(model_header)
        self._cap_hint_model = QLabel("")
        self._cap_hint_model.setStyleSheet("color: #b45309;")  # amber-ish
        model_layout.addWidget(self._cap_hint_model)
        model_form = QFormLayout()
        self._configure_form_layout(model_form)
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
        self._add_footer_button(model_layout, self._btn_apply_model)
        model_layout.addStretch(1)
        self._stack.addWidget(self._page_model)

        # Page: stage
        self._page_stage = QWidget()
        stage_layout = QVBoxLayout(self._page_stage)
        self._apply_page_layout(stage_layout)
        stage_header, self._stage_header_title, self._stage_header_subtitle = self._build_header(
            "Stage",
            "Configure analysis, loads, and outputs.",
        )
        stage_layout.addWidget(stage_header)
        self._cap_hint_stage = QLabel("")
        self._cap_hint_stage.setStyleSheet("color: #b45309;")  # amber-ish
        stage_layout.addWidget(self._cap_hint_stage)
        stage_form = QFormLayout()
        self._configure_form_layout(stage_form)
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

        self._quick_group = QGroupBox("Quick Presets")
        ql = QGridLayout(self._quick_group)
        ql.setContentsMargins(6, 6, 6, 6)
        ql.setHorizontalSpacing(8)
        ql.setVerticalSpacing(6)
        self._btn_q_fix_bottom = QPushButton("Fix bottom")
        self._btn_q_fix_lr = QPushButton("Fix left/right")
        self._btn_q_roller = QPushButton("Roller...")
        self._btn_q_gravity = QPushButton("Gravity")
        self._btn_q_traction = QPushButton("Traction on top")
        self._btn_q_outputs = QPushButton("Default outputs")
        ql.addWidget(self._btn_q_fix_bottom, 0, 0)
        ql.addWidget(self._btn_q_fix_lr, 0, 1)
        ql.addWidget(self._btn_q_roller, 0, 2)
        ql.addWidget(self._btn_q_gravity, 1, 0)
        ql.addWidget(self._btn_q_traction, 1, 1)
        ql.addWidget(self._btn_q_outputs, 1, 2)
        stage_layout.addWidget(self._quick_group)

        from geohpem.gui.widgets.output_requests_editor import OutputRequestsEditor

        self._cap_hint_outputs = QLabel("")
        self._cap_hint_outputs.setStyleSheet("color: #b45309;")  # amber-ish
        stage_layout.addWidget(self._cap_hint_outputs)

        self._stage_out_editor = OutputRequestsEditor(self._page_stage, title="Stage output_requests")
        stage_layout.addWidget(self._stage_out_editor.widget, 1)

        from geohpem.gui.widgets.stage_table_editor import (
            StageItemTableConfig,
            StageItemTableEditor,
        )

        self._available_sets: list[str] = []
        self._bcs_editor = StageItemTableEditor(
            self._page_stage,
            config=StageItemTableConfig(
                kind="bc", uid_prefix="bc", title="Stage BCs", default_field="u", default_type="dirichlet"
            ),
        )
        stage_layout.addWidget(self._bcs_editor.widget, 1)

        self._loads_editor = StageItemTableEditor(
            self._page_stage,
            config=StageItemTableConfig(
                kind="load", uid_prefix="load", title="Stage Loads", default_field="p", default_type="neumann"
            ),
        )
        stage_layout.addWidget(self._loads_editor.widget, 1)

        self._btn_apply_stage = QPushButton("Apply")
        self._add_footer_button(stage_layout, self._btn_apply_stage)
        self._stack.addWidget(self._page_stage)

        # Page: material
        self._page_material = QWidget()
        mat_layout = QVBoxLayout(self._page_material)
        self._apply_page_layout(mat_layout)
        mat_header, self._mat_header_title, self._mat_header_subtitle = self._build_header(
            "Material",
            "Define constitutive model and parameters.",
        )
        mat_layout.addWidget(mat_header)
        mat_form = QFormLayout()
        self._configure_form_layout(mat_form)
        mat_layout.addLayout(mat_form)

        self._mat_id = QLineEdit()
        self._mat_id.setReadOnly(True)
        mat_form.addRow("Material ID", self._mat_id)

        self._mat_model_name = QComboBox()
        self._mat_model_name.setEditable(True)
        mat_form.addRow("Model", self._mat_model_name)

        self._mat_behavior = QLineEdit()
        self._mat_behavior.setReadOnly(True)
        mat_form.addRow("Behavior", self._mat_behavior)


        mat_buttons = QWidget()
        mbl = QHBoxLayout(mat_buttons)
        mbl.setContentsMargins(0, 0, 0, 0)
        self._btn_mat_add = QPushButton("Add param")
        self._btn_mat_add_child = QPushButton("Add child")
        self._btn_mat_delete = QPushButton("Delete")
        self._btn_mat_json_to_table = QPushButton("JSON -> Tree")
        mbl.addWidget(self._btn_mat_add)
        mbl.addWidget(self._btn_mat_add_child)
        mbl.addWidget(self._btn_mat_delete)
        mbl.addStretch(1)
        mbl.addWidget(self._btn_mat_json_to_table)
        mat_layout.addWidget(mat_buttons)

        self._mat_tabs = QTabWidget()
        self._mat_tree = QTreeWidget()
        self._mat_tree.setColumnCount(2)
        self._mat_tree.setHeaderLabels(["param", "value"])
        self._mat_tree.setAlternatingRowColors(True)
        self._mat_tree.setRootIsDecorated(True)
        self._mat_tree.setUniformRowHeights(True)
        try:
            header = self._mat_tree.header()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        except Exception:
            pass
        self._mat_tree.setEditTriggers(
            self._QAbstractItemView.DoubleClicked
            | self._QAbstractItemView.EditKeyPressed
            | self._QAbstractItemView.AnyKeyPressed
        )
        self._mat_tabs.addTab(self._mat_tree, "Tree")

        self._mat_params = QPlainTextEdit()
        self._mat_params.setPlaceholderText("{ ... }")
        self._mat_tabs.addTab(self._mat_params, "JSON")
        mat_layout.addWidget(self._mat_tabs, 1)

        self._btn_apply_material = QPushButton("Apply")
        self._add_footer_button(mat_layout, self._btn_apply_material)
        self._stack.addWidget(self._page_material)

        # Page: assignments
        from geohpem.gui.widgets.assignments_editor import AssignmentsEditor

        self._page_assignments = QWidget()
        asg_layout = QVBoxLayout(self._page_assignments)
        self._apply_page_layout(asg_layout)
        asg_header, self._asg_header_title, self._asg_header_subtitle = self._build_header(
            "Assignments",
            "Map element sets to materials.",
        )
        asg_layout.addWidget(asg_header)
        self._assign_hint = QLabel("")
        self._assign_hint.setStyleSheet("color: #b45309;")
        asg_layout.addWidget(self._assign_hint)
        self._assign_editor = AssignmentsEditor(self._page_assignments)
        asg_layout.addWidget(self._assign_editor.widget, 1)
        self._btn_apply_assign = QPushButton("Apply")
        self._add_footer_button(asg_layout, self._btn_apply_assign)
        self._stack.addWidget(self._page_assignments)

        # Page: global output requests
        from geohpem.gui.widgets.output_requests_editor import OutputRequestsEditor

        self._page_global_out = QWidget()
        g_layout = QVBoxLayout(self._page_global_out)
        self._apply_page_layout(g_layout)
        gout_header, self._gout_header_title, self._gout_header_subtitle = self._build_header(
            "Global Outputs",
            "Optional outputs shared by all stages.",
        )
        g_layout.addWidget(gout_header)
        g_layout.addWidget(QLabel("Global output_requests (optional)"))
        self._global_out_editor = OutputRequestsEditor(self._page_global_out, title="Global output_requests")
        g_layout.addWidget(self._global_out_editor.widget, 1)
        self._btn_apply_global_out = QPushButton("Apply")
        self._add_footer_button(g_layout, self._btn_apply_global_out)
        self._stack.addWidget(self._page_global_out)

        # Callbacks configured by MainWindow
        self._apply_model_cb: Callable[[str, float, float], None] | None = None
        self._apply_stage_cb: Callable[[str, dict[str, Any]], None] | None = None
        self._apply_material_cb: Callable[[str, str, dict[str, Any], str | None], None] | None = None
        self._apply_assignments_cb: Callable[[list[dict[str, Any]]], None] | None = None
        self._apply_global_output_requests_cb: Callable[[list[dict[str, Any]]], None] | None = None

        self._current_stage_index: int | None = None
        self._current_stage_uid: str | None = None
        self._solver_caps: dict[str, Any] | None = None
        self._current_material_id: str | None = None
        self._mat_param_meta: dict[str, dict[str, str]] = {}

        self._btn_apply_model.clicked.connect(self._on_apply_model)
        self._btn_apply_stage.clicked.connect(self._on_apply_stage)
        self._btn_apply_material.clicked.connect(self._on_apply_material)
        self._btn_mat_add.clicked.connect(self._on_material_add_row)
        self._btn_mat_add_child.clicked.connect(self._on_material_add_child)
        self._btn_mat_delete.clicked.connect(self._on_material_delete_row)
        self._btn_mat_json_to_table.clicked.connect(self._on_material_json_to_table)
        self._mat_tabs.currentChanged.connect(self._on_material_tab_changed)
        self._mat_model_name.currentTextChanged.connect(self._on_material_model_changed)
        self._btn_apply_assign.clicked.connect(self._on_apply_assignments)
        self._btn_apply_global_out.clicked.connect(self._on_apply_global_output_requests)
        self._btn_q_fix_bottom.clicked.connect(self._quick_fix_bottom)
        self._btn_q_fix_lr.clicked.connect(self._quick_fix_left_right)
        self._btn_q_roller.clicked.connect(self._quick_roller)
        self._btn_q_gravity.clicked.connect(self._quick_gravity)
        self._btn_q_traction.clicked.connect(self._quick_traction_top)
        self._btn_q_outputs.clicked.connect(self._quick_default_outputs)

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

    def bind_apply_material(self, cb: Callable[[str, str, dict[str, Any], str | None], None]) -> None:
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
        sections: list[tuple[str, list[tuple[str, str]]]] | None = None,
    ) -> None:
        self._info_header_title.setText(title or "Info")
        self._info_header_subtitle.setText(details or "")
        self._clear_layout(self._info_cards_layout)
        if cards:
            for key, value in cards:
                self._info_cards_layout.addWidget(self._make_info_card(key, value))
            self._info_cards_layout.addStretch(1)
        self._info_cards.setVisible(bool(cards))

        self._info_tree.clear()
        used_sections = sections
        if used_sections is None:
            used_sections = [("Details", fields)]
        if not used_sections:
            used_sections = [("Details", [("Info", "(no details)")])]

        from PySide6.QtGui import QFont  # type: ignore
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        for sec_title, sec_fields in used_sections:
            top = QTreeWidgetItem([sec_title or "Details", ""])
            font = QFont()
            font.setBold(True)
            top.setFont(0, font)
            try:
                top.setFirstColumnSpanned(True)
            except Exception:
                pass
            try:
                flags = top.flags()
                top.setFlags(flags & ~self._Qt.ItemIsSelectable)
            except Exception:
                pass
            if not sec_fields:
                sec_fields = [("Info", "(no details)")]
            for key, value in sec_fields:
                row = QTreeWidgetItem([str(key), str(value)])
                row.setToolTip(1, str(value))
                top.addChild(row)
            self._info_tree.addTopLevelItem(top)
        try:
            self._info_tree.expandAll()
        except Exception:
            pass

        self._stack.setCurrentWidget(self._page_info)

    def _build_header(self, title: str, subtitle: str) -> tuple[QWidget, QLabel, QLabel]:
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout  # type: ignore

        header = QFrame()
        header.setStyleSheet("QFrame { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; }")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(10, 8, 10, 8)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #6b7280;")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return header, title_label, subtitle_label

    def _apply_page_layout(self, layout) -> None:  # noqa: ANN001
        try:
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(8)
        except Exception:
            pass

    def _configure_form_layout(self, layout) -> None:  # noqa: ANN001
        try:
            layout.setFormAlignment(self._Qt.AlignLeft | self._Qt.AlignTop)
            layout.setLabelAlignment(self._Qt.AlignLeft | self._Qt.AlignVCenter)
            layout.setFieldGrowthPolicy(layout.ExpandingFieldsGrow)
            layout.setHorizontalSpacing(10)
            layout.setVerticalSpacing(6)
        except Exception:
            pass

    def _add_footer_button(self, layout, button) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import QHBoxLayout, QWidget  # type: ignore

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addStretch(1)
        rl.addWidget(button)
        layout.addWidget(row)

    def _clear_layout(self, layout) -> None:  # noqa: ANN001
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _make_info_card(self, title: str, value: str) -> QWidget:
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout  # type: ignore

        card = QFrame()
        card.setStyleSheet("QFrame { border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 6, 8, 6)
        lab_title = QLabel(str(title))
        lab_title.setStyleSheet("color: #6b7280; font-size: 11px;")
        lab_val = QLabel(str(value))
        lab_val.setStyleSheet("font-weight: 600; font-size: 12px;")
        lay.addWidget(lab_title)
        lay.addWidget(lab_val)
        return card

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
        try:
            self._model_header_subtitle.setText(f"Mode: {mode} | g=({gx:g}, {gy:g})")
        except Exception:
            pass
        self._stack.setCurrentWidget(self._page_model)

    def show_stage(self, stage_index: int, stage: dict[str, Any]) -> None:
        self._current_stage_index = stage_index
        self._current_stage_uid = str(stage.get("uid", "")) if isinstance(stage, dict) else None
        self._stage_id.setText(str(stage.get("id", f"stage_{stage_index+1}")))
        at = stage.get("analysis_type", "static")
        idx = self._analysis_type.findData(at)
        if idx >= 0:
            self._analysis_type.setCurrentIndex(idx)
        try:
            self._stage_header_subtitle.setText(f"{self._stage_id.text()} | {at}")
        except Exception:
            pass
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
        from geohpem.domain.material_catalog import behavior_for_model, behavior_label, model_meta

        self._current_material_id = material_id
        self._mat_id.setText(material_id)
        model_name = str(material.get("model_name", ""))
        behavior = behavior_for_model(model_name) or str(material.get("behavior", "custom"))

        self._mat_behavior.setText(behavior_label(behavior))
        self._refresh_material_model_options(model_name)

        self._update_material_header(model_name, behavior)
        self._mat_param_meta = model_meta(model_name)
        params = material.get("parameters", {})
        self._set_material_params(params if isinstance(params, dict) else {}, meta=self._mat_param_meta)
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

    def _require_stage(self) -> bool:
        if not self._current_stage_uid:
            try:
                from PySide6.QtWidgets import QMessageBox  # type: ignore

                QMessageBox.information(self.dock, "Stage", "Select a stage first.")
            except Exception:
                pass
            return False
        return True

    def _quick_set_name(self, candidates: list[str]) -> str | None:
        for name in candidates:
            if name in self._available_sets:
                return name
        return None

    def _add_stage_bc(self, item: dict[str, Any]) -> bool:
        items = self._bcs_editor.items()
        typ = str(item.get("type", ""))
        set_name = str(item.get("set", ""))
        for it in items:
            if str(it.get("type", "")) == typ and str(it.get("set", "")) == set_name:
                return False
        items.append(item)
        self._bcs_editor.set_items(items)
        return True

    def _add_stage_load(self, item: dict[str, Any]) -> bool:
        items = self._loads_editor.items()
        typ = str(item.get("type", ""))
        set_name = str(item.get("set", ""))
        for it in items:
            if str(it.get("type", "")) == typ and str(it.get("set", "")) == set_name:
                return False
        items.append(item)
        self._loads_editor.set_items(items)
        return True

    def _quick_fix_bottom(self) -> None:
        if not self._require_stage():
            return
        name = self._quick_set_name(["bottom", "boundary_bottom"])
        if not name:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            QMessageBox.information(self.dock, "Quick Preset", "No bottom set found (bottom/boundary_bottom).")
            return
        self._add_stage_bc({"type": "displacement", "field": "u", "set": name, "value": {"ux": 0.0, "uy": 0.0}})
        self._on_apply_stage()

    def _quick_fix_left_right(self) -> None:
        if not self._require_stage():
            return
        added = False
        for key in ("left", "boundary_left"):
            if key in self._available_sets:
                added = (
                    self._add_stage_bc({"type": "displacement", "field": "u", "set": key, "value": {"ux": 0.0}})
                    or added
                )
        for key in ("right", "boundary_right"):
            if key in self._available_sets:
                added = (
                    self._add_stage_bc({"type": "displacement", "field": "u", "set": key, "value": {"ux": 0.0}})
                    or added
                )
        if not added:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            QMessageBox.information(self.dock, "Quick Preset", "No left/right sets found.")
            return
        self._on_apply_stage()

    def _quick_roller(self) -> None:
        if not self._require_stage():
            return
        if not self._available_sets:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            QMessageBox.information(self.dock, "Roller", "No sets available.")
            return
        set_name, ok = self._QInputDialog.getItem(self.dock, "Roller", "Set:", self._available_sets, 0, False)
        if not ok:
            return
        axis, ok2 = self._QInputDialog.getItem(self.dock, "Roller", "Direction:", ["ux", "uy"], 0, False)
        if not ok2:
            return
        val = {"ux": 0.0} if axis == "ux" else {"uy": 0.0}
        self._add_stage_bc({"type": "displacement", "field": "u", "set": str(set_name), "value": val})
        self._on_apply_stage()

    def _quick_gravity(self) -> None:
        if not self._require_stage():
            return
        self._add_stage_load({"type": "gravity", "field": "u", "value": [0.0, -9.81]})
        self._on_apply_stage()

    def _quick_traction_top(self) -> None:
        if not self._require_stage():
            return
        name = self._quick_set_name(["top", "boundary_top"])
        if not name:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            QMessageBox.information(self.dock, "Quick Preset", "No top set found (top/boundary_top).")
            return
        self._add_stage_load({"type": "traction", "field": "u", "set": name, "value": [0.0, -1.0e5]})
        self._on_apply_stage()

    def _quick_default_outputs(self) -> None:
        if not self._require_stage():
            return
        items = self._stage_out_editor.requests()
        wanted = [("u", "node"), ("vm", "element"), ("p", "node")]
        allowed = self._allowed_output_names()

        def has_req(name: str, loc: str) -> bool:
            for it in items:
                if str(it.get("name", "")) == name and str(it.get("location", "")) == loc:
                    return True
            return False

        for name, loc in wanted:
            if allowed and name not in allowed:
                continue
            if has_req(name, loc):
                continue
            items.append({"name": name, "location": loc, "every_n": 1})
        self._stage_out_editor.set_requests(items)
        self._on_apply_stage()

    def _on_apply_material(self) -> None:
        if self._current_material_id is None or not self._apply_material_cb:
            return
        model_name = self._current_material_model_name()
        try:
            if self._mat_tabs.currentWidget() == self._mat_params:
                params = json.loads(self._mat_params.toPlainText() or "{}")
                if not isinstance(params, dict):
                    raise ValueError("parameters must be an object")
            else:
                params = self._material_params_from_tree()
        except Exception:
            params = {}
        from geohpem.domain.material_catalog import behavior_for_model

        behavior = behavior_for_model(model_name) or "custom"
        self._apply_material_cb(self._current_material_id, model_name, params, behavior)
        self._set_material_params(params, meta=self._mat_param_meta)

    def _assign_options(self):
        from geohpem.gui.widgets.assignments_editor import AssignmentOptions

        return AssignmentOptions(
            element_sets=getattr(self, "_element_sets", []),
            materials=sorted(list((getattr(self, "_materials", set()) or set()))),
        )

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

    def _set_material_params(self, params: dict[str, Any], *, meta: dict[str, dict[str, str]] | None = None) -> None:
        if meta is None:
            meta = self._mat_param_meta
        self._material_set_tree(params, meta=meta)
        try:
            self._mat_params.setPlainText(json.dumps(params, indent=2, ensure_ascii=False))
        except Exception:
            self._mat_params.setPlainText("{}")

    def _material_set_tree(self, params: dict[str, Any], *, meta: dict[str, dict[str, str]] | None = None) -> None:
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        self._mat_tree.clear()
        meta = meta or {}

        def meta_for(path_key: str) -> dict[str, str]:
            entry = meta.get(path_key)
            return entry if isinstance(entry, dict) else {}

        def add_node(parent, key, value, path: list[str]):  # noqa: ANN001
            path_key = ".".join(path)
            info = meta_for(path_key)
            label = info.get("label", "")
            tooltip = info.get("tooltip", "")
            item = QTreeWidgetItem([str(key), ""])
            if label or tooltip:
                tip = f"{label} — {tooltip}".strip(" —") if label or tooltip else ""
                if tip:
                    item.setToolTip(0, tip)
                    item.setToolTip(1, tip)
            if isinstance(value, dict):
                item.setData(0, self._Qt.UserRole, {"kind": "dict"})
                item.setFlags(item.flags() | self._Qt.ItemIsEditable)
                for k in sorted(value.keys()):
                    add_node(item, k, value.get(k), [*path, str(k)])
            elif isinstance(value, list):
                item.setData(0, self._Qt.UserRole, {"kind": "list"})
                item.setFlags(item.flags() | self._Qt.ItemIsEditable)
                for i, v in enumerate(value):
                    add_node(item, f"[{i}]", v, [*path, f"[{i}]"])
            else:
                item.setData(0, self._Qt.UserRole, {"kind": "value"})
                item.setFlags(item.flags() | self._Qt.ItemIsEditable)
                item.setText(1, self._format_material_value(value))
            if parent is None:
                self._mat_tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            return item

        for key in sorted(params.keys()):
            add_node(None, key, params.get(key), [str(key)])
        try:
            self._mat_tree.expandAll()
        except Exception:
            pass

    def _material_params_from_tree(self) -> dict[str, Any]:
        def parse_item(item) -> Any:  # noqa: ANN001
            kind = None
            try:
                meta = item.data(0, self._Qt.UserRole) or {}
                kind = meta.get("kind")
            except Exception:
                kind = None
            if kind == "dict" or (kind is None and item.childCount() > 0):
                out: dict[str, Any] = {}
                for i in range(item.childCount()):
                    ch = item.child(i)
                    key = str(ch.text(0)).strip()
                    if not key:
                        continue
                    out[key] = parse_item(ch)
                return out
            if kind == "list":
                children = []
                for i in range(item.childCount()):
                    ch = item.child(i)
                    label = str(ch.text(0)).strip()
                    try:
                        idx = int(label.strip("[]"))
                    except Exception:
                        idx = i
                    children.append((idx, parse_item(ch)))
                return [v for _i, v in sorted(children, key=lambda kv: kv[0])]
            return self._parse_material_value(str(item.text(1)))

        out: dict[str, Any] = {}
        for i in range(self._mat_tree.topLevelItemCount()):
            item = self._mat_tree.topLevelItem(i)
            key = str(item.text(0)).strip()
            if not key:
                continue
            out[key] = parse_item(item)
        return out

    def _format_material_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float, str, bool)):
            return str(value)
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    def _parse_material_value(self, text: str) -> Any:
        raw = str(text or "").strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def _on_material_add_row(self) -> None:
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        item = QTreeWidgetItem(["param", "0.0"])
        item.setData(0, self._Qt.UserRole, {"kind": "value"})
        item.setFlags(item.flags() | self._Qt.ItemIsEditable)
        self._mat_tree.addTopLevelItem(item)
        self._mat_tree.setCurrentItem(item)
        try:
            self._mat_tabs.setCurrentIndex(self._mat_tabs.indexOf(self._mat_tree))
        except Exception:
            pass

    def _on_material_delete_row(self) -> None:
        item = self._mat_tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            idx = self._mat_tree.indexOfTopLevelItem(item)
            if idx >= 0:
                self._mat_tree.takeTopLevelItem(idx)
        else:
            parent.removeChild(item)

    def _on_material_json_to_table(self) -> None:
        text = self._mat_params.toPlainText() or "{}"
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            QMessageBox.information(self.dock, "JSON -> Tree", f"Invalid JSON:\n{exc}")
            return
        self._material_set_tree(data, meta=self._mat_param_meta)
        try:
            self._mat_tabs.setCurrentIndex(self._mat_tabs.indexOf(self._mat_tree))
        except Exception:
            pass

    def _on_material_tab_changed(self, index: int) -> None:
        if self._mat_tabs.widget(index) == self._mat_params:
            try:
                params = self._material_params_from_tree()
                self._mat_params.setPlainText(json.dumps(params, indent=2, ensure_ascii=False))
            except Exception:
                pass

    def _on_material_add_child(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem  # type: ignore

        item = self._mat_tree.currentItem()
        if item is None:
            QMessageBox.information(self.dock, "Add Child", "Select a parameter to add a child.")
            return
        meta = item.data(0, self._Qt.UserRole) or {}
        kind = meta.get("kind")
        if kind not in ("dict", "list"):
            QMessageBox.information(self.dock, "Add Child", "Select a dict/list node to add a child.")
            return
        if kind == "list":
            key = f"[{item.childCount()}]"
        else:
            key = "param"
        child = QTreeWidgetItem([key, "0.0"])
        child.setData(0, self._Qt.UserRole, {"kind": "value"})
        child.setFlags(child.flags() | self._Qt.ItemIsEditable)
        item.addChild(child)
        item.setExpanded(True)
        self._mat_tree.setCurrentItem(child)

    def _on_material_model_changed(self) -> None:
        from geohpem.domain.material_catalog import behavior_for_model, behavior_label, model_defaults, model_meta

        model_name = self._current_material_model_name()
        behavior = behavior_for_model(model_name) or "custom"
        self._mat_behavior.setText(behavior_label(behavior))
        self._update_material_header(model_name, behavior)
        self._mat_param_meta = model_meta(model_name)

        defaults = model_defaults(model_name)
        if defaults:
            self._set_material_params(defaults, meta=self._mat_param_meta)
            return
        params = self._material_current_params()
        if params is None:
            return
        self._set_material_params(params, meta=self._mat_param_meta)

    def _material_has_params(self) -> bool:
        params = self._material_current_params()
        return bool(params)

    def _material_current_params(self) -> dict[str, Any] | None:
        if self._mat_tabs.currentWidget() == self._mat_params:
            try:
                data = json.loads(self._mat_params.toPlainText() or "{}")
                return data if isinstance(data, dict) else None
            except Exception:
                return None
        try:
            return self._material_params_from_tree()
        except Exception:
            return None

    def _current_material_model_name(self) -> str:
        try:
            text = str(self._mat_model_name.currentText()).strip()
        except Exception:
            text = ""
        try:
            data = self._mat_model_name.currentData()
            if isinstance(data, str) and data.strip():
                name = data.strip()
                try:
                    from geohpem.domain.material_catalog import model_by_name

                    if model_by_name(name) is not None:
                        return name
                except Exception:
                    return name
                if text and text == name:
                    return name
        except Exception:
            pass
        try:
            from geohpem.domain.material_catalog import model_by_name

            if text and model_by_name(text) is not None:
                return text
        except Exception:
            pass
        return text

    def _refresh_material_model_options(self, current: str) -> None:
        from geohpem.domain.material_catalog import all_models

        self._mat_model_name.blockSignals(True)
        self._mat_model_name.clear()
        models = all_models()
        for m in models:
            self._mat_model_name.addItem(m.label, m.name)
        if current and self._mat_model_name.findData(current) < 0:
            self._mat_model_name.addItem(current, current)
        idx = self._mat_model_name.findData(current) if current else -1
        if idx >= 0:
            self._mat_model_name.setCurrentIndex(idx)
        elif self._mat_model_name.count() > 0:
            self._mat_model_name.setCurrentIndex(0)
        self._mat_model_name.blockSignals(False)

    def _update_material_header(self, model_name: str, behavior: str) -> None:
        from geohpem.domain.material_catalog import behavior_label, model_by_name

        label = model_name or "custom"
        model = model_by_name(model_name)
        if model is not None:
            label = model.label
        beh_label = behavior_label(behavior)
        try:
            self._mat_header_subtitle.setText(
                f"Material ID: {self._current_material_id or ''} | {label} | {beh_label}"
            )
        except Exception:
            pass
