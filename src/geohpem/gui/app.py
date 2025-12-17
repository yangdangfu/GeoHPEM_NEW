from __future__ import annotations

import sys
from pathlib import Path


def run_gui(open_case_dir: str | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PySide6 is required: install dependencies (e.g. conda env geohpem)") from exc

    from geohpem.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    if open_case_dir:
        window.open_case_folder(Path(open_case_dir))

    return app.exec()

