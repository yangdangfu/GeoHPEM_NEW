from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnitsDialogResult:
    display_units: dict[str, str]


class UnitsDialog:
    def __init__(
        self,
        parent,
        *,
        base_units: dict[str, str],
        current_display_units: dict[str, str],
    ) -> None:  # noqa: ANN001
        from PySide6.QtWidgets import (
            QComboBox,
            QDialog,  # type: ignore
            QDialogButtonBox,
            QFormLayout,
            QLabel,
            QVBoxLayout,
        )

        from geohpem.units import available_units_for_kind

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Display Units")

        layout = QVBoxLayout(self._dialog)
        layout.addWidget(
            QLabel("Choose display units (data values remain in project units).")
        )

        form = QFormLayout()
        layout.addLayout(form)

        self._combos: dict[str, QComboBox] = {}
        for kind in ("length", "pressure"):
            combo = QComboBox()
            base_u = base_units.get(kind, "")
            combo.addItem(f"Project ({base_u or '?'})", "project")
            for u in available_units_for_kind(kind):
                combo.addItem(u, u)
            cur = current_display_units.get(kind, "project")
            idx = combo.findData(cur)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._combos[kind] = combo
            form.addRow(kind.capitalize(), combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self._dialog.accept)
        buttons.rejected.connect(self._dialog.reject)

    def exec(self) -> UnitsDialogResult | None:
        from PySide6.QtWidgets import QDialog  # type: ignore

        if self._dialog.exec() != QDialog.Accepted:
            return None
        units: dict[str, str] = {}
        for kind, combo in self._combos.items():
            units[kind] = str(combo.currentData())
        return UnitsDialogResult(display_units=units)
