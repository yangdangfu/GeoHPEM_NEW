# Architecture Overview

This document describes the overall architecture of GeoHPEM, including its layered design, data flow, and key architectural decisions.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Layer Descriptions](#layer-descriptions)
3. [Data Flow](#data-flow)
4. [Key Data Structures](#key-data-structures)
5. [Entry Points](#entry-points)

---

## High-Level Architecture

GeoHPEM follows a **layered architecture** with clear separation between presentation, application logic, and data:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ MainWindow  │  │  Workspaces │  │   Dialogs & Widgets     │  │
│  │             │  │ Input/Output│  │ (Docks, Import, etc.)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                     State Management Layer                       │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  ProjectModel   │  │SelectionModel│  │    UndoStack      │   │
│  │ (request, mesh) │  │              │  │                   │   │
│  └─────────────────┘  └──────────────┘  └───────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                      Application Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  precheck   │  │  run_case   │  │   Project Package       │  │
│  │             │  │             │  │ (load/save .geohpem)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                       Contract Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   io.py     │  │ validate.py │  │     schemas/*.json      │  │
│  │ read/write  │  │             │  │ (request, result)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Mesh     │  │     Viz     │  │   Solver Adapter        │  │
│  │ (convert,   │  │ (VTK/PV)    │  │ (fake, python:module)   │  │
│  │  quality)   │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │       External Solvers         │
              │  (via SolverProtocol interface)│
              └───────────────────────────────┘
```

---

## Layer Descriptions

### 1. Presentation Layer (`gui/`)

The topmost layer handling all user interaction.

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `MainWindow` | `gui/main_window.py` | Central orchestrator: menus, docks, workspace switching |
| `WorkspaceStack` | `gui/workspaces/` | Manages Input/Output workspace views |
| `InputWorkspace` | `gui/workspaces/input_workspace.py` | Editing view (MVP placeholder) |
| `OutputWorkspace` | `gui/workspaces/output_workspace.py` | Result visualization with PyVista |
| Dock Widgets | `gui/widgets/docks/` | Project tree, properties, stages, log, tasks |
| Dialogs | `gui/dialogs/` | Modal dialogs for import, precheck, sets, etc. |

**Key Pattern**: The `MainWindow` acts as a **mediator** connecting UI components with the state management layer.

### 2. State Management Layer (`gui/model/`)

Manages application state with reactive signals.

| Component | Responsibility |
|-----------|----------------|
| `ProjectModel` | Holds in-memory project data (request, mesh), emits change signals |
| `SelectionModel` | Tracks current selection (stage, material, set) |
| `UndoStack` | Provides undo/redo capability for all edits |

**Key Pattern**: Uses Qt signals (`Signal`) for reactive state propagation.

```python
# Example: ProjectModel signal usage
self.model.changed.connect(self._on_model_changed)
self.model.stages_changed.connect(lambda stages: self.stage_dock.set_stages(stages))
```

### 3. Application Layer (`app/`, `project/`)

Core application logic independent of UI.

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `precheck` | `app/precheck.py` | Validates request+mesh before solver run |
| `run_case` | `app/run_case.py` | Orchestrates solver execution |
| `package` | `project/package.py` | Load/save `.geohpem` ZIP archives |
| `case_folder` | `project/case_folder.py` | Load case folders (request.json + mesh.npz) |
| `workdir` | `project/workdir.py` | Create temporary working directories |
| `templates` | `project/templates.py` | New project templates |
| `normalize` | `project/normalize.py` | Ensure stable IDs for entities |
| `migrations` | `project/migrations/` | Version migration for project files |

### 4. Contract Layer (`contract/`)

Defines the interface between GUI and solvers.

| Component | Responsibility |
|-----------|----------------|
| `types.py` | `SolverProtocol` interface definition |
| `io.py` | Read/write case folders and result folders |
| `validate.py` | Request validation |
| `errors.py` | `ContractError` exception |
| `schemas/` | JSON Schema files for request/result validation |

**Contract v0.1 Format**:
```
case_folder/
├── request.json   # Analysis configuration
├── mesh.npz       # Mesh arrays (points, cells_*, sets)
└── out/           # Results (after solver run)
    ├── result.json
    └── result.npz
```

### 5. Infrastructure Layer

Supporting services for mesh, visualization, and solver integration.

| Module | Responsibility |
|--------|----------------|
| `mesh/` | Mesh import (meshio), conversion, quality analysis |
| `viz/` | Contract mesh → PyVista conversion, result array extraction, cell type mapping |
| `solver_adapter/` | Solver loading, fake solver for testing |
| `geometry/` | 2D geometry primitives (Polygon2D) |
| `util/` | ID generation, logging configuration |

**Viz Module Key Functions** (`viz/vtk_convert.py`):
- `contract_mesh_to_pyvista(mesh)`: Convert Contract NPZ mesh to PyVista UnstructuredGrid
  - Adds `__cell_type_code` and `__cell_local_id` cell data for element tracking
- `cell_type_code_to_name(code)`: Map internal cell type code to Contract name (1→"tri3", 2→"quad4")
- `available_steps_from_arrays(arrays)`: Extract step IDs from result array keys
- `get_array_for(arrays, location, name, step)`: Retrieve specific result array
- `vector_magnitude(v)`: Compute magnitude of vector field

---

## Data Flow

### Project Loading Flow

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  User opens  │────►│ load_geohpem│────►│ validate &   │────►│ ProjectModel│
│  .geohpem    │     │ (unzip)     │     │ ensure_ids   │     │ .set_project│
└──────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                                                                     │
                     ┌─────────────┐     ┌──────────────┐            │
                     │ Dock widgets│◄────│ Signal emit  │◄───────────┘
                     │ update      │     │ (changed)    │
                     └─────────────┘     └──────────────┘
```

### Solver Run Flow

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ User clicks  │────►│  precheck   │────►│ write_case_  │────►│ SolveWorker │
│    "Run"     │     │ (validate)  │     │ folder       │     │  (QThread)  │
└──────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                                                                     │
                     ┌─────────────┐     ┌──────────────┐            │
                     │OutputWorkspace◄───│ load results │◄───────────┘
                     │ .set_result │     │              │
                     └─────────────┘     └──────────────┘
```

### State Change Flow

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ User edits   │────►│ ProjectModel│────►│ UndoCommand  │────►│   Signal    │
│ (e.g. stage) │     │ .update_*   │     │ pushed       │     │   emitted   │
└──────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                                                                     │
                     ┌─────────────┐                                 │
                     │ UI updated  │◄────────────────────────────────┘
                     │ (reactive)  │
                     └─────────────┘
```

---

## Key Data Structures

### ProjectData

```python
@dataclass(slots=True)
class ProjectData:
    request: dict[str, Any]           # Analysis configuration (JSON-serializable)
    mesh: dict[str, np.ndarray]       # Mesh arrays (points, cells, sets)
    result_meta: dict[str, Any] | None      # Result metadata (registry, status)
    result_arrays: dict[str, np.ndarray] | None  # Result arrays
    manifest: dict[str, Any] | None   # Package metadata (version, timestamps)
```

### Request JSON Structure

```json
{
  "schema_version": "0.1",
  "unit_system": {"force": "kN", "length": "m", "time": "s", "pressure": "kPa"},
  "model": {
    "dimension": 2,
    "mode": "plane_strain",  // or "axisymmetric"
    "gravity": [0.0, -9.81]
  },
  "materials": {
    "soil_1": {"model_name": "...", "parameters": {...}}
  },
  "assignments": [
    {"element_set": "soil", "cell_type": "tri3", "material_id": "soil_1"}
  ],
  "stages": [
    {
      "id": "stage_1",
      "uid": "...",  // stable internal ID
      "analysis_type": "static",
      "num_steps": 10,
      "bcs": [...],
      "loads": [...],
      "output_requests": [...]
    }
  ]
}
```

### Mesh NPZ Structure

```python
{
    "points": np.array([[x1,y1], [x2,y2], ...]),      # (N, 2) float
    "cells_tri3": np.array([[n1,n2,n3], ...]),       # (M, 3) int32
    "cells_quad4": np.array([[n1,n2,n3,n4], ...]),   # (K, 4) int32 (optional)
    "node_set__bottom": np.array([0, 1, 2]),         # int32
    "edge_set__left": np.array([[0,3], [3,6]]),      # (E, 2) int32
    "elem_set__soil__tri3": np.array([0, 1, 2, 3]),  # int32
}
```

---

## Entry Points

### CLI Entry (`cli.py`)

```
geohpem <command> [options]

Commands:
  about             Show version info
  gui               Launch the GUI
  run <case_dir>    Run solver on a case folder
  contract-example  Generate example contract files
```

### GUI Entry (`gui/app.py`)

```python
def run_gui(open_case_dir: str | None = None) -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # ... restore session or open specified case
    return app.exec()
```

### Module Entry (`__main__.py`)

```python
from geohpem.main import main
raise SystemExit(main())
```

---

## Architectural Decisions

### 1. Qt Signal-Based Reactivity

**Decision**: Use Qt signals for state propagation instead of manual callbacks.

**Rationale**: 
- Native Qt pattern, well-supported
- Automatic thread safety for cross-thread signals
- Clean decoupling between emitter and receiver

### 2. Contract-Based Solver Interface

**Decision**: Define a strict JSON/NPZ contract between GUI and solver.

**Rationale**:
- Solver can be developed independently
- Easy to test with fake solver
- Supports multiple solver backends (Python modules, external processes)

### 3. ZIP-Based Project Files

**Decision**: `.geohpem` files are ZIP archives containing JSON + NPZ.

**Rationale**:
- Self-contained, portable
- Human-inspectable (unzip to view/edit)
- Efficient storage with compression

### 4. Temporary Working Directory

**Decision**: Always materialize project to temp folder before solver run.

**Rationale**:
- Solver expects file-based I/O
- Isolates solver from in-memory state
- Easy cleanup after run

---

Last updated: 2024-12-18 (v2 - added viz module details)

