from __future__ import annotations


class TasksDock:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Slot  # type: ignore
        from PySide6.QtWidgets import (
            QDockWidget,
            QLabel,  # type: ignore
            QProgressBar,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )

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

        outer = self

        class _Slots(QObject):
            @Slot(int, str)
            def on_progress(self, percent: int, message: str) -> None:
                outer._on_progress(percent, message)

            @Slot()
            def on_started(self) -> None:
                outer._set_state("Running")

            @Slot()
            def on_finished(self) -> None:
                outer._set_state("Idle")
                outer._clear_worker()

            @Slot(str, object)
            def on_failed(self, *_args) -> None:
                outer._set_state("Failed")

            @Slot(object)
            def on_canceled(self, *_args) -> None:
                outer._set_state("Canceled")

        self._slots = _Slots()

    def attach_worker(self, worker) -> None:
        # Keep a strong reference to avoid premature GC during background runs.
        self._worker = worker
        worker.progress.connect(self._slots.on_progress)
        worker.started.connect(self._slots.on_started)
        worker.finished.connect(self._slots.on_finished)
        if hasattr(worker, "failed"):
            worker.failed.connect(self._slots.on_failed)
        if hasattr(worker, "canceled"):
            worker.canceled.connect(self._slots.on_canceled)
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
