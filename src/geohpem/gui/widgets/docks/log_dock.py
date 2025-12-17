from __future__ import annotations


class LogDock:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QDockWidget, QPlainTextEdit  # type: ignore

        self.dock = QDockWidget("Log")
        self.dock.setObjectName("dock_log")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.dock.setWidget(self.text)

    def append_info(self, message: str) -> None:
        self.text.appendPlainText(message)

    def attach_worker(self, worker) -> None:
        worker.log.connect(self.append_info)

