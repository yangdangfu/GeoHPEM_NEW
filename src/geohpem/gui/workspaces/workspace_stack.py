from __future__ import annotations


class WorkspaceStack:
    def __init__(self) -> None:
        from PySide6.QtWidgets import QStackedWidget  # type: ignore

        from geohpem.gui.workspaces.input_workspace import InputWorkspace
        from geohpem.gui.workspaces.output_workspace import OutputWorkspace

        self.widget = QStackedWidget()
        self._workspaces = {
            "input": InputWorkspace(),
            "output": OutputWorkspace(),
        }
        for ws in self._workspaces.values():
            self.widget.addWidget(ws.widget)
        self.set_workspace("input")

    def set_workspace(self, name: str) -> None:
        ws = self._workspaces[name]
        self.widget.setCurrentWidget(ws.widget)

    def get(self, name: str):
        return self._workspaces[name]
