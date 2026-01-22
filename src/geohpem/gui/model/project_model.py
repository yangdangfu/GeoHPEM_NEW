from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from geohpem.gui.model.undo_stack import UndoCommand, UndoStack
from geohpem.project.types import ProjectData


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
            assignments_changed = Signal(object)  # list
            undo_state_changed = Signal(bool, bool)  # can_undo, can_redo

        self._signals = _Signals()
        self.changed = self._signals.changed
        self.request_changed = self._signals.request_changed
        self.mesh_changed = self._signals.mesh_changed
        self.stages_changed = self._signals.stages_changed
        self.materials_changed = self._signals.materials_changed
        self.assignments_changed = self._signals.assignments_changed
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
        self.assignments_changed.emit(project.request.get("assignments", []))
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )

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
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )
        self.set_dirty(True)

    def redo(self) -> None:
        self.undo_stack.redo()
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )
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
        try:
            from geohpem.project.normalize import ensure_request_ids

            ensure_request_ids(project.request, project.mesh)
        except Exception:
            pass
        self.request_changed.emit(project.request)
        self.stages_changed.emit(project.request.get("stages", []))
        self.materials_changed.emit(project.request.get("materials", {}))
        self.assignments_changed.emit(project.request.get("assignments", []))

    def _with_request_undo(
        self, name: str, mutator: Callable[[], None], *, merge_key: str | None = None
    ) -> None:
        before = self._clone_request()
        mutator()
        after = self._clone_request()
        if before == after:
            return

        def _undo() -> None:
            self._set_request_no_undo(copy.deepcopy(before))

        def _redo() -> None:
            self._set_request_no_undo(copy.deepcopy(after))

        self.undo_stack.push_and_redo(
            UndoCommand(name=name, undo=_undo, redo=_redo), merge_key=merge_key
        )
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )
        self.set_dirty(True)

    def update_request(
        self, new_request: dict[str, Any], *, merge_key: str | None = None
    ) -> None:
        def mut() -> None:
            project = self.ensure_project()
            project.request = new_request
            try:
                from geohpem.project.normalize import ensure_request_ids

                ensure_request_ids(project.request, project.mesh)
            except Exception:
                pass

        self._with_request_undo("Edit Request", mut, merge_key=merge_key)

    def update_assignments(self, assignments: list[dict[str, Any]]) -> None:
        from geohpem.domain.request_ops import set_assignments

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_assignments(project.request, assignments)

        self._with_request_undo("Edit Assignments", mut)

    def update_global_output_requests(
        self, output_requests: list[dict[str, Any]]
    ) -> None:
        from geohpem.domain.request_ops import set_global_output_requests

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_global_output_requests(
                project.request, output_requests
            )

        self._with_request_undo("Edit Global Output Requests", mut)

    def update_mesh(self, new_mesh: dict[str, Any]) -> None:
        project = self.ensure_project()
        before = {k: np.asarray(v).copy() for k, v in project.mesh.items()}
        after = {k: np.asarray(v).copy() for k, v in new_mesh.items()}

        def _undo() -> None:
            project.mesh = {k: np.asarray(v).copy() for k, v in before.items()}
            from geohpem.project.normalize import ensure_request_ids

            ensure_request_ids(project.request, project.mesh)
            self.mesh_changed.emit(project.mesh)

        def _redo() -> None:
            project.mesh = {k: np.asarray(v).copy() for k, v in after.items()}
            from geohpem.project.normalize import ensure_request_ids

            ensure_request_ids(project.request, project.mesh)
            self.mesh_changed.emit(project.mesh)

        self.undo_stack.push_and_redo(
            UndoCommand(name="Edit Mesh", undo=_undo, redo=_redo)
        )
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )
        self.set_dirty(True)

    def update_request_and_mesh(
        self,
        *,
        request: dict[str, Any],
        mesh: dict[str, Any],
        name: str = "Edit Project",
        merge_key: str | None = None,
    ) -> None:
        """
        Atomically update request+mesh in one undo step.

        Useful when a UI action creates/renames sets (touches mesh) and also updates request.sets_meta (labels/uid).
        """
        import copy

        project = self.ensure_project()
        before_req = copy.deepcopy(project.request)
        before_mesh = {k: np.asarray(v).copy() for k, v in project.mesh.items()}
        after_req = copy.deepcopy(request)
        after_mesh = {k: np.asarray(v).copy() for k, v in mesh.items()}

        def _apply(req: dict[str, Any], m: dict[str, Any]) -> None:
            project.request = req
            project.mesh = m
            try:
                from geohpem.project.normalize import ensure_request_ids

                ensure_request_ids(project.request, project.mesh)
            except Exception:
                pass
            self.request_changed.emit(project.request)
            self.mesh_changed.emit(project.mesh)
            self.stages_changed.emit(project.request.get("stages", []))
            self.materials_changed.emit(project.request.get("materials", {}))
            self.assignments_changed.emit(project.request.get("assignments", []))

        def _undo() -> None:
            _apply(
                copy.deepcopy(before_req),
                {k: np.asarray(v).copy() for k, v in before_mesh.items()},
            )

        def _redo() -> None:
            _apply(
                copy.deepcopy(after_req),
                {k: np.asarray(v).copy() for k, v in after_mesh.items()},
            )

        self.undo_stack.push_and_redo(
            UndoCommand(name=name, undo=_undo, redo=_redo), merge_key=merge_key
        )
        self.undo_state_changed.emit(
            self.undo_stack.can_undo(), self.undo_stack.can_redo()
        )
        self.set_dirty(True)

    def update_model(self, mode: str, gx: float, gy: float) -> None:
        from geohpem.domain.request_ops import set_model

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_model(project.request, mode=mode, gravity=(gx, gy))

        self._with_request_undo("Edit Model", mut)

    def update_model_mode(self, mode: str) -> None:
        from geohpem.domain.request_ops import set_model_mode

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_model_mode(project.request, mode)

        self._with_request_undo("Set Mode", mut)

    def update_gravity(self, gx: float, gy: float) -> None:
        from geohpem.domain.request_ops import set_gravity

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_gravity(project.request, gx, gy)

        self._with_request_undo("Set Gravity", mut)

    def update_stage(self, index: int, patch: dict[str, Any]) -> None:
        from geohpem.domain.request_ops import apply_stage_patch_by_index

        def mut() -> None:
            project = self.ensure_project()
            project.request = apply_stage_patch_by_index(project.request, index, patch)

        self._with_request_undo("Edit Stage", mut)

    def update_stage_by_uid(self, stage_uid: str, patch: dict[str, Any]) -> None:
        """
        Update a stage by stable uid (preferred over index to avoid reference drift).
        """
        from geohpem.domain.request_ops import apply_stage_patch_by_uid

        def mut() -> None:
            project = self.ensure_project()
            project.request = apply_stage_patch_by_uid(
                project.request, stage_uid, patch
            )

        self._with_request_undo("Edit Stage", mut)

    def add_stage(self, *, copy_from: int | None = None) -> int:
        from geohpem.domain.request_ops import add_stage

        added_index: int | None = None

        def mut() -> None:
            nonlocal added_index
            project = self.ensure_project()
            req2, idx = add_stage(project.request, copy_from_index=copy_from)
            project.request = req2
            added_index = idx

        self._with_request_undo("Add Stage", mut)
        if added_index is not None:
            return int(added_index)
        try:
            stages = self.ensure_project().request.get("stages", [])
            return max(0, len(stages) - 1) if isinstance(stages, list) else 0
        except Exception:
            return 0

    def delete_stage(self, index: int) -> None:
        from geohpem.domain.request_ops import delete_stage

        def mut() -> None:
            project = self.ensure_project()
            project.request = delete_stage(project.request, index)

        self._with_request_undo("Delete Stage", mut)

    def set_material(
        self,
        material_id: str,
        model_name: str,
        parameters: dict[str, Any],
        *,
        behavior: str | None = None,
    ) -> None:
        from geohpem.domain.request_ops import upsert_material

        def mut() -> None:
            project = self.ensure_project()
            project.request = upsert_material(
                project.request,
                material_id,
                model_name,
                parameters,
                behavior=behavior,
            )

        self._with_request_undo("Edit Material", mut)

    def delete_material(self, material_id: str) -> None:
        from geohpem.domain.request_ops import delete_material

        def mut() -> None:
            project = self.ensure_project()
            project.request = delete_material(project.request, material_id)

        self._with_request_undo("Delete Material", mut)

    def update_geometry(self, geometry: dict[str, Any] | None) -> None:
        from geohpem.domain.request_ops import set_geometry

        def mut() -> None:
            project = self.ensure_project()
            project.request = set_geometry(project.request, geometry)

        self._with_request_undo("Edit Geometry", mut)
