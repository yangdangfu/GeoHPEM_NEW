from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from geohpem.geometry.polygon2d import Polygon2D, get_polygon_from_request, set_polygon_in_request
from geohpem.gui.model.project_model import ProjectModel
from geohpem.mesh.generate_pygmsh import PygmshConfig, generate_from_polygon


@dataclass(frozen=True, slots=True)
class _Vertex:
    x: float
    y: float


class GeometryDock:
    """
    MVP geometry editor:
    - draw a single polygon domain
    - edit vertices by dragging
    - edit edge group names
    - generate mesh via pygmsh and update ProjectModel.mesh
    """

    def __init__(self) -> None:
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtGui import QPainter  # type: ignore
        from PySide6.QtWidgets import (
            QDockWidget,
            QGraphicsScene,
            QGraphicsView,
            QHBoxLayout,
            QLabel,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )  # type: ignore

        self._Qt = Qt
        self._QMessageBox = QMessageBox

        self.dock = QDockWidget("Geometry")
        self.dock.setObjectName("dock_geometry")

        root = QWidget()
        layout = QVBoxLayout(root)
        self.dock.setWidget(root)

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        self.btn_draw = QPushButton("Draw Polygon")
        self.btn_finish = QPushButton("Finish")
        self.btn_rect = QPushButton("Rectangle")
        self.btn_clear = QPushButton("Clear")
        self.btn_edges = QPushButton("Edge Labels...")
        self.btn_mesh = QPushButton("Generate Mesh...")
        bl.addWidget(self.btn_draw)
        bl.addWidget(self.btn_finish)
        bl.addWidget(self.btn_rect)
        bl.addWidget(self.btn_clear)
        bl.addWidget(self.btn_edges)
        bl.addWidget(self.btn_mesh)
        bl.addStretch(1)
        layout.addWidget(bar)

        self.info = QLabel("Polygon2D: not set")
        layout.addWidget(self.info)
        self.coord = QLabel("x=0, y=0")
        layout.addWidget(self.coord)

        self.scene = QGraphicsScene()
        outer = self

        class DrawView(QGraphicsView):
            def __init__(self, scene) -> None:  # noqa: ANN001
                super().__init__(scene)
                self.setMouseTracking(True)
                self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
                self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

            def wheelEvent(self, event) -> None:  # noqa: ANN001
                # Ctrl+wheel to zoom
                if event.modifiers() & outer._Qt.ControlModifier:
                    angle = event.angleDelta().y()
                    if angle == 0:
                        return
                    factor = 1.15 if angle > 0 else 1 / 1.15
                    self.scale(factor, factor)
                    return
                return super().wheelEvent(event)

            def mousePressEvent(self, event) -> None:  # noqa: ANN001
                # Middle-button pan (hand drag)
                if event.button() == outer._Qt.MiddleButton:
                    self._panning = True
                    self._pan_start = event.position().toPoint()
                    self.setCursor(outer._Qt.ClosedHandCursor)
                    event.accept()
                    return

                if outer._draw_mode:
                    btn = event.button()
                    if btn == outer._Qt.LeftButton:
                        pos = event.position()
                        scene_pos = self.mapToScene(int(pos.x()), int(pos.y()))
                        x = float(scene_pos.x())
                        y = float(-scene_pos.y())
                        outer._draw_points.append((x, y))
                        outer._update_preview()
                        return
                    if btn == outer._Qt.RightButton:
                        outer._finish_draw()
                        return
                return super().mousePressEvent(event)

            def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
                if event.button() == outer._Qt.MiddleButton:
                    self._panning = False
                    self.unsetCursor()
                    event.accept()
                    return
                return super().mouseReleaseEvent(event)

            def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
                pos = event.position()
                scene_pos = self.mapToScene(int(pos.x()), int(pos.y()))
                outer.coord.setText(f"x={scene_pos.x():.4g}, y={(-scene_pos.y()):.4g}")
                if getattr(self, "_panning", False):
                    p = event.position().toPoint()
                    delta = p - getattr(self, "_pan_start", p)
                    self._pan_start = p
                    self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
                    self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
                    event.accept()
                    return
                return super().mouseMoveEvent(event)

            def drawBackground(self, painter, rect) -> None:  # noqa: ANN001
                # Draw a light grid and axes for spatial reference.
                super().drawBackground(painter, rect)
                painter.save()

                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

                # Determine grid step based on current zoom (scene units per 100 px)
                p1 = self.mapToScene(0, 0)
                p2 = self.mapToScene(100, 0)
                scene_per_100px = abs(p2.x() - p1.x())
                # Choose a "nice" step near scene_per_100px
                base = max(scene_per_100px, 1e-9)
                nice_steps = [1, 2, 5, 10]
                exp = 0
                while base >= 10:
                    base /= 10
                    exp += 1
                while base < 1:
                    base *= 10
                    exp -= 1
                step = min(nice_steps, key=lambda s: abs(s - base)) * (10 ** exp)
                minor = step / 5

                from PySide6.QtGui import QPen  # type: ignore

                pen_minor = QPen(outer._Qt.lightGray)
                pen_minor.setWidth(0)
                pen_major = QPen(outer._Qt.gray)
                pen_major.setWidth(0)
                pen_axes = QPen(outer._Qt.darkGray)
                pen_axes.setWidth(0)

                # Draw minor grid
                def draw_grid(delta: float, pen) -> None:  # noqa: ANN001
                    painter.setPen(pen)
                    left = rect.left()
                    right = rect.right()
                    top = rect.top()
                    bottom = rect.bottom()

                    import math

                    x0 = math.floor(left / delta) * delta
                    x = x0
                    while x <= right:
                        painter.drawLine(x, top, x, bottom)
                        x += delta

                    y0 = math.floor(top / delta) * delta
                    y = y0
                    while y <= bottom:
                        painter.drawLine(left, y, right, y)
                        y += delta

                draw_grid(minor, pen_minor)
                draw_grid(step, pen_major)

                # Axes at (0,0)
                painter.setPen(pen_axes)
                painter.drawLine(rect.left(), 0.0, rect.right(), 0.0)
                painter.drawLine(0.0, rect.top(), 0.0, rect.bottom())

                painter.restore()

        self.view = DrawView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        layout.addWidget(self.view, 1)

        self._model: ProjectModel | None = None
        self._poly: Polygon2D | None = None

        self._vertex_items: list[Any] = []
        self._edge_items: list[Any] = []

        self._draw_mode = False
        self._draw_points: list[tuple[float, float]] = []
        self._preview_items: list[Any] = []

        self.btn_finish.setEnabled(False)

        self.btn_draw.clicked.connect(self._start_draw)
        self.btn_finish.clicked.connect(self._finish_draw)
        self.btn_rect.clicked.connect(self._create_rectangle)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_edges.clicked.connect(self._edit_edge_labels)
        self.btn_mesh.clicked.connect(self._generate_mesh)

    def bind_model(self, model: ProjectModel) -> None:
        self._model = model
        model.request_changed.connect(self._on_request_changed)
        if model.state().project:
            self._on_request_changed(model.state().project.request)

    def _on_request_changed(self, request: dict[str, Any]) -> None:
        poly = get_polygon_from_request(request)
        self._set_polygon(poly, push_to_model=False)

    def _set_polygon(self, poly: Polygon2D | None, *, push_to_model: bool) -> None:
        self._poly = poly
        self._redraw()
        if poly is None:
            self.info.setText("Polygon2D: not set")
        else:
            self.info.setText(f"Polygon2D: {len(poly.vertices)} vertices, region={poly.region_name}")
        if push_to_model and self._model and self._model.state().project:
            req = self._model.state().project.request
            req2 = set_polygon_in_request(req, poly)
            self._model.update_request(req2)

    def _redraw(self) -> None:
        from PySide6.QtCore import QPointF  # type: ignore
        from PySide6.QtGui import QPen  # type: ignore
        from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem  # type: ignore

        self.scene.clear()
        self._vertex_items = []
        self._edge_items = []

        if not self._poly:
            return

        verts = self._poly.vertices
        pen_edge = QPen(self._Qt.black)
        pen_edge.setWidth(2)
        pen_edge.setCosmetic(True)
        r = 2.5

        # edges
        for i in range(len(verts)):
            x1, y1 = verts[i]
            x2, y2 = verts[(i + 1) % len(verts)]
            li = QGraphicsLineItem(x1, -y1, x2, -y2)
            li.setPen(pen_edge)
            self.scene.addItem(li)
            self._edge_items.append(li)

        # vertices (draggable)
        def on_vertex_moved(idx: int, pos: QPointF, commit: bool) -> None:
            if self._poly is None:
                return
            newx = float(pos.x())
            newy = float(-pos.y())
            new_verts = list(self._poly.vertices)
            if 0 <= idx < len(new_verts):
                new_verts[idx] = (newx, newy)
                self._poly = Polygon2D(vertices=new_verts, edge_groups=self._poly.edge_groups, region_name=self._poly.region_name)
                # Update adjacent edges live without clearing the scene.
                if self._edge_items:
                    n = len(new_verts)
                    prev_i = (idx - 1) % n
                    next_i = (idx + 1) % n
                    # edge prev_i: prev -> idx
                    x0, y0 = new_verts[prev_i]
                    x1, y1 = new_verts[idx]
                    self._edge_items[prev_i].setLine(x0, -y0, x1, -y1)
                    # edge idx: idx -> next
                    x2, y2 = new_verts[next_i]
                    self._edge_items[idx].setLine(x1, -y1, x2, -y2)
                if commit:
                    # Commit to request (will rebuild scene once).
                    self._set_polygon(self._poly, push_to_model=True)

        class VertexItem(QGraphicsEllipseItem):
            def __init__(
                self,
                idx: int,
                x: float,
                y: float,
                radius: float,
                cb: Callable[[int, QPointF, bool], None],
            ) -> None:
                super().__init__(-radius, -radius, 2 * radius, 2 * radius)
                self._idx = idx
                self._cb = cb
                self.setPos(x, y)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

            def itemChange(self, change, value):  # noqa: ANN001
                if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
                    self._cb(self._idx, self.scenePos(), False)
                return super().itemChange(change, value)

            def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
                out = super().mouseReleaseEvent(event)
                self._cb(self._idx, self.scenePos(), True)
                return out

        for i, (x, y) in enumerate(verts):
            it = VertexItem(i, float(x), float(-y), r, on_vertex_moved)
            it.setBrush(self._Qt.white)
            pen_v = QPen(self._Qt.black)
            pen_v.setCosmetic(True)
            pen_v.setWidth(2)
            it.setPen(pen_v)
            self.scene.addItem(it)
            self._vertex_items.append(it)

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))

    def _create_rectangle(self) -> None:
        poly = Polygon2D(
            vertices=[(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)],
            edge_groups=["bottom", "right", "top", "left"],
            region_name="domain",
        )
        self._set_polygon(poly, push_to_model=True)

    def _start_draw(self) -> None:
        self._draw_mode = True
        self._draw_points = []
        self._clear_preview()
        self.btn_finish.setEnabled(True)
        self.info.setText("Draw mode: left-click to add points, right-click or Finish to close.")

    def _finish_draw(self) -> None:
        if not self._draw_mode:
            return
        self._draw_mode = False
        self.btn_finish.setEnabled(False)
        pts = list(self._draw_points)
        self._draw_points = []
        self._clear_preview()
        if len(pts) < 3:
            self.info.setText("Polygon2D: not set")
            return
        poly = Polygon2D(vertices=pts, edge_groups=[], region_name="domain")
        self._set_polygon(poly, push_to_model=True)

    def _clear(self) -> None:
        self._set_polygon(None, push_to_model=True)

    def _clear_preview(self) -> None:
        for it in self._preview_items:
            try:
                self.scene.removeItem(it)
            except Exception:
                pass
        self._preview_items = []

    def _update_preview(self) -> None:
        from PySide6.QtGui import QPen  # type: ignore
        from PySide6.QtCore import Qt  # type: ignore
        from PySide6.QtWidgets import QGraphicsLineItem  # type: ignore

        self._clear_preview()
        if len(self._draw_points) < 2:
            return
        pen = QPen(Qt.darkGray)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        for i in range(len(self._draw_points) - 1):
            x1, y1 = self._draw_points[i]
            x2, y2 = self._draw_points[i + 1]
            li = QGraphicsLineItem(x1, -y1, x2, -y2)
            li.setPen(pen)
            self.scene.addItem(li)
            self._preview_items.append(li)

    def _edit_edge_labels(self) -> None:
        if not self._poly:
            self._QMessageBox.information(self.dock, "Edge Labels", "Create a polygon first.")
            return

        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout  # type: ignore

        dialog = QDialog(self.dock)
        dialog.setWindowTitle("Edge Labels")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        layout.addLayout(form)

        edits: list[Any] = []
        groups = self._poly.normalized_edge_groups()
        verts = self._poly.vertices
        for i, g in enumerate(groups):
            x1, y1 = verts[i]
            x2, y2 = verts[(i + 1) % len(verts)]
            le = QLineEdit(str(g))
            form.addRow(f"Edge {i+1} ({x1:.3g},{y1:.3g})->({x2:.3g},{y2:.3g})", le)
            edits.append(le)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.Accepted:
            return

        new_groups = [e.text().strip() or f"edge_{i+1}" for i, e in enumerate(edits)]
        new_poly = Polygon2D(vertices=list(self._poly.vertices), edge_groups=new_groups, region_name=self._poly.region_name)
        self._set_polygon(new_poly, push_to_model=True)

    def _generate_mesh(self) -> None:
        if not self._poly:
            self._QMessageBox.information(self.dock, "Generate Mesh", "Create a polygon first.")
            return
        if not self._model or not self._model.state().project:
            self._QMessageBox.information(self.dock, "Generate Mesh", "Open a project first.")
            return

        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QVBoxLayout  # type: ignore

        dialog = QDialog(self.dock)
        dialog.setWindowTitle("Mesh Parameters")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        layout.addLayout(form)

        mesh_size = QDoubleSpinBox()
        mesh_size.setRange(1e-6, 1e6)
        mesh_size.setDecimals(6)
        mesh_size.setValue(0.5)
        form.addRow("mesh_size", mesh_size)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.Accepted:
            return

        cfg = PygmshConfig(mesh_size=float(mesh_size.value()))
        try:
            mesh_dict, report = generate_from_polygon(self._poly, cfg)
        except Exception as exc:
            self._QMessageBox.critical(self.dock, "Generate Mesh Failed", str(exc))
            return

        self._model.update_mesh(mesh_dict)
        self._QMessageBox.information(
            self.dock,
            "Mesh Generated",
            f"points={report.points}\n"
            f"cells={report.cells}\n"
            f"node_sets={len(report.node_sets)} edge_sets={len(report.edge_sets)} elem_sets={len(report.element_sets)}",
        )
