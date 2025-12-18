from __future__ import annotations


class InputWorkspace:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal  # type: ignore
        from PySide6.QtGui import QFont  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QCheckBox,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QInputDialog,
            QListWidget,
            QMessageBox,
            QPushButton,
            QSplitter,
            QScrollArea,
            QVBoxLayout,
            QWidget,
        )

        class _Signals(QObject):
            new_project_requested = Signal()
            open_project_requested = Signal()
            open_case_requested = Signal()
            import_mesh_requested = Signal()
            validate_requested = Signal()
            run_requested = Signal()
            switch_output_requested = Signal()
            create_set_requested = Signal(object)  # payload dict

        self._signals = _Signals()
        self.new_project_requested = self._signals.new_project_requested
        self.open_project_requested = self._signals.open_project_requested
        self.open_case_requested = self._signals.open_case_requested
        self.import_mesh_requested = self._signals.import_mesh_requested
        self.validate_requested = self._signals.validate_requested
        self.run_requested = self._signals.run_requested
        self.switch_output_requested = self._signals.switch_output_requested
        self.create_set_requested = self._signals.create_set_requested

        self.widget = QWidget()
        self._QMessageBox = QMessageBox
        self._QInputDialog = QInputDialog

        outer = QVBoxLayout(self.widget)
        outer.setContentsMargins(0, 0, 0, 0)

        split = QSplitter()
        outer.addWidget(split, 1)

        # Left: dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        split.addWidget(scroll)

        root = QWidget()
        scroll.setWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("Input Workspace")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)
        layout.addWidget(QLabel("建模主要在左/右侧 Dock（Project/Geometry/Properties/Stages）完成。这里提供流程导航与快捷入口。"))

        # Status
        gb_status = QGroupBox("Status")
        st = QVBoxLayout(gb_status)
        self._lbl_project = QLabel("Project: (none)")
        self._lbl_solver = QLabel("Solver: fake")
        self._lbl_dirty = QLabel("State: clean")
        st.addWidget(self._lbl_project)
        st.addWidget(self._lbl_solver)
        st.addWidget(self._lbl_dirty)
        layout.addWidget(gb_status)

        # Quick actions
        gb_actions = QGroupBox("Quick Actions")
        al = QHBoxLayout(gb_actions)
        self._btn_new = QPushButton("New Project...")
        self._btn_open_proj = QPushButton("Open Project...")
        self._btn_open_case = QPushButton("Open Case Folder...")
        self._btn_import = QPushButton("Import Mesh...")
        self._btn_validate = QPushButton("Validate (F7)")
        self._btn_run = QPushButton("Run")
        self._btn_output = QPushButton("Go to Output")
        al.addWidget(self._btn_new)
        al.addWidget(self._btn_open_proj)
        al.addWidget(self._btn_open_case)
        al.addWidget(self._btn_import)
        al.addWidget(self._btn_validate)
        al.addWidget(self._btn_run)
        al.addWidget(self._btn_output)
        layout.addWidget(gb_actions)

        # Workflow checklist (static guidance)
        gb_flow = QGroupBox("Recommended Workflow")
        fl = QVBoxLayout(gb_flow)
        fl.addWidget(QLabel("1) 几何/网格：导入现成网格（Import Mesh）或画几何→网格化（Geometry Dock）。"))
        fl.addWidget(QLabel("2) Sets：检查/重命名/创建 sets（Edit -> Manage Sets...）。"))
        fl.addWidget(QLabel("3) 输入：配置 Model/Materials/Assignments/Stages（Properties Dock）。"))
        fl.addWidget(QLabel("4) 校验：Tools -> Validate Inputs... (F7)。"))
        fl.addWidget(QLabel("5) 求解：Solve -> Run (...)（后台运行，可取消，失败会生成诊断包）。"))
        fl.addWidget(QLabel("6) 后处理：切换到 Output（云图/Probe/Profiles/Pins/导出）。"))
        layout.addWidget(gb_flow)

        gb_tips = QGroupBox("Tips")
        tl = QVBoxLayout(gb_tips)
        tl.addWidget(QLabel("- Output 场景建议隐藏编辑 Dock（Geometry/Properties/Stages），专注可视化；可在 View 菜单随时打开。"))
        tl.addWidget(QLabel("- 若要与 solver 团队联调：File -> Export Case Folder... 导出 request.json + mesh.npz。"))
        layout.addWidget(gb_tips)

        layout.addStretch(1)

        # Right: mesh preview
        preview = QWidget()
        pv = QVBoxLayout(preview)
        pv.setContentsMargins(10, 10, 10, 10)
        pv.addWidget(QLabel("Mesh Preview (Input)"))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Highlight set:"))
        self._combo_set = QComboBox()
        self._combo_set.addItem("(None)", "")
        rl.addWidget(self._combo_set, 1)
        self._btn_fit = QPushButton("Fit")
        rl.addWidget(self._btn_fit)
        pv.addWidget(row)

        self._sel_info = QLabel("Pick: (none)")
        self._sel_info.setWordWrap(True)
        pv.addWidget(self._sel_info)

        gb_sel = QGroupBox("Selection (from preview)")
        sl = QVBoxLayout(gb_sel)
        self._lbl_sel_nodes = QLabel("Nodes: 0")
        self._lbl_sel_edges = QLabel("Edges: 0")
        self._lbl_sel_elems = QLabel("Elements: 0")
        sl.addWidget(self._lbl_sel_nodes)
        sl.addWidget(self._lbl_sel_edges)
        sl.addWidget(self._lbl_sel_elems)

        row_box = QWidget()
        bxl = QHBoxLayout(row_box)
        bxl.setContentsMargins(0, 0, 0, 0)
        self._chk_box_replace = QCheckBox("Replace")
        self._chk_box_brush = QCheckBox("Brush")
        self._chk_box_brush.setToolTip("Keep box selection active for repeated drags.")
        self._btn_box_nodes = QPushButton("Box nodes")
        self._btn_box_cells = QPushButton("Box elems")
        bxl.addWidget(self._chk_box_replace)
        bxl.addWidget(self._chk_box_brush)
        bxl.addStretch(1)
        bxl.addWidget(self._btn_box_nodes)
        bxl.addWidget(self._btn_box_cells)
        sl.addWidget(row_box)

        row_sel = QWidget()
        rsl = QHBoxLayout(row_sel)
        rsl.setContentsMargins(0, 0, 0, 0)
        self._btn_add_node = QPushButton("Add picked node")
        self._btn_add_edge = QPushButton("Add edge (last 2 picks)")
        self._btn_add_cell = QPushButton("Add picked cell")
        self._btn_clear_sel = QPushButton("Clear")
        rsl.addWidget(self._btn_add_node)
        rsl.addWidget(self._btn_add_edge)
        rsl.addWidget(self._btn_add_cell)
        rsl.addWidget(self._btn_clear_sel)
        sl.addWidget(row_sel)

        row_create = QWidget()
        crl = QHBoxLayout(row_create)
        crl.setContentsMargins(0, 0, 0, 0)
        self._btn_create_node_set = QPushButton("Create node set...")
        self._btn_create_edge_set = QPushButton("Create edge set...")
        self._btn_create_elem_set = QPushButton("Create elem set...")
        crl.addWidget(self._btn_create_node_set)
        crl.addWidget(self._btn_create_edge_set)
        crl.addWidget(self._btn_create_elem_set)
        sl.addWidget(row_create)
        pv.addWidget(gb_sel)

        self._viewer = None
        self._viewer_host = QWidget()
        self._viewer_host_layout = QVBoxLayout(self._viewer_host)
        self._viewer_host_layout.setContentsMargins(0, 0, 0, 0)
        pv.addWidget(self._viewer_host, 1)
        split.addWidget(preview)
        try:
            split.setStretchFactor(0, 0)
            split.setStretchFactor(1, 1)
            split.setSizes([420, 1000])
        except Exception:
            pass

        # Wire buttons to signals
        self._btn_new.clicked.connect(self.new_project_requested.emit)
        self._btn_open_proj.clicked.connect(self.open_project_requested.emit)
        self._btn_open_case.clicked.connect(self.open_case_requested.emit)
        self._btn_import.clicked.connect(self.import_mesh_requested.emit)
        self._btn_validate.clicked.connect(self.validate_requested.emit)
        self._btn_run.clicked.connect(self.run_requested.emit)
        self._btn_output.clicked.connect(self.switch_output_requested.emit)

        self._btn_fit.clicked.connect(self._fit_view)
        self._combo_set.currentIndexChanged.connect(lambda *_: self._render_preview())
        self._btn_add_node.clicked.connect(self._add_picked_node)
        self._btn_add_edge.clicked.connect(self._add_edge_from_last_two_picks)
        self._btn_add_cell.clicked.connect(self._add_picked_cell)
        self._btn_clear_sel.clicked.connect(self._clear_selection)
        self._btn_create_node_set.clicked.connect(self._create_node_set_from_selection)
        self._btn_create_edge_set.clicked.connect(self._create_edge_set_from_selection)
        self._btn_create_elem_set.clicked.connect(self._create_elem_set_from_selection)
        self._btn_box_nodes.clicked.connect(lambda: self._toggle_box_select("node"))
        self._btn_box_cells.clicked.connect(lambda: self._toggle_box_select("cell"))

        self._request = None
        self._mesh = None
        self._mesh_sig = None
        self._vtk_mesh = None
        self._grid = None
        self._set_label_by_key = {}
        self._node_set_membership = {}
        self._elem_set_membership = {}
        self._n_tri = 0
        self._last_probe_pid = None
        self._last_cell = None  # (cell_type, local_id)
        self._last_probe_pid_history: list[int] = []
        self._box_mode: str | None = None  # None|'node'|'cell'
        self._box_replace: bool = False
        self._box_brush: bool = False
        self._sel_nodes: set[int] = set()
        self._sel_edges: set[tuple[int, int]] = set()
        self._sel_elems: dict[str, set[int]] = {}
        self._pending_highlight_key: str | None = None
        self._normal_pick_enabled = False
        self._pick_cb = None
        self._cell_pick_cb = None
        self._is_2d_view = True

        self.set_status(project=None, dirty=False, solver="fake")
        self._update_selection_ui()

    def set_status(self, *, project: str | None, dirty: bool, solver: str) -> None:
        """
        Update dashboard status labels and button enablement (best-effort).
        """
        self._lbl_project.setText(f"Project: {project or '(none)'}")
        self._lbl_solver.setText(f"Solver: {solver or 'fake'}")
        self._lbl_dirty.setText("State: dirty" if dirty else "State: clean")

        has_project = bool(project)
        self._btn_import.setEnabled(has_project)
        self._btn_validate.setEnabled(has_project)
        self._btn_run.setEnabled(has_project)
        self._btn_output.setEnabled(has_project)

    def set_data(self, *, request, mesh) -> None:  # noqa: ANN001
        """
        Update the preview from in-memory project data (best-effort).
        """
        self._request = request
        self._mesh = mesh

        sig = self._compute_mesh_signature(mesh)
        mesh_changed = sig != self._mesh_sig
        self._mesh_sig = sig
        if mesh_changed:
            self._vtk_mesh = None
            self._grid = None

        self._rebuild_sets()
        self._ensure_viewer()
        self._render_preview(reset_camera=mesh_changed)
        self._update_selection_ui()

    def shutdown(self) -> None:
        v = self._viewer
        if v is None:
            return
        try:
            import vtk  # type: ignore

            vtk.vtkObject.GlobalWarningDisplayOff()
        except Exception:
            pass
        try:
            plotter = getattr(v, "plotter", None)
            if plotter is not None and hasattr(plotter, "close"):
                plotter.close()
        except Exception:
            pass
        try:
            if hasattr(v, "close"):
                v.close()
        except Exception:
            pass
        try:
            if hasattr(v, "setParent"):
                v.setParent(None)
            if hasattr(v, "deleteLater"):
                v.deleteLater()
        except Exception:
            pass
        self._viewer = None
        self._vtk_mesh = None
        self._grid = None
        self._mesh_sig = None

    def _ensure_viewer(self) -> None:
        if self._viewer is not None:
            return
        try:
            from pyvistaqt import QtInteractor  # type: ignore
        except Exception:
            self._viewer_host_layout.addWidget(QLabel("PyVistaQt not installed. Install pyvista + pyvistaqt."))
            return
        self._viewer = QtInteractor(self._viewer_host)
        self._viewer_host_layout.addWidget(self._viewer)
        self._viewer.set_background("white")
        self._apply_2d_view()

        def on_pick(*args, **kwargs):  # noqa: ANN001
            if self._box_mode is not None:
                return
            point = None
            if args:
                point = args[0]
            if point is None and "point" in kwargs:
                point = kwargs["point"]
            self._on_probe(point)

        def on_cell_pick(*args, **kwargs):  # noqa: ANN001
            if self._box_mode is not None:
                return
            self._on_cell_pick(args, kwargs)

        self._pick_cb = on_pick
        self._cell_pick_cb = on_cell_pick
        self._enable_normal_picking()

    def _apply_2d_view(self) -> None:
        """
        Configure the VTK viewer for 2D-only interaction (pan/zoom, no rotation).
        """
        if not self._is_2d_view or self._viewer is None:
            return
        plotter = getattr(self._viewer, "plotter", self._viewer)
        try:
            from geohpem.viz.vtk_interaction import apply_2d_interaction

            apply_2d_interaction(plotter)
        except Exception:
            return

    def _disable_all_picking(self) -> None:
        if self._viewer is None:
            return
        plotter = getattr(self._viewer, "plotter", self._viewer)
        try:
            if hasattr(plotter, "disable_picking"):
                plotter.disable_picking()  # type: ignore[misc]
        except Exception:
            pass
        self._normal_pick_enabled = False

    def _enable_normal_picking(self) -> None:
        if self._viewer is None or self._pick_cb is None or self._cell_pick_cb is None:
            return
        if self._normal_pick_enabled:
            return
        # Ensure no conflicting pick mode is active.
        self._disable_all_picking()
        try:
            self._viewer.enable_point_picking(
                callback=self._pick_cb,
                show_message=False,
                left_clicking=True,
                use_picker=True,
                show_point=True,
            )
        except TypeError:
            # compatibility with older versions
            self._viewer.enable_point_picking(callback=self._pick_cb, show_message=False, left_clicking=True, show_point=True, use_mesh=True)
        try:
            self._viewer.enable_cell_picking(  # type: ignore[attr-defined]
                callback=self._cell_pick_cb,
                show=False,
                through=False,
                show_message=False,
                start=True,
            )
        except Exception:
            pass
        self._normal_pick_enabled = True
        self._apply_2d_view()

    def _fit_view(self) -> None:
        if self._viewer is None:
            return
        try:
            self._viewer.reset_camera()
            self._viewer.render()
        except Exception:
            pass

    def _compute_mesh_signature(self, mesh) -> tuple[int, int, int, int] | None:  # noqa: ANN001
        """
        Best-effort signature to detect mesh topology changes without deep hashing.
        Returns (n_points, n_tri, n_quad, n_edge_pairs) or None.
        """
        if not isinstance(mesh, dict):
            return None
        try:
            import numpy as np

            pts = np.asarray(mesh.get("points", []))
            n_points = int(pts.shape[0]) if pts.ndim == 2 else int(pts.size)
            tri = np.asarray(mesh.get("cells_tri3", []))
            n_tri = int(tri.shape[0]) if tri.ndim == 2 else int(tri.size)
            quad = np.asarray(mesh.get("cells_quad4", []))
            n_quad = int(quad.shape[0]) if quad.ndim == 2 else int(quad.size)
            # edge sets are optional; include total pair count as a coarse signal
            n_edge_pairs = 0
            for k, v in mesh.items():
                if isinstance(k, str) and k.startswith("edge_set__"):
                    arr = np.asarray(v)
                    if arr.ndim >= 2:
                        n_edge_pairs += int(arr.shape[0])
                    else:
                        n_edge_pairs += int(arr.size // 2)
            return (n_points, n_tri, n_quad, n_edge_pairs)
        except Exception:
            return None

    def _rebuild_sets(self) -> None:
        keep_key = str(self._combo_set.currentData() or "")
        preferred = self._pending_highlight_key

        self._combo_set.blockSignals(True)
        self._combo_set.clear()
        self._combo_set.addItem("(None)", "")

        self._set_label_by_key = {}
        self._node_set_membership = {}
        self._elem_set_membership = {}
        self._n_tri = 0

        mesh = self._mesh
        if not isinstance(mesh, dict):
            self._combo_set.blockSignals(False)
            return

        # optional labels from request.sets_meta
        req = self._request
        if isinstance(req, dict):
            sm = req.get("sets_meta")
            if isinstance(sm, dict):
                for k, v in sm.items():
                    if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("label"), str):
                        self._set_label_by_key[k] = str(v["label"])

        def label_for_key(k: str) -> str:
            return self._set_label_by_key.get(k) or k

        # counts for mapping element local_id -> vtk cell id
        try:
            self._n_tri = int(getattr(mesh.get("cells_tri3"), "shape", [0])[0])
        except Exception:
            self._n_tri = 0

        for k in sorted(mesh.keys()):
            if k.startswith(("node_set__", "edge_set__", "elem_set__")):
                self._combo_set.addItem(label_for_key(k), k)

        # membership
        import numpy as np

        for k, arr in mesh.items():
            if not isinstance(k, str):
                continue
            if k.startswith("node_set__"):
                name = k.split("__", 1)[1]
                nodes = np.asarray(arr, dtype=np.int64).reshape(-1)
                for nid in nodes:
                    self._node_set_membership.setdefault(int(nid), []).append(name)
            if k.startswith("elem_set__"):
                # elem_set__NAME__tri3
                rest = k.split("__", 1)[1]
                parts = rest.split("__")
                if len(parts) < 2:
                    continue
                name = parts[0]
                cell_type = parts[1]
                ids = np.asarray(arr, dtype=np.int64).reshape(-1)
                by_id = self._elem_set_membership.setdefault(cell_type, {})
                for cid in ids:
                    by_id.setdefault(int(cid), []).append(name)

        # Restore preferred selection (newly created) or previous selection if possible.
        target = preferred or keep_key
        if target:
            for i in range(self._combo_set.count()):
                if str(self._combo_set.itemData(i) or "") == target:
                    self._combo_set.setCurrentIndex(i)
                    break
        self._pending_highlight_key = None
        self._combo_set.blockSignals(False)

    def _ensure_grid(self):  # noqa: ANN001
        if self._grid is not None:
            return self._grid, False
        mesh = self._mesh
        if not isinstance(mesh, dict) or "points" not in mesh:
            return None, False
        from geohpem.viz.vtk_convert import contract_mesh_to_pyvista

        self._vtk_mesh = contract_mesh_to_pyvista(mesh)
        self._grid = self._vtk_mesh.grid
        return self._grid, True

    def _render_preview(self, *, reset_camera: bool = False) -> None:
        if self._viewer is None:
            return
        mesh = self._mesh
        if not isinstance(mesh, dict) or "points" not in mesh:
            self._viewer.clear()
            self._sel_info.setText("No mesh loaded.")
            self._viewer.render()
            return
        try:
            grid, is_new_grid = self._ensure_grid()
            if grid is None:
                raise RuntimeError("No mesh grid")
            self._viewer.clear()
            self._viewer.add_mesh(grid, show_edges=True, color="#F2F2F2", edge_color="#888888", line_width=1)

            key = str(self._combo_set.currentData() or "")
            if key:
                self._highlight_set(mesh, grid, key)
            self._highlight_selection(mesh, grid)
            if reset_camera or is_new_grid:
                self._viewer.reset_camera()
            self._viewer.render()
            self._sel_info.setText("Pick: click node/cell to inspect; choose a set to highlight.")
        except Exception as exc:
            self._viewer.clear()
            self._sel_info.setText(f"Preview failed: {exc}")
            try:
                self._viewer.render()
            except Exception:
                pass

    def _highlight_set(self, mesh, grid, key: str) -> None:  # noqa: ANN001
        import numpy as np
        import pyvista as pv  # type: ignore

        if key.startswith("node_set__"):
            nodes = np.asarray(mesh.get(key, []), dtype=np.int64).reshape(-1)
            if nodes.size:
                nodes = nodes[(nodes >= 0) & (nodes < int(grid.n_points))]
                if nodes.size == 0:
                    return
                pts = np.asarray(grid.points)[nodes]
                pd = pv.PolyData(pts)
                self._viewer.add_mesh(pd, color="#D00000", point_size=14, render_points_as_spheres=False)
            return
        if key.startswith("edge_set__"):
            pairs = np.asarray(mesh.get(key, []), dtype=np.int64).reshape(-1, 2)
            if pairs.size == 0:
                return
            uniq = np.unique(pairs.ravel())
            pts = np.asarray(mesh["points"], dtype=float)[uniq]
            pts3 = np.column_stack([pts[:, 0], pts[:, 1], np.zeros((pts.shape[0],), dtype=float)])
            idx = {int(nid): i for i, nid in enumerate(uniq)}
            lines = []
            for a, b in pairs:
                lines.extend([2, idx[int(a)], idx[int(b)]])
            poly = pv.PolyData(pts3)
            poly.lines = np.asarray(lines, dtype=np.int64)
            self._viewer.add_mesh(poly, color="#D00000", line_width=4)
            return
        if key.startswith("elem_set__"):
            # elem_set__NAME__tri3/quad4 -> local ids per cell type
            rest = key.split("__", 1)[1]
            parts = rest.split("__")
            if len(parts) < 2:
                return
            cell_type = parts[1]
            local_ids = np.asarray(mesh.get(key, []), dtype=np.int64).reshape(-1)
            if local_ids.size == 0:
                return
            if cell_type == "tri3":
                vtk_ids = local_ids
            elif cell_type == "quad4":
                vtk_ids = self._n_tri + local_ids
            else:
                vtk_ids = local_ids
            vtk_ids = np.asarray(vtk_ids, dtype=np.int64).reshape(-1)
            vtk_ids = vtk_ids[(vtk_ids >= 0) & (vtk_ids < int(grid.n_cells))]
            if vtk_ids.size == 0:
                return
            sub = grid.extract_cells(vtk_ids)
            # Make it very visible over the base mesh: thick wireframe + semi-transparent fill.
            try:
                self._viewer.add_mesh(sub, style="wireframe", color="#D00000", line_width=5)
            except Exception:
                pass
            self._viewer.add_mesh(sub, color="#D00000", opacity=0.55, show_edges=True, edge_color="#D00000", line_width=2)

    def _highlight_selection(self, mesh, grid) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        import numpy as np
        import pyvista as pv  # type: ignore

        nodes = np.asarray(sorted(self._sel_nodes), dtype=np.int64).reshape(-1)
        if nodes.size:
            nodes = nodes[(nodes >= 0) & (nodes < int(grid.n_points))]
            if nodes.size:
                pts = np.asarray(grid.points)[nodes]
                pd = pv.PolyData(pts)
                self._viewer.add_mesh(pd, color="#FF8800", point_size=14, render_points_as_spheres=False)

        if self._sel_edges:
            pairs = np.asarray(sorted(self._sel_edges), dtype=np.int64).reshape(-1, 2)
            uniq = np.unique(pairs.ravel())
            uniq = uniq[(uniq >= 0) & (uniq < int(grid.n_points))]
            if uniq.size:
                pts = np.asarray(grid.points)[uniq]
                idx = {int(nid): i for i, nid in enumerate(uniq.tolist())}
                lines: list[int] = []
                for a, b in pairs.tolist():
                    if int(a) in idx and int(b) in idx:
                        lines.extend([2, idx[int(a)], idx[int(b)]])
                if lines:
                    poly = pv.PolyData(pts)
                    poly.lines = np.asarray(lines, dtype=np.int64)
                    self._viewer.add_mesh(poly, color="#FF8800", line_width=3)

        for cell_type, ids_set in self._sel_elems.items():
            if not ids_set:
                continue
            local_ids = np.asarray(sorted(ids_set), dtype=np.int64).reshape(-1)
            if local_ids.size == 0:
                continue
            if cell_type == "tri3":
                vtk_ids = local_ids
            elif cell_type == "quad4":
                vtk_ids = self._n_tri + local_ids
            else:
                vtk_ids = local_ids
            vtk_ids = vtk_ids[(vtk_ids >= 0) & (vtk_ids < int(grid.n_cells))]
            if vtk_ids.size == 0:
                continue
            sub = grid.extract_cells(vtk_ids)
            self._viewer.add_mesh(sub, color="#FF8800", opacity=0.65, show_edges=True, edge_color="#FF8800", line_width=2)

    def _on_probe(self, point) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        mesh = self._mesh
        if not isinstance(mesh, dict) or "points" not in mesh:
            return
        try:
            import numpy as np

            grid, _ = self._ensure_grid()
            if grid is None:
                return
            if point is None:
                return
            if hasattr(point, "GetPickPosition"):
                point = point.GetPickPosition()
            if isinstance(point, np.ndarray):
                point = point.tolist()
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                px = float(point[0])
                py = float(point[1])
                pz = float(point[2]) if len(point) >= 3 else 0.0
            else:
                return
            pid = int(grid.find_closest_point((px, py, pz)))
            self._last_probe_pid = pid
            self._last_probe_pid_history.append(pid)
            self._last_probe_pid_history = self._last_probe_pid_history[-2:]
            node_sets = self._node_set_membership.get(pid, [])
            self._sel_info.setText(f"Pick node: pid={pid} x={px:.6g} y={py:.6g} node_sets={node_sets}")
        except Exception:
            # ignore
            pass

    def _on_cell_pick(self, args, kwargs) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        mesh = self._mesh
        if not isinstance(mesh, dict):
            return
        try:
            from geohpem.viz.vtk_convert import cell_type_code_to_name

            grid, _ = self._ensure_grid()
            if grid is None:
                return
            cell_id = None
            for a in args:
                if isinstance(a, int):
                    cell_id = int(a)
                    break
                if hasattr(a, "cell_id"):
                    try:
                        cell_id = int(getattr(a, "cell_id"))
                        break
                    except Exception:
                        pass
            if cell_id is None and "cell_id" in kwargs:
                try:
                    cell_id = int(kwargs["cell_id"])
                except Exception:
                    cell_id = None
            if cell_id is None or cell_id < 0 or cell_id >= grid.n_cells:
                return
            ctype_code = int(grid.cell_data["__cell_type_code"][cell_id])
            local_id = int(grid.cell_data["__cell_local_id"][cell_id])
            ctype = cell_type_code_to_name(ctype_code) or str(ctype_code)
            self._last_cell = (str(ctype), int(local_id))
            elem_sets = self._elem_set_membership.get(ctype, {}).get(local_id, [])
            self._sel_info.setText(f"Pick cell: cell_id={cell_id} type={ctype} local_id={local_id} elem_sets={elem_sets}")
        except Exception:
            pass

    def _update_selection_ui(self) -> None:
        n_nodes = len(self._sel_nodes)
        n_edges = len(self._sel_edges)
        n_elems = sum(len(v) for v in self._sel_elems.values())
        self._lbl_sel_nodes.setText(f"Nodes: {n_nodes}")
        self._lbl_sel_edges.setText(f"Edges: {n_edges}")
        if self._sel_elems:
            parts = [f"{k}:{len(v)}" for k, v in sorted(self._sel_elems.items()) if v]
            self._lbl_sel_elems.setText(f"Elements: {n_elems}  ({', '.join(parts)})" if parts else f"Elements: {n_elems}")
        else:
            self._lbl_sel_elems.setText(f"Elements: {n_elems}")

        self._btn_add_node.setEnabled(self._last_probe_pid is not None)
        self._btn_add_edge.setEnabled(len(self._last_probe_pid_history) >= 2)
        self._btn_add_cell.setEnabled(self._last_cell is not None)
        self._btn_clear_sel.setEnabled(bool(n_nodes or n_edges or n_elems))
        self._btn_create_node_set.setEnabled(bool(n_nodes))
        self._btn_create_edge_set.setEnabled(bool(n_edges))
        self._btn_create_elem_set.setEnabled(bool(n_elems))

        active = self._box_mode is not None
        self._btn_box_nodes.setText("Cancel box" if self._box_mode == "node" else "Box nodes")
        self._btn_box_cells.setText("Cancel box" if self._box_mode == "cell" else "Box elems")
        self._btn_box_nodes.setEnabled((not active) or self._box_mode == "node")
        self._btn_box_cells.setEnabled((not active) or self._box_mode == "cell")

    def _toggle_box_select(self, mode: str) -> None:
        if self._viewer is None:
            return
        if self._box_mode == mode:
            self._stop_box_select()
            return
        if self._box_mode is not None:
            self._stop_box_select()
        self._start_box_select(mode)

    def _start_box_select(self, mode: str) -> None:
        if self._viewer is None:
            return
        plotter = getattr(self._viewer, "plotter", self._viewer)
        if not hasattr(plotter, "enable_rectangle_picking"):
            self._QMessageBox.information(self.widget, "Box Select", "Rectangle picking not supported by this viewer.")
            return
        # Rectangle picking conflicts with any existing picking mode in pyvista.
        self._disable_all_picking()
        self._box_mode = mode
        self._box_replace = bool(self._chk_box_replace.isChecked())
        self._box_brush = bool(self._chk_box_brush.isChecked())
        self._sel_info.setText(f"Box select {mode}: drag a rectangle in the viewport…")
        self._update_selection_ui()

        def cb(selection):  # noqa: ANN001
            self._on_box_picked(selection)

        try:
            plotter.enable_rectangle_picking(  # type: ignore[misc]
                callback=cb,
                show_message=False,
                start=True,
                show_frustum=False,
                style="wireframe",
                color="orange",
            )
        except Exception as exc:
            self._box_mode = None
            self._QMessageBox.critical(self.widget, "Box Select Failed", str(exc))
            self._update_selection_ui()
            self._enable_normal_picking()

    def _stop_box_select(self) -> None:
        if self._viewer is None:
            self._box_mode = None
            self._update_selection_ui()
            return
        self._disable_all_picking()
        self._box_mode = None
        self._sel_info.setText("Box select canceled.")
        self._update_selection_ui()
        self._enable_normal_picking()

    def _extract_by_frustum(self, frustum):  # noqa: ANN001
        """
        Extract a subset of the current grid using a vtkPlanes frustum.

        pyvista's rectangle picking callback provides a RectangleSelection
        object (viewport + frustum), not a dataset. We therefore extract
        selected points/cells using VTK filters, while preserving original
        ids via vtkIdFilter.
        """
        grid, _ = self._ensure_grid()
        if grid is None:
            return None
        try:
            import vtk  # type: ignore
            import pyvista as pv  # type: ignore

            # Prefer vtkExtractSelectedFrustum (matches rubber-band picking semantics).
            if hasattr(vtk, "vtkExtractSelectedFrustum"):
                esf = vtk.vtkExtractSelectedFrustum()
                esf.SetInputData(grid)  # type: ignore[arg-type]
                esf.SetFrustum(frustum)
                try:
                    esf.PreserveTopologyOff()
                except Exception:
                    pass
                esf.Update()
                return pv.wrap(esf.GetOutput())

            # Fallback: geometry extraction (less accurate for screen-space selection).
            idf = vtk.vtkIdFilter()
            idf.SetInputData(grid)  # type: ignore[arg-type]
            idf.SetPointIds(True)
            idf.SetCellIds(True)
            try:
                idf.SetPointIdsArrayName("__pid")
                idf.SetCellIdsArrayName("__cid")
            except Exception:
                pass
            idf.Update()

            eg = vtk.vtkExtractGeometry()
            eg.SetInputConnection(idf.GetOutputPort())
            eg.SetImplicitFunction(frustum)
            eg.ExtractInsideOn()
            eg.ExtractBoundaryCellsOn()
            eg.Update()
            return pv.wrap(eg.GetOutput())
        except Exception:
            return None

    def _on_box_picked(self, selection) -> None:  # noqa: ANN001
        if self._viewer is None:
            return
        grid, _ = self._ensure_grid()
        if grid is None:
            return
        frustum = getattr(selection, "frustum", None)
        if frustum is None:
            return
        picked = self._extract_by_frustum(frustum)
        if picked is None:
            return
        mode = self._box_mode
        if mode not in ("node", "cell"):
            return
        # Read live state (user may toggle while box-select is active).
        replace = bool(self._chk_box_replace.isChecked())
        brush = bool(self._chk_box_brush.isChecked())

        try:
            if mode == "node":
                import numpy as np

                ids: list[int] = []
                if hasattr(picked, "point_data"):
                    if "vtkOriginalPointIds" in picked.point_data:
                        ids = [int(x) for x in np.asarray(picked.point_data["vtkOriginalPointIds"]).reshape(-1).tolist()]
                    elif "__pid" in picked.point_data:
                        ids = [int(x) for x in np.asarray(picked.point_data["__pid"]).reshape(-1).tolist()]
                if not ids:
                    # fallback: map picked points to closest original ids
                    try:
                        pts = np.asarray(picked.points, dtype=float)
                        if pts.size:
                            ids = [int(grid.find_closest_point(tuple(p))) for p in pts]
                    except Exception:
                        ids = []
                ids = [i for i in ids if 0 <= int(i) < int(grid.n_points)]
                if replace:
                    self._sel_nodes = set(ids)
                else:
                    self._sel_nodes.update(ids)

            if mode == "cell":
                if replace:
                    self._sel_elems.clear()
                # Add by mapping picked cell_data -> (ctype, local_id)
                import numpy as np
                from geohpem.viz.vtk_convert import cell_type_code_to_name

                if hasattr(picked, "cell_data"):
                    if "__cell_type_code" in picked.cell_data and "__cell_local_id" in picked.cell_data:
                        codes = np.asarray(picked.cell_data["__cell_type_code"]).reshape(-1)
                        lids = np.asarray(picked.cell_data["__cell_local_id"]).reshape(-1)
                        for code, lid in zip(codes.tolist(), lids.tolist(), strict=False):
                            ctype = cell_type_code_to_name(int(code)) or str(code)
                            self._sel_elems.setdefault(str(ctype), set()).add(int(lid))
                    else:
                        # fall back to original cell ids (vtkExtractSelectedFrustum provides vtkOriginalCellIds)
                        cids = None
                        if "vtkOriginalCellIds" in picked.cell_data:
                            cids = np.asarray(picked.cell_data["vtkOriginalCellIds"]).reshape(-1)
                        elif "__cid" in picked.cell_data:
                            cids = np.asarray(picked.cell_data["__cid"]).reshape(-1)
                        if cids is not None and "__cell_type_code" in grid.cell_data and "__cell_local_id" in grid.cell_data:
                            for cid in cids.tolist():
                                try:
                                    c = int(cid)
                                except Exception:
                                    continue
                                if c < 0 or c >= int(grid.n_cells):
                                    continue
                                code = int(grid.cell_data["__cell_type_code"][c])
                                lid = int(grid.cell_data["__cell_local_id"][c])
                                ctype = cell_type_code_to_name(code) or str(code)
                                self._sel_elems.setdefault(str(ctype), set()).add(int(lid))

            self._update_selection_ui()
            self._render_preview()
        except Exception:
            pass
        finally:
            # In non-brush mode, stop after one selection.
            if not bool(brush):
                self._stop_box_select()

    def _add_picked_node(self) -> None:
        if self._last_probe_pid is None:
            return
        self._sel_nodes.add(int(self._last_probe_pid))
        self._update_selection_ui()
        try:
            self._render_preview()
        except Exception:
            pass

    def _add_edge_from_last_two_picks(self) -> None:
        if len(self._last_probe_pid_history) < 2:
            return
        a = int(self._last_probe_pid_history[-2])
        b = int(self._last_probe_pid_history[-1])
        if a == b:
            return
        self._sel_edges.add((a, b))
        self._update_selection_ui()
        try:
            self._render_preview()
        except Exception:
            pass

    def _add_picked_cell(self) -> None:
        if self._last_cell is None:
            return
        ct, lid = self._last_cell
        self._sel_elems.setdefault(str(ct), set()).add(int(lid))
        self._update_selection_ui()
        try:
            self._render_preview()
        except Exception:
            pass

    def _clear_selection(self) -> None:
        self._sel_nodes.clear()
        self._sel_edges.clear()
        self._sel_elems.clear()
        self._update_selection_ui()
        try:
            self._render_preview()
        except Exception:
            pass

    def _ask_set_name(self, *, title: str, default: str) -> str | None:
        txt, ok = self._QInputDialog.getText(self.widget, title, "Set name (no spaces):", text=default)
        if not ok:
            return None
        name = (txt or "").strip()
        if not name or any(ch.isspace() for ch in name):
            self._QMessageBox.warning(self.widget, title, "Invalid name. Please use a non-empty name without spaces.")
            return None
        return name

    def _create_node_set_from_selection(self) -> None:
        mesh = self._mesh
        if not isinstance(mesh, dict):
            return
        if not self._sel_nodes:
            return
        name = self._ask_set_name(title="Create Node Set", default="new_nodes")
        if not name:
            return
        key = f"node_set__{name}"
        if key in mesh:
            btn = self._QMessageBox.question(self.widget, "Overwrite Set?", f"Set already exists:\n{key}\n\nOverwrite it?")
            if btn != self._QMessageBox.Yes:
                return
        self._pending_highlight_key = key
        ids = sorted({int(x) for x in self._sel_nodes})
        self.create_set_requested.emit({"kind": "node", "name": name, "key": key, "ids": ids})

    def _create_edge_set_from_selection(self) -> None:
        mesh = self._mesh
        if not isinstance(mesh, dict):
            return
        if not self._sel_edges:
            return
        name = self._ask_set_name(title="Create Edge Set", default="new_edges")
        if not name:
            return
        key = f"edge_set__{name}"
        if key in mesh:
            btn = self._QMessageBox.question(self.widget, "Overwrite Set?", f"Set already exists:\n{key}\n\nOverwrite it?")
            if btn != self._QMessageBox.Yes:
                return
        self._pending_highlight_key = key
        pairs = [[int(a), int(b)] for a, b in sorted(self._sel_edges)]
        self.create_set_requested.emit({"kind": "edge", "name": name, "key": key, "pairs": pairs})

    def _create_elem_set_from_selection(self) -> None:
        mesh = self._mesh
        if not isinstance(mesh, dict):
            return
        if not self._sel_elems:
            return
        # If multiple cell types selected, ask user which block to use.
        if len(self._sel_elems) == 1:
            ct = next(iter(self._sel_elems.keys()))
        else:
            items = [f"{k} ({len(v)})" for k, v in sorted(self._sel_elems.items()) if v]
            if not items:
                return
            picked, ok = self._QInputDialog.getItem(self.widget, "Create Element Set", "Cell type:", items, 0, False)
            if not ok:
                return
            ct = str(picked).split(" ", 1)[0].strip()
        name = self._ask_set_name(title="Create Element Set", default="new_elems")
        if not name:
            return
        key = f"elem_set__{name}__{ct}"
        if key in mesh:
            btn = self._QMessageBox.question(self.widget, "Overwrite Set?", f"Set already exists:\n{key}\n\nOverwrite it?")
            if btn != self._QMessageBox.Yes:
                return
        self._pending_highlight_key = key
        ids = sorted({int(x) for x in self._sel_elems.get(ct, set())})
        self.create_set_requested.emit({"kind": "elem", "name": name, "cell_type": ct, "key": key, "ids": ids})
