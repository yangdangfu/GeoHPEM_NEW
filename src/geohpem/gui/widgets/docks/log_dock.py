from __future__ import annotations


class LogDock:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Slot  # type: ignore
        from PySide6.QtWidgets import QDockWidget, QPlainTextEdit  # type: ignore

        self.dock = QDockWidget("Log")
        self.dock.setObjectName("dock_log")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.dock.setWidget(self.text)

        outer = self

        class _Slots(QObject):
            @Slot(str)
            def on_log(self, message: str) -> None:
                outer.append_info(message)

        self._slots = _Slots()

    def append_info(self, message: str) -> None:
        self.text.appendPlainText(message)

    def attach_worker(self, worker) -> None:
        # Ensure UI updates happen in the GUI thread (Qt queued connection via QObject receiver).
        worker.log.connect(self._slots.on_log)
