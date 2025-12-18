from __future__ import annotations

from pathlib import Path
from typing import Any

from geohpem.contract.io import read_result_folder
from geohpem.contract.io import write_case_folder
from geohpem.gui.dialogs.import_mesh_dialog import ImportMeshDialog
from geohpem.gui.dialogs.batch_run_dialog import BatchRunDialog
from geohpem.gui.dialogs.compare_outputs_dialog import CompareOutputsDialog
from geohpem.gui.dialogs.mesh_quality_dialog import MeshQualityDialog
from geohpem.gui.dialogs.precheck_dialog import PrecheckDialog
from geohpem.gui.dialogs.sets_dialog import SetsDialog
from geohpem.gui.dialogs.solver_dialog import SolverDialog
from geohpem.gui.dialogs.units_dialog import UnitsDialog
from geohpem.gui.model.project_model import ProjectModel
from geohpem.gui.model.selection_model import Selection, SelectionModel
from geohpem.gui.widgets.docks.geometry_dock import GeometryDock
from geohpem.gui.widgets.docks.log_dock import LogDock
from geohpem.gui.widgets.docks.project_dock import ProjectDock
from geohpem.gui.widgets.docks.properties_dock import PropertiesDock
from geohpem.gui.widgets.docks.stage_dock import StageDock
from geohpem.gui.widgets.docks.tasks_dock import TasksDock
from geohpem.gui.workspaces.output_workspace import OutputWorkspace
from geohpem.gui.workspaces.workspace_stack import WorkspaceStack
from geohpem.project.case_folder import load_case_folder
from geohpem.project.normalize import find_stage_index_by_uid
from geohpem.project.package import DEFAULT_EXT, load_geohpem, save_geohpem
from geohpem.project.types import ProjectData
from geohpem.project.workdir import materialize_to_workdir, update_project_from_workdir


class MainWindow:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Qt, Slot  # type: ignore
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
                    outer._shutdown_before_close()
                    event.accept()
                else:
                    event.ignore()

        self._win = _GeoMainWindow()
        self._win.setWindowTitle("GeoHPEM")
        self._win.resize(1400, 900)

        outer = self

        class _UiSlots(QObject):
            @Slot(object)
            def on_output_ready(self, out_dir) -> None:  # noqa: ANN001
                outer.open_output_folder(Path(out_dir))

            @Slot(str, object)
            def on_solver_failed(self, error_text: str, diag_path) -> None:  # noqa: ANN001
                outer._on_solver_failed(error_text, diag_path)

            @Slot(object)
            def on_solver_canceled(self, diag_path) -> None:  # noqa: ANN001
                outer._on_solver_canceled(diag_path)

        self._ui_slots = _UiSlots()

        self.workspace_stack = WorkspaceStack()
        self._win.setCentralWidget(self.workspace_stack.widget)

        self.project_dock = ProjectDock()
        self.geometry_dock = GeometryDock()
        self.properties_dock = PropertiesDock()
        self.stage_dock = StageDock()
        self.log_dock = LogDock()
        self.tasks_dock = TasksDock()

        self._win.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock.dock)
        self._win.addDockWidget(Qt.LeftDockWidgetArea, self.geometry_dock.dock)
        self._win.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock.dock)
        self._win.addDockWidget(Qt.RightDockWidgetArea, self.stage_dock.dock)
        self._win.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock.dock)
        self._win.addDockWidget(Qt.BottomDockWidgetArea, self.tasks_dock.dock)

        self._win.tabifyDockWidget(self.project_dock.dock, self.geometry_dock.dock)
        self._win.tabifyDockWidget(self.log_dock.dock, self.tasks_dock.dock)
        self.log_dock.dock.raise_()

        self.model = ProjectModel()
        self.selection = SelectionModel()
        self._active_workers: list[object] = []
        self._unit_context = None  # UnitContext | None
        self._solver_caps_cache: dict[str, dict[str, Any]] = {}

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

        self._action_units = QAction("Display Units...", self._win)
        self._action_units.triggered.connect(self._on_display_units)

        self._action_batch_run = QAction("Batch Run...", self._win)
        self._action_batch_run.triggered.connect(self._on_batch_run)

        self._action_compare_outputs = QAction("Compare Outputs...", self._win)
        self._action_compare_outputs.triggered.connect(self._on_compare_outputs)

        self._action_import_mesh = QAction("Import Mesh...", self._win)
        self._action_import_mesh.triggered.connect(self._on_import_mesh)

        self._action_ws_input = QAction("Workspace: Input", self._win)
        self._action_ws_input.triggered.connect(lambda: self.workspace_stack.set_workspace("input"))

        self._action_ws_output = QAction("Workspace: Output", self._win)
        self._action_ws_output.triggered.connect(lambda: self.workspace_stack.set_workspace("output"))

        self._action_select_solver = QAction("Select Solver...", self._win)
        self._action_select_solver.triggered.connect(self._on_select_solver)

        self._action_run = QAction("Run", self._win)
        self._action_run.triggered.connect(self._on_run_solver)

        self._action_sets = QAction("Manage Sets...", self._win)
        self._action_sets.triggered.connect(self._on_manage_sets)

        self._action_mesh_quality = QAction("Mesh Quality...", self._win)
        self._action_mesh_quality.triggered.connect(self._on_mesh_quality)

        self._action_undo = QAction("Undo", self._win)
        self._action_undo.setShortcut("Ctrl+Z")
        self._action_undo.triggered.connect(self.model.undo)
        self._action_redo = QAction("Redo", self._win)
        self._action_redo.setShortcut("Ctrl+Y")
        self._action_redo.triggered.connect(self.model.redo)

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
        menu_file.addAction(self._action_import_mesh)
        menu_file.addAction(self._action_open_results)

        menu_edit = self._win.menuBar().addMenu("Edit")
        menu_edit.addAction(self._action_undo)
        menu_edit.addAction(self._action_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self._action_sets)

        menu_mesh = self._win.menuBar().addMenu("Mesh")
        menu_mesh.addAction(self._action_mesh_quality)

        menu_ws = self._win.menuBar().addMenu("Workspace")
        menu_ws.addAction(self._action_ws_input)
        menu_ws.addAction(self._action_ws_output)

        menu_view = self._win.menuBar().addMenu("View")
        menu_view.addAction(self._action_units)

        menu_tools = self._win.menuBar().addMenu("Tools")
        menu_tools.addAction(self._action_batch_run)
        menu_tools.addAction(self._action_compare_outputs)

        menu_solve = self._win.menuBar().addMenu("Solve")
        menu_solve.addAction(self._action_select_solver)
        menu_solve.addAction(self._action_run)

        menu_help = self._win.menuBar().addMenu("Help")
        menu_help.addAction(self._action_about)

        self.project_dock.case_open_requested.connect(self.open_case_folder)
        self.project_dock.output_open_requested.connect(self.open_output_folder)
        self.project_dock.selection_changed.connect(self._on_tree_selection)

        self.stage_dock.stage_selected.connect(self._on_stage_selected)
        self.stage_dock.add_stage.connect(self._on_stage_add)
        self.stage_dock.copy_stage.connect(self._on_stage_copy)
        self.stage_dock.delete_stage.connect(self._on_stage_delete)

        self.properties_dock.bind_apply_model(self._apply_model)
        self.properties_dock.bind_apply_stage(self._apply_stage)
        self.properties_dock.bind_apply_material(self._apply_material)

        self.model.changed.connect(self._on_model_changed)
        self.model.stages_changed.connect(lambda stages: self.stage_dock.set_stages(stages))
        self.model.request_changed.connect(self._refresh_tree)
        self.model.request_changed.connect(lambda req: self._apply_unit_context_from_request(req))
        self.model.materials_changed.connect(lambda mats: self._refresh_tree(self.model.ensure_project().request))
        self.model.mesh_changed.connect(lambda m: self._refresh_tree(self.model.ensure_project().request))
        self.model.undo_state_changed.connect(self._on_undo_state_changed)

        self.geometry_dock.bind_model(self.model)
        self._on_undo_state_changed(False, False)

        self.selection.changed.connect(self._on_selection_changed)

        self._update_run_action_text()
        self._apply_solver_capabilities(self._safe_get_solver_caps(self._settings.get_solver_selector()))
        self._shutdown_done = False

    @property
    def qt(self):
        return self._win

    def show(self) -> None:
        self._win.show()

    def _shutdown_before_close(self) -> None:
        if getattr(self, "_shutdown_done", False):
            return
        self._shutdown_done = True
        # Best-effort cancel active background workers.
        for w in list(self._active_workers):
            try:
                if hasattr(w, "cancel"):
                    w.cancel()
            except Exception:
                pass
        # Teardown VTK/Qt render windows before the native HWND/context is destroyed.
        try:
            out = self.workspace_stack.get("output")
            if hasattr(out, "shutdown"):
                out.shutdown()
        except Exception:
            pass

    def _load_project_data(self, project: ProjectData, display_path: Path | None) -> None:
        workdir = materialize_to_workdir(project)
        project_file = display_path if (display_path and display_path.suffix.lower() == DEFAULT_EXT) else None
        # Ensure stable IDs exist (stages/materials/geometry/sets meta)
        from geohpem.project.normalize import ensure_request_ids

        ensure_request_ids(project.request, project.mesh)
        self.model.set_project(
            project,
            display_path=display_path,
            project_file=project_file,
            work_case_dir=workdir,
            dirty=False,
        )

        # Drive the tree by the materialized case dir.
        self.project_dock.set_case(workdir, request=project.request, mesh=project.mesh)
        self.stage_dock.set_stages(project.request.get("stages", []))
        self.log_dock.append_info(f"Loaded: {display_path or workdir}")
        self._apply_unit_context_from_request(project.request)

        if project.result_meta is not None and project.result_arrays is not None:
            self.open_output_folder(workdir / "out")
        self.workspace_stack.set_workspace("input")

    def _refresh_tree(self, request: dict[str, Any]) -> None:
        state = self.model.state()
        if not state.project or not state.work_case_dir:
            return
        self.project_dock.set_case(state.work_case_dir, request=state.project.request, mesh=state.project.mesh)

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
        state = self.model.state()
        if not state.project:
            return
        project = state.project
        # Pull back latest out/ (if any) from work dir before saving.
        if state.work_case_dir:
            project = update_project_from_workdir(project, state.work_case_dir)
        try:
            saved = save_geohpem(project_file, project)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Save Failed", str(exc))
            return
        self._settings.add_recent_project(saved)
        self._settings.set_last_project(saved)
        self._rebuild_recent_menu()
        self.model.set_project(
            project,
            display_path=saved,
            project_file=saved,
            work_case_dir=state.work_case_dir,
            dirty=False,
        )
        self.log_dock.append_info(f"Saved: {saved}")

    def open_output_folder(self, out_dir: Path) -> None:
        try:
            meta, arrays = read_result_folder(out_dir)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Open Output Failed", str(exc))
            return

        output_ws = self.workspace_stack.get("output")
        if isinstance(output_ws, OutputWorkspace):
            mesh = None
            req = None
            state = self.model.state()
            if state.project:
                mesh = state.project.mesh
                req = state.project.request
            else:
                # try load mesh from sibling mesh.npz
                try:
                    from geohpem.contract.io import read_case_folder

                    req, m = read_case_folder(out_dir.parent)
                    mesh = m
                except Exception:
                    mesh = None
            output_ws.set_result(meta, arrays, mesh=mesh)
            if req is not None:
                self._apply_unit_context_from_request(req)
        self.log_dock.append_info(f"Opened output: {out_dir}")
        self.workspace_stack.set_workspace("output")

    def _apply_unit_context_from_request(self, request: dict[str, Any]) -> None:
        from geohpem.units import UnitContext, merge_display_units, normalize_unit_system, request_unit_system

        base = normalize_unit_system(request_unit_system(request))
        base.setdefault("length", "m")
        base.setdefault("pressure", "kPa")
        base.setdefault("force", "kN")
        base.setdefault("time", "s")
        display_pref = self._settings.get_display_units()
        display = merge_display_units(base, display_pref)
        self._unit_context = UnitContext(base=base, display=display)
        self.geometry_dock.set_unit_context(self._unit_context)
        output_ws = self.workspace_stack.get("output")
        if isinstance(output_ws, OutputWorkspace):
            output_ws.set_unit_context(self._unit_context)

    def _safe_get_solver_caps(self, selector: str) -> dict[str, Any] | None:
        try:
            return self._get_solver_caps(selector)
        except Exception:
            return None

    def _get_solver_caps(self, selector: str) -> dict[str, Any]:
        selector = (selector or "").strip() or "fake"
        if selector in self._solver_caps_cache:
            return self._solver_caps_cache[selector]
        from geohpem.solver_adapter.loader import load_solver

        solver = load_solver(selector)
        caps = solver.capabilities()
        if not isinstance(caps, dict):
            raise TypeError("solver.capabilities() must return a dict")
        self._solver_caps_cache[selector] = caps
        return caps

    def _apply_solver_capabilities(self, caps: dict[str, Any] | None) -> None:
        self.properties_dock.set_solver_capabilities(caps)

    def _update_run_action_text(self) -> None:
        selector = self._settings.get_solver_selector()
        label = selector
        if selector == "fake":
            label = "fake"
        elif selector.startswith("python:"):
            label = selector.split("python:", 1)[1].strip() or selector
        self._action_run.setText(f"Run ({label})")

    def _on_select_solver(self) -> None:
        cur = self._settings.get_solver_selector()
        dlg = SolverDialog(self._win, current_selector=cur)
        res = dlg.exec()
        if res is None:
            return
        try:
            caps = self._get_solver_caps(res.solver_selector)
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Solver", f"Failed to load solver '{res.solver_selector}':\n{exc}")
            return
        self._settings.set_solver_selector(res.solver_selector)
        self._update_run_action_text()
        self._apply_solver_capabilities(caps)
        self.log_dock.append_info(f"Selected solver: {res.solver_selector}")

    def _on_batch_run(self) -> None:
        dlg = BatchRunDialog(self._win, solver_selector=self._settings.get_solver_selector())
        dlg.exec()

    def _on_compare_outputs(self) -> None:
        dlg = CompareOutputsDialog(self._win)
        dlg.exec()

    def _on_display_units(self) -> None:
        state = self.model.state()
        if not state.project:
            self._QMessageBox.information(self._win, "Display Units", "Open a project/case first.")
            return
        from geohpem.units import normalize_unit_system, request_unit_system

        base = normalize_unit_system(request_unit_system(state.project.request))
        base.setdefault("length", "m")
        base.setdefault("pressure", "kPa")
        current = self._settings.get_display_units()
        dlg = UnitsDialog(self._win, base_units=base, current_display_units=current)
        res = dlg.exec()
        if res is None:
            return
        self._settings.set_display_units(res.display_units)
        self._apply_unit_context_from_request(state.project.request)

    def _confirm_discard_if_dirty(self) -> bool:
        if not self.model.state().dirty:
            return True
        btn = self._QMessageBox.question(
            self._win,
            "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            self._QMessageBox.Yes | self._QMessageBox.No,
        )
        return btn == self._QMessageBox.Yes

    def _confirm_close(self) -> bool:
        if not self.model.state().dirty:
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
        project_file = self.model.state().project_file
        if project_file and project_file.suffix.lower() == DEFAULT_EXT:
            self.save_project(project_file)
            return not self.model.state().dirty
        self._on_save_as()
        return not self.model.state().dirty

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
        self.model.set_dirty(True)

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
        project_file = self.model.state().project_file
        if project_file and project_file.suffix.lower() == DEFAULT_EXT:
            self.save_project(project_file)
            return
        self._on_save_as()

    def _on_save_as(self) -> None:
        if not self.model.state().project:
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

    def _on_run_solver(self) -> None:
        try:
            state = self.model.state()
            if not state.project or not state.work_case_dir:
                self._QMessageBox.information(self._win, "Run", "Open a project/case first.")
                return
            from geohpem.app.precheck import precheck_request_mesh

            solver_selector = self._settings.get_solver_selector()
            try:
                caps = self._get_solver_caps(solver_selector)
            except Exception as exc:
                self._QMessageBox.critical(self._win, "Run", f"Failed to load solver '{solver_selector}':\n{exc}")
                return

            issues = precheck_request_mesh(state.project.request, state.project.mesh, capabilities=caps)
            dlg = PrecheckDialog(self._win, issues)
            if not dlg.exec():
                return
            # Ensure work dir reflects latest in-memory inputs.
            write_case_folder(state.work_case_dir, state.project.request, state.project.mesh)

            from geohpem.gui.workers.solve_worker import SolveWorker

            worker = SolveWorker(case_dir=state.work_case_dir, solver_selector=solver_selector)
            # Keep strong reference during run to prevent GC-related crashes.
            self._active_workers.append(worker)
            worker.finished.connect(lambda: self._active_workers.remove(worker) if worker in self._active_workers else None)
            self.tasks_dock.attach_worker(worker)
            self.log_dock.attach_worker(worker)
            worker.output_ready.connect(self._ui_slots.on_output_ready)
            if hasattr(worker, "failed"):
                worker.failed.connect(self._ui_slots.on_solver_failed)  # type: ignore[attr-defined]
            if hasattr(worker, "canceled"):
                worker.canceled.connect(self._ui_slots.on_solver_canceled)  # type: ignore[attr-defined]
            worker.start()
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Run Failed", str(exc))

    def _on_solver_failed(self, error_text: str, diag_path) -> None:  # noqa: ANN001
        msg = f"Solver failed:\n{error_text}"
        if diag_path:
            try:
                msg += f"\n\nDiagnostics:\n{diag_path}"
            except Exception:
                pass
        self._QMessageBox.critical(self._win, "Solve Failed", msg)
        self.log_dock.append_info(msg)

    def _on_solver_canceled(self, diag_path) -> None:  # noqa: ANN001
        msg = "Solve canceled."
        if diag_path:
            try:
                msg += f"\n\nDiagnostics:\n{diag_path}"
            except Exception:
                pass
        self._QMessageBox.information(self._win, "Solve", msg)
        self.log_dock.append_info(msg)

    def _on_manage_sets(self) -> None:
        state = self.model.state()
        if not state.project:
            self._QMessageBox.information(self._win, "Sets", "Open a project/case first.")
            return

        def apply_mesh(new_mesh):
            self.model.update_mesh(new_mesh)

        dlg = SetsDialog(self._win, mesh=state.project.mesh, on_apply=apply_mesh)
        dlg.exec()

    def _on_mesh_quality(self) -> None:
        state = self.model.state()
        if not state.project:
            self._QMessageBox.information(self._win, "Mesh", "Open a project/case first.")
            return
        dlg = MeshQualityDialog(self._win, state.project.mesh)
        dlg.exec()

    def _on_import_mesh(self) -> None:
        state = self.model.state()
        if not state.project:
            self._QMessageBox.information(self._win, "Import Mesh", "Open a project/case first.")
            return
        try:
            dlg = ImportMeshDialog(self._win)
            res = dlg.exec()
        except Exception as exc:
            self._QMessageBox.critical(self._win, "Import Mesh Failed", str(exc))
            return
        if not res:
            return
        self.model.update_mesh(res.mesh)
        self.log_dock.append_info(
            f"Imported mesh: points={res.report.points}, cells={res.report.cells}, "
            f"node_sets={len(res.report.node_sets)}, edge_sets={len(res.report.edge_sets)}, elem_sets={len(res.report.element_sets)}"
        )

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

    def _on_model_changed(self, state) -> None:  # noqa: ANN001
        title = "GeoHPEM - Untitled"
        if state.display_path:
            title = f"GeoHPEM - {state.display_path.name}"
        if state.dirty:
            title += " *"
        self._win.setWindowTitle(title)

    def _on_undo_state_changed(self, can_undo: bool, can_redo: bool) -> None:
        self._action_undo.setEnabled(bool(can_undo))
        self._action_redo.setEnabled(bool(can_redo))

    def _on_tree_selection(self, payload: dict[str, Any]) -> None:
        t = str(payload.get("type", ""))
        if t == "stage" and "uid" in payload and not payload.get("uid"):
            # fallback for older payloads
            payload = dict(payload)
            payload["type"] = "stage"
        self.selection.set(Selection(kind=t, ref=payload))

    def _on_stage_selected(self, uid: str) -> None:
        self.selection.set(Selection(kind="stage", ref={"type": "stage", "uid": uid}))

    def _on_selection_changed(self, sel) -> None:  # noqa: ANN001
        state = self.model.state()
        if not state.project or sel is None:
            self.properties_dock.show_empty()
            return

        t = sel.kind
        ref = sel.ref
        if t == "model":
            self.properties_dock.show_model(state.project.request)
            return
        if t == "stage":
            uid = str(ref.get("uid", ""))
            idx = find_stage_index_by_uid(state.project.request, uid)
            if idx is None:
                self.properties_dock.show_empty()
                return
            stages = state.project.request.get("stages", [])
            if 0 <= idx < len(stages) and isinstance(stages[idx], dict):
                self.properties_dock.show_stage(idx, stages[idx])
                self.stage_dock.select_stage(idx)
                return
        if t == "material":
            mid = str(ref.get("id", ""))
            mats = state.project.request.get("materials", {})
            if isinstance(mats, dict) and mid in mats and isinstance(mats[mid], dict):
                self.properties_dock.show_material(mid, mats[mid])
                return

        self.properties_dock.show_empty()

    def _on_stage_add(self) -> None:
        idx = self.model.add_stage(copy_from=None)
        self.stage_dock.select_stage(idx)

    def _on_stage_copy(self, uid: str) -> None:
        state = self.model.state()
        if not state.project:
            return
        idx0 = find_stage_index_by_uid(state.project.request, uid)
        if idx0 is None:
            return
        idx = self.model.add_stage(copy_from=idx0)
        self.stage_dock.select_stage(idx)

    def _on_stage_delete(self, uid: str) -> None:
        state = self.model.state()
        if not state.project:
            return
        idx = find_stage_index_by_uid(state.project.request, uid)
        if idx is None:
            return
        try:
            self.model.delete_stage(idx)
        except Exception as exc:
            self._QMessageBox.information(self._win, "Delete Stage", str(exc))

    def _apply_model(self, mode: str, gx: float, gy: float) -> None:
        self.model.update_model_mode(mode)
        self.model.update_gravity(gx, gy)
        self.log_dock.append_info(f"Updated model: mode={mode}, g=({gx},{gy})")

    def _apply_stage(self, index: int, patch: dict[str, Any]) -> None:
        self.model.update_stage(index, patch)
        self.log_dock.append_info(f"Updated stage[{index}]")

    def _apply_material(self, material_id: str, model_name: str, parameters: dict[str, Any]) -> None:
        self.model.set_material(material_id, model_name, parameters)
        self.log_dock.append_info(f"Updated material: {material_id}")
