# Solver Adapter Module

The `solver_adapter` module provides the interface between GeoHPEM and solver backends. It includes a solver loader and a fake solver for testing.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Solver Protocol](#solver-protocol)
4. [Solver Loading](#solver-loading)
5. [Fake Solver](#fake-solver)
6. [Implementing Custom Solvers](#implementing-custom-solvers)

---

## Overview

GeoHPEM supports multiple solver backends through a plugin architecture:

- **Fake Solver**: Built-in placeholder for development and testing
- **Reference Elastic Solver**: Full FEM implementation for linear elasticity (plane strain/stress)
- **Reference Seepage Solver**: Full implementation for steady-state seepage (Poisson/Darcy)
- **Python Module Solvers**: Load solvers from Python modules
- **External Solvers**: (Future) Subprocess-based external solvers

The solver adapter ensures all backends conform to the `SolverProtocol` interface.

### Reference Solvers

The reference solvers (`reference_elastic.py` and `reference_seepage.py`) serve multiple purposes:

1. **Template for Solver Teams**: Provide working examples of the solver interface
2. **Platform Regression**: Baseline implementations for testing and validation
3. **End-to-End Testing**: Enable full workflow testing (materials/BCs/loads → solve → output → post-processing)

These are "minimal real implementations" (linear elasticity/seepage), not full-featured commercial solver replacements.

### GUI Solver Selection

Users can select the solver via **Solve → Select Solver...** menu:
- The selected solver is persisted in user settings
- The "Run" menu item displays the current solver name
- Before running, the dialog allows testing solver loading via "Check & Show Capabilities"

---

## Module Structure

```
solver_adapter/
├── __init__.py
├── loader.py              # Solver loading logic
├── fake.py                # Fake solver implementation
├── reference_elastic.py    # Reference elastic solver (FEM)
└── reference_seepage.py   # Reference seepage solver (Poisson/Darcy)
```

---

## Solver Protocol

All solvers must implement the `SolverProtocol` interface (defined in `contract/types.py`):

```python
class SolverProtocol(Protocol):
    def capabilities(self) -> JsonDict:
        """
        Return solver capabilities.
        
        Returns:
            {
                "name": "solver_name",
                "version": "1.0.0",
                "contract": {"min": "0.1", "max": "0.1"},
                "modes": ["plane_strain", "axisymmetric"],
                "analysis_types": ["static", "dynamic", ...],
                "fields": ["u", "p", ...],
                "results": ["u", "p", "stress", "strain", ...],
            }
        """
        ...

    def solve(
        self,
        request: JsonDict,
        mesh: ArrayDict,
        callbacks: JsonDict | None = None,
    ) -> tuple[JsonDict, ArrayDict]:
        """
        Execute the solver.
        
        Args:
            request: Analysis configuration (JSON dict)
                - schema_version
                - model (dimension, mode, gravity)
                - materials
                - assignments
                - stages (with BCs, loads, output_requests)
            
            mesh: Mesh data (dict of numpy arrays)
                - points: (N, 2) float
                - cells_tri3: (M, 3) int32
                - cells_quad4: (K, 4) int32 (optional)
                - node_set__*, edge_set__*, elem_set__*
            
            callbacks: Optional progress callbacks
                - on_progress(progress, message, stage_id, step)
                    progress: float 0-1
                    message: str description
                    stage_id: str current stage
                    step: int current step number
        
        Returns:
            (result_meta, result_arrays):
                result_meta: {
                    "schema_version": "0.1",
                    "status": "success" | "error",
                    "solver_info": {...},
                    "stages": [{...}],
                    "registry": [{...}],
                    "warnings": [...],
                    "errors": [...],
                }
                result_arrays: {
                    "nodal__<name>__step<NNNNNN>": np.ndarray,
                    ...
                }
        """
        ...
```

---

## Solver Loading

### loader.py

```python
def load_solver(selector: str) -> SolverProtocol:
    """
    Load a solver by selector string.
    
    Args:
        selector: Solver selector in one of these formats:
            - "fake": Built-in fake solver
            - "ref_elastic" or "reference_elastic": Reference elastic solver
            - "ref_seepage" or "reference_seepage": Reference seepage solver
            - "python:<module>": Load from Python module
    
    Returns:
        Solver instance implementing SolverProtocol
    
    Raises:
        ValueError: If selector format is unknown
        ImportError: If Python module cannot be loaded
        AttributeError: If module doesn't expose required interface
    
    Examples:
        load_solver("fake")
        load_solver("ref_elastic")
        load_solver("ref_seepage")
        load_solver("python:my_solver.backend")
    """
```

### Python Module Loading

For `python:<module>` selectors, the loader looks for:

1. `module.get_solver()` function returning a solver instance
2. `module.Solver` class that can be instantiated

Example module structure:

```python
# my_solver/backend.py

class MySolver:
    def capabilities(self):
        return {"name": "my_solver", ...}
    
    def solve(self, request, mesh, callbacks=None):
        ...

def get_solver():
    return MySolver()
```

Usage:
```bash
geohpem run case_folder --solver python:my_solver.backend
```

---

## Reference Elastic Solver

The `ReferenceElasticSolver` (`reference_elastic.py`) implements linear elasticity FEM:

### Capabilities

- **Materials**: `linear_elastic` (E, nu, rho optional)
- **Boundary Conditions**: `displacement` (ux/uy on node_set/edge_set→nodes)
- **Loads**: `gravity`, `traction` (on edge_set)
- **Output**: `u` (node), `sx/sy/sxy/vm` (element)
- **Modes**: `plane_strain`, `plane_stress`
- **Contract**: v0.2

### Implementation Details

- Standard FEM assembly (tri3 and quad4 elements)
- Plane stress/strain D-matrix computation
- Dirichlet BC enforcement (displacement constraints)
- Neumann BC application (traction loads)
- Body force integration (gravity)
- Stress computation from displacements (σ_xx, σ_yy, τ_xy, von Mises)

### Usage

```python
from geohpem.solver_adapter.loader import load_solver

solver = load_solver("ref_elastic")
caps = solver.capabilities()
# caps["analysis_types"] = ["static"]
# caps["materials"] = ["linear_elastic"]
# caps["bcs"] = ["displacement"]
# caps["loads"] = ["gravity", "traction"]

result_meta, result_arrays = solver.solve(request, mesh, callbacks)
```

### CLI Usage

```bash
geohpem run case_folder --solver ref_elastic
```

---

## Reference Seepage Solver

The `ReferenceSeepageSolver` (`reference_seepage.py`) implements steady-state seepage (Poisson/Darcy):

### Capabilities

- **Materials**: `darcy` (k - isotropic permeability)
- **Boundary Conditions**: `p` (Dirichlet on node_set/edge_set→nodes)
- **Loads**: `flux` (Neumann on edge_set)
- **Output**: `p` (node - pore pressure)
- **Modes**: `plane_strain`, `plane_stress`
- **Contract**: v0.2

### Implementation Details

- Poisson/Darcy equation discretization (tri3 and quad4)
- Dirichlet BC enforcement (prescribed pressure)
- Neumann BC application (flux boundary conditions)
- Sparse linear solver (scipy.sparse.linalg.spsolve)

### Usage

```python
from geohpem.solver_adapter.loader import load_solver

solver = load_solver("ref_seepage")
caps = solver.capabilities()
# caps["analysis_types"] = ["seepage_steady"]
# caps["materials"] = ["darcy"]
# caps["bcs"] = ["p"]
# caps["loads"] = ["flux"]

result_meta, result_arrays = solver.solve(request, mesh, callbacks)
```

### CLI Usage

```bash
geohpem run case_folder --solver ref_seepage
```

---

## Fake Solver

The fake solver (`fake.py`) is a placeholder implementation for development and testing:

### Features

- Simulates multi-stage analysis
- Generates placeholder displacement (u) and pore pressure (p) fields
- Supports progress callbacks
- Produces valid result format

### Implementation

```python
class FakeSolver:
    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "fake",
            "contract": {"min": "0.1", "max": "0.1"},
            "modes": ["plane_strain", "axisymmetric"],
            "analysis_types": ["static", "dynamic", "seepage_transient", "consolidation_u_p"],
            "fields": ["u", "p"],
            "results": ["u", "p", "stress", "strain"],
        }

    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        points = np.asarray(mesh["points"])
        n = points.shape[0]
        
        # Progress callback
        def cb_progress(p, msg, stage_id, step):
            if callbacks and (fn := callbacks.get("on_progress")):
                fn(p, msg, stage_id, step)
        
        stages = request["stages"]
        total_steps = sum(s.get("num_steps", 1) for s in stages)
        
        arrays = {}
        stage_infos = []
        step_counter = 0
        
        for si, stage in enumerate(stages):
            stage_id = stage.get("id", f"stage_{si+1}")
            num_steps = stage.get("num_steps", 1)
            times = []
            
            for step in range(num_steps):
                step_counter += 1
                p = step_counter / total_steps
                cb_progress(p, "fake solving...", stage_id, step)
                
                # Generate placeholder results
                disp = np.zeros((n, 2))
                disp[:, 0] = 1e-3 * p
                disp[:, 1] = -1e-3 * p
                pore = np.full((n,), 10.0 * p)
                
                step_key = f"{step_counter:06d}"
                arrays[f"nodal__u__step{step_key}"] = disp
                arrays[f"nodal__p__step{step_key}"] = pore
                times.append(stage.get("dt", 1.0) * (step + 1))
            
            stage_infos.append({"id": stage_id, "num_steps": num_steps, "times": times})
        
        meta = {
            "schema_version": "0.1",
            "status": "success",
            "solver_info": {"name": "fake"},
            "stages": stage_infos,
            "registry": [
                {"name": "u", "location": "node", "shape": "vector2", ...},
                {"name": "p", "location": "node", "shape": "scalar", ...},
            ],
            "warnings": [],
            "errors": [],
        }
        
        return meta, arrays
```

### Usage

```python
from geohpem.solver_adapter.fake import FakeSolver

solver = FakeSolver()

# Check capabilities
caps = solver.capabilities()
print(caps["analysis_types"])

# Run solver
result_meta, result_arrays = solver.solve(request, mesh)
```

---

## Implementing Custom Solvers

### Step 1: Create Solver Class

```python
# my_solver/solver.py
import numpy as np
from typing import Any

class MySolver:
    def capabilities(self) -> dict[str, Any]:
        return {
            "name": "my_solver",
            "version": "1.0.0",
            "contract": {"min": "0.1", "max": "0.1"},
            "modes": ["plane_strain"],
            "analysis_types": ["static"],
            "fields": ["u"],
            "results": ["u", "stress", "strain"],
        }
    
    def solve(
        self,
        request: dict[str, Any],
        mesh: dict[str, Any],
        callbacks: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # Extract mesh data
        points = np.asarray(mesh["points"])
        cells = np.asarray(mesh["cells_tri3"])
        n_nodes = points.shape[0]
        n_elements = cells.shape[0]
        
        # Progress reporting
        def report_progress(p: float, msg: str, stage_id: str, step: int):
            if callbacks and "on_progress" in callbacks:
                callbacks["on_progress"](p, msg, stage_id, step)
        
        # Get model settings
        model = request["model"]
        mode = model["mode"]  # "plane_strain" or "axisymmetric"
        gravity = model.get("gravity", [0, -9.81])
        
        # Get materials and assignments
        materials = request.get("materials", {})
        assignments = request.get("assignments", [])
        
        # Process stages
        stages = request["stages"]
        result_arrays = {}
        stage_infos = []
        global_step = 0
        
        for stage in stages:
            stage_id = stage.get("id", "unknown")
            num_steps = stage.get("num_steps", 1)
            analysis_type = stage.get("analysis_type", "static")
            bcs = stage.get("bcs", [])
            loads = stage.get("loads", [])
            
            times = []
            for step in range(num_steps):
                global_step += 1
                progress = global_step / sum(s.get("num_steps", 1) for s in stages)
                report_progress(progress, f"Solving {stage_id} step {step+1}", stage_id, step)
                
                # Your FEM solver logic here
                displacements = self._solve_step(
                    points, cells, materials, assignments,
                    bcs, loads, mode, gravity
                )
                
                # Store results
                step_key = f"{global_step:06d}"
                result_arrays[f"nodal__u__step{step_key}"] = displacements
                
                # Compute derived quantities
                stress = self._compute_stress(displacements, cells, materials)
                result_arrays[f"elem__stress__step{step_key}"] = stress
                
                times.append(stage.get("dt", 1.0) * (step + 1))
            
            stage_infos.append({
                "id": stage_id,
                "num_steps": num_steps,
                "times": times,
            })
        
        # Build result metadata
        result_meta = {
            "schema_version": "0.1",
            "status": "success",
            "solver_info": {
                "name": "my_solver",
                "version": "1.0.0",
            },
            "stages": stage_infos,
            "registry": [
                {
                    "name": "u",
                    "location": "node",
                    "shape": "vector2",
                    "unit": request.get("unit_system", {}).get("length", "m"),
                    "npz_pattern": "nodal__u__step{step:06d}",
                },
                {
                    "name": "stress",
                    "location": "element",
                    "shape": "tensor_voigt",
                    "unit": request.get("unit_system", {}).get("pressure", "kPa"),
                    "npz_pattern": "elem__stress__step{step:06d}",
                },
            ],
            "warnings": [],
            "errors": [],
        }
        
        return result_meta, result_arrays
    
    def _solve_step(self, points, cells, materials, assignments, bcs, loads, mode, gravity):
        # Implement your FEM solver here
        n_nodes = points.shape[0]
        return np.zeros((n_nodes, 2))  # Placeholder
    
    def _compute_stress(self, displacements, cells, materials):
        n_elements = cells.shape[0]
        return np.zeros((n_elements, 3))  # Placeholder (σ_xx, σ_yy, τ_xy)


def get_solver():
    """Entry point for solver loading."""
    return MySolver()
```

### Step 2: Make Module Importable

```python
# my_solver/__init__.py
from .solver import MySolver, get_solver

__all__ = ["MySolver", "get_solver"]
```

### Step 3: Use the Solver

```bash
# CLI
geohpem run case_folder --solver python:my_solver

# Or in code
from geohpem.solver_adapter.loader import load_solver

solver = load_solver("python:my_solver")
result_meta, result_arrays = solver.solve(request, mesh)
```

---

## Progress Callbacks

Solvers should report progress for responsive UI:

```python
def solve(self, request, mesh, callbacks=None):
    def report(progress, message, stage_id, step):
        if callbacks and "on_progress" in callbacks:
            callbacks["on_progress"](progress, message, stage_id, step)
    
    total_steps = sum(s.get("num_steps", 1) for s in request["stages"])
    current = 0
    
    for stage in request["stages"]:
        for step in range(stage.get("num_steps", 1)):
            current += 1
            report(
                progress=current / total_steps,  # 0.0 to 1.0
                message=f"Computing step {current}",
                stage_id=stage["id"],
                step=step,
            )
            # ... solve step ...
```

---

## Error Handling

Solvers should handle errors gracefully and report them in results:

```python
def solve(self, request, mesh, callbacks=None):
    errors = []
    warnings = []
    
    try:
        # ... solver logic ...
        status = "success"
    except Exception as e:
        errors.append(str(e))
        status = "error"
    
    result_meta = {
        "schema_version": "0.1",
        "status": status,
        "warnings": warnings,
        "errors": errors,
        # ...
    }
    
    return result_meta, result_arrays
```

---

## Testing Solvers

```python
import numpy as np
from my_solver import get_solver

def test_solver():
    solver = get_solver()
    
    # Check capabilities
    caps = solver.capabilities()
    assert "static" in caps["analysis_types"]
    
    # Minimal request
    request = {
        "schema_version": "0.1",
        "model": {"dimension": 2, "mode": "plane_strain", "gravity": [0, -9.81]},
        "materials": {},
        "assignments": [],
        "stages": [{"id": "test", "analysis_type": "static", "num_steps": 1}],
    }
    
    mesh = {
        "points": np.array([[0,0], [1,0], [0.5,1]]),
        "cells_tri3": np.array([[0, 1, 2]]),
    }
    
    # Run solver
    meta, arrays = solver.solve(request, mesh)
    
    assert meta["status"] == "success"
    assert "nodal__u__step000001" in arrays
```

---

---

## Solver Team Integration Guide

For solver teams integrating new solvers, see:

- **`docs/SOLVER_TEAM_GUIDE.md`**: Step-by-step guide for solver integration
- **`docs/REFERENCE_SOLVERS.md`**: Overview of reference solvers
- **`docs/CONTRACT_V0_2.md`**: Contract v0.2 specification
- **`docs/SOLVER_SUBMODULE_INTEGRATION.md`**: Technical integration details

The reference solvers (`reference_elastic.py` and `reference_seepage.py`) serve as templates that can be copied and modified for new solver implementations.

### Reference Case Generation

Generate test cases for reference solvers:

```bash
python scripts/make_reference_cases.py
```

This creates reference cases in `_Projects/cases/`:
- `reference_elastic_01/`: Elastic test case
- `reference_seepage_01/`: Seepage test case

---

Last updated: 2024-12-22 (v4 - reference solvers, contract v0.2 support)

