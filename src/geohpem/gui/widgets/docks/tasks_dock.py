from __future__ import annotations


class TasksDock:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QDockWidget, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget  # type: ignore

        self.dock = QDockWidget("Tasks")
        self.dock.setObjectName("dock_tasks")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        self.label = QLabel("Idle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.btn_cancel)
        layout.addStretch(1)

        self._worker = None
        self.btn_cancel.clicked.connect(self._on_cancel)

    def attach_worker(self, worker) -> None:
        # Keep a strong reference to avoid premature GC during background runs.
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.started.connect(lambda: self._set_state("Running"))
        worker.finished.connect(lambda: self._set_state("Idle"))
        worker.finished.connect(self._clear_worker)
        if hasattr(worker, "failed"):
            worker.failed.connect(lambda *_: self._set_state("Failed"))
        if hasattr(worker, "canceled"):
            worker.canceled.connect(lambda *_: self._set_state("Canceled"))
        self.btn_cancel.setEnabled(True)

    def _clear_worker(self) -> None:
        self._worker = None
        self.btn_cancel.setEnabled(False)

    def _set_state(self, state: str) -> None:
        self.label.setText(state)
        if state == "Idle":
            self.progress.setValue(0)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.label.setText(message)

    def _on_cancel(self) -> None:
        w = self._worker
        if w is None:
            return
        if hasattr(w, "cancel"):
            try:
                w.cancel()
                self.label.setText("Cancel requested...")
            except Exception:
                pass
