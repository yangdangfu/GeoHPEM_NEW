from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class SolveWorker:
    """
    Background solver runner.

    Emits progress/log updates and a final output folder path.
    """

    def __init__(self, case_dir: Path, solver_selector: str) -> None:
        from PySide6.QtCore import QObject, QThread, Signal, Slot  # type: ignore

        class _Worker(QObject):
            started = Signal()
            finished = Signal()
            progress = Signal(int, str)
            log = Signal(str)
            output_ready = Signal(object)  # Path

            def __init__(self, case_dir: Path, solver_selector: str) -> None:
                super().__init__()
                self._case_dir = case_dir
                self._solver_selector = solver_selector

            @Slot()
            def run(self) -> None:
                from geohpem.app.run_case import run_case

                self.started.emit()
                self.progress.emit(1, "Starting...")
                self.log.emit(f"Running solver: {self._solver_selector}")

                def on_progress(p: float, message: str, stage_id: str, step: int) -> None:
                    percent = int(max(0.0, min(1.0, p)) * 100)
                    self.progress.emit(percent, f"{stage_id} step {step}: {message}")

                callbacks: dict[str, Callable[..., Any]] = {
                    "on_progress": on_progress,
                    "should_cancel": lambda: False,
                    "on_log": lambda level, msg: self.log.emit(f"{level}: {msg}"),
                }

                try:
                    out_dir = run_case(
                        str(self._case_dir),
                        solver_selector=self._solver_selector,
                        callbacks=callbacks,
                    )
                    self.progress.emit(100, "Completed")
                    self.output_ready.emit(out_dir)
                except Exception as exc:
                    self.log.emit(f"FAILED: {exc}")
                finally:
                    self.finished.emit()

        self._thread = QThread()
        self._worker = _Worker(case_dir=case_dir, solver_selector=solver_selector)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self.started = self._worker.started
        self.finished = self._worker.finished
        self.progress = self._worker.progress
        self.log = self._worker.log
        self.output_ready = self._worker.output_ready

    def start(self) -> None:
        self._thread.start()

