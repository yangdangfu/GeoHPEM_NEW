from __future__ import annotations


class InputWorkspace:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget  # type: ignore

        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        layout.addWidget(QLabel("Input Workspace (MVP placeholder)"))
        layout.addStretch(1)

