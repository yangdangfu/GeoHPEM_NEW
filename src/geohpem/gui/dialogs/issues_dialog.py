from __future__ import annotations

from typing import Iterable

from geohpem.app.precheck import PrecheckIssue, summarize_issues


class IssuesDialog:
    def __init__(
        self,
        parent,  # noqa: ANN001
        *,
        title: str,
        issues: Iterable[PrecheckIssue],
        ok_text: str = "OK",
    ) -> None:
        from PySide6.QtWidgets import (
            QDialog,  # type: ignore
            QDialogButtonBox,
            QLabel,
            QListWidget,
            QVBoxLayout,
        )

        self._QDialog = QDialog
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle(title)
        self.dialog.resize(700, 450)

        layout = QVBoxLayout(self.dialog)
        issues_list = list(issues)
        e, w, i = summarize_issues(issues_list)
        layout.addWidget(QLabel(f"Errors: {e}   Warnings: {w}   Info: {i}"))

        self.list = QListWidget()
        for issue in issues_list:
            self.list.addItem(f"[{issue.severity}] {issue.code}: {issue.message}")
        layout.addWidget(self.list)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Ok).setText(ok_text)
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.dialog.accept)

    def exec(self) -> bool:
        return int(self.dialog.exec()) == int(self._QDialog.Accepted)
