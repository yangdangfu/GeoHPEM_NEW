from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from geohpem.mesh.convert import ImportReport


@dataclass(frozen=True, slots=True)
class ImportMeshResult:
    mesh: dict[str, Any]
    report: ImportReport


class ImportMeshDialog:
    def __init__(self, parent) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLineEdit,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

        self._QFileDialog = QFileDialog
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Import Mesh")
        self.dialog.resize(650, 200)

        layout = QVBoxLayout(self.dialog)

        form = QFormLayout()
        layout.addLayout(form)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        self.path = QLineEdit()
        self.btn_browse = QPushButton("Browse...")
        rl.addWidget(self.path)
        rl.addWidget(self.btn_browse)
        form.addRow("Mesh file", row)

        self.gen_sets = QCheckBox("Generate sets from Gmsh physical groups (if available)")
        self.gen_sets.setChecked(True)
        form.addRow("", self.gen_sets)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.buttons)

        self.btn_browse.clicked.connect(self._browse)
        self.buttons.accepted.connect(self.dialog.accept)
        self.buttons.rejected.connect(self.dialog.reject)

    def exec(self) -> ImportMeshResult | None:
        if self.dialog.exec() != self.dialog.Accepted:
            return None

        path = self.path.text().strip()
        if not path:
            return None

        from geohpem.mesh.import_mesh import import_with_meshio_report

        mesh, report = import_with_meshio_report(path)
        if not self.gen_sets.isChecked():
            mesh = {k: v for k, v in mesh.items() if not (k.startswith("node_set__") or k.startswith("edge_set__") or k.startswith("elem_set__"))}
        return ImportMeshResult(mesh=mesh, report=report)

    def _browse(self) -> None:
        file, _ = self._QFileDialog.getOpenFileName(
            self.dialog,
            "Select mesh file",
            "",
            "Mesh files (*.msh *.vtk *.vtu *.xdmf *.obj *.stl);;All Files (*)",
        )
        if file:
            self.path.setText(file)

