from __future__ import annotations

import sys
from pathlib import Path


def run_gui(open_case_dir: str | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PySide6 is required: install dependencies (e.g. conda env geohpem)") from exc

    from geohpem.gui.main_window import MainWindow
    from geohpem.gui.settings import SettingsStore

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    if open_case_dir:
        p = Path(open_case_dir)
        if p.is_dir():
            window.open_case_folder(p)
        else:
            window.open_project_file(p)
    else:
        settings = SettingsStore()
        last = settings.get_last_project()
        if last:
            from PySide6.QtWidgets import QMessageBox  # type: ignore

            btn = QMessageBox.question(
                window.qt,
                "Restore",
                f"Restore last session?\n{last}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if btn == QMessageBox.Yes:
                if last.is_dir():
                    window.open_case_folder(last)
                else:
                    window.open_project_file(last)

    return app.exec()
