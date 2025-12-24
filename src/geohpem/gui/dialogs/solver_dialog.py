from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SolverDialogResult:
    solver_selector: str


class SolverDialog:
    def __init__(self, parent, *, current_selector: str) -> None:  # noqa: ANN001
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QVBoxLayout,
            QWidget,
        )

        self._Qt = Qt
        self._QMessageBox = QMessageBox

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Select Solver")
        self._dialog.resize(640, 420)

        root = QWidget()
        layout = QVBoxLayout(self._dialog)
        layout.addWidget(root)
        v = QVBoxLayout(root)

        v.addWidget(QLabel("Choose which solver implementation to use.\n"
                            "Tip: external solvers can be loaded via python module (submodule/package)."))

        form = QFormLayout()
        v.addLayout(form)

        self._type = QComboBox()
        self._type.addItem("Fake (built-in)", "fake")
        self._type.addItem("Reference Elastic (built-in)", "ref_elastic")
        self._type.addItem("Reference Seepage (built-in)", "ref_seepage")
        self._type.addItem("Python module (python:<module>)", "python")
        form.addRow("Solver", self._type)

        self._module = QLineEdit()
        self._module.setPlaceholderText("e.g. geohpem_solver or solver_package.entrypoint")
        form.addRow("Module", self._module)

        row = QWidget()
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        self._btn_check = QPushButton("Check & Show Capabilities")
        row_l.addWidget(self._btn_check)
        row_l.addStretch(1)
        v.addWidget(row)

        v.addWidget(QLabel("Capabilities (solver.capabilities())"))
        self._caps = QPlainTextEdit()
        self._caps.setReadOnly(True)
        self._caps.setPlainText("(click 'Check' to load solver and view capabilities)")
        v.addWidget(self._caps, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self._dialog.accept)
        buttons.rejected.connect(self._dialog.reject)

        self._btn_check.clicked.connect(self._check)
        self._type.currentIndexChanged.connect(self._sync_enabled)

        self._set_from_selector(current_selector)
        self._sync_enabled()

    def _set_from_selector(self, selector: str) -> None:
        selector = (selector or "").strip()
        if selector == "fake":
            self._type.setCurrentIndex(self._type.findData("fake"))
            self._module.setText("")
            return
        if selector == "ref_elastic":
            self._type.setCurrentIndex(self._type.findData("ref_elastic"))
            self._module.setText("")
            return
        if selector == "ref_seepage":
            self._type.setCurrentIndex(self._type.findData("ref_seepage"))
            self._module.setText("")
            return
            self._module.setText("")
            return
        if selector.startswith("python:"):
            self._type.setCurrentIndex(self._type.findData("python"))
            self._module.setText(selector.split("python:", 1)[1].strip())
            return
        # unknown selector -> show as module style for debugging
        self._type.setCurrentIndex(self._type.findData("python"))
        self._module.setText(selector)

    def _sync_enabled(self) -> None:
        t = str(self._type.currentData())
        self._module.setEnabled(t == "python")

    def _selector(self) -> str:
        t = str(self._type.currentData())
        if t in ("fake", "ref_elastic", "ref_seepage"):
            return t
        module = self._module.text().strip()
        return f"python:{module}"

    def _check(self) -> None:
        try:
            from geohpem.solver_adapter.loader import load_solver
        except Exception as exc:  # pragma: no cover
            self._QMessageBox.critical(self._dialog, "Solver", f"Failed to import solver loader: {exc}")
            return

        selector = self._selector()
        if selector.startswith("python:") and selector == "python:":
            self._QMessageBox.information(self._dialog, "Solver", "Please enter a python module name.")
            return

        try:
            solver = load_solver(selector)
            caps = solver.capabilities()
        except Exception as exc:
            self._caps.setPlainText(f"FAILED to load solver:\n{exc}")
            return

        import json

        try:
            self._caps.setPlainText(json.dumps(caps, indent=2, ensure_ascii=False))
        except Exception:
            self._caps.setPlainText(str(caps))

    def exec(self) -> SolverDialogResult | None:
        from PySide6.QtWidgets import QDialog  # type: ignore

        if self._dialog.exec() != QDialog.Accepted:
            return None
        selector = self._selector()
        if selector.startswith("python:") and selector == "python:":
            self._QMessageBox.information(self._dialog, "Solver", "Please enter a python module name.")
            return None
        return SolverDialogResult(solver_selector=selector)
