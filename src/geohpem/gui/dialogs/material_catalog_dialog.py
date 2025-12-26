from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Qt  # type: ignore
from PySide6.QtWidgets import (  # type: ignore
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QGroupBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from geohpem.domain import material_catalog as mc
from geohpem.gui.widgets.json_editor import JsonEditorWidget


def _model_to_dict(model: mc.MaterialModel) -> dict[str, Any]:
    return {
        "name": model.name,
        "label": model.label,
        "behavior": model.behavior,
        "description": model.description,
        "defaults": copy.deepcopy(model.defaults),
        "meta": copy.deepcopy(model.meta),
        "solver_mapping": copy.deepcopy(model.solver_mapping),
    }


class MaterialCatalogDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Material Catalog")
        self.resize(980, 640)

        self._saved = False
        self._block = False

        self._user_catalog = mc.read_user_catalog() or {}
        self._user_models = mc.normalize_models(self._user_catalog.get("models"))
        self._user_names = set(self._user_models.keys())
        self._base_models = mc.default_model_dicts()
        self._base_names = set(self._base_models.keys())

        self._models: dict[str, dict[str, Any]] = {}
        for m in mc.all_models():
            self._models[m.name] = _model_to_dict(m)

        self._initial_models = copy.deepcopy(self._models)
        self._modified: set[str] = set()
        self._deleted: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Material Catalog")
        header.setStyleSheet("font-weight: 600; font-size: 13px;")
        path_label = QLabel(f"User catalog: {mc.user_catalog_path()}")
        path_label.setStyleSheet("color: #6b7280;")
        layout.addWidget(header)
        layout.addWidget(path_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QGroupBox("Models")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self._list = QListWidget()
        left_layout.addWidget(self._list, 1)

        btn_bar = QHBoxLayout()
        self._btn_copy = QPushButton("Copy")
        self._btn_rename = QPushButton("Rename")
        self._btn_delete = QPushButton("Delete")
        self._btn_reset = QPushButton("Reset Model")
        btn_bar.addWidget(self._btn_copy)
        btn_bar.addWidget(self._btn_rename)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addWidget(self._btn_reset)
        left_layout.addLayout(btn_bar)

        splitter.addWidget(left)

        right = QGroupBox("Definition")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addLayout(form)

        self._name = QLineEdit()
        self._name.setReadOnly(True)
        form.addRow("Name", self._name)

        self._label = QLineEdit()
        form.addRow("Label", self._label)

        self._behavior = QComboBox()
        for key, label in mc.behavior_options():
            self._behavior.addItem(label, key)
        form.addRow("Behavior", self._behavior)

        self._description = QLineEdit()
        form.addRow("Description", self._description)

        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(6, 6, 6, 6)
        self._tabs = QTabWidget()
        self._defaults_edit = JsonEditorWidget()
        self._tabs.addTab(self._defaults_edit, "Defaults")
        self._meta_edit = JsonEditorWidget()
        self._tabs.addTab(self._meta_edit, "Meta")
        self._solver_map_edit = JsonEditorWidget()
        self._tabs.addTab(self._solver_map_edit, "Solver Mapping")
        params_layout.addWidget(self._tabs, 1)
        right_layout.addWidget(params_group, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close | QDialogButtonBox.Reset)
        layout.addWidget(buttons)
        buttons.rejected.connect(self.reject)
        reload_btn = buttons.button(QDialogButtonBox.Reset)
        if reload_btn is not None:
            reload_btn.setText("Reload")
            reload_btn.clicked.connect(self._on_reload)
            reload_btn.setToolTip("Reload from disk and discard unsaved edits.")
        apply_btn = buttons.button(QDialogButtonBox.Apply)
        if apply_btn is not None:
            apply_btn.setToolTip("Apply changes without closing the dialog.")
            apply_btn.clicked.connect(self._on_apply)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.reject)

        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._btn_copy.clicked.connect(self._on_copy)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_reset.clicked.connect(self._on_reset)

        self._populate_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._update_buttons()

    def saved(self) -> bool:
        return self._saved

    def _populate_list(self) -> None:
        self._list.clear()
        for name in sorted(self._models.keys()):
            model = self._models[name]
            label = model.get("label") or name
            is_user = name in self._user_names
            suffix = " [user]" if is_user else ""
            item = QListWidgetItem(f"{name} - {label}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            if is_user:
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            self._list.addItem(item)

    def _current_name(self) -> str | None:
        item = self._list.currentItem()
        if not item:
            return None
        name = item.data(Qt.ItemDataRole.UserRole)
        return str(name) if name else None

    def _sync_current_from_ui(self) -> bool:
        name = self._current_name()
        if not name:
            return True
        model = self._models.get(name)
        if model is None:
            return True
        try:
            defaults = self._defaults_edit.data()
        except Exception as exc:
            QMessageBox.information(self, "Defaults", f"Invalid JSON:\n{exc}")
            return False
        if not isinstance(defaults, dict):
            QMessageBox.information(self, "Defaults", "Defaults must be a JSON object.")
            return False
        try:
            meta = self._meta_edit.data()
        except Exception as exc:
            QMessageBox.information(self, "Meta", f"Invalid JSON:\n{exc}")
            return False
        if not isinstance(meta, dict):
            QMessageBox.information(self, "Meta", "Meta must be a JSON object.")
            return False
        try:
            solver_mapping = self._solver_map_edit.data()
        except Exception as exc:
            QMessageBox.information(self, "Solver Mapping", f"Invalid JSON:\n{exc}")
            return False
        if not isinstance(solver_mapping, dict):
            QMessageBox.information(self, "Solver Mapping", "Solver mapping must be a JSON object.")
            return False

        new_model = dict(model)
        new_model["label"] = str(self._label.text()).strip() or name
        new_model["behavior"] = str(self._behavior.currentData() or "custom")
        new_model["description"] = str(self._description.text()).strip()
        if name in self._base_names:
            base = self._base_models.get(name, {})
            if isinstance(base.get("defaults"), dict) and not defaults:
                defaults = copy.deepcopy(base.get("defaults", {}))
            if isinstance(base.get("meta"), dict) and not meta:
                meta = copy.deepcopy(base.get("meta", {}))
            if isinstance(base.get("solver_mapping"), dict) and not solver_mapping:
                solver_mapping = copy.deepcopy(base.get("solver_mapping", {}))
        new_model["defaults"] = copy.deepcopy(defaults)
        new_model["meta"] = copy.deepcopy(meta)
        new_model["solver_mapping"] = copy.deepcopy(solver_mapping)
        self._models[name] = new_model

        if new_model != self._initial_models.get(name):
            if name in self._base_names:
                self._user_names.add(name)
            self._modified.add(name)
        return True

    def _load_model_into_ui(self, name: str) -> None:
        model = self._models.get(name, {})
        self._block = True
        self._name.setText(name)
        self._label.setText(str(model.get("label", "")))
        behavior = str(model.get("behavior", "custom"))
        idx = self._behavior.findData(behavior)
        if idx >= 0:
            self._behavior.setCurrentIndex(idx)
        else:
            self._behavior.addItem(behavior, behavior)
            self._behavior.setCurrentIndex(self._behavior.findData(behavior))
        self._description.setText(str(model.get("description", "")))
        self._defaults_edit.set_data(model.get("defaults", {}))
        self._meta_edit.set_data(model.get("meta", {}))
        self._solver_map_edit.set_data(model.get("solver_mapping", {}))
        self._block = False

    def _on_selection_changed(self, current, _previous) -> None:  # noqa: ANN001
        if self._block:
            return
        if not self._sync_current_from_ui():
            self._block = True
            if _previous is not None:
                self._list.setCurrentItem(_previous)
            self._block = False
            return
        if current is None:
            return
        name = str(current.data(Qt.ItemDataRole.UserRole) or "")
        if not name:
            return
        self._load_model_into_ui(name)
        self._update_buttons()

    def _update_buttons(self) -> None:
        name = self._current_name()
        if not name:
            self._btn_rename.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._btn_reset.setEnabled(False)
            return
        is_base = name in self._base_names
        is_user = name in self._user_names
        self._btn_rename.setEnabled(is_user and not is_base)
        self._btn_delete.setEnabled(is_user and not is_base)
        self._btn_reset.setEnabled(is_base and is_user)

    def _ask_new_name(self, title: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self, title, "Model name:", text=default)
        if not ok:
            return None
        name = str(text).strip()
        return name if name else None

    def _on_copy(self) -> None:
        name = self._current_name()
        if not name:
            return
        new_name = self._ask_new_name("Copy Model", f"{name}_copy")
        if not new_name:
            return
        if new_name in self._models:
            QMessageBox.information(self, "Copy Model", f"Model '{new_name}' already exists.")
            return
        base = copy.deepcopy(self._models[name])
        base["name"] = new_name
        base["label"] = base.get("label") or new_name
        self._models[new_name] = base
        self._user_names.add(new_name)
        self._modified.add(new_name)
        self._populate_list()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_name:
                self._list.setCurrentItem(item)
                break

    def _on_rename(self) -> None:
        name = self._current_name()
        if not name:
            return
        new_name = self._ask_new_name("Rename Model", name)
        if not new_name or new_name == name:
            return
        if new_name in self._models:
            QMessageBox.information(self, "Rename Model", f"Model '{new_name}' already exists.")
            return
        if name not in self._user_names:
            QMessageBox.information(self, "Rename Model", "Default models cannot be renamed. Use Copy instead.")
            return
        model = copy.deepcopy(self._models[name])
        model["name"] = new_name
        self._models[new_name] = model
        self._user_names.discard(name)
        self._user_names.add(new_name)
        self._modified.discard(name)
        self._modified.add(new_name)
        self._models.pop(name, None)
        self._populate_list()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_name:
                self._list.setCurrentItem(item)
                break

    def _on_delete(self) -> None:
        name = self._current_name()
        if not name:
            return
        if name in self._base_names:
            QMessageBox.information(self, "Delete Model", "Default models cannot be deleted. Use Reset.")
            return
        btn = QMessageBox.warning(
            self,
            "Delete Model",
            f"Delete user model '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if btn != QMessageBox.StandardButton.Yes:
            return
        self._models.pop(name, None)
        self._user_names.discard(name)
        self._modified.discard(name)
        self._deleted.add(name)
        self._populate_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_reset(self) -> None:
        name = self._current_name()
        if not name:
            return
        if name not in self._base_names:
            QMessageBox.information(self, "Reset Model", "Reset is only available for default models.")
            return
        if name not in self._user_names:
            QMessageBox.information(self, "Reset Model", "No user override exists for this model.")
            return
        btn = QMessageBox.warning(
            self,
            "Reset Model",
            f"Reset '{name}' to default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if btn != QMessageBox.StandardButton.Yes:
            return
        self._models[name] = copy.deepcopy(self._base_models[name])
        self._user_names.discard(name)
        self._modified.discard(name)
        self._populate_list()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self._list.setCurrentItem(item)
                break

    def _on_reload(self) -> None:
        mc.reload_catalog()
        self._user_catalog = mc.read_user_catalog() or {}
        self._user_models = mc.normalize_models(self._user_catalog.get("models"))
        self._user_names = set(self._user_models.keys())
        self._base_models = mc.default_model_dicts()
        self._base_names = set(self._base_models.keys())
        self._models = {}
        for m in mc.all_models():
            self._models[m.name] = _model_to_dict(m)
        self._initial_models = copy.deepcopy(self._models)
        self._modified.clear()
        self._deleted.clear()
        self._populate_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _on_save(self) -> None:
        if not self._sync_current_from_ui():
            return
        overrides = (self._user_names | self._modified) - self._deleted
        models_list = []
        for name in sorted(overrides):
            if name in self._models:
                models_list.append(self._models[name])
        data: dict[str, Any] = {"version": str(self._user_catalog.get("version", "1.0"))}
        if isinstance(self._user_catalog.get("behaviors"), dict):
            data["behaviors"] = self._user_catalog.get("behaviors")
        data["models"] = models_list
        errors = mc.validate_catalog(data)
        if errors:
            msg = "\n".join(errors[:15])
            if len(errors) > 15:
                msg += f"\n... ({len(errors)} errors)"
            QMessageBox.information(self, "Catalog Validation", f"Please fix these issues:\n{msg}")
            return
        try:
            mc.write_user_catalog(data)
        except Exception as exc:
            QMessageBox.information(self, "Save Catalog", f"Failed to save catalog:\n{exc}")
            return
        self._saved = True
        self._initial_models = copy.deepcopy(self._models)
        self._modified.clear()
        self._deleted.clear()
        current = self._current_name()
        self._populate_list()
        if current:
            for i in range(self._list.count()):
                item = self._list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current:
                    self._list.setCurrentItem(item)
                    break
        self._update_buttons()

    def _on_apply(self) -> None:
        self._on_save()
