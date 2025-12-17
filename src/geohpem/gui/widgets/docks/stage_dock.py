from __future__ import annotations

from typing import Any


class StageDock:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QDockWidget, QListWidget  # type: ignore

        self.dock = QDockWidget("Stages")
        self.dock.setObjectName("dock_stages")
        self.list = QListWidget()
        self.dock.setWidget(self.list)

    def set_stages(self, stages: list[dict[str, Any]]) -> None:
        self.list.clear()
        for i, s in enumerate(stages):
            sid = s.get("id", f"stage_{i+1}")
            at = s.get("analysis_type", "?")
            self.list.addItem(f"{sid} [{at}]")

