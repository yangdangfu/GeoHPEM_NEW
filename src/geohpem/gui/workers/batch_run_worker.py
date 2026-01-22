from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable


class BatchRunWorker:
    """
    Background batch runner for multiple case folders.
    """

    def __init__(
        self,
        root: Path,
        *,
        solver_selector: str,
        baseline_root: Path | None,
        report_path: Path,
    ) -> None:
        from PySide6.QtCore import QObject, QThread, Signal, Slot  # type: ignore

        class _Worker(QObject):
            started = Signal()
            finished = Signal()
            progress = Signal(int, str)
            log = Signal(str)
            report_ready = Signal(object)  # Path
            failed = Signal(str)  # message
            cancel_requested = Signal()

            def __init__(
                self,
                root: Path,
                solver_selector: str,
                baseline_root: Path | None,
                report_path: Path,
            ) -> None:
                super().__init__()
                self._root = Path(root)
                self._solver_selector = solver_selector
                self._baseline_root = Path(baseline_root) if baseline_root else None
                self._report_path = Path(report_path)
                self._cancel = False
                self.cancel_requested.connect(self._on_cancel)

            @Slot()
            def _on_cancel(self) -> None:
                self._cancel = True
                self.log.emit("Cancel requested...")

            @Slot()
            def run(self) -> None:
                from geohpem.app.case_runner import (
                    discover_case_folders,
                    run_cases,
                    write_case_run_report,
                )

                self.started.emit()

                cases = discover_case_folders(self._root)
                if not cases:
                    self.failed.emit(f"No case folders found under: {self._root}")
                    self.finished.emit()
                    return

                t0 = time.perf_counter()

                def on_progress(
                    i: int, total: int, case_dir: Path, status: str
                ) -> None:
                    # Rough overall progress, one case at a time.
                    pct = int(((i - 1) / max(total, 1)) * 100)
                    if status == "running":
                        self.progress.emit(
                            pct, f"[{i}/{total}] Running: {case_dir.name}"
                        )
                    else:
                        self.progress.emit(
                            pct, f"[{i}/{total}] {status.upper()}: {case_dir.name}"
                        )
                    self.log.emit(f"{status}: {case_dir}")

                records = run_cases(
                    cases,
                    solver_selector=self._solver_selector,
                    baseline_root=self._baseline_root,
                    on_progress=on_progress,
                    should_cancel=lambda: bool(self._cancel),
                )
                write_case_run_report(records, self._report_path)
                elapsed = time.perf_counter() - t0

                total = len(records)
                failed = sum(1 for r in records if r.status != "success")
                self.progress.emit(
                    100,
                    f"Completed: cases={total}, failed={failed}, elapsed={elapsed:.2f}s",
                )
                self.report_ready.emit(self._report_path)
                self.finished.emit()

        self._thread = QThread()
        self._worker = _Worker(
            root=root,
            solver_selector=solver_selector,
            baseline_root=baseline_root,
            report_path=report_path,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self.started = self._worker.started
        self.finished = self._worker.finished
        self.progress = self._worker.progress
        self.log = self._worker.log
        self.report_ready = self._worker.report_ready
        self.failed = self._worker.failed

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        try:
            self._worker.cancel_requested.emit()
        except Exception:
            pass
