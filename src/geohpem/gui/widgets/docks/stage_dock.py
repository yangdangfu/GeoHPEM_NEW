from __future__ import annotations

import json
from typing import Any


def _stage_diff(prev: dict[str, Any] | None, cur: dict[str, Any]) -> str:
    if prev is None:
        return "First stage."

    keys = [
        "analysis_type",
        "num_steps",
        "dt",
        "activate",
        "deactivate",
        "bcs",
        "loads",
        "output_requests",
    ]
    lines: list[str] = []
    for k in keys:
        a = prev.get(k)
        b = cur.get(k)
        if a == b:
            continue
        if k in ("bcs", "loads", "output_requests"):
            la = len(a) if isinstance(a, list) else 0
            lb = len(b) if isinstance(b, list) else 0
            lines.append(f"{k}: {la} -> {lb}")
        else:
            lines.append(f"{k}: {a!r} -> {b!r}")
    return "\n".join(lines) if lines else "No changes vs previous stage."


class StageDock:
    def __init__(self) -> None:
        from PySide6.QtCore import Signal  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QDockWidget,
            QHBoxLayout,
            QListWidget,
            QPlainTextEdit,
            QPushButton,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )

        class _Signals(QWidget):
            stage_selected = Signal(str)  # uid
            add_stage = Signal()
            copy_stage = Signal(str)  # uid
            delete_stage = Signal(str)  # uid

        self._signals = _Signals()
        self.stage_selected = self._signals.stage_selected
        self.add_stage = self._signals.add_stage
        self.copy_stage = self._signals.copy_stage
        self.delete_stage = self._signals.delete_stage

        self.dock = QDockWidget("Stages")
        self.dock.setObjectName("dock_stages")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        toolbar = QWidget()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(0, 0, 0, 0)
        self.btn_add = QPushButton("Add")
        self.btn_copy = QPushButton("Copy")
        self.btn_del = QPushButton("Delete")
        tl.addWidget(self.btn_add)
        tl.addWidget(self.btn_copy)
        tl.addWidget(self.btn_del)
        tl.addStretch(1)
        layout.addWidget(toolbar)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        self.list = QListWidget()
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)

        splitter.addWidget(self.list)
        splitter.addWidget(self.diff)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        self._stages: list[dict[str, Any]] = []

        self.list.currentRowChanged.connect(self._on_row_changed)
        # Clicking an already-selected row does not emit currentRowChanged.
        # Ensure users can re-select a stage (e.g., when only one stage exists)
        # and still drive Properties updates.
        try:
            self.list.itemClicked.connect(lambda *_: self._on_row_changed(self.list.currentRow()))
        except Exception:
            pass
        self.btn_add.clicked.connect(lambda: self.add_stage.emit())
        self.btn_copy.clicked.connect(self._on_copy)
        self.btn_del.clicked.connect(self._on_delete)

    def set_stages(self, stages: list[dict[str, Any]]) -> None:
        self._stages = [s for s in stages if isinstance(s, dict)]
        self.list.clear()
        for i, s in enumerate(self._stages):
            sid = s.get("id", f"stage_{i+1}")
            at = s.get("analysis_type", "?")
            self.list.addItem(f"{sid} [{at}]")
        if self._stages:
            self.list.setCurrentRow(0)
            # Ensure Properties is updated even if the first row is already current.
            self._on_row_changed(0)

    def select_stage(self, index: int) -> None:
        if index < 0:
            return
        if index >= self.list.count():
            return
        self.list.setCurrentRow(index)

    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._stages):
            self.diff.setPlainText("")
            return
        prev = self._stages[row - 1] if row - 1 >= 0 else None
        cur = self._stages[row]
        self.diff.setPlainText(_stage_diff(prev, cur))
        uid = str(cur.get("uid", ""))
        if uid:
            self.stage_selected.emit(uid)

    def _on_copy(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        uid = str(self._stages[row].get("uid", ""))
        if uid:
            self.copy_stage.emit(uid)

    def _on_delete(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        uid = str(self._stages[row].get("uid", ""))
        if uid:
            self.delete_stage.emit(uid)
