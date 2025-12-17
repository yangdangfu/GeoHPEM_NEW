from __future__ import annotations

from pathlib import Path


class SettingsStore:
    """
    Thin wrapper over QSettings to store recent projects and last session info.
    """

    ORG = "GeoHPEM"
    APP = "GeoHPEM"

    def __init__(self) -> None:
        from PySide6.QtCore import QSettings  # type: ignore

        self._q = QSettings(self.ORG, self.APP)

    def get_recent_projects(self) -> list[Path]:
        raw = self._q.value("recent_projects", [], type=list)
        paths: list[Path] = []
        for item in raw:
            try:
                p = Path(str(item))
            except Exception:
                continue
            if p.exists():
                paths.append(p)
        return paths[:10]

    def add_recent_project(self, path: Path) -> None:
        items = [str(p) for p in self.get_recent_projects() if p.resolve() != path.resolve()]
        items.insert(0, str(path))
        self._q.setValue("recent_projects", items[:10])

    def set_last_project(self, path: Path) -> None:
        self._q.setValue("last_project", str(path))

    def get_last_project(self) -> Path | None:
        raw = self._q.value("last_project", "", type=str)
        if not raw:
            return None
        p = Path(raw)
        return p if p.exists() else None
