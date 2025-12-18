from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


@dataclass(frozen=True, slots=True)
class SetItem:
    kind: str  # node|edge|elem
    name: str
    cell_type: str | None = None  # for elem
    count: int = 0


def _parse_int_list(text: str) -> np.ndarray:
    """
    Parse a comma-separated list of ints and ranges, e.g. "0,1,5-10".
    Returns a sorted unique int32 array.
    """
    text = (text or "").strip()
    if not text:
        return np.zeros((0,), dtype=np.int32)
    items: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            ia = int(a)
            ib = int(b)
            if ib < ia:
                ia, ib = ib, ia
            for v in range(ia, ib + 1):
                items.add(v)
        else:
            items.add(int(part))
    arr = np.array(sorted(items), dtype=np.int32)
    return arr


def _parse_edge_pairs(text: str) -> np.ndarray:
    """
    Parse edge pairs as node indices.

    Accepted forms (mixed separators allowed):
    - "0-1, 1-2, 2-3"
    - "0 1; 1 2; 2 3"
    - "0,1; 1,2"  (comma inside pair)

    Returns (K,2) int32.
    """
    text = (text or "").strip()
    if not text:
        return np.zeros((0, 2), dtype=np.int32)
    # Split pairs by ';' or ',' or newline.
    normalized = text.replace("|", ";")
    parts: list[str] = []
    for chunk in normalized.splitlines():
        parts.extend([p.strip() for p in chunk.replace(";", ",").split(",") if p.strip()])
    pairs: list[tuple[int, int]] = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        if "-" in p and " " not in p:
            a, b = p.split("-", 1)
            pairs.append((int(a), int(b)))
            continue
        # split by whitespace
        toks = [t for t in p.split() if t]
        if len(toks) != 2:
            raise ValueError(f"Invalid edge pair: {part!r}")
        pairs.append((int(toks[0]), int(toks[1])))
    return np.asarray(pairs, dtype=np.int32).reshape(-1, 2)


class SetsDialog:
    """
    Minimal Sets manager:
    - list node/edge/element sets from mesh dict keys
    - create node/element sets by indices string
    - rename/delete sets (for all kinds)
    """

    def __init__(
        self,
        parent,  # noqa: ANN001
        *,
        mesh: dict[str, Any],
        on_apply: Callable[[dict[str, Any]], None],
    ) -> None:
        from PySide6.QtWidgets import (
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMessageBox,
            QPushButton,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

        self._QMessageBox = QMessageBox
        self._mesh = dict(mesh)
        self._on_apply = on_apply

        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Sets Manager")
        self.dialog.resize(900, 520)

        root = QVBoxLayout(self.dialog)
        splitter = QSplitter()
        root.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Sets"))
        self.list = QListWidget()
        ll.addWidget(self.list)

        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        self.btn_delete = QPushButton("Delete")
        self.btn_rename = QPushButton("Rename")
        bl.addWidget(self.btn_rename)
        bl.addWidget(self.btn_delete)
        bl.addStretch(1)
        ll.addWidget(btn_row)

        splitter.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("Create New Set"))

        form = QFormLayout()
        rl.addLayout(form)

        self.kind = QComboBox()
        self.kind.addItem("Node set", "node")
        self.kind.addItem("Edge set", "edge")
        self.kind.addItem("Element set (tri3)", "elem_tri3")
        self.kind.addItem("Element set (quad4)", "elem_quad4")
        form.addRow("Kind", self.kind)

        self.name = QLineEdit()
        form.addRow("Name", self.name)

        self.indices = QLineEdit()
        self.indices.setPlaceholderText("Nodes: 0,1,2-10  |  Edges: 0-1;1-2;2-3  |  Elems: 0,2,3-20")
        form.addRow("Indices", self.indices)

        self.btn_add = QPushButton("Add")
        rl.addWidget(self.btn_add)
        rl.addStretch(1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        root.addWidget(buttons)
        buttons.rejected.connect(self.dialog.reject)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_rename.clicked.connect(self._on_rename)

        self._refresh_list()

    def exec(self) -> None:
        self.dialog.exec()

    def _iter_set_items(self) -> list[SetItem]:
        items: list[SetItem] = []
        for k, v in self._mesh.items():
            if k.startswith("node_set__"):
                name = k.split("__", 1)[1]
                items.append(SetItem(kind="node", name=name, count=int(np.asarray(v).size)))
            elif k.startswith("edge_set__"):
                name = k.split("__", 1)[1]
                items.append(SetItem(kind="edge", name=name, count=int(np.asarray(v).shape[0])))
            elif k.startswith("elem_set__"):
                rest = k.split("__", 1)[1]
                parts = rest.split("__")
                name = parts[0]
                cell_type = parts[1] if len(parts) > 1 else None
                items.append(SetItem(kind="elem", name=name, cell_type=cell_type, count=int(np.asarray(v).size)))
        items.sort(key=lambda x: (x.kind, x.name, x.cell_type or ""))
        return items

    def _refresh_list(self) -> None:
        self.list.clear()
        for item in self._iter_set_items():
            label = f"{item.kind}:{item.name}"
            if item.cell_type:
                label += f":{item.cell_type}"
            label += f" ({item.count})"
            self.list.addItem(label)

    def _on_add(self) -> None:
        from geohpem.domain.mesh_ops import add_edge_set, add_elem_set, add_node_set

        kind = str(self.kind.currentData())
        name = self.name.text().strip()
        if not name:
            self._QMessageBox.information(self.dialog, "Add Set", "Name is required.")
            return

        if kind == "node":
            idx = _parse_int_list(self.indices.text())
            self._mesh = add_node_set(self._mesh, name, idx)
        elif kind == "edge":
            edges = _parse_edge_pairs(self.indices.text())
            self._mesh = add_edge_set(self._mesh, name, edges)
        elif kind == "elem_tri3":
            idx = _parse_int_list(self.indices.text())
            self._mesh = add_elem_set(self._mesh, name, "tri3", idx)
        elif kind == "elem_quad4":
            idx = _parse_int_list(self.indices.text())
            self._mesh = add_elem_set(self._mesh, name, "quad4", idx)
        else:
            self._QMessageBox.information(self.dialog, "Add Set", f"Unknown kind: {kind}")
            return

        self._on_apply(self._mesh)
        self._refresh_list()

    def _selected_key(self) -> str | None:
        row = self.list.currentRow()
        if row < 0:
            return None
        txt = self.list.item(row).text()
        # Format: kind:name[:cell] (count)
        head = txt.split("(", 1)[0].strip()
        parts = head.split(":")
        if len(parts) < 2:
            return None
        kind = parts[0]
        name = parts[1]
        cell = parts[2] if len(parts) > 2 else None
        if kind == "node":
            return f"node_set__{name}"
        if kind == "edge":
            return f"edge_set__{name}"
        if kind == "elem":
            if cell:
                return f"elem_set__{name}__{cell}"
            return None
        return None

    def _on_delete(self) -> None:
        from geohpem.domain.mesh_ops import delete_set

        key = self._selected_key()
        if not key:
            return
        self._mesh = delete_set(self._mesh, key)
        self._on_apply(self._mesh)
        self._refresh_list()

    def _on_rename(self) -> None:
        from PySide6.QtWidgets import QInputDialog  # type: ignore
        from geohpem.domain.mesh_ops import rename_set

        key = self._selected_key()
        if not key:
            return
        new_name, ok = QInputDialog.getText(self.dialog, "Rename", "New name")
        if not ok:
            return
        new_name = str(new_name).strip()
        if not new_name:
            return

        if key.startswith("node_set__"):
            new_key = f"node_set__{new_name}"
        elif key.startswith("edge_set__"):
            new_key = f"edge_set__{new_name}"
        elif key.startswith("elem_set__"):
            rest = key.split("__", 1)[1]
            parts = rest.split("__")
            if len(parts) < 2:
                return
            cell = parts[1]
            new_key = f"elem_set__{new_name}__{cell}"
        else:
            return

        if new_key in self._mesh:
            self._QMessageBox.information(self.dialog, "Rename", f"Target already exists: {new_key}")
            return

        self._mesh = rename_set(self._mesh, key, new_key)
        self._on_apply(self._mesh)
        self._refresh_list()
