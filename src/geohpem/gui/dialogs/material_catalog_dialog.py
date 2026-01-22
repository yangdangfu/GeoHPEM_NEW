from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Qt  # type: ignore
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,  # type: ignore
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from geohpem.domain import material_catalog as mc
from geohpem.gui.widgets.json_editor import JsonEditorWidget


class MaterialCatalogDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Material Catalog")
        self.resize(980, 640)

        self._saved = False
        self._block = False

        self._user_catalog: dict[str, Any] = {}
        self._base_models: dict[str, dict[str, Any]] = {}
        self._user_models: dict[str, dict[str, Any]] = {}
        self._saved_models: dict[str, dict[str, Any]] = {}
        self._view_models: dict[str, dict[str, Any]] = {}
        self._dirty_models: set[str] = set()
        self._load_state()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Material Catalog")
        path_label = QLabel(f"User catalog: {mc.user_catalog_path()}")
        layout.addWidget(header)
        layout.addWidget(path_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QGroupBox("Models")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter...")
        left_layout.addWidget(self._filter)
        self._list = QTreeWidget()
        self._list.setColumnCount(3)
        self._list.setHeaderLabels(["Model", "Label", "Status"])
        self._list.setRootIsDecorated(False)
        self._list.setAlternatingRowColors(True)
        self._list.setUniformRowHeights(True)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setIndentation(0)
        header = self._list.header()
        header.setStretchLastSection(False)
        try:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        except Exception:
            pass
        left_layout.addWidget(self._list, 1)

        btn_bar = QHBoxLayout()
        self._btn_copy = QPushButton("Copy")
        self._btn_rename = QPushButton("Rename")
        self._btn_delete = QPushButton("Delete")
        self._btn_reset = QPushButton("Reset Model")
        self._btn_reset.setToolTip(
            "Reset this model back to the default catalog values."
        )
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

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close)
        layout.addWidget(buttons)
        buttons.rejected.connect(self.reject)
        apply_btn = buttons.button(QDialogButtonBox.Apply)
        if apply_btn is not None:
            apply_btn.setToolTip("Apply changes without closing the dialog.")
            apply_btn.clicked.connect(self._on_apply)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.reject)

        self._filter.textChanged.connect(self._apply_filter)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._btn_copy.clicked.connect(self._on_copy)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_reset.clicked.connect(self._on_reset)

        self._populate_list()
        if self._list.topLevelItemCount() > 0:
            self._list.setCurrentItem(self._list.topLevelItem(0))
        self._update_buttons()

    def saved(self) -> bool:
        return self._saved

    def _populate_list(self) -> None:
        self._list.clear()
        for name in sorted(self._view_models.keys()):
            model = self._view_models[name]
            label = model.get("label") or name
            status = self._model_status(name)
            item = QTreeWidgetItem([name, str(label), status])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            if name in self._dirty_models:
                f = item.font(0)
                f.setBold(True)
                item.setFont(0, f)
                item.setFont(1, f)
            self._list.addTopLevelItem(item)
        self._apply_filter(self._filter.text())

    def _current_name(self) -> str | None:
        item = self._list.currentItem()
        if not item:
            return None
        name = item.data(0, Qt.ItemDataRole.UserRole)
        return str(name) if name else None

    def _sync_current_from_ui(self, name: str | None = None) -> bool:
        name = name or self._current_name()
        if not name:
            return True
        model = self._view_models.get(name)
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
            QMessageBox.information(
                self, "Solver Mapping", "Solver mapping must be a JSON object."
            )
            return False

        new_model = dict(model)
        new_model["label"] = str(self._label.text()).strip() or name
        new_model["behavior"] = str(self._behavior.currentData() or "custom")
        new_model["description"] = str(self._description.text()).strip()
        if name in self._base_models:
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
        self._view_models[name] = new_model
        self._update_dirty(name)
        return True

    def _load_model_into_ui(self, name: str) -> None:
        model = self._view_models.get(name, {})
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
        prev_name = ""
        if _previous is not None:
            prev_name = str(_previous.data(0, Qt.ItemDataRole.UserRole) or "")
        if prev_name:
            if not self._sync_current_from_ui(prev_name):
                self._block = True
                if _previous is not None:
                    self._list.setCurrentItem(_previous)
                self._block = False
                return
            self._refresh_list_item(prev_name)
        if current is None:
            return
        name = str(current.data(0, Qt.ItemDataRole.UserRole) or "")
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
        is_base = name in self._base_models
        is_user_only = name in self._user_models and name not in self._base_models
        is_override = self._has_saved_override(name)
        self._btn_rename.setEnabled(is_user_only)
        self._btn_delete.setEnabled(is_user_only)
        self._btn_reset.setEnabled(
            is_base and (is_override or name in self._dirty_models)
        )

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
        if new_name in self._view_models:
            QMessageBox.information(
                self, "Copy Model", f"Model '{new_name}' already exists."
            )
            return
        base = copy.deepcopy(self._view_models[name])
        base["name"] = new_name
        base["label"] = base.get("label") or new_name
        self._view_models[new_name] = base
        self._user_models[new_name] = copy.deepcopy(base)
        self._dirty_models.add(new_name)
        self._populate_list()
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == new_name:
                self._list.setCurrentItem(item)
                break

    def _on_rename(self) -> None:
        name = self._current_name()
        if not name:
            return
        new_name = self._ask_new_name("Rename Model", name)
        if not new_name or new_name == name:
            return
        if new_name in self._view_models:
            QMessageBox.information(
                self, "Rename Model", f"Model '{new_name}' already exists."
            )
            return
        if name not in self._user_models or name in self._base_models:
            QMessageBox.information(
                self,
                "Rename Model",
                "Default models cannot be renamed. Use Copy instead.",
            )
            return
        model = copy.deepcopy(self._view_models[name])
        model["name"] = new_name
        self._view_models[new_name] = model
        self._user_models.pop(name, None)
        self._user_models[new_name] = copy.deepcopy(model)
        self._dirty_models.discard(name)
        self._dirty_models.add(new_name)
        self._view_models.pop(name, None)
        self._populate_list()
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == new_name:
                self._list.setCurrentItem(item)
                break

    def _on_delete(self) -> None:
        name = self._current_name()
        if not name:
            return
        if name in self._base_models:
            QMessageBox.information(
                self, "Delete Model", "Default models cannot be deleted. Use Reset."
            )
            return
        btn = QMessageBox.warning(
            self,
            "Delete Model",
            f"Delete user model '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if btn != QMessageBox.StandardButton.Yes:
            return
        self._view_models.pop(name, None)
        self._user_models.pop(name, None)
        self._dirty_models.discard(name)
        self._populate_list()
        if self._list.topLevelItemCount() > 0:
            self._list.setCurrentItem(self._list.topLevelItem(0))

    def _on_reset(self) -> None:
        name = self._current_name()
        if not name:
            return
        if name not in self._base_models:
            QMessageBox.information(
                self, "Reset Model", "Reset is only available for default models."
            )
            return
        if name not in self._user_models:
            QMessageBox.information(
                self, "Reset Model", "No user override exists for this model."
            )
            return
        btn = QMessageBox.warning(
            self,
            "Reset Model",
            f"Reset '{name}' to default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if btn != QMessageBox.StandardButton.Yes:
            return
        self._block = True
        self._view_models[name] = copy.deepcopy(self._base_models[name])
        self._user_models.pop(name, None)
        self._dirty_models.discard(name)
        self._populate_list()
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == name:
                self._list.setCurrentItem(item)
                break
        self._load_model_into_ui(name)
        self._block = False
        self._update_buttons()
        self._persist_catalog(sync_current=False)

    def _persist_catalog(self, *, sync_current: bool = True) -> None:
        if sync_current and not self._sync_current_from_ui():
            return
        models_list: list[dict[str, Any]] = []
        for name, model in self._view_models.items():
            if name in self._base_models:
                if model != self._base_models[name]:
                    models_list.append(model)
            else:
                models_list.append(model)
        data: dict[str, Any] = {
            "version": str(self._user_catalog.get("version", "1.0"))
        }
        if isinstance(self._user_catalog.get("behaviors"), dict):
            data["behaviors"] = self._user_catalog.get("behaviors")
        data["models"] = models_list
        errors = mc.validate_catalog(data)
        if errors:
            msg = "\n".join(errors[:15])
            if len(errors) > 15:
                msg += f"\n... ({len(errors)} errors)"
            QMessageBox.information(
                self, "Catalog Validation", f"Please fix these issues:\n{msg}"
            )
            return
        try:
            mc.write_user_catalog(data)
        except Exception as exc:
            QMessageBox.information(
                self, "Save Catalog", f"Failed to save catalog:\n{exc}"
            )
            return
        self._saved = True
        self._user_models = self._build_user_models_from_view()
        self._saved_models = copy.deepcopy(self._view_models)
        self._dirty_models.clear()
        current = self._current_name()
        self._populate_list()
        if current:
            for i in range(self._list.topLevelItemCount()):
                item = self._list.topLevelItem(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == current:
                    self._list.setCurrentItem(item)
                    break
        self._update_buttons()

    def _on_apply(self) -> None:
        self._persist_catalog()

    def _load_state(self) -> None:
        self._user_catalog = mc.read_user_catalog() or {}
        self._base_models = mc.default_model_dicts()
        raw_user = mc.normalize_models(self._user_catalog.get("models"))
        self._user_models = self._prune_user_models(raw_user)
        merged: dict[str, dict[str, Any]] = {}
        for name, base in self._base_models.items():
            merged[name] = copy.deepcopy(base)
        for name, override in self._user_models.items():
            if name in merged:
                view = dict(merged[name])
                view.update(override)
                for key in ("defaults", "meta", "solver_mapping"):
                    base_val = merged[name].get(key)
                    user_val = override.get(key)
                    if isinstance(base_val, dict) and isinstance(user_val, dict):
                        merged_val = dict(base_val)
                        merged_val.update(user_val)
                        view[key] = merged_val
                    elif user_val is None:
                        view[key] = base_val
                merged[name] = view
            else:
                merged[name] = copy.deepcopy(override)
        self._saved_models = copy.deepcopy(merged)
        self._view_models = copy.deepcopy(merged)
        self._dirty_models.clear()

    def _model_status(self, name: str) -> str:
        if name in self._dirty_models:
            return "modified"
        if name in self._user_models and name not in self._base_models:
            return "user"
        if self._has_saved_override(name):
            return "override"
        return ""

    def _has_saved_override(self, name: str) -> bool:
        if name not in self._user_models:
            return False
        if name not in self._base_models:
            return False
        return self._normalize_model_for_compare(
            self._user_models[name], name
        ) != self._normalize_model_for_compare(
            self._base_models[name],
            name,
        )

    def _prune_user_models(
        self, raw: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for name, model in raw.items():
            if name not in self._base_models:
                out[name] = copy.deepcopy(model)
                continue
            if self._normalize_model_for_compare(
                model, name
            ) != self._normalize_model_for_compare(
                self._base_models[name],
                name,
            ):
                out[name] = copy.deepcopy(model)
        return out

    def _update_dirty(self, name: str) -> None:
        view = self._view_models.get(name)
        if view is None:
            self._dirty_models.discard(name)
            return
        saved = self._saved_models.get(name)
        if saved is None:
            self._dirty_models.add(name)
            return
        if self._normalize_model_for_compare(
            view, name
        ) != self._normalize_model_for_compare(saved, name):
            self._dirty_models.add(name)
        else:
            self._dirty_models.discard(name)

    def _build_user_models_from_view(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for name, model in self._view_models.items():
            if name in self._base_models:
                if self._normalize_model_for_compare(
                    model, name
                ) != self._normalize_model_for_compare(self._base_models[name], name):
                    out[name] = copy.deepcopy(model)
            else:
                out[name] = copy.deepcopy(model)
        return out

    def _normalize_model_for_compare(
        self, model: dict[str, Any], name: str
    ) -> dict[str, Any]:
        out = dict(model)
        label = out.get("label")
        if not isinstance(label, str) or not label.strip():
            out["label"] = name
        behavior = out.get("behavior")
        if not isinstance(behavior, str) or not behavior.strip():
            out["behavior"] = "custom"
        desc = out.get("description")
        if not isinstance(desc, str):
            out["description"] = ""
        for key in ("defaults", "meta", "solver_mapping"):
            val = out.get(key)
            if not isinstance(val, dict):
                out[key] = {}
        # Normalize scalar types inside defaults/solver_mapping to reduce false diffs.
        out["defaults"] = self._normalize_scalar_values(out.get("defaults", {}))
        out["solver_mapping"] = self._normalize_scalar_values(
            out.get("solver_mapping", {})
        )
        return out

    def _normalize_scalar_values(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._normalize_scalar_values(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._normalize_scalar_values(v) for v in value]
        if isinstance(value, str):
            raw = value.strip()
            lowered = raw.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            if lowered == "null":
                return None
            # numeric pattern
            import re

            if re.match(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$", raw):
                try:
                    return float(raw)
                except Exception:
                    return value
        return value

    def _refresh_list_item(self, name: str) -> None:
        model = self._view_models.get(name)
        if not model:
            return
        label = model.get("label") or name
        status = self._model_status(name)
        suffix = f" [{status}]" if status else ""
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == name:
                item.setText(0, name)
                item.setText(1, str(label))
                item.setText(2, status)
                f = item.font(0)
                f.setBold(name in self._dirty_models)
                item.setFont(0, f)
                item.setFont(1, f)
                break

    def _apply_filter(self, text: str) -> None:
        needle = (text or "").strip().lower()
        for i in range(self._list.topLevelItemCount()):
            item = self._list.topLevelItem(i)
            if not needle:
                item.setHidden(False)
                continue
            label = " ".join([str(item.text(col)).lower() for col in range(3)])
            item.setHidden(needle not in label)
