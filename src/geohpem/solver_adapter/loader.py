from __future__ import annotations

import importlib

from geohpem.contract.types import SolverProtocol
from geohpem.solver_adapter.fake import FakeSolver


def load_solver(selector: str) -> SolverProtocol:
    if selector == "fake":
        return FakeSolver()
    if selector.startswith("python:"):
        module_name = selector.split("python:", 1)[1].strip()
        if not module_name:
            raise ValueError("Expected python:<module>")
        module = importlib.import_module(module_name)
        if hasattr(module, "get_solver"):
            return module.get_solver()
        if hasattr(module, "Solver"):
            return module.Solver()
        raise AttributeError(f"{module_name} must expose get_solver() or Solver")
    raise ValueError(f"Unknown solver selector: {selector}")

