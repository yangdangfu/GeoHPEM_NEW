from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import copy
import numpy as np

from geohpem.project.types import ProjectData
from geohpem.gui.model.undo_stack import UndoCommand, UndoStack


@dataclass(slots=True)
class ProjectState:
    display_path: Path | None
    project_file: Path | None
    work_case_dir: Path | None
    dirty: bool
    project: ProjectData | None


class ProjectModel:
    """
    In-memory project state for GUI.

    This keeps request/mesh authoritative in memory; disk (work_case_dir / .geohpem) is derived.
    """

    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal  # type: ignore

        class _Signals(QObject):
            changed = Signal(object)  # ProjectState
            request_changed = Signal(object)  # dict
            mesh_changed = Signal(object)  # dict
            stages_changed = Signal(object)  # list
            materials_changed = Signal(object)  # dict
            undo_state_changed = Signal(bool, bool)  # can_undo, can_redo

        self._signals = _Signals()
        self.changed = self._signals.changed
        self.request_changed = self._signals.request_changed
        self.mesh_changed = self._signals.mesh_changed
        self.stages_changed = self._signals.stages_changed
        self.materials_changed = self._signals.materials_changed
        self.undo_state_changed = self._signals.undo_state_changed

        self._display_path: Path | None = None
        self._project_file: Path | None = None
        self._work_case_dir: Path | None = None
        self._dirty: bool = False
        self._project: ProjectData | None = None
        self.undo_stack = UndoStack()

    def state(self) -> ProjectState:
        return ProjectState(
            display_path=self._display_path,
            project_file=self._project_file,
            work_case_dir=self._work_case_dir,
            dirty=self._dirty,
            project=self._project,
        )

    def set_project(
        self,
        project: ProjectData,
        *,
        display_path: Path | None,
        project_file: Path | None,
        work_case_dir: Path | None,
        dirty: bool,
    ) -> None:
        self._project = project
        self._display_path = display_path
        self._project_file = project_file
        self._work_case_dir = work_case_dir
        self._dirty = dirty
        self.undo_stack.clear()
        self.changed.emit(self.state())
        self.request_changed.emit(project.request)
        self.mesh_changed.emit(project.mesh)
        self.stages_changed.emit(project.request.get("stages", []))
        self.materials_changed.emit(project.request.get("materials", {}))
        self.undo_state_changed.emit(self.undo_stack.can_undo(), self.undo_stack.can_redo())

    def set_dirty(self, dirty: bool) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self.changed.emit(self.state())

    def can_undo(self) -> bool:
        return self.undo_stack.can_undo()

    def can_redo(self) -> bool:
        return self.undo_stack.can_redo()

    def undo(self) -> None:
        self.undo_stack.undo()
        self.undo_state_changed.emit(self.undo_stack.can_undo(), self.undo_stack.can_redo())
        self.set_dirty(True)

    def redo(self) -> None:
        self.undo_stack.redo()
        self.undo_state_changed.emit(self.undo_stack.can_undo(), self.undo_stack.can_redo())
        self.set_dirty(True)

    def ensure_project(self) -> ProjectData:
        if not self._project:
            raise RuntimeError("No project loaded")
        return self._project

    def _clone_request(self) -> dict[str, Any]:
        project = self.ensure_project()
        return copy.deepcopy(project.request)

    def _set_request_no_undo(self, request: dict[str, Any]) -> None:
        project = self.ensure_project()
        project.request = request
        self.request_changed.emit(project.request)
        self.stages_changed.emit(project.request.get("stages", []))
        self.materials_changed.emit(project.request.get("materials", {}))

    def _with_request_undo(self, name: str, mutator: Callable[[], None]) -> None:
        before = self._clone_request()
        mutator()
        after = self._clone_request()
        if before == after:
            return

        def _undo() -> None:
            self._set_request_no_undo(copy.deepcopy(before))

        def _redo() -> None:
            self._set_request_no_undo(copy.deepcopy(after))

        self.undo_stack.push_and_redo(UndoCommand(name=name, undo=_undo, redo=_redo))
        self.undo_state_changed.emit(self.undo_stack.can_undo(), self.undo_stack.can_redo())
        self.set_dirty(True)

    def update_request(self, new_request: dict[str, Any]) -> None:
        def mut() -> None:
            project = self.ensure_project()
            project.request = new_request

        self._with_request_undo("Edit Request", mut)

    def update_mesh(self, new_mesh: dict[str, Any]) -> None:
        project = self.ensure_project()
        before = {k: np.asarray(v).copy() for k, v in project.mesh.items()}
        after = {k: np.asarray(v).copy() for k, v in new_mesh.items()}

        def _undo() -> None:
            project.mesh = {k: np.asarray(v).copy() for k, v in before.items()}
            self.mesh_changed.emit(project.mesh)

        def _redo() -> None:
            project.mesh = {k: np.asarray(v).copy() for k, v in after.items()}
            self.mesh_changed.emit(project.mesh)

        self.undo_stack.push_and_redo(UndoCommand(name="Edit Mesh", undo=_undo, redo=_redo))
        self.undo_state_changed.emit(self.undo_stack.can_undo(), self.undo_stack.can_redo())
        self.set_dirty(True)

    def update_model_mode(self, mode: str) -> None:
        def mut() -> None:
            project = self.ensure_project()
            model = project.request.setdefault("model", {})
            model["mode"] = mode

        self._with_request_undo("Set Mode", mut)

    def update_gravity(self, gx: float, gy: float) -> None:
        def mut() -> None:
            project = self.ensure_project()
            model = project.request.setdefault("model", {})
            model["gravity"] = [float(gx), float(gy)]

        self._with_request_undo("Set Gravity", mut)

    def update_stage(self, index: int, patch: dict[str, Any]) -> None:
        def mut() -> None:
            project = self.ensure_project()
            stages = project.request.setdefault("stages", [])
            if index < 0 or index >= len(stages):
                raise IndexError(index)
            stage = stages[index]
            if not isinstance(stage, dict):
                raise TypeError("stage is not an object")
            stage.update(patch)

        self._with_request_undo("Edit Stage", mut)

    def add_stage(self, *, copy_from: int | None = None) -> int:
        project = self.ensure_project()
        stages = project.request.setdefault("stages", [])
        added_index: int | None = None

        def mut() -> None:
            nonlocal added_index
            project = self.ensure_project()
            stages = project.request.setdefault("stages", [])
            if copy_from is None:
                new_stage: dict[str, Any] = {
                    "id": f"stage_{len(stages)+1}",
                    "analysis_type": "static",
                    "num_steps": 1,
                    "bcs": [],
                    "loads": [],
                    "output_requests": [],
                }
            else:
                src = stages[copy_from]
                if not isinstance(src, dict):
                    raise TypeError("stage is not an object")
                new_stage = copy.deepcopy(src)
                new_stage["id"] = f"{new_stage.get('id','stage')}_copy"
            stages.append(new_stage)
            added_index = len(stages) - 1

        self._with_request_undo("Add Stage", mut)
        return int(added_index if added_index is not None else len(stages) - 1)

    def delete_stage(self, index: int) -> None:
        def mut() -> None:
            project = self.ensure_project()
            stages = project.request.get("stages", [])
            if not isinstance(stages, list):
                return
            if len(stages) <= 1:
                raise ValueError("Cannot delete the last stage")
            if index < 0 or index >= len(stages):
                raise IndexError(index)
            stages.pop(index)

        self._with_request_undo("Delete Stage", mut)

    def set_material(self, material_id: str, model_name: str, parameters: dict[str, Any]) -> None:
        def mut() -> None:
            project = self.ensure_project()
            mats = project.request.setdefault("materials", {})
            mats[material_id] = {"model_name": model_name, "parameters": parameters}

        self._with_request_undo("Edit Material", mut)

    def delete_material(self, material_id: str) -> None:
        def mut() -> None:
            project = self.ensure_project()
            mats = project.request.get("materials", {})
            if not isinstance(mats, dict):
                return
            if material_id in mats:
                del mats[material_id]

        self._with_request_undo("Delete Material", mut)

    def update_geometry(self, geometry: dict[str, Any] | None) -> None:
        def mut() -> None:
            project = self.ensure_project()
            if geometry is None:
                project.request.pop("geometry", None)
            else:
                project.request["geometry"] = geometry

        self._with_request_undo("Edit Geometry", mut)
