from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


from geohpem.util.ids import new_uid


@dataclass(frozen=True, slots=True)
class StageItemTableConfig:
    kind: str  # "bc" | "load"
    uid_prefix: str  # "bc" | "load"
    title: str
    default_field: str
    default_type: str


class StageItemTableEditor:
    """
    Table editor for stage.bcs or stage.loads.

    Design goals:
    - Keep stable uid (generate if missing).
    - Preserve unknown fields by carrying an original dict per row and only updating known keys.
    - Provide a set-name dropdown (editable combo).
    """

    COL_UID = 0
    COL_FIELD = 1
    COL_TYPE = 2
    COL_SET = 3
    COL_VALUE = 4

    def __init__(self, parent, *, config: StageItemTableConfig) -> None:  # noqa: ANN001
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QAbstractItemView,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QTableWidgetItem = QTableWidgetItem
        self._QComboBox = QComboBox

        self.config = config
        self.widget = QWidget(parent)
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(QLabel(config.title))
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

        # Table tab
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["uid", "field", "type", "set", "value"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.table, "Table")

        # JSON tab (advanced)
        self.json_edit = QPlainTextEdit()
        self.json_edit.setPlaceholderText("JSON list (advanced). Click 'JSON -> Table' to apply.")
        self.tabs.addTab(self.json_edit, "JSON")

        self._set_options: list[str] = []

        self.btn_add.clicked.connect(self._on_add)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_sync.clicked.connect(self._on_sync_json_to_table)

    def set_set_options(self, names: list[str]) -> None:
        self._set_options = list(names)
        # Update existing comboboxes.
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, self.COL_SET)
            if cb is None:
                continue
            try:
                current = str(cb.currentText())
            except Exception:
                current = ""
            self._populate_set_combo(cb, current)

    def set_items(self, items: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        normalized: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            uid = it.get("uid")
            if not isinstance(uid, str) or not uid:
                it = dict(it)
                it["uid"] = new_uid(self.config.uid_prefix)
            normalized.append(it)

        for it in normalized:
            self._append_row(it)

        # also refresh JSON view
        try:
            self.json_edit.setPlainText(json.dumps(normalized, indent=2, ensure_ascii=False))
        except Exception:
            self.json_edit.setPlainText("[]")

    def items(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            uid_item = self.table.item(row, self.COL_UID)
            if uid_item is None:
                continue
            base = uid_item.data(self._Qt.UserRole)
            if isinstance(base, dict):
                obj = dict(base)
            else:
                obj = {}

            uid = str(uid_item.text()).strip()
            if not uid:
                uid = new_uid(self.config.uid_prefix)
            obj["uid"] = uid

            field = self._text(row, self.COL_FIELD)
            if field:
                obj["field"] = field

            typ = self._text(row, self.COL_TYPE)
            if typ:
                obj["type"] = typ

            set_name = self._set_text(row)
            if set_name:
                obj["set"] = set_name

            value_text = self._text(row, self.COL_VALUE)
            if value_text.strip():
                try:
                    obj["value"] = json.loads(value_text)
                except Exception:
                    # keep raw string if invalid JSON
                    obj["value"] = value_text

            out.append(obj)

        # Keep JSON tab in sync (read-only-ish)
        try:
            self.json_edit.setPlainText(json.dumps(out, indent=2, ensure_ascii=False))
        except Exception:
            pass
        return out

    def _text(self, row: int, col: int) -> str:
        it = self.table.item(row, col)
        return str(it.text()).strip() if it is not None else ""

    def _set_text(self, row: int) -> str:
        cb = self.table.cellWidget(row, self.COL_SET)
        if cb is None:
            return ""
        try:
            return str(cb.currentText()).strip()
        except Exception:
            return ""

    def _append_row(self, obj: dict[str, Any]) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        uid = str(obj.get("uid", "")) if isinstance(obj.get("uid"), str) else new_uid(self.config.uid_prefix)
        it_uid = self._QTableWidgetItem(uid)
        it_uid.setFlags(it_uid.flags() & ~self._Qt.ItemIsEditable)
        it_uid.setData(self._Qt.UserRole, dict(obj))
        self.table.setItem(r, self.COL_UID, it_uid)

        it_field = self._QTableWidgetItem(str(obj.get("field", "")))
        self.table.setItem(r, self.COL_FIELD, it_field)

        it_type = self._QTableWidgetItem(str(obj.get("type", "")))
        self.table.setItem(r, self.COL_TYPE, it_type)

        cb = self._QComboBox()
        cb.setEditable(True)
        self._populate_set_combo(cb, str(obj.get("set", "")))
        self.table.setCellWidget(r, self.COL_SET, cb)

        val = obj.get("value", "")
        try:
            if isinstance(val, (dict, list)):
                val_txt = json.dumps(val, ensure_ascii=False)
            else:
                val_txt = "" if val is None else str(val)
        except Exception:
            val_txt = "" if val is None else str(val)
        it_val = self._QTableWidgetItem(val_txt)
        self.table.setItem(r, self.COL_VALUE, it_val)

    def _populate_set_combo(self, combo, current: str) -> None:  # noqa: ANN001
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        for n in self._set_options:
            combo.addItem(n)
        if current and combo.findText(current) < 0:
            combo.addItem(current)
        if current:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _on_add(self) -> None:
        obj: dict[str, Any] = {
            "uid": new_uid(self.config.uid_prefix),
            "field": self.config.default_field,
            "type": self.config.default_type,
            "set": "",
            "value": [0.0, 0.0] if self.config.kind == "bc" else 0.0,
        }
        self._append_row(obj)
        self.table.selectRow(self.table.rowCount() - 1)

    def _on_delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)

    def _on_sync_json_to_table(self) -> None:
        text = self.json_edit.toPlainText() or "[]"
        try:
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON list")
        except Exception as exc:
            self._QMessageBox.information(self.widget, "JSON -> Table", f"Invalid JSON:\n{exc}")
            return
        cleaned: list[dict[str, Any]] = []
        for it in data:
            if not isinstance(it, dict):
                continue
            cleaned.append(it)
        self.set_items(cleaned)
