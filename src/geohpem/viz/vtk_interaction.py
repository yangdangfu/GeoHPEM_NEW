from __future__ import annotations

import weakref
from typing import Any, Callable


def apply_2d_interaction(
    plotter: Any, *, on_right_click: Callable[..., Any] | None = None
) -> None:
    """
    Configure a PyVista/VTK plotter for 2D-only interaction:
    - No 3D rotation
    - Middle mouse drag = pan
    - Mouse wheel = zoom
    - Right mouse = no VTK camera interaction (reserved for context menu)
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

    def _weak_cb(cb: Callable[..., Any] | None):  # noqa: ANN001
        if cb is None:
            return None
        try:
            if hasattr(cb, "__self__") and cb.__self__ is not None:
                return weakref.WeakMethod(cb)  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            return weakref.ref(cb)  # type: ignore[arg-type]
        except Exception:
            return None

    class _GeoHPEM2DStyle(vtk.vtkInteractorStyleImage):  # type: ignore[misc]
        def __init__(self) -> None:  # noqa: D401
            super().__init__()
            self._geohpem_right_click_cb = _weak_cb(on_right_click)

        def OnLeftButtonDown(self):  # noqa: N802
            # Reserve left click for picking; do not pan/rotate.
            return

        def OnLeftButtonUp(self):  # noqa: N802
            return

        def OnRightButtonDown(self):  # noqa: N802
            # Reserved for Qt context menu.
            cb_ref = getattr(self, "_geohpem_right_click_cb", None)
            cb = None
            try:
                cb = cb_ref() if cb_ref is not None else None
            except Exception:
                cb = None
            if cb is not None:
                try:
                    inter = self.GetInteractor()
                    pos = inter.GetEventPosition() if inter is not None else None
                except Exception:
                    pos = None
                try:
                    cb(pos)
                except TypeError:
                    try:
                        cb()
                    except Exception:
                        pass
                except Exception:
                    pass
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
