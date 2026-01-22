from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from geohpem.util.ids import new_uid


@dataclass(frozen=True, slots=True)
class AssignmentOptions:
    element_sets: list[tuple[str, str]]  # (name, cell_type)
    materials: list[str]


class AssignmentsEditor:
    """
    Table editor for request.assignments.

    Each assignment minimally includes:
    - element_set (name)
    - cell_type (tri3/quad4/...)
    - material_id

    Preserves unknown fields per row via the stored base dict.
    """

    COL_UID = 0
    COL_ELEMENT_SET = 1
    COL_CELL_TYPE = 2
    COL_MATERIAL = 3
    COL_EXTRA = 4

    def __init__(self, parent) -> None:  # noqa: ANN001
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (
            QAbstractItemView,  # type: ignore
            QComboBox,
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QComboBox = QComboBox
        self._QTableWidgetItem = QTableWidgetItem
        from geohpem.gui.widgets.json_editor import JsonEditorWidget

        self.widget = QWidget(parent)
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(QLabel("Assignments (material mapping)"))
        self.btn_add = QPushButton("Add")
        self.btn_delete = QPushButton("Delete")
        self.btn_sync = QPushButton("JSON -> Table")
        hl.addStretch(1)
        hl.addWidget(self.btn_add)
        hl.addWidget(self.btn_delete)
        hl.addWidget(self.btn_sync)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["uid", "element_set", "cell_type", "material_id", "extra(json)"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.table, "Table")

        self.json_edit = JsonEditorWidget(show_toolbar=False)
        self.tabs.addTab(self.json_edit, "JSON")

        self._options = AssignmentOptions(element_sets=[], materials=[])

        self.btn_add.clicked.connect(self._on_add)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_sync.clicked.connect(self._on_sync_json_to_table)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if index == self.tabs.indexOf(self.json_edit):
            try:
                self.json_edit.set_data(self.assignments())
            except Exception:
                pass

    def set_options(self, options: AssignmentOptions) -> None:
        self._options = options
        # Refresh existing combos to include new options.
        for row in range(self.table.rowCount()):
            cb_es = self.table.cellWidget(row, self.COL_ELEMENT_SET)
            cb_ct = self.table.cellWidget(row, self.COL_CELL_TYPE)
            cb_m = self.table.cellWidget(row, self.COL_MATERIAL)
            if cb_es is not None:
                self._populate_element_set_combo(cb_es, str(cb_es.currentText()))
            if cb_ct is not None:
                self._populate_cell_type_combo(cb_ct, str(cb_ct.currentText()))
            if cb_m is not None:
                self._populate_material_combo(cb_m, str(cb_m.currentText()))

    def set_assignments(self, assignments: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        normalized: list[dict[str, Any]] = []
        for it in assignments:
            if not isinstance(it, dict):
                continue
            uid = it.get("uid")
            if not isinstance(uid, str) or not uid:
                it = dict(it)
                it["uid"] = new_uid("assign")
            normalized.append(it)

        for it in normalized:
            self._append_row(it)

        try:
            self.json_edit.set_data(normalized)
        except Exception:
            self.json_edit.set_data([])

    def assignments(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            it_uid = self.table.item(row, self.COL_UID)
            if it_uid is None:
                continue
            base = it_uid.data(self._Qt.UserRole)
            obj = dict(base) if isinstance(base, dict) else {}

            uid = str(it_uid.text()).strip() or new_uid("assign")
            obj["uid"] = uid

            es = self._combo_text(row, self.COL_ELEMENT_SET)
            ct = self._combo_text(row, self.COL_CELL_TYPE)
            mid = self._combo_text(row, self.COL_MATERIAL)
            if es:
                obj["element_set"] = es
            if ct:
                obj["cell_type"] = ct
            if mid:
                obj["material_id"] = mid

            extra_txt = self._text(row, self.COL_EXTRA)
            if extra_txt.strip():
                try:
                    extra = json.loads(extra_txt)
                    if isinstance(extra, dict):
                        # merge extra keys without overriding core fields
                        for k, v in extra.items():
                            if k in ("uid", "element_set", "cell_type", "material_id"):
                                continue
                            obj[k] = v
                except Exception:
                    # ignore invalid extra json
                    pass

            out.append(obj)

        try:
            self.json_edit.set_data(out)
        except Exception:
            pass
        return out

    def _text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return str(it.text()).strip() if it is not None else ""

    def _combo_text(self, row: int, col: int) -> str:
        cb = self.table.cellWidget(row, col)
        if cb is None:
            return ""
        try:
            return str(cb.currentText()).strip()
        except Exception:
            return ""

    def _append_row(self, obj: dict[str, Any]) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        uid = (
            str(obj.get("uid", ""))
            if isinstance(obj.get("uid"), str)
            else new_uid("assign")
        )
        it_uid = self._QTableWidgetItem(uid)
        it_uid.setFlags(it_uid.flags() & ~self._Qt.ItemIsEditable)
        it_uid.setData(self._Qt.UserRole, dict(obj))
        self.table.setItem(r, self.COL_UID, it_uid)

        cb_es = self._QComboBox()
        cb_es.setEditable(True)
        self._populate_element_set_combo(cb_es, str(obj.get("element_set", "")))
        self.table.setCellWidget(r, self.COL_ELEMENT_SET, cb_es)

        cb_ct = self._QComboBox()
        cb_ct.setEditable(True)
        self._populate_cell_type_combo(cb_ct, str(obj.get("cell_type", "")))
        self.table.setCellWidget(r, self.COL_CELL_TYPE, cb_ct)

        cb_m = self._QComboBox()
        cb_m.setEditable(True)
        self._populate_material_combo(cb_m, str(obj.get("material_id", "")))
        self.table.setCellWidget(r, self.COL_MATERIAL, cb_m)

        # Extra keys snapshot (excluding core fields)
        extra: dict[str, Any] = {}
        for k, v in obj.items():
            if k in ("uid", "element_set", "cell_type", "material_id"):
                continue
            extra[k] = v
        extra_txt = json.dumps(extra, ensure_ascii=False) if extra else ""
        self.table.setItem(r, self.COL_EXTRA, self._QTableWidgetItem(extra_txt))

    def _populate_element_set_combo(self, combo, current: str) -> None:  # noqa: ANN001
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        # element set names (unique)
        names = sorted({n for n, _ct in self._options.element_sets if n})
        for n in names:
            combo.addItem(n)
        if current and combo.findText(current) < 0:
            combo.addItem(current)
        if current:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _populate_cell_type_combo(self, combo, current: str) -> None:  # noqa: ANN001
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        cts = sorted({ct for _n, ct in self._options.element_sets if ct})
        # common fallbacks
        for ct in ("tri3", "quad4"):
            if ct not in cts:
                cts.append(ct)
        for ct in cts:
            combo.addItem(ct)
        if current and combo.findText(current) < 0:
            combo.addItem(current)
        if current:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _populate_material_combo(self, combo, current: str) -> None:  # noqa: ANN001
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        for m in self._options.materials:
            combo.addItem(m)
        if current and combo.findText(current) < 0:
            combo.addItem(current)
        if current:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _on_add(self) -> None:
        default_es = (
            self._options.element_sets[0][0] if self._options.element_sets else ""
        )
        default_ct = (
            self._options.element_sets[0][1] if self._options.element_sets else "tri3"
        )
        default_m = self._options.materials[0] if self._options.materials else ""
        obj: dict[str, Any] = {
            "uid": new_uid("assign"),
            "element_set": default_es,
            "cell_type": default_ct,
            "material_id": default_m,
        }
        self._append_row(obj)
        self.table.selectRow(self.table.rowCount() - 1)

    def _on_delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)

    def _on_sync_json_to_table(self) -> None:
        try:
            data = self.json_edit.data()
            if not isinstance(data, list):
                raise ValueError("Expected a JSON list")
        except Exception as exc:
            self._QMessageBox.information(
                self.widget, "JSON -> Table", f"Invalid JSON:\n{exc}"
            )
            return
        cleaned: list[dict[str, Any]] = []
        for it in data:
            if isinstance(it, dict):
                cleaned.append(it)
        self.set_assignments(cleaned)
        try:
            self.tabs.setCurrentIndex(self.tabs.indexOf(self.table))
        except Exception:
            pass
