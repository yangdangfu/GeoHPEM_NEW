from __future__ import annotations

import logging
from pathlib import Path

from geohpem.contract.io import read_case_folder, write_result_folder
from geohpem.solver_adapter.loader import load_solver

logger = logging.getLogger(__name__)


def run_case(case_dir: str, solver_selector: str = "fake") -> None:
    case_path = Path(case_dir)
    request, mesh = read_case_folder(case_path)

    solver = load_solver(solver_selector)
    result_meta, result_arrays = solver.solve(request, mesh, callbacks=None)

    out_dir = case_path / "out"
    write_result_folder(out_dir, result_meta, result_arrays)
    logger.info("Wrote results to %s", out_dir)

