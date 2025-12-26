from __future__ import annotations


DEFAULT_QSS = """
QMainWindow {
  background: #f7f7f9;
}

QDockWidget::title {
  background: #f3f4f6;
  padding: 4px 8px;
  border-bottom: 1px solid #e5e7eb;
}

QGroupBox {
  margin-top: 14px;
  font-weight: 600;
}
QGroupBox::title {
  subcontrol-origin: margin;
  subcontrol-position: top left;
  left: 8px;
  padding: 0 4px;
}

QToolBar {
  spacing: 6px;
}
QToolButton {
  padding: 4px 8px;
}

QTabBar::tab {
  padding: 6px 10px;
}

QHeaderView::section {
  background: #f3f4f6;
  padding: 4px 6px;
  border: 1px solid #e5e7eb;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {
  padding: 4px 6px;
}

QPushButton {
  padding: 4px 10px;
}

QTreeWidget, QListWidget, QTableWidget {
  background: #ffffff;
}
"""


def apply_theme(app) -> None:  # noqa: ANN001
    try:
        app.setStyleSheet(DEFAULT_QSS)
    except Exception:
        pass
