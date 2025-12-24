from __future__ import annotations

from pathlib import Path


class BatchRunDialog:
    def __init__(self, parent, *, solver_selector: str) -> None:  # noqa: ANN001
        from PySide6.QtCore import QObject, Slot  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QProgressBar,
            QVBoxLayout,
            QWidget,
        )

        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Batch Run")
        self._dialog.resize(760, 520)

        layout = QVBoxLayout(self._dialog)
        layout.addWidget(QLabel("Run multiple case folders under a root directory.\n"
                                "Each case folder must contain request.json + mesh.npz."))

        form = QFormLayout()
        layout.addLayout(form)

        self._root = QLineEdit()
        btn_root = QPushButton("Browse...")
        row_root = QWidget()
        row_root_l = QHBoxLayout(row_root)
        row_root_l.setContentsMargins(0, 0, 0, 0)
        row_root_l.addWidget(self._root, 1)
        row_root_l.addWidget(btn_root)
        form.addRow("Cases root", row_root)

        self._solver = QLineEdit()
        self._solver.setText(solver_selector)
        self._solver.setPlaceholderText("fake | ref_elastic | ref_seepage | python:<module>")
        form.addRow("Solver", self._solver)

        self._use_baseline = QCheckBox("Compare with baseline root")
        self._baseline = QLineEdit()
        self._baseline.setEnabled(False)
        btn_base = QPushButton("Browse...")
        btn_base.setEnabled(False)
        row_base = QWidget()
        row_base_l = QHBoxLayout(row_base)
        row_base_l.setContentsMargins(0, 0, 0, 0)
        row_base_l.addWidget(self._baseline, 1)
        row_base_l.addWidget(btn_base)
        form.addRow("", self._use_baseline)
        form.addRow("Baseline root", row_base)

        self._report = QLineEdit()
        btn_report = QPushButton("Browse...")
        row_rep = QWidget()
        row_rep_l = QHBoxLayout(row_rep)
        row_rep_l.setContentsMargins(0, 0, 0, 0)
        row_rep_l.addWidget(self._report, 1)
        row_rep_l.addWidget(btn_report)
        form.addRow("Report path", row_rep)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        layout.addWidget(self._log, 1)

        buttons = QDialogButtonBox()
        self._btn_run = buttons.addButton("Run", QDialogButtonBox.AcceptRole)
        self._btn_cancel = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        self._btn_close = buttons.addButton("Close", QDialogButtonBox.DestructiveRole)
        self._btn_close.setEnabled(False)
        layout.addWidget(buttons)

        self._worker = None

        outer = self

        class _Slots(QObject):
            @Slot(int, str)
            def on_progress(self, p: int, msg: str) -> None:
                outer._progress.setValue(int(p))
                outer._append(msg)

            @Slot(str)
            def on_log(self, msg: str) -> None:
                outer._append(msg)

            @Slot(str)
            def on_failed(self, msg: str) -> None:
                outer._append(f"FAILED: {msg}")
                outer._QMessageBox.critical(outer._dialog, "Batch Run", msg)

            @Slot(object)
            def on_report_ready(self, p) -> None:  # noqa: ANN001
                outer._append(f"Report written: {p}")
                outer._QMessageBox.information(outer._dialog, "Batch Run", f"Completed.\nReport:\n{p}")

            @Slot()
            def on_finished(self) -> None:
                outer._btn_run.setEnabled(True)
                outer._btn_cancel.setEnabled(False)
                outer._btn_close.setEnabled(True)
                outer._worker = None

        self._slots = _Slots()

        def update_baseline_enabled() -> None:
            on = bool(self._use_baseline.isChecked())
            self._baseline.setEnabled(on)
            btn_base.setEnabled(on)

        self._use_baseline.stateChanged.connect(update_baseline_enabled)
        update_baseline_enabled()

        def browse_root() -> None:
            d = self._QFileDialog.getExistingDirectory(self._dialog, "Select Cases Root")
            if d:
                self._root.setText(d)
                # default report path
                self._report.setText(str(Path(d) / "batch_report.json"))

        def browse_base() -> None:
            d = self._QFileDialog.getExistingDirectory(self._dialog, "Select Baseline Root")
            if d:
                self._baseline.setText(d)

        def browse_report() -> None:
            f, _ = self._QFileDialog.getSaveFileName(self._dialog, "Report Path", "", "JSON (*.json);;All Files (*)")
            if f:
                self._report.setText(f)

        btn_root.clicked.connect(browse_root)
        btn_base.clicked.connect(browse_base)
        btn_report.clicked.connect(browse_report)

        self._btn_run.clicked.connect(self._on_run)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_close.clicked.connect(self._dialog.accept)

    def exec(self) -> int:
        return int(self._dialog.exec())

    def _append(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _on_run(self) -> None:
        from geohpem.gui.workers.batch_run_worker import BatchRunWorker

        root = Path(self._root.text().strip())
        if not root.exists():
            self._QMessageBox.information(self._dialog, "Batch Run", "Please select a valid cases root folder.")
            return
        solver = self._solver.text().strip() or "fake"

        baseline = None
        if self._use_baseline.isChecked():
            b = Path(self._baseline.text().strip())
            if not b.exists():
                self._QMessageBox.information(self._dialog, "Batch Run", "Baseline root does not exist.")
                return
            baseline = b

        report_txt = self._report.text().strip()
        report_path = Path(report_txt) if report_txt else (root / "batch_report.json")

        self._btn_run.setEnabled(False)
        self._btn_close.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._progress.setValue(0)
        self._append(f"Starting batch run: root={root} solver={solver}")

        worker = BatchRunWorker(root, solver_selector=solver, baseline_root=baseline, report_path=report_path)
        self._worker = worker
        # Connect to QObject slots to ensure UI updates happen in GUI thread.
        worker.progress.connect(self._slots.on_progress)
        worker.log.connect(self._slots.on_log)
        worker.failed.connect(self._slots.on_failed)
        worker.report_ready.connect(self._slots.on_report_ready)
        worker.finished.connect(self._slots.on_finished)
        worker.start()

    def _on_cancel(self) -> None:
        w = self._worker
        if w is not None and hasattr(w, "cancel"):
            try:
                w.cancel()
                self._append("Cancel requested (best-effort).")
            except Exception:
                pass
