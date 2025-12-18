from __future__ import annotations


class InputWorkspace:
    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal  # type: ignore
        from PySide6.QtGui import QFont  # type: ignore
        from PySide6.QtWidgets import (  # type: ignore
            QComboBox,
            QGroupBox,
            QHBoxLayout,
            QLabel,
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

        self._signals = _Signals()
        self.new_project_requested = self._signals.new_project_requested
        self.open_project_requested = self._signals.open_project_requested
        self.open_case_requested = self._signals.open_case_requested
        self.import_mesh_requested = self._signals.import_mesh_requested
        self.validate_requested = self._signals.validate_requested
        self.run_requested = self._signals.run_requested
        self.switch_output_requested = self._signals.switch_output_requested

        self.widget = QWidget()
        self._QMessageBox = QMessageBox

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

        self._request = None
        self._mesh = None
        self._mesh_sig = None
        self._vtk_mesh = None
        self._grid = None
        self._set_label_by_key = {}
        self._node_set_membership = {}
        self._elem_set_membership = {}
        self._n_tri = 0

        self.set_status(project=None, dirty=False, solver="fake")

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

        def on_pick(*args, **kwargs):  # noqa: ANN001
            point = None
            if args:
                point = args[0]
            if point is None and "point" in kwargs:
                point = kwargs["point"]
            self._on_probe(point)

        try:
            self._viewer.enable_point_picking(callback=on_pick, show_message=False, left_clicking=True, use_picker=True, show_point=True)
        except TypeError:
            self._viewer.enable_point_picking(callback=on_pick, show_message=False, left_clicking=True, show_point=True, use_mesh=True)

        def on_cell_pick(*args, **kwargs):  # noqa: ANN001
            self._on_cell_pick(args, kwargs)

        try:
            self._viewer.enable_cell_picking(callback=on_cell_pick, show=False, through=False, show_message=False, start=True)  # type: ignore[attr-defined]
        except Exception:
            pass

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

        # Restore previous selection if possible.
        if keep_key:
            for i in range(self._combo_set.count()):
                if str(self._combo_set.itemData(i) or "") == keep_key:
                    self._combo_set.setCurrentIndex(i)
                    break
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
            self._viewer.add_mesh(grid, show_edges=True, color="white")

            key = str(self._combo_set.currentData() or "")
            if key:
                self._highlight_set(mesh, grid, key)
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
                self._viewer.add_mesh(pd, color="red", point_size=8, render_points_as_spheres=False)
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
            self._viewer.add_mesh(poly, color="red", line_width=3)
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
            self._viewer.add_mesh(sub, color="red", opacity=0.4, show_edges=True)

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
            elem_sets = self._elem_set_membership.get(ctype, {}).get(local_id, [])
            self._sel_info.setText(f"Pick cell: cell_id={cell_id} type={ctype} local_id={local_id} elem_sets={elem_sets}")
        except Exception:
            pass
