from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt  # type: ignore
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,  # type: ignore
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class JsonEditorWidget(QWidget):
    """
    Tree-first JSON editor with a raw JSON tab for advanced edits.

    - Supports dict and list roots.
    - Values are parsed as JSON when possible (e.g., 1, true, [..], {...}).
    - Falls back to string when parsing fails.
    """

    _ROLE_TYPE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self, parent: QWidget | None = None, *, show_toolbar: bool = True
    ) -> None:
        super().__init__(parent)
        self._block = False
        self._root_type: str = "object"
        self._show_toolbar = bool(show_toolbar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tool_bar = QWidget()
        tool = QHBoxLayout(self._tool_bar)
        tool.setContentsMargins(0, 0, 0, 0)
        self._btn_add_group = QPushButton("Add group")
        self._btn_add_param = QPushButton("Add parameter")
        self._btn_delete = QPushButton("Delete")
        self._btn_json_to_tree = QPushButton("JSON -> Tree")
        tool.addWidget(self._btn_add_group)
        tool.addWidget(self._btn_add_param)
        tool.addWidget(self._btn_delete)
        tool.addStretch(1)
        tool.addWidget(self._btn_json_to_tree)
        layout.addWidget(self._tool_bar)
        self._tool_bar.setVisible(self._show_toolbar)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["key", "value"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self._tabs.addTab(self._tree, "Tree")

        self._json_edit = QPlainTextEdit()
        self._json_edit.setPlaceholderText("{ ... }")
        self._tabs.addTab(self._json_edit, "JSON")

        self._btn_add_group.clicked.connect(self._on_add_group)
        self._btn_add_param.clicked.connect(self._on_add_param)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_json_to_tree.clicked.connect(self._on_json_to_tree)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._root_item: QTreeWidgetItem | None = None
        self.set_data({})

    def set_data(self, data: Any) -> None:
        if not isinstance(data, (dict, list)):
            data = {}
        self._root_type = "array" if isinstance(data, list) else "object"
        self._block = True
        self._tree.clear()
        self._root_item = QTreeWidgetItem(
            ["root", "{...}" if self._root_type == "object" else "[...]"]
        )
        try:
            self._root_item.setFlags(
                self._root_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
        except Exception:
            pass
        self._root_item.setData(0, self._ROLE_TYPE, self._root_type)
        self._tree.addTopLevelItem(self._root_item)
        self._build_children(self._root_item, data)
        try:
            self._tree.expandAll()
        except Exception:
            pass
        self._block = False
        self._sync_json_from_tree()

    def data(self) -> Any:
        if self._tabs.currentWidget() == self._json_edit:
            ok, msg = self._apply_json_to_tree(show_error=False)
            if not ok:
                raise ValueError(msg)
        return self._tree_to_data()

    def _tree_to_data(self) -> Any:
        root = self._root_item or self._tree.invisibleRootItem()
        if self._root_type == "array":
            return [
                self._item_to_value(root.child(i)) for i in range(root.childCount())
            ]
        out: dict[str, Any] = {}
        for i in range(root.childCount()):
            child = root.child(i)
            out[str(child.text(0))] = self._item_to_value(child)
        return out

    def _item_to_value(self, item: QTreeWidgetItem) -> Any:
        typ = item.data(0, self._ROLE_TYPE)
        if typ == "object":
            out: dict[str, Any] = {}
            for i in range(item.childCount()):
                child = item.child(i)
                out[str(child.text(0))] = self._item_to_value(child)
            return out
        if typ == "array":
            return [
                self._item_to_value(item.child(i)) for i in range(item.childCount())
            ]
        text = str(item.text(1)).strip()
        if not text:
            return ""
        lowered = text.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None
        try:
            return json.loads(text)
        except Exception:
            return text

    def _build_children(self, parent: QTreeWidgetItem, data: Any) -> None:
        if isinstance(data, dict):
            for key, val in data.items():
                item = self._new_item(str(key), val)
                parent.addChild(item)
        elif isinstance(data, list):
            for idx, val in enumerate(data):
                item = self._new_item(str(idx), val)
                parent.addChild(item)

    def _new_item(self, key: str, val: Any) -> QTreeWidgetItem:
        item = QTreeWidgetItem([key, ""])
        try:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        except Exception:
            pass
        if isinstance(val, dict):
            item.setData(0, self._ROLE_TYPE, "object")
            item.setText(1, "{...}")
            self._build_children(item, val)
        elif isinstance(val, list):
            item.setData(0, self._ROLE_TYPE, "array")
            item.setText(1, "[...]")
            self._build_children(item, val)
        elif isinstance(val, bool):
            item.setData(0, self._ROLE_TYPE, "value")
            item.setText(1, "true" if val else "false")
        else:
            item.setData(0, self._ROLE_TYPE, "value")
            if val is None:
                item.setText(1, "null")
            elif isinstance(val, (dict, list)):
                item.setText(1, json.dumps(val, ensure_ascii=False))
            else:
                item.setText(1, str(val))
        return item

    def _sync_json_from_tree(self) -> None:
        try:
            data = self._tree_to_data()
            self._json_edit.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            self._json_edit.setPlainText("{}" if self._root_type == "object" else "[]")

    def _apply_json_to_tree(self, *, show_error: bool) -> tuple[bool, str]:
        text = self._json_edit.toPlainText() or "{}"
        try:
            data = json.loads(text)
        except Exception as exc:
            msg = f"Invalid JSON:\n{exc}"
            if show_error:
                QMessageBox.information(self, "JSON -> Tree", msg)
            return False, msg
        if not isinstance(data, (dict, list)):
            msg = "JSON root must be an object or list."
            if show_error:
                QMessageBox.information(self, "JSON -> Tree", msg)
            return False, msg
        self.set_data(data)
        return True, ""

    def _on_tab_changed(self, index: int) -> None:
        if self._tabs.widget(index) == self._json_edit:
            self._sync_json_from_tree()

    def _on_json_to_tree(self) -> None:
        ok, _msg = self._apply_json_to_tree(show_error=True)
        if ok:
            self._tabs.setCurrentIndex(self._tabs.indexOf(self._tree))

    def _on_add_group(self) -> None:
        parent = self._current_container()
        if parent is None:
            return
        key = self._next_key(parent)
        if key is None:
            return
        child = self._new_item(key, {})
        parent.addChild(child)
        parent.setExpanded(True)
        self._tree.setCurrentItem(child)

    def _on_add_param(self) -> None:
        parent = self._current_container()
        if parent is None:
            return
        key = self._next_key(parent)
        if key is None:
            return
        child = self._new_item(key, "")
        parent.addChild(child)
        parent.setExpanded(True)
        self._tree.setCurrentItem(child)

    def _on_delete(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        if item is self._root_item:
            return
        parent = item.parent()
        if parent is None:
            idx = self._tree.indexOfTopLevelItem(item)
            if idx >= 0:
                self._tree.takeTopLevelItem(idx)
        else:
            parent.removeChild(item)

    def _ask_key(self) -> str | None:
        text, ok = QInputDialog.getText(self, "Add Key", "Key:")
        if not ok:
            return None
        key = str(text).strip()
        return key if key else None

    def _current_container(self) -> QTreeWidgetItem | None:
        if self._root_item is None:
            return None
        item = self._tree.currentItem() or self._root_item
        if item is self._root_item:
            return item
        typ = item.data(0, self._ROLE_TYPE)
        if typ in ("object", "array"):
            return item
        return item.parent() or self._root_item

    def _next_key(self, parent: QTreeWidgetItem) -> str | None:
        if self._is_array_parent(parent):
            return str(parent.childCount())
        return self._ask_key()

    def _is_array_parent(self, item: QTreeWidgetItem) -> bool:
        if item is self._root_item:
            return self._root_type == "array"
        return item.data(0, self._ROLE_TYPE) == "array"

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if self._block:
            return
        if item is self._root_item:
            return
        if col != 1:
            return
        text = str(item.text(1)).strip()
        if not text:
            item.setData(0, self._ROLE_TYPE, "value")
            item.takeChildren()
            return
        try:
            val = json.loads(text)
        except Exception:
            item.setData(0, self._ROLE_TYPE, "value")
            item.takeChildren()
            return
        if isinstance(val, dict):
            self._block = True
            item.setData(0, self._ROLE_TYPE, "object")
            item.setText(1, "{...}")
            item.takeChildren()
            self._build_children(item, val)
            self._block = False
        elif isinstance(val, list):
            self._block = True
            item.setData(0, self._ROLE_TYPE, "array")
            item.setText(1, "[...]")
            item.takeChildren()
            self._build_children(item, val)
            self._block = False
        else:
            item.setData(0, self._ROLE_TYPE, "value")
            item.takeChildren()
