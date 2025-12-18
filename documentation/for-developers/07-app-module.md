# App Module

The `app` module contains application-level services that bridge the gap between the GUI and the solver infrastructure.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Precheck Service](#precheck-service)
4. [Run Case Service](#run-case-service)
5. [Case Runner (Batch)](#case-runner-batch)
6. [Diagnostics](#diagnostics)
7. [Usage Examples](#usage-examples)

---

## Overview

The app module provides:

- **Precheck**: Validates request and mesh before solver execution (with capabilities awareness)
- **Run Case**: Orchestrates solver execution from case folder
- **Case Runner**: Batch execution of multiple case folders
- **Diagnostics**: Creates diagnostic ZIP packages for debugging solver failures

These services are used by both the GUI (via workers) and CLI.

---

## Module Structure

```
app/
├── __init__.py
├── precheck.py         # Request/mesh validation (with capabilities)
├── run_case.py         # Single case solver execution
├── case_runner.py      # Batch case execution
├── compare_outputs.py  # Output comparison utilities
├── diagnostics.py      # Diagnostic ZIP generation
└── errors.py           # Custom exceptions (CancelledError)
```

---

## Precheck Service

### precheck.py

The precheck service validates request and mesh data before running the solver, identifying potential issues early.

#### Issue Types

```python
@dataclass(frozen=True, slots=True)
class PrecheckIssue:
    severity: str    # "ERROR" | "WARN" | "INFO"
    code: str        # Issue code (e.g., "REQ_SCHEMA", "MESH_POINTS")
    message: str     # Human-readable description
```

#### Issue Codes

| Code | Severity | Description |
|------|----------|-------------|
| `REQ_SCHEMA` | ERROR | `schema_version` is not "0.1" |
| `REQ_MODEL` | ERROR | `model` is not an object |
| `REQ_DIM` | ERROR | `model.dimension` is not 2 |
| `REQ_MODE` | ERROR | Invalid `model.mode` |
| `REQ_STAGES` | ERROR | `stages` is empty or invalid |
| `MESH_POINTS` | ERROR | Missing `points` array |
| `MESH_EMPTY` | WARN | Mesh has 0 points |
| `MESH_CELLS` | ERROR | No cell arrays (`cells_*`) |
| `BC_SET_MISSING` | ERROR | BC references non-existent set |
| `LOAD_SET_MISSING` | ERROR | Load references non-existent set |
| `ASSIGN_SET_MISSING` | ERROR | Assignment references non-existent set |
| `STAGE_TYPE` | ERROR | Stage is not an object |
| `CAP_CONTRACT` | ERROR | Schema version not in solver's contract range |
| `CAP_MODE_UNSUPPORTED` | ERROR | Mode not supported by solver |
| `CAP_ANALYSIS_UNSUPPORTED` | ERROR | Analysis type not supported by solver |
| `CAP_OUTPUT_UNSUPPORTED` | WARN | Output field not in solver capabilities |

#### API

```python
def precheck_request_mesh(
    request: dict[str, Any],
    mesh: dict[str, Any],
    *,
    capabilities: dict[str, Any] | None = None,
) -> list[PrecheckIssue]:
    """
    Validate request and mesh before solver run.
    
    Args:
        request: Analysis configuration
        mesh: Mesh data
        capabilities: Optional solver capabilities dict for extended checks
    
    Returns:
        List of issues (empty if valid)
    
    Checks performed:
        - Schema version (+ contract range if capabilities provided)
        - Model configuration (+ mode support if capabilities provided)
        - Stage structure (+ analysis_type support if capabilities provided)
        - Mesh presence and validity
        - Set references in BCs, loads, assignments
        - Output request names (if capabilities provided)
    """

def summarize_issues(
    issues: Iterable[PrecheckIssue]
) -> tuple[int, int, int]:
    """
    Count issues by severity.
    
    Returns:
        (error_count, warning_count, info_count)
    """
```

#### Validation Details

**Request Validation**:
```python
# Schema version
if request.get("schema_version") != "0.1":
    # ERROR: REQ_SCHEMA

# Model object
model = request.get("model")
if not isinstance(model, dict):
    # ERROR: REQ_MODEL
else:
    if model.get("dimension") != 2:
        # ERROR: REQ_DIM
    if model.get("mode") not in ("plane_strain", "axisymmetric"):
        # ERROR: REQ_MODE

# Stages
stages = request.get("stages")
if not isinstance(stages, list) or not stages:
    # ERROR: REQ_STAGES
```

**Mesh Validation**:
```python
# Points array
if "points" not in mesh:
    # ERROR: MESH_POINTS
elif mesh["points"].shape[0] == 0:
    # WARN: MESH_EMPTY

# Cell arrays
if not any(k.startswith("cells_") for k in mesh.keys()):
    # ERROR: MESH_CELLS
```

**Set Reference Validation**:
```python
# Collect all set names from mesh
set_names = {k.split("__", 1)[1] for k in mesh if k.startswith("node_set__")}
set_names |= {k.split("__", 1)[1] for k in mesh if k.startswith("edge_set__")}
set_names |= {k.split("__", 2)[1] for k in mesh if k.startswith("elem_set__")}

# Check BC set references
for bc in stage.get("bcs", []):
    set_name = bc.get("set")
    if set_name and set_name not in set_names:
        # ERROR: BC_SET_MISSING

# Check load set references
for load in stage.get("loads", []):
    set_name = load.get("set")
    if set_name and set_name not in set_names:
        # ERROR: LOAD_SET_MISSING

# Check assignment set references
for assign in request.get("assignments", []):
    set_name = assign.get("element_set")
    if set_name and set_name not in set_names:
        # ERROR: ASSIGN_SET_MISSING
```

---

## Run Case Service

### run_case.py

Orchestrates solver execution on a case folder.

#### API

```python
def run_case(
    case_dir: str,
    solver_selector: str = "fake",
    callbacks: dict | None = None,
) -> Path:
    """
    Run solver on a prepared case folder.
    
    Args:
        case_dir: Path to folder containing request.json + mesh.npz
        solver_selector: Solver to use
            - "fake": Built-in fake solver
            - "python:<module>": Load from Python module
        callbacks: Optional callbacks for progress reporting
            - on_progress(progress, message, stage_id, step)
    
    Returns:
        Path to output folder (case_dir/out)
    
    Raises:
        FileNotFoundError: If case files are missing
        ContractError: If validation fails
        Exception: Solver-specific errors
    
    Process:
        1. Read case folder (request.json + mesh.npz)
        2. Ensure stable IDs in request
        3. Load solver by selector
        4. Execute solver.solve()
        5. Write results to case_dir/out/
        6. Return output path
    """
```

#### Execution Flow

```
┌──────────────────┐
│  read_case_folder │
│  (request, mesh)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ ensure_request_ids│
│  (add UIDs)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   load_solver    │
│  (by selector)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   solver.solve   │
│ (with callbacks) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│write_result_folder│
│   (to out/)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Return Path    │
│  (case_dir/out)  │
└──────────────────┘
```

---

## Case Runner (Batch)

### case_runner.py

Provides batch execution of multiple case folders with optional baseline comparison.

#### Data Types

```python
@dataclass(frozen=True, slots=True)
class CaseRunRecord:
    case_dir: Path
    status: str  # "success" | "failed" | "skipped"
    solver_selector: str
    elapsed_s: float
    out_dir: Path | None
    error: str | None
    diagnostics_zip: Path | None
    compare: dict[str, Any] | None  # Comparison results if baseline provided
```

#### API

```python
def discover_case_folders(root: Path) -> list[Path]:
    """Find case folders (containing request.json + mesh.npz) under root."""

def run_cases(
    case_dirs: Iterable[Path],
    *,
    solver_selector: str,
    baseline_root: Path | None = None,
    on_progress: Callable[[int, int, Path, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[CaseRunRecord]:
    """Run multiple case folders sequentially with optional baseline comparison."""

def write_case_run_report(records: list[CaseRunRecord], out_path: Path) -> Path:
    """Write batch run results to JSON file."""
```

---

## Diagnostics

### diagnostics.py

Creates diagnostic ZIP packages for debugging solver failures.

```python
@dataclass(frozen=True, slots=True)
class DiagnosticsInfo:
    zip_path: Path

def build_diagnostics_zip(
    case_dir: Path,
    *,
    solver_selector: str,
    capabilities: dict[str, Any] | None = None,
    error: str | None = None,
    tb: str | None = None,
    logs: list[str] | None = None,
    include_out: bool = True,
) -> DiagnosticsInfo:
    """
    Create a diagnostic ZIP for sharing with solver/platform teams.
    
    ZIP Contents:
        diag/meta.json, request_preview.json, result_preview.json, pip_freeze.txt
        case/request.json, mesh.npz, out/result.json, out/result.npz
    """
```

### errors.py

```python
class CancelledError(Exception):
    """Raised when a solver run is cancelled by the user."""
```

---

## Output Comparison

### compare_outputs.py

Utilities for comparing two sets of solver outputs.

#### Data Types

```python
@dataclass(frozen=True, slots=True)
class FieldKey:
    location: str  # "node" or "element"
    name: str      # Field name (e.g., "u", "p", "stress")

@dataclass(frozen=True, slots=True)
class FieldStats:
    min: float
    max: float
    mean: float
    l2: float    # L2 norm of difference
    linf: float  # L-infinity norm (max abs)
```

#### API

```python
def common_fields(meta_a: dict, meta_b: dict) -> list[FieldKey]:
    """Find fields present in both output registries."""

def common_steps(arrays_a: dict, arrays_b: dict) -> list[int]:
    """Find step IDs present in both array sets."""

def diff_stats_for(
    *, meta_a, arrays_a, meta_b, arrays_b, field: FieldKey, step: int
) -> FieldStats | None:
    """Compute difference statistics for a specific field at a step."""

def step_curve_for(*, arrays: dict, field: FieldKey, steps: list[int]) -> list[dict]:
    """Extract per-step min/max/mean for a field (for CSV export)."""

def load_outputs(path: Path) -> tuple[dict, dict]:
    """Load outputs from an out/ folder or case folder."""
```

---

## Usage Examples

### CLI Usage

```bash
# Run with fake solver
geohpem run examples/case_cli_test --solver fake

# Run with custom solver
geohpem run examples/case_cli_test --solver python:my_solver.backend

# Batch run all cases under a folder
geohpem batch-run examples/ --solver fake

# With baseline comparison
geohpem batch-run examples/ --solver python:my_solver --baseline baseline/
```

### Programmatic Usage

```python
from geohpem.app.run_case import run_case

# Simple run
out_path = run_case("examples/case_cli_test", solver_selector="fake")
print(f"Results written to: {out_path}")

# With progress callback
def on_progress(progress, message, stage_id, step):
    print(f"[{progress*100:.0f}%] {stage_id} step {step}: {message}")

out_path = run_case(
    "examples/case_cli_test",
    solver_selector="fake",
    callbacks={"on_progress": on_progress},
)
```

### Precheck Before Run

```python
from geohpem.app.precheck import precheck_request_mesh, summarize_issues
from geohpem.contract.io import read_case_folder

# Load case
request, mesh = read_case_folder("examples/case_cli_test")

# Run precheck
issues = precheck_request_mesh(request, mesh)
errors, warnings, info = summarize_issues(issues)

if errors > 0:
    print("Cannot run - errors found:")
    for issue in issues:
        if issue.severity == "ERROR":
            print(f"  [{issue.code}] {issue.message}")
else:
    if warnings > 0:
        print(f"Proceeding with {warnings} warnings")
    out_path = run_case("examples/case_cli_test")
```

### GUI Integration

The GUI uses these services via workers:

```python
# In MainWindow._on_run_fake()
from geohpem.app.precheck import precheck_request_mesh
from geohpem.gui.dialogs.precheck_dialog import PrecheckDialog
from geohpem.gui.workers.solve_worker import SolveWorker

# Precheck
issues = precheck_request_mesh(state.project.request, state.project.mesh)
dlg = PrecheckDialog(self._win, issues)
if not dlg.exec():
    return  # User cancelled

# Write case folder
write_case_folder(state.work_case_dir, state.project.request, state.project.mesh)

# Run in background
worker = SolveWorker(case_dir=state.work_case_dir, solver_selector="fake")
worker.output_ready.connect(self.open_output_folder)
worker.start()
```

---

## Integration with Other Modules

### Contract Module

```python
from geohpem.contract.io import read_case_folder, write_result_folder
from geohpem.contract.validate import validate_request_basic

# run_case uses contract I/O for file operations
request, mesh = read_case_folder(case_path)
validate_request_basic(request)  # Called by read_case_folder
# ... solver execution ...
write_result_folder(out_dir, result_meta, result_arrays)
```

### Project Module

```python
from geohpem.project.normalize import ensure_request_ids

# run_case ensures IDs before solving
ensure_request_ids(request, mesh)
```

### Solver Adapter Module

```python
from geohpem.solver_adapter.loader import load_solver

# run_case loads solver by selector
solver = load_solver(solver_selector)
result_meta, result_arrays = solver.solve(request, mesh, callbacks=callbacks)
```

---

## Error Handling

### Precheck Errors

Precheck issues don't raise exceptions - they return issue objects:

```python
issues = precheck_request_mesh(request, mesh)
if any(i.severity == "ERROR" for i in issues):
    # Handle validation failures
```

### Run Case Errors

`run_case` may raise various exceptions:

```python
try:
    out_path = run_case(case_dir, solver_selector)
except FileNotFoundError as e:
    print(f"Missing file: {e}")
except ContractError as e:
    print(f"Invalid request/mesh: {e}")
except Exception as e:
    print(f"Solver error: {e}")
```

---

## Logging

The app module uses Python's logging:

```python
import logging

logger = logging.getLogger(__name__)

# In run_case
logger.info("Wrote results to %s", out_dir)
```

Configure logging in your application:

```python
from geohpem.util.logging import configure_logging

configure_logging()  # Sets up basic logging
```

---

Last updated: 2024-12-18 (v3 - added compare_outputs module)

