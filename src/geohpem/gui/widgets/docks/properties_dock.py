from __future__ import annotations

import json
from typing import Any


class PropertiesDock:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QDockWidget, QPlainTextEdit  # type: ignore

        self.dock = QDockWidget("Properties")
        self.dock.setObjectName("dock_properties")
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.dock.setWidget(self.editor)

    def set_object(self, obj: Any) -> None:
        try:
            text = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        except Exception:
            text = repr(obj)
        self.editor.setPlainText(text)

