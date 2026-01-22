from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class UndoCommand:
    name: str
    redo: Callable[[], None]
    undo: Callable[[], None]
    merge_key: str | None = None
    timestamp: float = 0.0


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

    def push_and_redo(
        self,
        cmd: UndoCommand,
        *,
        merge_key: str | None = None,
        merge_window_s: float = 0.75,
    ) -> None:
        """
        Push a command and execute it.

        If merge_key is provided, consecutive commands can be coalesced into a single undo step
        when they are pushed within merge_window_s and the cursor is at the end.
        """
        now = time.monotonic()

        # Merge with previous command if:
        # - cursor is at the end (no redo history)
        # - previous command has same merge_key
        # - within merge window
        if (
            merge_key
            and self._cursor == len(self._cmds)
            and self._cmds
            and self._cmds[-1].merge_key == merge_key
            and (now - float(self._cmds[-1].timestamp)) <= float(merge_window_s)
        ):
            prev = self._cmds[-1]
            merged = UndoCommand(
                name=prev.name,
                undo=prev.undo,
                redo=cmd.redo,
                merge_key=merge_key,
                timestamp=now,
            )
            self._cmds[-1] = merged
            cmd.redo()
            return

        if self._cursor < len(self._cmds):
            del self._cmds[self._cursor :]
        stored = UndoCommand(
            name=cmd.name,
            undo=cmd.undo,
            redo=cmd.redo,
            merge_key=merge_key,
            timestamp=now,
        )
        self._cmds.append(stored)
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
