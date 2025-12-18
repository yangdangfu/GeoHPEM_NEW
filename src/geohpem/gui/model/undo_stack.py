from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class UndoCommand:
    name: str
    redo: Callable[[], None]
    undo: Callable[[], None]


class UndoStack:
    """
    Simple undo/redo stack.

    - Commands are appended and the cursor points to the next redo position.
    - Adding a new command truncates any redo history.
    """

    def __init__(self) -> None:
        self._cmds: list[UndoCommand] = []
        self._cursor: int = 0

    def clear(self) -> None:
        self._cmds.clear()
        self._cursor = 0

    def can_undo(self) -> bool:
        return self._cursor > 0

    def can_redo(self) -> bool:
        return self._cursor < len(self._cmds)

    def push_and_redo(self, cmd: UndoCommand) -> None:
        if self._cursor < len(self._cmds):
            del self._cmds[self._cursor :]
        self._cmds.append(cmd)
        self._cursor += 1
        cmd.redo()

    def undo(self) -> None:
        if not self.can_undo():
            return
        self._cursor -= 1
        self._cmds[self._cursor].undo()

    def redo(self) -> None:
        if not self.can_redo():
            return
        self._cmds[self._cursor].redo()
        self._cursor += 1

    def peek_undo_name(self) -> str | None:
        if not self.can_undo():
            return None
        return self._cmds[self._cursor - 1].name

    def peek_redo_name(self) -> str | None:
        if not self.can_redo():
            return None
        return self._cmds[self._cursor].name

