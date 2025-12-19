from __future__ import annotations

from typing import Any
import weakref


def apply_2d_interaction(plotter: Any) -> None:
    """
    Configure a PyVista/VTK plotter for 2D-only interaction:
    - No 3D rotation
    - Middle mouse drag = pan
    - Mouse wheel = zoom
    - Right mouse = no VTK interaction (reserved for context menu)
    - Left mouse = reserved for picking (no camera interaction)
    """
    try:
        import vtk  # type: ignore
    except Exception:
        return

    iren_wrapper = getattr(plotter, "iren", None)
    if iren_wrapper is None:
        return
    # PyVista wraps vtkRenderWindowInteractor as `plotter.iren.interactor`.
    vtk_iren = getattr(iren_wrapper, "interactor", None)
    if vtk_iren is None:
        vtk_iren = iren_wrapper
    if not hasattr(vtk_iren, "SetInteractorStyle"):
        return

    class _GeoHPEM2DStyle(vtk.vtkInteractorStyleImage):  # type: ignore[misc]
        def OnLeftButtonDown(self):  # noqa: N802
            # Reserve left click for picking; do not pan/rotate.
            return

        def OnLeftButtonUp(self):  # noqa: N802
            return

        def OnRightButtonDown(self):  # noqa: N802
            # Reserved for Qt context menu.
            return

        def OnRightButtonUp(self):  # noqa: N802
            return

        def OnMiddleButtonDown(self):  # noqa: N802
            # Pan with middle mouse.
            try:
                self.StartPan()
            except Exception:
                return

        def OnMiddleButtonUp(self):  # noqa: N802
            try:
                self.EndPan()
            except Exception:
                return

    try:
        style = _GeoHPEM2DStyle()
        # PyVista's picking utilities expect the VTK interactor style to expose
        # a `_parent()` callable returning the RenderWindowInteractor wrapper.
        # This is normally injected by PyVista; add it here for compatibility.
        try:
            setattr(style, "_parent", weakref.ref(iren_wrapper))
        except Exception:
            pass
        # Keep a Python reference so the style isn't garbage-collected.
        try:
            setattr(plotter, "_geohpem_interaction_style", style)
        except Exception:
            pass
        vtk_iren.SetInteractorStyle(style)
    except Exception:
        pass

    # Camera defaults for 2D.
    try:
        if hasattr(plotter, "enable_parallel_projection"):
            plotter.enable_parallel_projection()
    except Exception:
        pass
    try:
        if hasattr(plotter, "view_xy"):
            plotter.view_xy()
    except Exception:
        pass
