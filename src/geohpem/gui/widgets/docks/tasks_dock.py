from __future__ import annotations


class TasksDock:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QDockWidget, QLabel, QProgressBar, QVBoxLayout, QWidget  # type: ignore

        self.dock = QDockWidget("Tasks")
        self.dock.setObjectName("dock_tasks")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        self.label = QLabel("Idle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addStretch(1)

    def attach_worker(self, worker) -> None:
        worker.progress.connect(self._on_progress)
        worker.started.connect(lambda: self._set_state("Running"))
        worker.finished.connect(lambda: self._set_state("Idle"))

    def _set_state(self, state: str) -> None:
        self.label.setText(state)
        if state == "Idle":
            self.progress.setValue(0)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.label.setText(message)

