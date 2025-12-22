# Domain Module

The `domain/` module contains pure domain operations for manipulating project data (request and mesh) without side effects. These functions are used by the GUI and application layer to implement business logic.

## Module Structure

```
domain/
├── __init__.py
├── project.py        # (placeholder for future domain models)
├── mesh_ops.py       # Mesh manipulation operations
├── request_ops.py    # Request manipulation operations
└── boundary_ops.py   # Boundary edge computation and classification
```

---

## Mesh Operations (`mesh_ops.py`)

Pure functions for manipulating Contract mesh dictionaries.

### Set Discovery

```python
def collect_set_names(mesh: dict[str, Any]) -> list[str]:
    """
    Collect all unique set names from mesh keys.
    Parses: node_set__NAME, edge_set__NAME, elem_set__NAME__celltype
    """

def collect_element_sets(mesh: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Returns list of (element_set_name, cell_type) tuples.
    Parses: elem_set__NAME__tri3 -> ("NAME", "tri3")
    """
```

### Set Modification

```python
def add_node_set(mesh: dict, name: str, indices: np.ndarray) -> dict:
    """Add or overwrite node_set__NAME with int32 indices."""

def add_edge_set(mesh: dict, name: str, edges: np.ndarray) -> dict:
    """Add or overwrite edge_set__NAME with int32 Nx2 array."""

def add_elem_set(mesh: dict, name: str, cell_type: str, indices: np.ndarray) -> dict:
    """Add or overwrite elem_set__NAME__celltype with int32 indices."""

def delete_set(mesh: dict, key: str) -> dict:
    """Delete a set by its full key (e.g., 'node_set__left')."""

def rename_set(mesh: dict, old_key: str, new_key: str) -> dict:
    """Rename a set. Raises KeyError if old doesn't exist or new already exists."""
```

**Note**: All functions return a new dict (shallow copy with modified key).

---

## Request Operations (`request_ops.py`)

Pure functions for manipulating Contract request dictionaries. All functions perform deep copies to ensure immutability.

### Stage Operations

```python
def apply_stage_patch_by_uid(request: dict, stage_uid: str, patch: dict) -> dict:
    """Apply a patch to a stage identified by uid. Raises KeyError if not found."""

def apply_stage_patch_by_index(request: dict, index: int, patch: dict) -> dict:
    """Apply a patch to a stage by index. Raises IndexError if invalid."""

def add_stage(request: dict, *, copy_from_index: int | None = None) -> tuple[dict, int]:
    """
    Add a new stage and return (new_request, new_stage_index).
    
    - If copy_from_index is None: Creates a default stage
    - If copy_from_index is provided: Deep copies that stage with new uid
    
    Note: All nested items (bcs, loads, output_requests) get regenerated UIDs.
    """

def delete_stage(request: dict, index: int) -> dict:
    """Delete stage at index. Raises ValueError if last stage, IndexError if invalid."""
```

### Model Operations

```python
def set_model_mode(request: dict, mode: str) -> dict:
    """Set request.model.mode (e.g., 'plane_strain', 'axisymmetric')."""

def set_gravity(request: dict, gx: float, gy: float) -> dict:
    """Set request.model.gravity = [gx, gy]."""

def set_model(request: dict, *, mode: str | None = None, 
              gravity: tuple[float, float] | None = None) -> dict:
    """Combined setter for model properties."""
```

### Material Operations

```python
def upsert_material(request: dict, material_id: str, model_name: str, 
                    parameters: dict) -> dict:
    """
    Add or update a material.
    
    - Preserves existing uid if material exists
    - Generates new uid if material is new
    """

def delete_material(request: dict, material_id: str) -> dict:
    """Remove a material by ID."""
```

### Assignment Operations

```python
def set_assignments(request: dict, assignments: list[dict]) -> dict:
    """
    Replace request.assignments with a new list.
    
    - Auto-generates uid for items missing it
    """
```

### Output Request Operations

```python
def set_global_output_requests(request: dict, output_requests: list[dict]) -> dict:
    """
    Replace request.output_requests with a new list.
    
    - Auto-generates uid for items missing it
    """
```

### Geometry Operations

```python
def set_geometry(request: dict, geometry: dict | None) -> dict:
    """Set or remove request.geometry."""

def set_set_label(request: dict, set_key: str, label: str) -> dict:
    """Update request.sets_meta[set_key].label (UI-only metadata)."""
```

---

## Boundary Operations (`boundary_ops.py`)

Pure functions for computing and classifying mesh boundary edges.

### Edge Computation

```python
def compute_boundary_edges(mesh: dict[str, Any]) -> np.ndarray:
    """
    Compute boundary edges from a 2D mesh connectivity.
    
    Boundary edges are those belonging to exactly one cell.
    Returns unique edges as (n,2) array with each row sorted (min,max).
    
    Handles multiple cell blocks (e.g., tri3 + quad4) by computing
    boundaries per block and then unioning.
    """

def compute_all_edges(mesh: dict[str, Any]) -> np.ndarray:
    """
    Compute unique undirected edges from a 2D mesh connectivity.
    
    Returns unique edges as (n,2) array with each row sorted (min,max).
    """
```

### Boundary Classification

```python
def classify_boundary_edges(
    mesh: dict[str, Any],
    *,
    edges: np.ndarray | None = None,
    tol_factor: float = 1e-6,
) -> dict[str, np.ndarray]:
    """
    Classify boundary edges into {all,bottom,top,left,right} by bounding box extremes.
    
    Best-effort helper for common engineering cases where the domain has
    clear min/max x/y boundaries.
    
    Args:
        mesh: Mesh dict with points
        edges: Optional pre-computed boundary edges (default: calls compute_boundary_edges)
        tol_factor: Tolerance factor for boundary detection (default: 1e-6)
    
    Returns:
        Dict with keys: "all", "bottom", "top", "left", "right"
        Each value is (n,2) array of edge node pairs.
    """
```

### Utilities

```python
def unique_nodes_from_edges(edges: np.ndarray) -> np.ndarray:
    """Extract unique node IDs from an edge array."""
```

---

## Usage Examples

### Adding a Node Set

```python
from geohpem.domain.mesh_ops import add_node_set
import numpy as np

mesh = {"points": np.array([[0, 0], [1, 0], [1, 1], [0, 1]]), ...}
new_mesh = add_node_set(mesh, "left", np.array([0, 3]))
# new_mesh["node_set__left"] = array([0, 3], dtype=int32)
```

### Adding a Stage

```python
from geohpem.domain.request_ops import add_stage

request = {...}
new_request, idx = add_stage(request)
# new_request["stages"][-1] is a new stage with generated uid
```

### Copying a Stage

```python
new_request, idx = add_stage(request, copy_from_index=0)
# new_request["stages"][-1] is a deep copy of stage 0 with new uids
```

### Updating Material

```python
from geohpem.domain.request_ops import upsert_material

new_request = upsert_material(
    request,
    material_id="clay",
    model_name="mohr_coulomb",
    parameters={"E": 10e6, "nu": 0.3, "c": 10e3, "phi": 30}
)
```

---

## Design Notes

### Immutability

All operations return new objects rather than modifying in place. This enables:
- Safe undo/redo implementation
- Predictable state management
- Easier testing

### UID Management

- UIDs are auto-generated for items that don't have them
- When copying stages, all nested item UIDs are regenerated to avoid conflicts
- UID prefixes: `stage_`, `bc_`, `load_`, `outreq_`, `mat_`, `assign_`

### Integration with GUI

The domain operations are used by `ProjectModel` to implement state changes:

```python
# In ProjectModel
def update_stage(self, stage_uid: str, patch: dict) -> None:
    old_request = self._request
    new_request = apply_stage_patch_by_uid(old_request, stage_uid, patch)
    
    def redo():
        self._request = new_request
        self.request_changed.emit(new_request)
    
    def undo():
        self._request = old_request
        self.request_changed.emit(old_request)
    
    self._undo_stack.push_and_redo(UndoCommand("Update stage", redo, undo))
```

---

Last updated: 2024-12-19 (v3 - added boundary_ops module)

