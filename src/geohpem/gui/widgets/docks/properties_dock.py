from __future__ import annotations

import json
from typing import Any, Callable


class PropertiesDock:
    """
    Minimal form-based property editor for MVP.
    """

    def __init__(self) -> None:
        from PySide6.QtWidgets import (
            QComboBox,
            QDockWidget,
            QDoubleSpinBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QPlainTextEdit,
            QSpinBox,
            QStackedWidget,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

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

        # Page: model
        self._page_model = QWidget()
        model_layout = QVBoxLayout(self._page_model)
        model_form = QFormLayout()
        model_layout.addLayout(model_form)

        self._mode = QComboBox()
        self._mode.addItem("Plane strain", "plane_strain")
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
        stage_form = QFormLayout()
        stage_layout.addLayout(stage_form)

        self._stage_id = QLineEdit()
        self._stage_id.setReadOnly(True)
        stage_form.addRow("Stage ID", self._stage_id)

        self._analysis_type = QComboBox()
        for v in ("static", "dynamic", "seepage_transient", "consolidation_u_p"):
            self._analysis_type.addItem(v, v)
        stage_form.addRow("Analysis Type", self._analysis_type)

        self._num_steps = QSpinBox()
        self._num_steps.setRange(1, 10_000_000)
        stage_form.addRow("Num Steps", self._num_steps)

        self._dt = QDoubleSpinBox()
        self._dt.setRange(0.0, 1e9)
        self._dt.setDecimals(9)
        stage_form.addRow("dt", self._dt)

        self._stage_output_json = QPlainTextEdit()
        self._stage_output_json.setPlaceholderText("Stage output_requests (JSON list)")
        stage_layout.addWidget(QLabel("Stage output_requests"))
        stage_layout.addWidget(self._stage_output_json)

        self._stage_bcs_json = QPlainTextEdit()
        self._stage_bcs_json.setPlaceholderText("Stage bcs (JSON list)")
        stage_layout.addWidget(QLabel("Stage bcs"))
        stage_layout.addWidget(self._stage_bcs_json)

        self._stage_loads_json = QPlainTextEdit()
        self._stage_loads_json.setPlaceholderText("Stage loads (JSON list)")
        stage_layout.addWidget(QLabel("Stage loads"))
        stage_layout.addWidget(self._stage_loads_json)

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

        # Callbacks configured by MainWindow
        self._apply_model_cb: Callable[[str, float, float], None] | None = None
        self._apply_stage_cb: Callable[[int, dict[str, Any]], None] | None = None
        self._apply_material_cb: Callable[[str, str, dict[str, Any]], None] | None = None

        self._current_stage_index: int | None = None
        self._current_material_id: str | None = None

        self._btn_apply_model.clicked.connect(self._on_apply_model)
        self._btn_apply_stage.clicked.connect(self._on_apply_stage)
        self._btn_apply_material.clicked.connect(self._on_apply_material)

        self.show_empty()

    def bind_apply_model(self, cb: Callable[[str, float, float], None]) -> None:
        self._apply_model_cb = cb

    def bind_apply_stage(self, cb: Callable[[int, dict[str, Any]], None]) -> None:
        self._apply_stage_cb = cb

    def bind_apply_material(self, cb: Callable[[str, str, dict[str, Any]], None]) -> None:
        self._apply_material_cb = cb

    def show_empty(self) -> None:
        self._stack.setCurrentWidget(self._page_empty)

    def show_model(self, request: dict[str, Any]) -> None:
        model = request.get("model", {}) if isinstance(request.get("model"), dict) else {}
        mode = model.get("mode", "plane_strain")
        idx = self._mode.findData(mode)
        if idx >= 0:
            self._mode.setCurrentIndex(idx)
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
        self._stage_id.setText(str(stage.get("id", f"stage_{stage_index+1}")))
        at = stage.get("analysis_type", "static")
        idx = self._analysis_type.findData(at)
        if idx >= 0:
            self._analysis_type.setCurrentIndex(idx)
        self._num_steps.setValue(int(stage.get("num_steps", 1)))
        self._dt.setValue(float(stage.get("dt", 1.0)))

        out_req = stage.get("output_requests", [])
        try:
            self._stage_output_json.setPlainText(json.dumps(out_req, indent=2, ensure_ascii=False))
        except Exception:
            self._stage_output_json.setPlainText("[]")

        bcs = stage.get("bcs", [])
        try:
            self._stage_bcs_json.setPlainText(json.dumps(bcs, indent=2, ensure_ascii=False))
        except Exception:
            self._stage_bcs_json.setPlainText("[]")

        loads = stage.get("loads", [])
        try:
            self._stage_loads_json.setPlainText(json.dumps(loads, indent=2, ensure_ascii=False))
        except Exception:
            self._stage_loads_json.setPlainText("[]")

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

    def _on_apply_model(self) -> None:
        if not self._apply_model_cb:
            return
        self._apply_model_cb(str(self._mode.currentData()), float(self._gx.value()), float(self._gy.value()))

    def _on_apply_stage(self) -> None:
        if self._current_stage_index is None or not self._apply_stage_cb:
            return
        try:
            out_req = json.loads(self._stage_output_json.toPlainText() or "[]")
            if not isinstance(out_req, list):
                raise ValueError("output_requests must be a list")
        except Exception:
            out_req = []

        try:
            bcs = json.loads(self._stage_bcs_json.toPlainText() or "[]")
            if not isinstance(bcs, list):
                raise ValueError("bcs must be a list")
        except Exception:
            bcs = []

        try:
            loads = json.loads(self._stage_loads_json.toPlainText() or "[]")
            if not isinstance(loads, list):
                raise ValueError("loads must be a list")
        except Exception:
            loads = []
        patch = {
            "analysis_type": str(self._analysis_type.currentData()),
            "num_steps": int(self._num_steps.value()),
            "dt": float(self._dt.value()),
            "output_requests": out_req,
            "bcs": bcs,
            "loads": loads,
        }
        self._apply_stage_cb(self._current_stage_index, patch)

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
