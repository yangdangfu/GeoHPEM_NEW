from __future__ import annotations

import logging
from pathlib import Path

from geohpem.contract.io import read_case_folder, read_result_folder
from geohpem.gui.widgets.docks.log_dock import LogDock
from geohpem.gui.widgets.docks.project_dock import ProjectDock
from geohpem.gui.widgets.docks.properties_dock import PropertiesDock
from geohpem.gui.widgets.docks.stage_dock import StageDock
from geohpem.gui.widgets.docks.tasks_dock import TasksDock
from geohpem.gui.workspaces.output_workspace import OutputWorkspace
from geohpem.gui.workspaces.workspace_stack import WorkspaceStack

logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtGui import QAction  # type: ignore
        from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox  # type: ignore

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QFileDialog = QFileDialog

        self._win = QMainWindow()
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

        self._action_open = QAction("Open Case Folder...", self._win)
        self._action_open.triggered.connect(self._on_open_case_dialog)

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
        menu_file.addAction(self._action_open)
        menu_file.addAction(self._action_open_results)

        menu_ws = self._win.menuBar().addMenu("Workspace")
        menu_ws.addAction(self._action_ws_input)
        menu_ws.addAction(self._action_ws_output)

        menu_solve = self._win.menuBar().addMenu("Solve")
        menu_solve.addAction(self._action_run)

        menu_help = self._win.menuBar().addMenu("Help")
        menu_help.addAction(self._action_about)

        self._current_case_dir: Path | None = None

        self.project_dock.case_open_requested.connect(self.open_case_folder)
        self.project_dock.output_open_requested.connect(self.open_output_folder)

    @property
    def qt(self):
        return self._win

    def show(self) -> None:
        self._win.show()

    def open_case_folder(self, case_dir: Path) -> None:
        try:
            request, mesh = read_case_folder(case_dir)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Open Case Failed", str(exc))
            return

        self._current_case_dir = case_dir
        self.project_dock.set_case(case_dir, request=request, mesh=mesh)
        self.properties_dock.set_object(("request", request))
        self.stage_dock.set_stages(request.get("stages", []))
        self.log_dock.append_info(f"Opened case: {case_dir}")
        self.workspace_stack.set_workspace("input")

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

    def _on_open_case_dialog(self) -> None:
        folder = self._QFileDialog.getExistingDirectory(self._win, "Open Case Folder")
        if not folder:
            return
        self.open_case_folder(Path(folder))

    def _on_open_output_dialog(self) -> None:
        folder = self._QFileDialog.getExistingDirectory(self._win, "Open Output Folder")
        if not folder:
            return
        self.open_output_folder(Path(folder))

    def _on_run_fake(self) -> None:
        if not self._current_case_dir:
            self._QMessageBox.information(self._win, "Run", "Open a case folder first.")
            return
        from geohpem.gui.workers.solve_worker import SolveWorker

        worker = SolveWorker(case_dir=self._current_case_dir, solver_selector="fake")
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

