# Contract Module

The `contract` module defines the interface between GeoHPEM and external solvers. It specifies the data formats, validation rules, and I/O operations for solver communication.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Contract v0.1 Specification](#contract-v01-specification)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)

---

## Overview

The contract module ensures that:

1. **Request data** (analysis configuration) conforms to a defined schema
2. **Mesh data** follows a consistent NPZ format
3. **Result data** is structured for easy consumption by the GUI
4. **Solvers** implement a consistent protocol (`SolverProtocol`)

---

## Module Structure

```
contract/
├── __init__.py
├── types.py       # SolverProtocol interface, type aliases
├── io.py          # Read/write case and result folders
├── validate.py    # Request validation functions
├── errors.py      # ContractError exception
└── schemas/
    ├── __init__.py
    ├── request.schema.json   # JSON Schema for request
    └── result.schema.json    # JSON Schema for result
```

---

## Contract v0.1 Specification

### File Structure

A **case folder** follows this structure:

```
case_folder/
├── request.json      # Analysis configuration
├── mesh.npz          # Mesh data (NumPy compressed archive)
└── out/              # Output directory (created by solver)
    ├── result.json   # Result metadata
    └── result.npz    # Result arrays
```

### Request JSON Format

```json
{
  "schema_version": "0.1",
  "unit_system": {
    "force": "kN",
    "length": "m",
    "time": "s",
    "pressure": "kPa"
  },
  "model": {
    "dimension": 2,
    "mode": "plane_strain",
    "gravity": [0.0, -9.81]
  },
  "materials": {
    "<material_id>": {
      "model_name": "<solver-defined>",
      "parameters": { ... }
    }
  },
  "assignments": [
    {
      "element_set": "<set_name>",
      "cell_type": "tri3",
      "material_id": "<material_id>"
    }
  ],
  "stages": [
    {
      "id": "stage_1",
      "uid": "<unique-id>",
      "analysis_type": "static",
      "num_steps": 10,
      "dt": 1.0,
      "bcs": [
        {
          "field": "u",
          "type": "dirichlet",
          "set": "<set_name>",
          "value": [0.0, 0.0]
        }
      ],
      "loads": [
        {
          "type": "gravity",
          "set": "<set_name>",
          "value": [0.0, -10.0]
        }
      ],
      "output_requests": [
        {
          "name": "u",
          "location": "node",
          "every_n": 1
        }
      ]
    }
  ],
  "output_requests": []
}
```

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Must be `"0.1"` |
| `model.dimension` | int | Must be `2` |
| `model.mode` | string | `"plane_strain"` or `"axisymmetric"` |
| `stages` | array | Non-empty list of stage objects |

### Mesh NPZ Format

The mesh is stored as a NumPy compressed archive (`.npz`) with the following keys:

| Key | Shape | Type | Description |
|-----|-------|------|-------------|
| `points` | (N, 2) | float64 | Node coordinates |
| `cells_tri3` | (M, 3) | int32 | Triangle connectivity (optional) |
| `cells_quad4` | (K, 4) | int32 | Quad connectivity (optional) |
| `node_set__<name>` | (L,) | int32 | Node set indices |
| `edge_set__<name>` | (E, 2) | int32 | Edge connectivity (node pairs) |
| `elem_set__<name>__<type>` | (F,) | int32 | Element set indices |

#### Set Naming Convention

- Node sets: `node_set__<name>` (e.g., `node_set__bottom`)
- Edge sets: `edge_set__<name>` (e.g., `edge_set__left`)
- Element sets: `elem_set__<name>__<cell_type>` (e.g., `elem_set__soil__tri3`)

### Result JSON Format

```json
{
  "schema_version": "0.1",
  "status": "success",
  "solver_info": {
    "name": "fake",
    "version": "0.1"
  },
  "stages": [
    {
      "id": "stage_1",
      "num_steps": 10,
      "times": [1.0, 2.0, ..., 10.0]
    }
  ],
  "registry": [
    {
      "name": "u",
      "location": "node",
      "shape": "vector2",
      "unit": "m",
      "npz_pattern": "nodal__u__step{step:06d}"
    },
    {
      "name": "p",
      "location": "node",
      "shape": "scalar",
      "unit": "kPa",
      "npz_pattern": "nodal__p__step{step:06d}"
    }
  ],
  "warnings": [],
  "errors": []
}
```

### Result NPZ Format

Result arrays are stored with step-indexed keys:

| Key Pattern | Shape | Description |
|-------------|-------|-------------|
| `nodal__<name>__step<NNNNNN>` | (N,) or (N,dim) | Nodal field at step |
| `elem__<name>__step<NNNNNN>` | (M,) or (M,dim) | Element field at step |
| `ip__<name>__step<NNNNNN>` | (I,) or (I,dim) | Integration point field |
| `global__<name>__step<NNNNNN>` | (D,) | Global/scalar value |

Example: `nodal__u__step000010` contains displacement at step 10.

---

## API Reference

### Types (`types.py`)

```python
JsonDict = dict[str, Any]
ArrayDict = dict[str, Any]

class SolverProtocol(Protocol):
    def capabilities(self) -> JsonDict:
        """Return solver capabilities (name, supported analysis types, etc.)."""
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
            request: Analysis configuration (validated JSON)
            mesh: Mesh arrays (from NPZ)
            callbacks: Optional progress callbacks
                - on_progress(progress: float, message: str, stage_id: str, step: int)
        
        Returns:
            (result_meta, result_arrays): Result JSON and NPZ arrays
        """
        ...
```

### I/O Functions (`io.py`)

```python
def read_case_folder(case_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Read a case folder.
    
    Args:
        case_dir: Path to folder containing request.json and mesh.npz
    
    Returns:
        (request, mesh): Tuple of request dict and mesh arrays
    
    Raises:
        FileNotFoundError: If required files are missing
        ContractError: If validation fails
    """

def write_case_folder(case_dir: Path, request: dict[str, Any], mesh: dict[str, Any]) -> None:
    """
    Write a case folder.
    
    Args:
        case_dir: Target directory (created if not exists)
        request: Analysis configuration
        mesh: Mesh arrays
    
    Raises:
        ContractError: If validation fails
    """

def read_result_folder(out_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Read solver results.
    
    Args:
        out_dir: Path to out/ folder containing result.json and result.npz
    
    Returns:
        (result_meta, result_arrays): Result metadata and arrays
    """

def write_result_folder(out_dir: Path, result_meta: dict[str, Any], result_arrays: dict[str, Any]) -> None:
    """
    Write solver results.
    
    Args:
        out_dir: Target directory (created if not exists)
        result_meta: Result metadata (JSON-serializable)
        result_arrays: Result arrays
    """
```

### Validation (`validate.py`)

```python
def validate_request_basic(request: dict[str, Any]) -> None:
    """
    Perform basic structural validation on request.
    
    Checks:
        - schema_version == "0.1"
        - model is an object with dimension=2 and valid mode
        - stages is a non-empty list
    
    Raises:
        ContractError: If validation fails
    """

def validate_request_jsonschema_if_available(request: dict[str, Any]) -> None:
    """
    Optional validation using jsonschema (if installed).
    
    This is for developer tooling and CI, not a hard runtime dependency.
    """
```

### Errors (`errors.py`)

```python
class ContractError(Exception):
    """Raised when contract validation fails."""
    pass
```

---

## Usage Examples

### Reading a Case Folder

```python
from pathlib import Path
from geohpem.contract.io import read_case_folder

case_dir = Path("examples/case_cli_test")
request, mesh = read_case_folder(case_dir)

print(f"Mode: {request['model']['mode']}")
print(f"Stages: {len(request['stages'])}")
print(f"Points: {mesh['points'].shape}")
```

### Writing Results

```python
from geohpem.contract.io import write_result_folder
import numpy as np

result_meta = {
    "schema_version": "0.1",
    "status": "success",
    "registry": [{"name": "u", "location": "node", "shape": "vector2"}],
}
result_arrays = {
    "nodal__u__step000001": np.zeros((100, 2)),
}

write_result_folder(Path("out"), result_meta, result_arrays)
```

### Implementing a Solver

```python
from geohpem.contract.types import SolverProtocol

class MySolver:
    def capabilities(self):
        return {
            "name": "my_solver",
            "analysis_types": ["static"],
        }
    
    def solve(self, request, mesh, callbacks=None):
        points = mesh["points"]
        # ... perform analysis ...
        
        result_meta = {"schema_version": "0.1", "status": "success", "registry": [...]}
        result_arrays = {"nodal__u__step000001": displacements}
        return result_meta, result_arrays

# Register as: python:my_module (with get_solver() function)
def get_solver() -> SolverProtocol:
    return MySolver()
```

---

## Schema Files

The `schemas/` folder contains JSON Schema files for formal validation:

- `request.schema.json`: Validates request.json structure
- `result.schema.json`: Validates result.json structure

These are used by `validate_request_jsonschema_if_available()` when `jsonschema` is installed.

---

Last updated: 2024-12-18

