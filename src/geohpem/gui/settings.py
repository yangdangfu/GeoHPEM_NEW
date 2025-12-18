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

    # ---- Display preferences ----

    def get_display_units(self) -> dict[str, str]:
        """
        Returns a dict like {"length": "project"|"m"|"mm", "pressure": "project"|"kPa"|...}.
        """
        # Note: PySide6 QSettings.value() does not accept `type=dict`.
        # It may return a Python dict (QVariantMap) or a JSON string depending on backend/version.
        raw = self._q.value("display_units", {})
        out: dict[str, str] = {}
        if isinstance(raw, str) and raw.strip():
            try:
                import json

                parsed = json.loads(raw)
                raw = parsed
            except Exception:
                raw = {}
        if isinstance(raw, dict):
            items = raw.items()
        elif isinstance(raw, list):
            # Sometimes stored as list of pairs.
            try:
                items = list(raw)  # type: ignore[assignment]
            except Exception:
                items = []
        else:
            items = []

        for item in items:
            try:
                k, v = item
            except Exception:
                continue
            if isinstance(k, str) and isinstance(v, str):
                out[k] = v
        return out

    def set_display_units(self, units: dict[str, str]) -> None:
        payload: dict[str, str] = {}
        for k, v in units.items():
            if isinstance(k, str) and isinstance(v, str):
                payload[k] = v
        self._q.setValue("display_units", payload)
