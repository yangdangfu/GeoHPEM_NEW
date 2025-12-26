from __future__ import annotations

from typing import Callable, Iterable

from geohpem.app.precheck import PrecheckIssue, summarize_issues


class PrecheckDialog:
    def __init__(
        self,
        parent,  # noqa: ANN001
        issues: Iterable[PrecheckIssue],
        *,
        on_jump: Callable[[PrecheckIssue], None] | None = None,
    ) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QListWidgetItem,
            QListWidget,
            QPushButton,
            QVBoxLayout,
        )  # type: ignore

        self._Qt = Qt
        self._QDialog = QDialog
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Pre-check")
        self.dialog.resize(700, 450)

        layout = QVBoxLayout(self.dialog)
        self._issues = list(issues)
        self._on_jump = on_jump
        issues_list = self._issues
        e, w, i = summarize_issues(issues_list)
        layout.addWidget(QLabel(f"Errors: {e}   Warnings: {w}   Info: {i}"))

        self.list = QListWidget()
        for issue in issues_list:
            item = QListWidgetItem(f"[{issue.severity}] {issue.code}: {issue.message}")
            item.setData(Qt.UserRole, issue)
            self.list.addItem(item)
        layout.addWidget(self.list)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._btn_jump = QPushButton("Go to")
        self._btn_jump.setEnabled(False)
        self.buttons.addButton(self._btn_jump, QDialogButtonBox.ActionRole)
        self.buttons.button(QDialogButtonBox.Ok).setText("Run")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancel")
        layout.addWidget(self.buttons)

        if e > 0:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        self.buttons.accepted.connect(self.dialog.accept)
        self.buttons.rejected.connect(self.dialog.reject)
        self.list.currentItemChanged.connect(self._on_selection_changed)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._btn_jump.clicked.connect(self._on_jump_clicked)
        if self._on_jump is None:
            self._btn_jump.setEnabled(False)
            self._btn_jump.setToolTip("Jump is not available.")

    def exec(self) -> bool:
        return int(self.dialog.exec()) == int(self._QDialog.Accepted)

    def _get_selected_issue(self) -> PrecheckIssue | None:
        item = self.list.currentItem()
        if item is None:
            return None
        issue = item.data(self._Qt.UserRole)
        return issue if isinstance(issue, PrecheckIssue) else None

    def _on_selection_changed(self, current, previous) -> None:  # noqa: ANN001
        if self._on_jump is None:
            self._btn_jump.setEnabled(False)
            return
        issue = self._get_selected_issue()
        self._btn_jump.setEnabled(bool(issue and issue.jump))

    def _on_jump_clicked(self) -> None:
        if self._on_jump is None:
            return
        issue = self._get_selected_issue()
        if issue is None or not issue.jump:
            return
        try:
            self._on_jump(issue)
        except Exception:
            pass

    def _on_item_double_clicked(self, item) -> None:  # noqa: ANN001
        if self._on_jump is None:
            return
        issue = item.data(self._Qt.UserRole)
        if not isinstance(issue, PrecheckIssue) or not issue.jump:
            return
        try:
            self._on_jump(issue)
        except Exception:
            pass
