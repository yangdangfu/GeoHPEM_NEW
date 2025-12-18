from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Selection:
    kind: str
    ref: dict[str, Any]


class SelectionModel:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal  # type: ignore

        class _Signals(QObject):
            changed = Signal(object)  # Selection | None

        self._signals = _Signals()
        self.changed = self._signals.changed
        self._sel: Selection | None = None

    def set(self, selection: Selection | None) -> None:
        self._sel = selection
        self.changed.emit(selection)

    def get(self) -> Selection | None:
        return self._sel

