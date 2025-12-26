# Domain Module

The `domain/` module contains pure domain operations for manipulating project data (request and mesh) without side effects. These functions are used by the GUI and application layer to implement business logic.

## Module Structure

```
domain/
├── __init__.py
├── project.py                  # (placeholder for future domain models)
├── mesh_ops.py                 # Mesh manipulation operations
├── request_ops.py              # Request manipulation operations
├── boundary_ops.py             # Boundary edge computation and classification
├── material_catalog.py         # Material catalog system (templates, defaults)
├── material_mapping.py         # Solver-specific material mapping
└── materials_catalog.default.json  # Default material catalog
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

## Material Catalog System (`material_catalog.py`)

The material catalog provides a template-based system for managing material models with:
- Default parameter values
- Metadata (labels, tooltips) for UI display
- Solver-specific mappings (e.g., GeoHPEM → Kratos)
- User-customizable models

### Catalog Structure

```python
@dataclass(frozen=True, slots=True)
class MaterialModel:
    name: str                    # Unique model identifier (e.g., "linear_elastic")
    label: str                   # Display label (e.g., "Linear Elastic")
    behavior: str                # Behavior category (e.g., "elastic", "plastic")
    defaults: dict[str, Any]     # Default parameter values
    meta: dict[str, dict[str, str]]  # Parameter metadata (label, tooltip)
    solver_mapping: dict[str, Any]   # Solver-specific mappings
    description: str = ""        # Description text
```

### Catalog Files

- **Default Catalog**: `domain/materials_catalog.default.json` (bundled with GeoHPEM)
- **User Catalog**: `~/.geohpem/materials_catalog.user.json` (user customization)
- **Merging**: User catalog overrides/adds to default catalog
- **Backup**: User catalog is automatically backed up before overwriting

### Key Functions

```python
def load_catalog(force: bool = False) -> dict[str, Any]:
    """
    Load merged catalog (default + user).
    Cached until force=True or reload_catalog() called.
    """

def reload_catalog() -> dict[str, Any]:
    """Force reload catalog from disk (clears cache)."""

def all_models() -> list[MaterialModel]:
    """Get all material models from merged catalog."""

def model_by_name(model_name: str) -> MaterialModel | None:
    """Find a model by name."""

def model_defaults(model_name: str) -> dict[str, Any] | None:
    """Get default parameters for a model."""

def model_meta(model_name: str) -> dict[str, dict[str, str]]:
    """Get parameter metadata (labels, tooltips) for a model."""

def behavior_for_model(model_name: str) -> str | None:
    """Get behavior type for a model."""

def behavior_options() -> list[tuple[str, str]]:
    """Get available behavior types (elastic, plastic, etc.)."""

def behavior_label(behavior: str) -> str:
    """Get display label for a behavior type."""

def validate_catalog(data: dict[str, Any]) -> list[str]:
    """Validate catalog structure. Returns list of error messages."""

def write_user_catalog(data: dict[str, Any]) -> None:
    """
    Write user catalog (creates backup before overwriting).
    Backup stored in ~/.geohpem/catalog_backups/
    """
```

### Catalog Schema

See `docs/materials_catalog.schema.json` for JSON schema:

```json
{
  "version": "string",
  "behaviors": {
    "elastic": "Elastic",
    "plastic": "Elasto-plastic",
    "poroelastic": "Poroelastic",
    "seepage": "Seepage",
    "custom": "Custom"
  },
  "models": [
    {
      "name": "linear_elastic",
      "label": "Linear Elastic",
      "behavior": "elastic",
      "description": "...",
      "defaults": {
        "E": 10000.0,
        "nu": 0.3,
        "rho": 2000.0
      },
      "meta": {
        "E": {
          "label": "Young's Modulus",
          "tooltip": "Elastic modulus in kPa"
        },
        ...
      },
      "solver_mapping": {
        "kratos": {
          "model_name": "LinearElasticPlaneStrain2DLaw",
          "params": {
            "YOUNG_MODULUS": "E",
            "POISSON_RATIO": "nu"
          }
        }
      }
    }
  ]
}
```

---

## Material Mapping (`material_mapping.py`)

Maps GeoHPEM materials to solver-specific formats using catalog definitions.

```python
def map_material_for_solver(material: dict[str, Any], solver_id: str) -> dict[str, Any]:
    """
    Remap material for a solver using catalog solver_mapping.
    
    If no mapping exists, returns the material unchanged.
    
    Args:
        material: GeoHPEM material dict with model_name and parameters
        solver_id: Solver identifier (e.g., "kratos")
    
    Returns:
        Remapped material dict (may change model_name and parameters)
    
    Example:
        Input: {
            "model_name": "linear_elastic",
            "parameters": {"E": 10000, "nu": 0.3}
        }
        
        Output (for kratos): {
            "model_name": "LinearElasticPlaneStrain2DLaw",
            "parameters": {"YOUNG_MODULUS": 10000, "POISSON_RATIO": 0.3}
        }
    """
```

**Mapping Logic**:
1. Look up material model in catalog using `model_name`
2. Check for `solver_mapping[solver_id]` entry
3. Map `model_name` and `behavior` if specified
4. Map parameters using `params` dictionary (target_key ← source_path)
5. Use dot notation for nested paths (e.g., "nested.E" maps `parameters.nested.E`)

**Parameter Path Resolution**:
- Simple keys: `"E"` → `parameters["E"]`
- Nested paths: `"nested.E"` → `parameters.get("nested", {}).get("E")`

---

## Usage Examples

**Using Material Catalog**:

```python
from geohpem.domain import material_catalog as mc

# Load catalog
catalog = mc.load_catalog()

# Get all models
models = mc.all_models()
for m in models:
    print(f"{m.name}: {m.label} ({m.behavior})")

# Get defaults for a model
defaults = mc.model_defaults("linear_elastic")
# {"E": 10000.0, "nu": 0.3, "rho": 2000.0}

# Get parameter metadata
meta = mc.model_meta("linear_elastic")
# {"E": {"label": "Young's Modulus", "tooltip": "..."}, ...}

# Get behavior label
label = mc.behavior_label("elastic")
# "Elastic"
```

**Material Mapping**:

```python
from geohpem.domain import material_mapping

material = {
    "model_name": "linear_elastic",
    "parameters": {"E": 10000, "nu": 0.3}
}

# Map for Kratos solver
kratos_material = material_mapping.map_material_for_solver(material, "kratos")
# {
#     "model_name": "LinearElasticPlaneStrain2DLaw",
#     "parameters": {"YOUNG_MODULUS": 10000, "POISSON_RATIO": 0.3}
# }
```

**User Catalog Customization**:

Users can customize the material catalog by editing `~/.geohpem/materials_catalog.user.json`:

```json
{
  "models": [
    {
      "name": "my_custom_model",
      "label": "My Custom Model",
      "behavior": "plastic",
      "defaults": {
        "E": 5000,
        "nu": 0.2
      },
      "meta": {
        "E": {
          "label": "Young's Modulus",
          "tooltip": "Custom tooltip"
        }
      }
    }
  ]
}
```

The GUI provides a **Material Catalog** dialog (Tools → Material Catalog...) to manage the user catalog with a visual interface.

---

Last updated: 2024-12-26 (v4 - added material_catalog and material_mapping)

