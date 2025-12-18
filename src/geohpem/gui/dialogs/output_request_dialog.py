from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OutputRequestDialogResult:
    output_requests: list[dict[str, Any]]


class OutputRequestDialog:
    def __init__(
        self,
        parent,
        *,
        capabilities: dict[str, Any] | None,
    ) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMessageBox,
            QSpinBox,
            QVBoxLayout,
        )

        self._QMessageBox = QMessageBox

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Add Output Requests")
        self._dialog.resize(520, 420)

        layout = QVBoxLayout(self._dialog)
        layout.addWidget(QLabel("Select outputs to request from solver (stage.output_requests)."))

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self._list, 1)

        form = QFormLayout()
        layout.addLayout(form)

        self._location = QComboBox()
        self._location.addItem("Node", "node")
        self._location.addItem("Element", "element")
        form.addRow("Location", self._location)

        self._every_n = QSpinBox()
        self._every_n.setRange(1, 1_000_000)
        self._every_n.setValue(1)
        form.addRow("Every N", self._every_n)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self._dialog.accept)
        buttons.rejected.connect(self._dialog.reject)

        names: list[str] = []
        if capabilities and isinstance(capabilities, dict):
            for key in ("results", "fields"):
                v = capabilities.get(key)
                if isinstance(v, list):
                    names.extend([str(x) for x in v if isinstance(x, str)])
        names = sorted({n for n in names if n})
        if not names:
            names = ["u", "p"]

        for n in names:
            item = QListWidgetItem(n)
            item.setSelected(n in ("u", "p"))
            self._list.addItem(item)

    def exec(self) -> OutputRequestDialogResult | None:
        from PySide6.QtWidgets import QDialog  # type: ignore

        if self._dialog.exec() != QDialog.Accepted:
            return None
        selected = [it.text().strip() for it in self._list.selectedItems() if it.text().strip()]
        if not selected:
            self._QMessageBox.information(self._dialog, "Output Requests", "Please select at least one field.")
            return None

        from geohpem.util.ids import new_uid

        location = str(self._location.currentData())
        every_n = int(self._every_n.value())
        reqs: list[dict[str, Any]] = []
        for n in selected:
            reqs.append({"uid": new_uid("outreq"), "name": n, "location": location, "every_n": every_n})
        return OutputRequestDialogResult(output_requests=reqs)

