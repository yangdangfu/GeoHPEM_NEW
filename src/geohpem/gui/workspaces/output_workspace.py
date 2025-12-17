from __future__ import annotations

from typing import Any


class OutputWorkspace:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QLabel, QListWidget, QSplitter, QVBoxLayout, QWidget  # type: ignore

        self._meta: dict[str, Any] | None = None

        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        splitter = QSplitter()
        layout.addWidget(splitter)

        self.registry_list = QListWidget()
        self.detail = QLabel("Select a registry item to inspect (MVP placeholder)")

        splitter.addWidget(self.registry_list)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(1, 1)

        self.registry_list.currentRowChanged.connect(self._on_registry_selected)

    def set_result(self, meta: dict[str, Any], arrays: dict[str, Any]) -> None:
        self._meta = meta
        self.registry_list.clear()
        for item in meta.get("registry", []):
            name = item.get("name", "<unnamed>")
            loc = item.get("location", "?")
            self.registry_list.addItem(f"{name} ({loc})")
        self.detail.setText("Result loaded. Registry populated.")

    def _on_registry_selected(self, row: int) -> None:
        if not self._meta or row < 0:
            return
        reg = self._meta.get("registry", [])
        if row >= len(reg):
            return
        item = reg[row]
        lines = [
            f"name: {item.get('name')}",
            f"location: {item.get('location')}",
            f"shape: {item.get('shape')}",
            f"unit: {item.get('unit')}",
            f"npz_pattern: {item.get('npz_pattern')}",
        ]
        self.detail.setText("\n".join(lines))

