from __future__ import annotations

from pathlib import Path
from typing import Any


class ProjectDock:
    def __init__(self) -> None:
        from PySide6.QtCore import Qt, Signal  # type: ignore
        from PySide6.QtWidgets import (
            QDockWidget,  # type: ignore
            QPushButton,
            QTreeWidget,
            QVBoxLayout,
            QWidget,
        )

        class _Signals(QWidget):
            case_open_requested = Signal(Path)
            output_open_requested = Signal(Path)
            selection_changed = Signal(object)  # payload dict

        self._signals = _Signals()
        self.case_open_requested = self._signals.case_open_requested
        self.output_open_requested = self._signals.output_open_requested
        self.selection_changed = self._signals.selection_changed

        self._Qt = Qt

        self.dock = QDockWidget("Project")
        self.dock.setObjectName("dock_project")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree)

        self.btn_open_out = QPushButton("Open out/ folder")
        layout.addWidget(self.btn_open_out)
        self.btn_open_out.clicked.connect(self._open_out_folder)

        self._case_dir: Path | None = None
        self._request: dict[str, Any] | None = None
        self._mesh: dict[str, Any] | None = None

    def set_case(
        self, case_dir: Path, request: dict[str, Any], mesh: dict[str, Any]
    ) -> None:
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        self._case_dir = case_dir
        self._request = request
        self._mesh = mesh

        prev_payload = None
        try:
            cur = self.tree.currentItem()
            if cur is not None:
                prev_payload = cur.data(0, self._Qt.UserRole)
        except Exception:
            prev_payload = None

        self.tree.clear()
        root = QTreeWidgetItem([case_dir.name])
        root.setData(0, self._Qt.UserRole, {"type": "project"})
        self.tree.addTopLevelItem(root)

        inputs = QTreeWidgetItem(["Inputs"])
        inputs.setData(0, self._Qt.UserRole, {"type": "inputs"})
        root.addChild(inputs)

        model_item = QTreeWidgetItem(["Model"])
        model_item.setData(0, self._Qt.UserRole, {"type": "model"})
        inputs.addChild(model_item)

        points_n = (
            int(getattr(mesh.get("points"), "shape", [0])[0])
            if mesh.get("points") is not None
            else 0
        )
        mesh_item = QTreeWidgetItem([f"Mesh (points={points_n})"])
        mesh_item.setData(0, self._Qt.UserRole, {"type": "mesh"})
        inputs.addChild(mesh_item)

        sets_item = QTreeWidgetItem(["Sets"])
        sets_item.setData(0, self._Qt.UserRole, {"type": "sets"})
        inputs.addChild(sets_item)

        node_sets_item = QTreeWidgetItem(["Node Sets"])
        node_sets_item.setData(0, self._Qt.UserRole, {"type": "node_sets"})
        sets_item.addChild(node_sets_item)
        for k, v in sorted(mesh.items(), key=lambda kv: kv[0]):
            if not k.startswith("node_set__"):
                continue
            name = k.split("__", 1)[1]
            count = int(getattr(v, "size", 0))
            child = QTreeWidgetItem([f"{name} ({count})"])
            child.setData(0, self._Qt.UserRole, {"type": "node_set", "name": name})
            node_sets_item.addChild(child)

        edge_sets_item = QTreeWidgetItem(["Edge Sets"])
        edge_sets_item.setData(0, self._Qt.UserRole, {"type": "edge_sets"})
        sets_item.addChild(edge_sets_item)
        for k, v in sorted(mesh.items(), key=lambda kv: kv[0]):
            if not k.startswith("edge_set__"):
                continue
            name = k.split("__", 1)[1]
            count = int(getattr(v, "shape", [0])[0])
            child = QTreeWidgetItem([f"{name} ({count})"])
            child.setData(0, self._Qt.UserRole, {"type": "edge_set", "name": name})
            edge_sets_item.addChild(child)

        elem_sets_item = QTreeWidgetItem(["Element Sets"])
        elem_sets_item.setData(0, self._Qt.UserRole, {"type": "element_sets"})
        sets_item.addChild(elem_sets_item)
        for k, v in sorted(mesh.items(), key=lambda kv: kv[0]):
            if not k.startswith("elem_set__"):
                continue
            rest = k.split("__", 1)[1]
            parts = rest.split("__")
            name = parts[0]
            cell_type = parts[1] if len(parts) > 1 else "?"
            count = int(getattr(v, "size", 0))
            child = QTreeWidgetItem([f"{name}:{cell_type} ({count})"])
            child.setData(
                0,
                self._Qt.UserRole,
                {"type": "element_set", "name": name, "cell_type": cell_type},
            )
            elem_sets_item.addChild(child)

        materials_item = QTreeWidgetItem(["Materials"])
        materials_item.setData(0, self._Qt.UserRole, {"type": "materials"})
        inputs.addChild(materials_item)
        for mid in sorted((request.get("materials") or {}).keys()):
            child = QTreeWidgetItem([mid])
            child.setData(0, self._Qt.UserRole, {"type": "material", "id": mid})
            materials_item.addChild(child)

        assignments = request.get("assignments", [])
        asg_n = len(assignments) if isinstance(assignments, list) else 0
        asg_item = QTreeWidgetItem([f"Assignments ({asg_n})"])
        asg_item.setData(0, self._Qt.UserRole, {"type": "assignments"})
        inputs.addChild(asg_item)

        global_out = request.get("output_requests", [])
        out_n = len(global_out) if isinstance(global_out, list) else 0
        out_req_item = QTreeWidgetItem([f"Global output_requests ({out_n})"])
        out_req_item.setData(0, self._Qt.UserRole, {"type": "global_output_requests"})
        inputs.addChild(out_req_item)

        stages_item = QTreeWidgetItem(["Stages"])
        stages_item.setData(0, self._Qt.UserRole, {"type": "stages"})
        inputs.addChild(stages_item)
        for i, s in enumerate(request.get("stages", [])):
            sid = s.get("id", f"stage_{i+1}") if isinstance(s, dict) else f"stage_{i+1}"
            suid = s.get("uid", "") if isinstance(s, dict) else ""
            child = QTreeWidgetItem([sid])
            child.setData(
                0, self._Qt.UserRole, {"type": "stage", "uid": suid, "index": i}
            )
            stages_item.addChild(child)

        outputs = QTreeWidgetItem(["Outputs"])
        outputs.setData(0, self._Qt.UserRole, {"type": "outputs"})
        root.addChild(outputs)

        out_item = QTreeWidgetItem(["out/"])
        out_item.setData(0, self._Qt.UserRole, {"type": "out_folder"})
        outputs.addChild(out_item)

        root.setExpanded(True)
        inputs.setExpanded(True)
        outputs.setExpanded(True)
        materials_item.setExpanded(True)
        stages_item.setExpanded(True)
        sets_item.setExpanded(True)
        node_sets_item.setExpanded(True)
        edge_sets_item.setExpanded(True)
        elem_sets_item.setExpanded(True)

        self._restore_selection(root, prev_payload, fallback=model_item)

    def _restore_selection(self, root, payload, fallback=None) -> None:  # noqa: ANN001
        if payload:
            try:
                found = self._find_item_by_payload(root, payload)
                if found is not None:
                    self.tree.setCurrentItem(found)
                    return
            except Exception:
                pass
        if fallback is not None:
            self.tree.setCurrentItem(fallback)

    def _find_item_by_payload(self, root, payload):  # noqa: ANN001
        target_type = str(payload.get("type", ""))

        def matches(item_payload: dict[str, Any]) -> bool:
            if str(item_payload.get("type", "")) != target_type:
                return False
            if target_type == "stage":
                uid = str(payload.get("uid", ""))
                if uid:
                    return str(item_payload.get("uid", "")) == uid
                try:
                    idx = int(payload.get("index"))
                except Exception:
                    idx = None
                if idx is not None:
                    try:
                        return int(item_payload.get("index", -1)) == idx
                    except Exception:
                        return False
                return False
            if target_type == "material":
                return str(item_payload.get("id", "")) == str(payload.get("id", ""))
            if target_type in ("node_set", "edge_set"):
                return str(item_payload.get("name", "")) == str(payload.get("name", ""))
            if target_type == "element_set":
                return str(item_payload.get("name", "")) == str(
                    payload.get("name", "")
                ) and str(item_payload.get("cell_type", "")) == str(
                    payload.get("cell_type", "")
                )
            # For general nodes (model/mesh/sets/etc.), type match is enough.
            return True

        def walk(item):
            data = item.data(0, self._Qt.UserRole) or {}
            if isinstance(data, dict) and matches(data):
                return item
            for i in range(item.childCount()):
                got = walk(item.child(i))
                if got is not None:
                    return got
            return None

        return walk(root)

    def select_payload(self, payload: dict[str, Any]) -> None:
        if not payload:
            return
        root = self.tree.topLevelItem(0)
        if root is None:
            return
        try:
            item = self._find_item_by_payload(root, payload)
        except Exception:
            item = None
        if item is None:
            return
        try:
            self.tree.setCurrentItem(item)
        except Exception:
            pass

    def _open_out_folder(self) -> None:
        if not self._case_dir:
            return
        out_dir = self._case_dir / "out"
        self.output_open_requested.emit(out_dir)

    def _on_selection_changed(self, current, previous) -> None:  # noqa: ANN001
        if current is None:
            return
        payload = current.data(0, self._Qt.UserRole)
        if payload is None:
            return
        self.selection_changed.emit(payload)
