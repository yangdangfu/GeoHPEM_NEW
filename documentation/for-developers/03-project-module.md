# Project Module

The `project` module handles project file management, including loading, saving, and migrating project data between different formats.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Project File Format](#project-file-format)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)

---

## Overview

GeoHPEM supports two project formats:

1. **Case Folder**: Directory with `request.json` + `mesh.npz` (+ optional `out/`)
2. **Project File**: `.geohpem` ZIP archive (portable, self-contained)

The project module provides:
- Loading/saving both formats
- Project templates for new projects
- ID normalization for stable references
- Version migration for compatibility
- Temporary working directory management

---

## Module Structure

```
project/
├── __init__.py
├── types.py           # ProjectData dataclass
├── package.py         # .geohpem ZIP file handling
├── case_folder.py     # Case folder loading
├── workdir.py         # Temporary working directory
├── templates.py       # New project templates
├── normalize.py       # ID normalization
└── migrations/
    ├── __init__.py
    └── migrate.py     # Version migration logic
```

---

## Project File Format

### .geohpem File Structure

A `.geohpem` file is a ZIP archive with the following contents:

```
project.geohpem (ZIP)
├── manifest.json      # Package metadata
├── request.json       # Analysis configuration
├── mesh.npz           # Mesh data
└── out/               # Results (optional)
    ├── result.json
    └── result.npz
```

### manifest.json

```json
{
  "schema_version": "0.1",
  "created_at": "2024-12-18T10:30:00+00:00",
  "app": {
    "name": "geohpem",
    "version": "0.1.0"
  },
  "contract": {
    "request": "0.1",
    "result": "0.1"
  }
}
```

---

## API Reference

### ProjectData (`types.py`)

```python
@dataclass(slots=True)
class ProjectData:
    """
    In-memory representation of a complete project.
    
    Attributes:
        request: Analysis configuration (JSON-serializable dict)
        mesh: Mesh arrays (dict of numpy arrays)
        result_meta: Result metadata (optional, from solver)
        result_arrays: Result arrays (optional, from solver)
        manifest: Package metadata (optional, for .geohpem files)
    """
    request: dict[str, Any]
    mesh: dict[str, np.ndarray]
    result_meta: dict[str, Any] | None = None
    result_arrays: dict[str, np.ndarray] | None = None
    manifest: dict[str, Any] | None = None
```

### Package Functions (`package.py`)

```python
DEFAULT_EXT = ".geohpem"

def save_geohpem(path: str | Path, project: ProjectData) -> Path:
    """
    Save project to a .geohpem file.
    
    Args:
        path: Output path (will add .geohpem extension if missing)
        project: Project data to save
    
    Returns:
        Path to saved file (normalized with .geohpem extension)
    
    Raises:
        ContractError: If validation fails
    
    Notes:
        - Automatically ensures request IDs before saving
        - Validates request against basic schema
        - Compresses all data in ZIP format
    """

def load_geohpem(path: str | Path) -> ProjectData:
    """
    Load project from a .geohpem file.
    
    Args:
        path: Path to .geohpem file
    
    Returns:
        Loaded ProjectData
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ContractError: If validation fails
    
    Notes:
        - Applies migrations to older format versions
        - Ensures stable IDs after loading
    """

def normalize_project_path(path: str | Path) -> Path:
    """Add .geohpem extension if not present."""

def make_manifest(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a new manifest with current timestamp and version."""
```

### Case Folder Functions (`case_folder.py`)

```python
def load_case_folder(case_dir: str | Path) -> ProjectData:
    """
    Load project from a case folder.
    
    Args:
        case_dir: Path to folder containing request.json + mesh.npz
    
    Returns:
        ProjectData with request, mesh, and results (if out/ exists)
    
    Notes:
        - Automatically loads results from out/ if present
        - Ensures stable IDs after loading
    """
```

### Working Directory Functions (`workdir.py`)

```python
def materialize_to_workdir(project: ProjectData) -> Path:
    """
    Create a temporary case folder for solver runs.
    
    This writes the in-memory project to a temporary directory:
    - request.json
    - mesh.npz
    - out/ (if results exist)
    
    Args:
        project: Project data to materialize
    
    Returns:
        Path to temporary directory
    
    Notes:
        - Caller is responsible for cleanup
        - Directory is created with prefix "geohpem_case_"
    """

def update_project_from_workdir(project: ProjectData, case_dir: Path) -> ProjectData:
    """
    Pull back results from working directory after solver run.
    
    Args:
        project: Original project
        case_dir: Working directory with potential out/ results
    
    Returns:
        New ProjectData with updated results (if out/ exists)
    """
```

### Template Functions (`templates.py`)

```python
def new_empty_project(
    *,
    mode: str = "plane_strain",
    unit_system: dict[str, str] | None = None,
) -> ProjectData:
    """
    Create a new empty project.
    
    Args:
        mode: "plane_strain" or "axisymmetric"
        unit_system: Custom units (default: kN, m, s, kPa)
    
    Returns:
        ProjectData with empty mesh and single default stage
    """

def new_sample_project(
    *,
    mode: str = "plane_strain",
    unit_system: dict[str, str] | None = None,
) -> ProjectData:
    """
    Create a sample project with a unit square mesh.
    
    Args:
        mode: "plane_strain" or "axisymmetric"
        unit_system: Custom units
    
    Returns:
        ProjectData with:
        - 4 points forming unit square
        - 2 triangles
        - Example material, assignment, and BC
        - Node/edge/element sets
    """
```

### Normalization Functions (`normalize.py`)

```python
def ensure_request_ids(request: dict[str, Any], mesh: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Ensure stable IDs exist for project entities.
    
    Adds/ensures:
        - stages[*].uid
        - materials[*].uid
        - geometry polygon vertex_ids/edge_ids
        - sets_meta[*].uid (for NPZ set keys)
    
    Args:
        request: Request dict (modified in-place)
        mesh: Optional mesh dict (for set key discovery)
    
    Returns:
        The (possibly modified) request dict
    """

def find_stage_index_by_uid(request: dict[str, Any], uid: str) -> int | None:
    """
    Find stage index by its stable UID.
    
    Args:
        request: Request dict
        uid: Stage UID to find
    
    Returns:
        Stage index (0-based) or None if not found
    """
```

### Migration Functions (`migrations/`)

```python
def migrate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Migrate manifest to current version."""

def migrate_request(request: dict[str, Any]) -> dict[str, Any]:
    """Migrate request to current version."""

def migrate_result(result: dict[str, Any]) -> dict[str, Any]:
    """Migrate result to current version."""
```

---

## Usage Examples

### Creating and Saving a New Project

```python
from pathlib import Path
from geohpem.project.templates import new_sample_project
from geohpem.project.package import save_geohpem

# Create sample project
project = new_sample_project(mode="plane_strain")

# Save to file
saved_path = save_geohpem("my_project", project)
print(f"Saved to: {saved_path}")  # my_project.geohpem
```

### Loading a Project

```python
from geohpem.project.package import load_geohpem

project = load_geohpem("my_project.geohpem")

print(f"Mode: {project.request['model']['mode']}")
print(f"Stages: {len(project.request['stages'])}")
print(f"Has results: {project.result_meta is not None}")
```

### Loading from Case Folder

```python
from geohpem.project.case_folder import load_case_folder

project = load_case_folder("examples/case_cli_test")
```

### Running Solver with Working Directory

```python
from geohpem.project.workdir import materialize_to_workdir, update_project_from_workdir
from geohpem.app.run_case import run_case

# Materialize to temp directory
workdir = materialize_to_workdir(project)

# Run solver
run_case(str(workdir), solver_selector="fake")

# Pull back results
project = update_project_from_workdir(project, workdir)
```

### Ensuring IDs Before Operations

```python
from geohpem.project.normalize import ensure_request_ids, find_stage_index_by_uid

# Ensure all entities have stable IDs
ensure_request_ids(request, mesh)

# Find stage by UID
stage_uid = request["stages"][0]["uid"]
idx = find_stage_index_by_uid(request, stage_uid)
print(f"Stage UID {stage_uid} is at index {idx}")
```

---

## Design Notes

### Why Stable IDs?

Stage and material indices can change (e.g., when deleting a stage). Stable UIDs allow:
- Reliable selection tracking across edits
- Undo/redo without index confusion
- Cross-references that survive reordering

### Why Temporary Working Directory?

1. **Isolation**: Solver operates on a clean snapshot
2. **File-Based I/O**: Some solvers expect files, not in-memory data
3. **Atomic Updates**: Results can be pulled back atomically
4. **Debugging**: Easy to inspect what was sent to solver

### Why ZIP for .geohpem?

1. **Portability**: Single file, easy to share
2. **Inspection**: Users can unzip to view/edit manually
3. **Compression**: Efficient storage for large meshes
4. **Versioning**: Manifest tracks format version for migrations

---

Last updated: 2024-12-18

