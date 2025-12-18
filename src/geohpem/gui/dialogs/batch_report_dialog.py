from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class BatchReportRecord:
    case_dir: Path
    status: str
    solver_selector: str
    elapsed_s: float | None
    rss_start_mb: float | None
    rss_end_mb: float | None
    out_dir: Path | None
    diagnostics_zip: Path | None
    compare_max_linf: float | None
    compare_max_l2: float | None


def _to_path(v: Any) -> Path | None:
    if isinstance(v, str) and v:
        try:
            return Path(v)
        except Exception:
            return None
    return None


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def parse_batch_report(path: Path) -> list[BatchReportRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    recs = data.get("records", [])
    out: list[BatchReportRecord] = []
    if not isinstance(recs, list):
        return out
    for r in recs:
        if not isinstance(r, dict):
            continue
        cmp = r.get("compare")
        max_linf = None
        max_l2 = None
        if isinstance(cmp, dict):
            diffs = cmp.get("diffs", [])
            if isinstance(diffs, list):
                for d in diffs:
                    if not isinstance(d, dict):
                        continue
                    linf = _to_float(d.get("linf"))
                    l2 = _to_float(d.get("l2"))
                    if linf is not None:
                        max_linf = linf if max_linf is None else max(max_linf, linf)
                    if l2 is not None:
                        max_l2 = l2 if max_l2 is None else max(max_l2, l2)
        out.append(
            BatchReportRecord(
                case_dir=_to_path(r.get("case_dir")) or Path("."),
                status=str(r.get("status", "")),
                solver_selector=str(r.get("solver_selector", "")),
                elapsed_s=_to_float(r.get("elapsed_s")),
                rss_start_mb=_to_float(r.get("rss_start_mb")),
                rss_end_mb=_to_float(r.get("rss_end_mb")),
                out_dir=_to_path(r.get("out_dir")),
                diagnostics_zip=_to_path(r.get("diagnostics_zip")),
                compare_max_linf=max_linf,
                compare_max_l2=max_l2,
            )
        )
    return out


class BatchReportDialog:
    def __init__(
        self,
        parent,
        *,
        open_case_cb: Callable[[Path], None] | None = None,
        open_output_cb: Callable[[Path], None] | None = None,
    ) -> None:  # noqa: ANN001
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QAbstractItemView,
            QCheckBox,
            QDialog,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        self._Qt = Qt
        self._QFileDialog = QFileDialog
        self._QMessageBox = QMessageBox
        self._QTableWidgetItem = QTableWidgetItem

        self._open_case_cb = open_case_cb
        self._open_output_cb = open_output_cb

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Batch Report Viewer")
        self._dialog.resize(1100, 650)

        layout = QVBoxLayout(self._dialog)

        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        self._label_path = QLabel("No report loaded.")
        btn_open = QPushButton("Open Report...")
        self._chk_ok = QCheckBox("success")
        self._chk_ok.setChecked(True)
        self._chk_failed = QCheckBox("failed")
        self._chk_failed.setChecked(True)
        self._chk_canceled = QCheckBox("canceled")
        self._chk_canceled.setChecked(True)
        top_l.addWidget(btn_open)
        top_l.addWidget(self._label_path, 1)
        top_l.addWidget(QLabel("Filter:"))
        top_l.addWidget(self._chk_ok)
        top_l.addWidget(self._chk_failed)
        top_l.addWidget(self._chk_canceled)
        layout.addWidget(top)

        self._summary = QLabel("")
        layout.addWidget(self._summary)

        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels(
            [
                "case",
                "status",
                "elapsed_s",
                "rss_start_mb",
                "rss_end_mb",
                "rss_delta_mb",
                "max_linf",
                "max_l2",
                "out_dir",
                "diagnostics",
            ]
        )
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        actions = QWidget()
        actions_l = QHBoxLayout(actions)
        actions_l.setContentsMargins(0, 0, 0, 0)
        self._btn_open_case = QPushButton("Open Case")
        self._btn_open_out = QPushButton("Open Output")
        self._btn_open_diag = QPushButton("Open Diagnostics Zip")
        self._btn_copy = QPushButton("Copy Selected Paths")
        self._btn_close = QPushButton("Close")
        actions_l.addWidget(self._btn_open_case)
        actions_l.addWidget(self._btn_open_out)
        actions_l.addWidget(self._btn_open_diag)
        actions_l.addStretch(1)
        actions_l.addWidget(self._btn_copy)
        actions_l.addWidget(self._btn_close)
        layout.addWidget(actions)

        self._records_all: list[BatchReportRecord] = []
        self._records_view: list[BatchReportRecord] = []

        btn_open.clicked.connect(self._open_report)
        self._chk_ok.stateChanged.connect(self._apply_filter)
        self._chk_failed.stateChanged.connect(self._apply_filter)
        self._chk_canceled.stateChanged.connect(self._apply_filter)

        self._btn_open_case.clicked.connect(self._open_case)
        self._btn_open_out.clicked.connect(self._open_out)
        self._btn_open_diag.clicked.connect(self._open_diag)
        self._btn_copy.clicked.connect(self._copy_paths)
        self._btn_close.clicked.connect(self._dialog.accept)

        self._table.doubleClicked.connect(lambda *_: self._open_out())

    def exec(self) -> int:
        return int(self._dialog.exec())

    def _open_report(self) -> None:
        file, _ = self._QFileDialog.getOpenFileName(self._dialog, "Open Batch Report", "", "JSON (*.json);;All Files (*)")
        if not file:
            return
        path = Path(file)
        try:
            recs = parse_batch_report(path)
        except Exception as exc:
            self._QMessageBox.critical(self._dialog, "Batch Report", str(exc))
            return
        self._label_path.setText(str(path))
        self._records_all = recs
        self._apply_filter()

    def _apply_filter(self) -> None:
        allowed: set[str] = set()
        if self._chk_ok.isChecked():
            allowed.add("success")
        if self._chk_failed.isChecked():
            allowed.add("failed")
        if self._chk_canceled.isChecked():
            allowed.add("canceled")
        self._records_view = [r for r in self._records_all if r.status in allowed]
        self._render_table()

    def _render_table(self) -> None:
        self._table.setRowCount(len(self._records_view))
        ok = sum(1 for r in self._records_all if r.status == "success")
        failed = sum(1 for r in self._records_all if r.status == "failed")
        canceled = sum(1 for r in self._records_all if r.status == "canceled")
        self._summary.setText(f"Total={len(self._records_all)}  success={ok}  failed={failed}  canceled={canceled}")

        def set_item(row: int, col: int, txt: str) -> None:
            it = self._QTableWidgetItem(txt)
            self._table.setItem(row, col, it)

        for row, r in enumerate(self._records_view):
            set_item(row, 0, r.case_dir.name)
            set_item(row, 1, r.status)
            set_item(row, 2, f"{r.elapsed_s:.4g}" if r.elapsed_s is not None else "")
            set_item(row, 3, f"{r.rss_start_mb:.4g}" if r.rss_start_mb is not None else "")
            set_item(row, 4, f"{r.rss_end_mb:.4g}" if r.rss_end_mb is not None else "")
            if r.rss_start_mb is not None and r.rss_end_mb is not None:
                set_item(row, 5, f"{(r.rss_end_mb - r.rss_start_mb):.4g}")
            else:
                set_item(row, 5, "")
            set_item(row, 6, f"{r.compare_max_linf:.4g}" if r.compare_max_linf is not None else "")
            set_item(row, 7, f"{r.compare_max_l2:.4g}" if r.compare_max_l2 is not None else "")
            set_item(row, 8, str(r.out_dir) if r.out_dir else "")
            set_item(row, 9, str(r.diagnostics_zip) if r.diagnostics_zip else "")

        self._table.resizeColumnsToContents()

    def _selected(self) -> BatchReportRecord | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._records_view):
            return None
        return self._records_view[row]

    def _open_case(self) -> None:
        r = self._selected()
        if r is None:
            return
        if self._open_case_cb:
            self._open_case_cb(r.case_dir)
            return
        self._open_in_explorer(r.case_dir)

    def _open_out(self) -> None:
        r = self._selected()
        if r is None or not r.out_dir:
            return
        if self._open_output_cb:
            self._open_output_cb(r.out_dir)
            return
        self._open_in_explorer(r.out_dir)

    def _open_diag(self) -> None:
        r = self._selected()
        if r is None or not r.diagnostics_zip:
            return
        self._open_in_explorer(r.diagnostics_zip)

    def _copy_paths(self) -> None:
        r = self._selected()
        if r is None:
            return
        parts = [str(r.case_dir)]
        if r.out_dir:
            parts.append(str(r.out_dir))
        if r.diagnostics_zip:
            parts.append(str(r.diagnostics_zip))
        text = "\n".join(parts)
        try:
            from PySide6.QtGui import QGuiApplication  # type: ignore

            QGuiApplication.clipboard().setText(text)
        except Exception:
            pass

    def _open_in_explorer(self, path: Path) -> None:
        try:
            import os

            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception as exc:
            self._QMessageBox.information(self._dialog, "Open", f"Failed to open:\n{path}\n\n{exc}")
