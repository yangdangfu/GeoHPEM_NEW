from __future__ import annotations

from pathlib import Path
from typing import Any


class ProjectDock:
    def __init__(self) -> None:
        from PySide6.QtCore import Qt, Signal  # type: ignore
        from PySide6.QtWidgets import QDockWidget, QTreeWidget, QWidget, QVBoxLayout, QPushButton  # type: ignore

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

    def set_case(self, case_dir: Path, request: dict[str, Any], mesh: dict[str, Any]) -> None:
        from PySide6.QtWidgets import QTreeWidgetItem  # type: ignore

        self._case_dir = case_dir
        self._request = request
        self._mesh = mesh

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

        points_n = int(getattr(mesh.get("points"), "shape", [0])[0]) if mesh.get("points") is not None else 0
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
            child.setData(0, self._Qt.UserRole, {"type": "element_set", "name": name, "cell_type": cell_type})
            elem_sets_item.addChild(child)

        materials_item = QTreeWidgetItem(["Materials"])
        materials_item.setData(0, self._Qt.UserRole, {"type": "materials"})
        inputs.addChild(materials_item)
        for mid in sorted((request.get("materials") or {}).keys()):
            child = QTreeWidgetItem([mid])
            child.setData(0, self._Qt.UserRole, {"type": "material", "id": mid})
            materials_item.addChild(child)

        stages_item = QTreeWidgetItem(["Stages"])
        stages_item.setData(0, self._Qt.UserRole, {"type": "stages"})
        inputs.addChild(stages_item)
        for i, s in enumerate(request.get("stages", [])):
            sid = s.get("id", f"stage_{i+1}") if isinstance(s, dict) else f"stage_{i+1}"
            child = QTreeWidgetItem([sid])
            child.setData(0, self._Qt.UserRole, {"type": "stage", "index": i})
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

        self.tree.setCurrentItem(model_item)

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
