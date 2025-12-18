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
            failed = Signal(str, object)  # error_text, diag_zip_path (Path|None)
            canceled = Signal(object)  # diag_zip_path (Path|None)
            cancel_requested = Signal()

            def __init__(self, case_dir: Path, solver_selector: str) -> None:
                super().__init__()
                self._case_dir = case_dir
                self._solver_selector = solver_selector
                self._cancel = False
                self._logs: list[str] = []

                self.cancel_requested.connect(self._on_cancel_requested)

            @Slot()
            def _on_cancel_requested(self) -> None:
                self._cancel = True
                self.log.emit("Cancel requested...")

            @Slot()
            def run(self) -> None:
                from geohpem.app.run_case import run_case
                from geohpem.app.diagnostics import build_diagnostics_zip
                from geohpem.app.errors import CancelledError
                from geohpem.app.error_mapping import map_exception
                import traceback

                self.started.emit()
                self.progress.emit(1, "Starting...")
                self.log.emit(f"Running solver: {self._solver_selector}")
                self._logs.append(f"Running solver: {self._solver_selector}")

                def on_progress(p: float, message: str, stage_id: str, step: int) -> None:
                    percent = int(max(0.0, min(1.0, p)) * 100)
                    self.progress.emit(percent, f"{stage_id} step {step}: {message}")

                def on_log(level: str, msg: str) -> None:
                    line = f"{level}: {msg}"
                    self._logs.append(line)
                    self.log.emit(line)

                callbacks: dict[str, Callable[..., Any]] = {
                    "on_progress": on_progress,
                    "should_cancel": lambda: bool(self._cancel),
                    "on_log": on_log,
                }

                try:
                    if self._cancel:
                        raise CancelledError("Cancelled by user")
                    out_dir = run_case(
                        str(self._case_dir),
                        solver_selector=self._solver_selector,
                        callbacks=callbacks,
                    )
                    self.progress.emit(100, "Completed")
                    self.output_ready.emit(out_dir)
                except CancelledError as exc:
                    info = map_exception(exc)
                    msg = f"[{info.code}] {info.message}"
                    tb = traceback.format_exc()
                    diag = None
                    try:
                        caps = None
                        try:
                            from geohpem.solver_adapter.loader import load_solver

                            caps = load_solver(self._solver_selector).capabilities()
                        except Exception:
                            caps = None
                        diag = build_diagnostics_zip(
                            Path(self._case_dir),
                            solver_selector=self._solver_selector,
                            capabilities=caps if isinstance(caps, dict) else None,
                            error_code=info.code,
                            error_details=info.details,
                            error=msg,
                            tb=tb,
                            logs=self._logs,
                            include_out=True,
                        ).zip_path
                    except Exception:
                        diag = None
                    self.log.emit("CANCELED")
                    self.canceled.emit(diag)
                except Exception as exc:
                    tb = traceback.format_exc()
                    info = map_exception(exc)
                    msg = f"[{info.code}] {info.message}"
                    diag = None
                    try:
                        # Try capture solver capabilities for diagnostics (best-effort).
                        caps = None
                        try:
                            from geohpem.solver_adapter.loader import load_solver

                            caps = load_solver(self._solver_selector).capabilities()
                        except Exception:
                            caps = None
                        diag = build_diagnostics_zip(
                            Path(self._case_dir),
                            solver_selector=self._solver_selector,
                            capabilities=caps if isinstance(caps, dict) else None,
                            error_code=info.code,
                            error_details=info.details,
                            error=msg,
                            tb=tb,
                            logs=self._logs,
                            include_out=True,
                        ).zip_path
                    except Exception:
                        diag = None

                    self.log.emit(f"FAILED: {msg}")
                    self.failed.emit(msg, diag)
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
        self.failed = self._worker.failed
        self.canceled = self._worker.canceled

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        """
        Request cancellation (best-effort). The solver must respect callbacks['should_cancel'].
        """
        try:
            self._worker.cancel_requested.emit()
        except Exception:
            pass
