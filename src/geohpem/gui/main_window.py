from __future__ import annotations

from pathlib import Path
from typing import Any

from geohpem.contract.io import read_result_folder
from geohpem.gui.widgets.docks.log_dock import LogDock
from geohpem.gui.widgets.docks.project_dock import ProjectDock
from geohpem.gui.widgets.docks.properties_dock import PropertiesDock
from geohpem.gui.widgets.docks.stage_dock import StageDock
from geohpem.gui.widgets.docks.tasks_dock import TasksDock
from geohpem.gui.workspaces.output_workspace import OutputWorkspace
from geohpem.gui.workspaces.workspace_stack import WorkspaceStack
from geohpem.project.case_folder import load_case_folder
from geohpem.project.package import DEFAULT_EXT, load_geohpem, save_geohpem
from geohpem.project.types import ProjectData
from geohpem.project.workdir import materialize_to_workdir, update_project_from_workdir


class MainWindow:
    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtGui import QAction  # type: ignore
        from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox  # type: ignore

        from geohpem.gui.settings import SettingsStore

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QFileDialog = QFileDialog

        self._settings = SettingsStore()

        outer = self

        class _GeoMainWindow(QMainWindow):
            def closeEvent(self, event):  # type: ignore[override]
                if outer._confirm_close():
                    event.accept()
                else:
                    event.ignore()

        self._win = _GeoMainWindow()
        self._win.setWindowTitle("GeoHPEM")
        self._win.resize(1400, 900)

        self.workspace_stack = WorkspaceStack()
        self._win.setCentralWidget(self.workspace_stack.widget)

        self.project_dock = ProjectDock()
        self.properties_dock = PropertiesDock()
        self.stage_dock = StageDock()
        self.log_dock = LogDock()
        self.tasks_dock = TasksDock()

        self._win.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock.dock)
        self._win.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock.dock)
        self._win.addDockWidget(Qt.RightDockWidgetArea, self.stage_dock.dock)
        self._win.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock.dock)
        self._win.addDockWidget(Qt.BottomDockWidgetArea, self.tasks_dock.dock)

        self._win.tabifyDockWidget(self.log_dock.dock, self.tasks_dock.dock)
        self.log_dock.dock.raise_()

        self._project_file: Path | None = None
        self._project: ProjectData | None = None
        self._work_case_dir: Path | None = None
        self._dirty = False

        self._action_new = QAction("New Project...", self._win)
        self._action_new.triggered.connect(self._on_new_project)

        self._action_open = QAction("Open Project...", self._win)
        self._action_open.triggered.connect(self._on_open_project_dialog)

        self._action_open_case = QAction("Open Case Folder...", self._win)
        self._action_open_case.triggered.connect(self._on_open_case_dialog)

        self._action_save = QAction("Save", self._win)
        self._action_save.triggered.connect(self._on_save)

        self._action_save_as = QAction("Save As...", self._win)
        self._action_save_as.triggered.connect(self._on_save_as)

        self._action_open_results = QAction("Open Output Folder...", self._win)
        self._action_open_results.triggered.connect(self._on_open_output_dialog)

        self._action_ws_input = QAction("Workspace: Input", self._win)
        self._action_ws_input.triggered.connect(lambda: self.workspace_stack.set_workspace("input"))

        self._action_ws_output = QAction("Workspace: Output", self._win)
        self._action_ws_output.triggered.connect(lambda: self.workspace_stack.set_workspace("output"))

        self._action_run = QAction("Run (Fake Solver)", self._win)
        self._action_run.triggered.connect(self._on_run_fake)

        self._action_about = QAction("About", self._win)
        self._action_about.triggered.connect(self._on_about)

        menu_file = self._win.menuBar().addMenu("File")
        menu_file.addAction(self._action_new)
        menu_file.addAction(self._action_open)

        self._menu_recent = QMenu("Open Recent", self._win)
        menu_file.addMenu(self._menu_recent)
        self._rebuild_recent_menu()

        menu_file.addAction(self._action_open_case)
        menu_file.addSeparator()
        menu_file.addAction(self._action_save)
        menu_file.addAction(self._action_save_as)
        menu_file.addSeparator()
        menu_file.addAction(self._action_open_results)

        menu_ws = self._win.menuBar().addMenu("Workspace")
        menu_ws.addAction(self._action_ws_input)
        menu_ws.addAction(self._action_ws_output)

        menu_solve = self._win.menuBar().addMenu("Solve")
        menu_solve.addAction(self._action_run)

        menu_help = self._win.menuBar().addMenu("Help")
        menu_help.addAction(self._action_about)

        self.project_dock.case_open_requested.connect(self.open_case_folder)
        self.project_dock.output_open_requested.connect(self.open_output_folder)

    @property
    def qt(self):
        return self._win

    def show(self) -> None:
        self._win.show()

    def set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty

    def _load_project_data(self, project: ProjectData, display_path: Path | None) -> None:
        self._project = project
        self._project_file = display_path
        self._work_case_dir = materialize_to_workdir(project)

        title = "GeoHPEM - Untitled" if display_path is None else "GeoHPEM"
        if display_path:
            title = f"GeoHPEM - {display_path.name}"
        self._win.setWindowTitle(title)

        # For now, project tree is driven by the materialized case dir.
        self.project_dock.set_case(self._work_case_dir, request=project.request, mesh=project.mesh)
        self.properties_dock.set_object(("request", project.request))
        self.stage_dock.set_stages(project.request.get("stages", []))
        self.log_dock.append_info(f"Loaded project: {display_path or self._work_case_dir}")

        if project.result_meta is not None and project.result_arrays is not None:
            self.open_output_folder(self._work_case_dir / "out")

        self.workspace_stack.set_workspace("input")
        self._dirty = False

    def open_project_file(self, project_file: Path) -> None:
        try:
            project = load_geohpem(project_file)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Open Project Failed", str(exc))
            return
        self._settings.add_recent_project(project_file)
        self._settings.set_last_project(project_file)
        self._rebuild_recent_menu()
        self._load_project_data(project, display_path=project_file)

    def open_case_folder(self, case_dir: Path) -> None:
        try:
            project = load_case_folder(case_dir)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Open Case Failed", str(exc))
            return
        self._settings.add_recent_project(case_dir)
        self._settings.set_last_project(case_dir)
        self._rebuild_recent_menu()
        self._load_project_data(project, display_path=case_dir)

    def save_project(self, project_file: Path) -> None:
        if not self._project:
            return
        # Pull back latest out/ (if any) from work dir before saving.
        if self._work_case_dir:
            self._project = update_project_from_workdir(self._project, self._work_case_dir)
        try:
            saved = save_geohpem(project_file, self._project)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Save Failed", str(exc))
            return
        self._project_file = saved
        self._settings.add_recent_project(saved)
        self._settings.set_last_project(saved)
        self._rebuild_recent_menu()
        self._dirty = False
        self.log_dock.append_info(f"Saved: {saved}")

    def open_output_folder(self, out_dir: Path) -> None:
        try:
            meta, arrays = read_result_folder(out_dir)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Open Output Failed", str(exc))
            return

        output_ws = self.workspace_stack.get("output")
        if isinstance(output_ws, OutputWorkspace):
            output_ws.set_result(meta, arrays)
        self.log_dock.append_info(f"Opened output: {out_dir}")
        self.workspace_stack.set_workspace("output")

    def _confirm_discard_if_dirty(self) -> bool:
        if not self._dirty:
            return True
        btn = self._QMessageBox.question(
            self._win,
            "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            self._QMessageBox.Yes | self._QMessageBox.No,
        )
        return btn == self._QMessageBox.Yes

    def _confirm_close(self) -> bool:
        if not self._dirty:
            return True
        btn = self._QMessageBox.question(
            self._win,
            "Unsaved Changes",
            "You have unsaved changes. Save before closing?",
            self._QMessageBox.Yes | self._QMessageBox.No | self._QMessageBox.Cancel,
        )
        if btn == self._QMessageBox.Cancel:
            return False
        if btn == self._QMessageBox.No:
            return True
        # Yes -> Save
        if self._project_file and self._project_file.suffix.lower() == DEFAULT_EXT:
            self.save_project(self._project_file)
            return not self._dirty
        self._on_save_as()
        return not self._dirty

    def _on_open_project_dialog(self) -> None:
        if not self._confirm_discard_if_dirty():
            return
        file, _ = self._QFileDialog.getOpenFileName(
            self._win,
            "Open Project",
            "",
            f"GeoHPEM Project (*{DEFAULT_EXT});;All Files (*)",
        )
        if not file:
            return
        self.open_project_file(Path(file))

    def _on_new_project(self) -> None:
        if not self._confirm_discard_if_dirty():
            return

        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QComboBox, QVBoxLayout  # type: ignore
        from geohpem.project.templates import new_empty_project, new_sample_project

        dialog = QDialog(self._win)
        dialog.setWindowTitle("New Project")

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        layout.addLayout(form)

        combo_mode = QComboBox()
        combo_mode.addItem("Plane strain", "plane_strain")
        combo_mode.addItem("Axisymmetric", "axisymmetric")
        form.addRow("Mode", combo_mode)

        combo_template = QComboBox()
        combo_template.addItem("Empty project", "empty")
        combo_template.addItem("Sample (unit square)", "sample")
        form.addRow("Template", combo_template)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return

        mode = str(combo_mode.currentData())
        template = str(combo_template.currentData())

        project = new_sample_project(mode=mode) if template == "sample" else new_empty_project(mode=mode)
        self._load_project_data(project, display_path=None)
        self._project_file = None
        self._dirty = True

    def _on_open_case_dialog(self) -> None:
        if not self._confirm_discard_if_dirty():
            return
        folder = self._QFileDialog.getExistingDirectory(self._win, "Open Case Folder")
        if not folder:
            return
        self.open_case_folder(Path(folder))

    def _on_open_output_dialog(self) -> None:
        folder = self._QFileDialog.getExistingDirectory(self._win, "Open Output Folder")
        if not folder:
            return
        self.open_output_folder(Path(folder))

    def _on_save(self) -> None:
        if self._project_file and self._project_file.suffix.lower() == DEFAULT_EXT:
            self.save_project(self._project_file)
            return
        self._on_save_as()

    def _on_save_as(self) -> None:
        if not self._project:
            self._QMessageBox.information(self._win, "Save As", "Open a project/case first.")
            return
        file, _ = self._QFileDialog.getSaveFileName(
            self._win,
            "Save Project As",
            "",
            f"GeoHPEM Project (*{DEFAULT_EXT});;All Files (*)",
        )
        if not file:
            return
        self.save_project(Path(file))

    def _on_run_fake(self) -> None:
        if not self._work_case_dir:
            self._QMessageBox.information(self._win, "Run", "Open a project/case first.")
            return
        from geohpem.gui.workers.solve_worker import SolveWorker

        worker = SolveWorker(case_dir=self._work_case_dir, solver_selector="fake")
        self.tasks_dock.attach_worker(worker)
        self.log_dock.attach_worker(worker)
        worker.output_ready.connect(self.open_output_folder)
        worker.start()

    def _on_about(self) -> None:
        import platform

        from geohpem import __version__

        self._QMessageBox.information(
            self._win,
            "About GeoHPEM",
            f"GeoHPEM {__version__}\nPython {platform.python_version()}",
        )

    def _rebuild_recent_menu(self) -> None:
        from PySide6.QtGui import QAction  # type: ignore

        self._menu_recent.clear()
        items = self._settings.get_recent_projects()
        if not items:
            act = QAction("(Empty)", self._win)
            act.setEnabled(False)
            self._menu_recent.addAction(act)
            return
        for p in items:
            act = QAction(str(p), self._win)
            act.triggered.connect(lambda checked=False, pp=p: self.open_case_folder(pp) if pp.is_dir() else self.open_project_file(pp))
            self._menu_recent.addAction(act)
