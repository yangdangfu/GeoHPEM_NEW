from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from geohpem.util.ids import new_uid


@dataclass(frozen=True, slots=True)
class OutputRequestOptions:
    names: list[str]


class OutputRequestsEditor:
    """
    Table editor for (stage|global) output_requests list.

    Columns:
    - uid (read-only)
    - name (combo, editable)
    - location (combo)
    - every_n (spinbox)
    - extra (json dict; merged into row without overwriting core fields)
    """

    COL_UID = 0
    COL_NAME = 1
    COL_LOCATION = 2
    COL_EVERY_N = 3
    COL_EXTRA = 4

    def __init__(self, parent, *, title: str) -> None:  # noqa: ANN001
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QAbstractItemView,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QSpinBox,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QComboBox = QComboBox
        self._QSpinBox = QSpinBox
        self._QTableWidgetItem = QTableWidgetItem

        self.widget = QWidget(parent)
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(QLabel(title))
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
        self.table.setHorizontalHeaderLabels(["uid", "name", "location", "every_n", "extra(json)"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.table, "Table")

        self.json_edit = QPlainTextEdit()
        self.json_edit.setPlaceholderText("JSON list (advanced). Click 'JSON -> Table' to apply.")
        self.tabs.addTab(self.json_edit, "JSON")

        self._options = OutputRequestOptions(names=[])

        self.btn_add.clicked.connect(self._on_add)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_sync.clicked.connect(self._on_sync_json_to_table)

    def set_options(self, options: OutputRequestOptions) -> None:
        self._options = options
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, self.COL_NAME)
            if cb is not None:
                self._populate_name_combo(cb, str(cb.currentText()))

    def set_requests(self, items: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        normalized: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            uid = it.get("uid")
            if not isinstance(uid, str) or not uid:
                it = dict(it)
                it["uid"] = new_uid("outreq")
            normalized.append(it)
        for it in normalized:
            self._append_row(it)
        try:
            self.json_edit.setPlainText(json.dumps(normalized, indent=2, ensure_ascii=False))
        except Exception:
            self.json_edit.setPlainText("[]")

    def requests(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            it_uid = self.table.item(row, self.COL_UID)
            if it_uid is None:
                continue
            base = it_uid.data(self._Qt.UserRole)
            obj = dict(base) if isinstance(base, dict) else {}

            uid = str(it_uid.text()).strip() or new_uid("outreq")
            obj["uid"] = uid

            name = self._combo_text(row, self.COL_NAME)
            loc = self._combo_text(row, self.COL_LOCATION)
            every = self._spin_value(row, self.COL_EVERY_N)
            if name:
                obj["name"] = name
            if loc:
                obj["location"] = loc
            obj["every_n"] = int(every) if every is not None else 1

            extra_txt = self._text(row, self.COL_EXTRA)
            if extra_txt.strip():
                try:
                    extra = json.loads(extra_txt)
                    if isinstance(extra, dict):
                        for k, v in extra.items():
                            if k in ("uid", "name", "location", "every_n"):
                                continue
                            obj[k] = v
                except Exception:
                    pass

            out.append(obj)

        try:
            self.json_edit.setPlainText(json.dumps(out, indent=2, ensure_ascii=False))
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

    def _spin_value(self, row: int, col: int) -> int | None:
        w = self.table.cellWidget(row, col)
        if w is None:
            return None
        try:
            return int(w.value())
        except Exception:
            return None

    def _append_row(self, obj: dict[str, Any]) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        uid = str(obj.get("uid", "")) if isinstance(obj.get("uid"), str) else new_uid("outreq")
        it_uid = self._QTableWidgetItem(uid)
        it_uid.setFlags(it_uid.flags() & ~self._Qt.ItemIsEditable)
        it_uid.setData(self._Qt.UserRole, dict(obj))
        self.table.setItem(r, self.COL_UID, it_uid)

        cb_name = self._QComboBox()
        cb_name.setEditable(True)
        self._populate_name_combo(cb_name, str(obj.get("name", "")))
        self.table.setCellWidget(r, self.COL_NAME, cb_name)

        cb_loc = self._QComboBox()
        cb_loc.addItem("node", "node")
        cb_loc.addItem("element", "element")
        cb_loc.addItem("ip", "ip")
        loc = str(obj.get("location", "node") or "node")
        cb_loc.setCurrentText(loc)
        self.table.setCellWidget(r, self.COL_LOCATION, cb_loc)

        sp = self._QSpinBox()
        sp.setRange(1, 1_000_000)
        sp.setValue(int(obj.get("every_n", 1) or 1))
        self.table.setCellWidget(r, self.COL_EVERY_N, sp)

        extra: dict[str, Any] = {}
        for k, v in obj.items():
            if k in ("uid", "name", "location", "every_n"):
                continue
            extra[k] = v
        extra_txt = json.dumps(extra, ensure_ascii=False) if extra else ""
        self.table.setItem(r, self.COL_EXTRA, self._QTableWidgetItem(extra_txt))

    def _populate_name_combo(self, combo, current: str) -> None:  # noqa: ANN001
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        for n in self._options.names:
            combo.addItem(n)
        if current and combo.findText(current) < 0:
            combo.addItem(current)
        if current:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _on_add(self) -> None:
        default_name = self._options.names[0] if self._options.names else ""
        obj: dict[str, Any] = {"uid": new_uid("outreq"), "name": default_name, "location": "node", "every_n": 1}
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
        cleaned: list[dict[str, Any]] = [it for it in data if isinstance(it, dict)]
        self.set_requests(cleaned)

