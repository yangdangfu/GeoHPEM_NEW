from __future__ import annotations

from pathlib import Path
from typing import Any


class ProjectDock:
    def __init__(self) -> None:
        from PySide6.QtCore import Signal  # type: ignore
        from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QPushButton  # type: ignore

        class _Signals(QWidget):
            case_open_requested = Signal(Path)
            output_open_requested = Signal(Path)

        self._signals = _Signals()
        self.case_open_requested = self._signals.case_open_requested
        self.output_open_requested = self._signals.output_open_requested

        self.dock = QDockWidget("Project")
        self.dock.setObjectName("dock_project")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_open_out = QPushButton("Open out/ folder")
        btn_layout.addWidget(self.btn_open_out)
        layout.addWidget(btn_row)

        self.btn_open_out.clicked.connect(self._open_out_folder)

        self._case_dir: Path | None = None
        self._request: dict[str, Any] | None = None
        self._mesh: dict[str, Any] | None = None

    def set_case(self, case_dir: Path, request: dict[str, Any], mesh: dict[str, Any]) -> None:
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        self._case_dir = case_dir
        self._request = request
        self._mesh = mesh

        self.tree.clear()
        root = QTreeWidgetItem([case_dir.name])
        self.tree.addTopLevelItem(root)
        root.addChild(QTreeWidgetItem(["request.json"]))
        root.addChild(QTreeWidgetItem(["mesh.npz"]))
        root.addChild(QTreeWidgetItem(["out/"]))
        root.setExpanded(True)

    def _open_out_folder(self) -> None:
        if not self._case_dir:
            return
        out_dir = self._case_dir / "out"
        self.output_open_requested.emit(out_dir)

