from __future__ import annotations

from typing import Iterable

from geohpem.app.precheck import PrecheckIssue, summarize_issues


class PrecheckDialog:
    def __init__(self, parent, issues: Iterable[PrecheckIssue]) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QListWidget,
            QVBoxLayout,
        )  # type: ignore

        self._QDialog = QDialog
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Pre-check")
        self.dialog.resize(700, 450)

        layout = QVBoxLayout(self.dialog)
        issues_list = list(issues)
        e, w, i = summarize_issues(issues_list)
        layout.addWidget(QLabel(f"Errors: {e}   Warnings: {w}   Info: {i}"))

        self.list = QListWidget()
        for issue in issues_list:
            self.list.addItem(f"[{issue.severity}] {issue.code}: {issue.message}")
        layout.addWidget(self.list)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Run")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancel")
        layout.addWidget(self.buttons)

        if e > 0:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        self.buttons.accepted.connect(self.dialog.accept)
        self.buttons.rejected.connect(self.dialog.reject)

    def exec(self) -> bool:
        return int(self.dialog.exec()) == int(self._QDialog.Accepted)
