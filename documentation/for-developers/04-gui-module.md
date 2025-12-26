# GUI Module

The `gui` module implements the graphical user interface using PySide6 (Qt 6). It follows a model-view pattern with reactive state management via Qt signals.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Architecture](#architecture)
4. [Components](#components)
5. [State Management](#state-management)
6. [Workspaces](#workspaces)
7. [Extending the GUI](#extending-the-gui)

---

## Overview

The GUI is built with:
- **PySide6**: Qt 6 bindings for Python
- **PyVista/VTK**: 3D visualization (results display)
- **Qt Signals**: Reactive state propagation

Key design principles:
- **MainWindow as Mediator**: Coordinates all UI components
- **Model-View Separation**: State in `ProjectModel`, display in widgets
- **Workspace Pattern**: Input/Output views for different tasks

---

## Module Structure

```
gui/
├── __init__.py
├── app.py                    # Application entry point
├── main_window.py            # Main window (central orchestrator)
├── settings.py               # Persistent settings storage
├── model/                    # State management
│   ├── project_model.py      # Project state with signals
│   ├── selection_model.py    # Selection tracking
│   └── undo_stack.py         # Undo/redo support
├── workspaces/               # Main content areas
│   ├── workspace_stack.py    # Workspace switching
│   ├── input_workspace.py    # Editing view
│   └── output_workspace.py   # Results visualization
├── widgets/                  # Reusable widgets
│   └── docks/                # Dock panels
│       ├── geometry_dock.py  # Geometry tree
│       ├── log_dock.py       # Log output
│       ├── project_dock.py   # Project tree
│       ├── properties_dock.py# Property editor
│       ├── stage_dock.py     # Stage list
│       └── tasks_dock.py     # Running tasks
├── dialogs/                      # Modal dialogs
│   ├── import_mesh_dialog.py     # Mesh import
│   ├── mesh_quality_dialog.py    # Quality statistics
│   ├── precheck_dialog.py        # Pre-run validation
│   ├── sets_dialog.py            # Set management
│   └── material_catalog_dialog.py # Material catalog editor
├── widgets/                  # Reusable widgets
│   ├── json_editor.py        # JSON editor widget (tree + raw)
│   └── ...
└── workers/                  # Background tasks
    └── solve_worker.py       # Solver execution
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              MainWindow                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                          Menu Bar                                    ││
│  │  File | Edit | Mesh | Workspace | Solve | Help                      ││
│  └─────────────────────────────────────────────────────────────────────┘│
│  ┌──────────────┐ ┌───────────────────────────────┐ ┌──────────────────┐│
│  │ ProjectDock  │ │                               │ │ PropertiesDock   ││
│  │ ------------ │ │      WorkspaceStack           │ │ --------------- ││
│  │ Project Tree │ │                               │ │ Property Editor  ││
│  ├──────────────┤ │  ┌─────────────────────────┐  │ ├──────────────────┤│
│  │ GeometryDock │ │  │   InputWorkspace        │  │ │    StageDock     ││
│  │ ------------ │ │  │   or                    │  │ │ --------------- ││
│  │ Geometry Tree│ │  │   OutputWorkspace       │  │ │   Stage List     ││
│  │              │ │  │   (PyVista viewer)      │  │ │                  ││
│  │              │ │  │                         │  │ │                  ││
│  └──────────────┘ │  └─────────────────────────┘  │ └──────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  LogDock  |  TasksDock                                              ││
│  │  ---------------------------------------------------------------    ││
│  │  Log messages / Running tasks                                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          State Layer                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │  ProjectModel   │  │SelectionModel│  │       UndoStack             │ │
│  │  (signals)      │  │  (signals)   │  │  (commands)                 │ │
│  └─────────────────┘  └──────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Application Entry (`app.py`)

```python
def run_gui(open_case_dir: str | None = None) -> int:
    """
    Launch the GUI application.
    
    Args:
        open_case_dir: Optional path to open on startup
    
    Returns:
        Exit code from Qt event loop
    """
```

Key responsibilities:
- Create `QApplication`
- Install exception hook for error dialogs
- Create and show `MainWindow`
- Handle session restoration
- Run Qt event loop

### Main Window (`main_window.py`)

The `MainWindow` class is the central orchestrator:

```python
class MainWindow:
    def __init__(self) -> None:
        # Create Qt window
        self._win = QMainWindow()
        
        # Central widget: workspace stack
        self.workspace_stack = WorkspaceStack()
        
        # Dock widgets
        self.project_dock = ProjectDock()
        self.geometry_dock = GeometryDock()
        self.properties_dock = PropertiesDock()
        self.stage_dock = StageDock()
        self.log_dock = LogDock()
        self.tasks_dock = TasksDock()
        
        # State management
        self.model = ProjectModel()
        self.selection = SelectionModel()
        
        # ... menus, actions, signal connections ...
```

**Key Methods**:

| Method | Description |
|--------|-------------|
| `open_project_file(path)` | Load .geohpem file |
| `open_case_folder(path)` | Load case folder |
| `save_project(path)` | Save to .geohpem |
| `open_output_folder(path)` | Display results |
| `show()` | Show the window |
| `_shutdown_before_close()` | Clean up VTK/workers before exit |
| `_suggest_material_id()` | Generate unique material ID (mat_1, mat_2, ...) |
| `_on_add_material(preferred_id)` | Show dialog to add new material |
| `_on_delete_material(material_id)` | Show dialog to delete material |
| `_on_project_context_menu(pos)` | Handle ProjectDock tree context menu |

**Menu Structure**:

| Menu | Actions |
|------|---------|
| File | New, Open, Save, Save As, Recent Projects, Exit |
| Edit | Undo, Redo |
| Mesh | Import Mesh, Mesh Quality, Manage Sets |
| View | Display Units... |
| **Tools** | **Material Catalog..., Batch Run..., Compare Outputs...** |
| Solve | Select Solver..., Run |
| Workspace | Switch Input/Output |
| Help | About |

**Solver Capabilities Management**:

```python
# Cached solver capabilities by selector
_solver_caps_cache: dict[str, dict[str, Any]] = {}

def _get_solver_caps(selector: str) -> dict[str, Any]:
    """Load and cache solver capabilities."""

def _apply_solver_capabilities(caps: dict[str, Any] | None) -> None:
    """Propagate capabilities to PropertiesDock."""
```

On startup and when solver is changed:
1. Load solver capabilities via `load_solver(selector).capabilities()`
2. Cache result in `_solver_caps_cache`
3. Pass to `properties_dock.set_solver_capabilities(caps)`
4. Pass to `precheck_request_mesh(..., capabilities=caps)` before runs

**Signal Connections**:

```python
# Model changes update UI
self.model.changed.connect(self._on_model_changed)
self.model.stages_changed.connect(lambda stages: self.stage_dock.set_stages(stages))
self.model.request_changed.connect(self._refresh_tree)

# Selection changes update properties
self.selection.changed.connect(self._on_selection_changed)

# Dock actions
self.stage_dock.stage_selected.connect(self._on_stage_selected)
self.properties_dock.bind_apply_stage(self._apply_stage)
```

### Settings (`settings.py`)

Persists user preferences using Qt's `QSettings`:

```python
class SettingsStore:
    # Session
    def get_last_project(self) -> Path | None: ...
    def set_last_project(self, path: Path) -> None: ...
    def get_recent_projects(self) -> list[Path]: ...
    def add_recent_project(self, path: Path) -> None: ...
    
    # Display preferences
    def get_display_units(self) -> dict[str, str]: ...
    def set_display_units(self, units: dict[str, str]) -> None: ...
    
    # Solver preferences
    def get_solver_selector(self) -> str: ...  # Returns "fake" or "python:<module>"
    def set_solver_selector(self, selector: str) -> None: ...
```

---

## State Management

### ProjectModel (`model/project_model.py`)

Holds the authoritative in-memory project state:

```python
class ProjectModel:
    """
    Signals:
        changed(ProjectState)      - Any state change
        request_changed(dict)      - Request modified
        mesh_changed(dict)         - Mesh modified
        stages_changed(list)       - Stages list changed
        materials_changed(dict)    - Materials changed
        undo_state_changed(bool, bool) - Undo/redo availability
    """
    
    def state(self) -> ProjectState:
        """Get current state snapshot."""
    
    def set_project(self, project, *, display_path, project_file, work_case_dir, dirty):
        """Set the entire project (clears undo stack)."""
    
    def update_stage(self, index, patch):
        """Update a stage (with undo support)."""
    
    def add_stage(self, *, copy_from=None) -> int:
        """Add a new stage."""
    
    def delete_stage(self, index):
        """Delete a stage."""
    
    def set_material(self, material_id, model_name, parameters):
        """Add or update a material."""
    
    def update_mesh(self, new_mesh):
        """Replace the mesh."""
    
    def undo(self) / def redo(self):
        """Undo/redo operations."""
```

**ProjectState**:

```python
@dataclass(slots=True)
class ProjectState:
    display_path: Path | None      # Shown in title bar
    project_file: Path | None      # .geohpem file path
    work_case_dir: Path | None     # Temp working directory
    dirty: bool                    # Has unsaved changes
    project: ProjectData | None    # The actual data
```

### SelectionModel (`model/selection_model.py`)

Tracks current selection:

```python
@dataclass(frozen=True, slots=True)
class Selection:
    kind: str              # "stage", "material", "model", "set", etc.
    ref: dict[str, Any]    # Reference data (e.g., {"uid": "...", "type": "stage"})

class SelectionModel:
    """
    Signals:
        changed(Selection | None) - Selection changed
    """
    
    def set(self, selection: Selection | None) -> None: ...
    def get(self) -> Selection | None: ...
```

### UndoStack (`model/undo_stack.py`)

Generic undo/redo support with **command merging**:

```python
@dataclass(frozen=True, slots=True)
class UndoCommand:
    name: str
    undo: Callable[[], None]
    redo: Callable[[], None]
    merge_key: str | None = None  # For coalescing consecutive commands
    timestamp: float = 0.0        # For merge window checking

class UndoStack:
    def push_and_redo(self, cmd: UndoCommand, *, 
                      merge_key: str | None = None, 
                      merge_window_s: float = 0.75) -> None:
        """
        Push and execute a command.
        If merge_key matches previous command and within merge_window_s,
        coalesce into single undo step (keeps old undo, uses new redo).
        """
    def undo(self) -> None: ...
    def redo(self) -> None: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def clear(self) -> None: ...
```

**Merge Behavior**: When a user rapidly edits the same field (e.g., typing in a text field), consecutive commands with the same `merge_key` within `merge_window_s` (default 0.75s) are merged into a single undo step. The merged command keeps the original `undo` (to restore initial state) but uses the latest `redo`.

---

## Workspaces

### WorkspaceStack (`workspaces/workspace_stack.py`)

Manages switching between Input and Output views:

```python
class WorkspaceStack:
    def __init__(self) -> None:
        self._workspaces = {
            "input": InputWorkspace(),
            "output": OutputWorkspace(),
        }
    
    def set_workspace(self, name: str) -> None:
        """Switch to workspace by name ("input" or "output")."""
    
    def get(self, name: str):
        """Get workspace instance."""
```

### InputWorkspace (`workspaces/input_workspace.py`)

Comprehensive input editing workspace with mesh preview and selection tools:

```python
class InputWorkspace:
    # Signals for MainWindow integration
    new_project_requested = Signal()
    open_project_requested = Signal()
    open_case_requested = Signal()
    import_mesh_requested = Signal()
    validate_requested = Signal()
    run_requested = Signal()
    switch_output_requested = Signal()
    create_set_requested = Signal(object)  # payload dict
```

**Dashboard (Left Panel)**:
- **Status**: Project name, solver, dirty state
- **Quick Actions**: New, Open Project, Open Case, Import Mesh, Validate (F7), Run, Go to Output
- **Workflow Checklist**: Step-by-step guidance for users
- **Tips**: Best practices for modeling workflow

**Mesh Preview (Right Panel)**:
- PyVista-based 3D/2D mesh visualization
- **Highlight set dropdown**: Select node/edge/element set to highlight
- **Fit button**: Reset camera to mesh extents

**Selection System**:
- **Pick node**: Left-click to select single node (shows ID, coordinates, set membership)
- **Pick cell**: Click cell to select element (shows type, local ID, set membership)
- **Box nodes**: Rectangle selection for multiple nodes
- **Box elems**: Rectangle selection for multiple elements
- **Brush mode**: Keep box selection active for repeated drags
- **Replace mode**: Clear previous selection when boxing

**Selection Actions**:
- **Add picked node**: Add last clicked node to selection
- **Add edge (last 2 picks)**: Create edge from two consecutive picks
- **Add picked cell**: Add last clicked cell to selection
- **Clear**: Clear all selections

**Set Creation**:
- **Create node set...**: Prompt for name, emit `create_set_requested`
- **Create edge set...**: Prompt for name, emit `create_set_requested`
- **Create elem set...**: Prompt for name, emit `create_set_requested`

**Boundary Selection Tools**:
- **Polyline**: Interactive boundary edge selection
  - Click boundary nodes to build a polyline
  - Automatically finds shortest path along boundary between consecutive picks
  - Snaps clicks to nearest boundary node (within tolerance)
  - Finish/Clear buttons to complete or cancel
- **Component from pick**: Extract entire boundary connected component
  - Selects all boundary edges reachable from last picked node
  - Uses BFS traversal of boundary graph
- **Auto boundary** (context menu): Quick selection by position
  - Bottom/Top/Left/Right/All boundary edges
  - Uses `classify_boundary_edges()` from `domain.boundary_ops`

**Selection Modes**:
- **Replace**: Clear selection before adding new items
- **Subtract**: Remove items from current selection (mutually exclusive with Replace)
- **Brush**: Keep box selection active for repeated drags

**Selection Inversion** (context menu):
- **Invert nodes**: Select all nodes not currently selected
- **Invert edges**: Select all edges not currently selected
- **Invert elements**: Select all elements not currently selected

**Context Menu** (right-click in preview):
- Fit view
- Selection mode toggles (Replace, Subtract, Brush)
- Clear selection (C)
- Invert selections
- Box nodes (B) / Box elems (Shift+B)
- Polyline mode
- Component extraction
- Auto boundary selection
- Create set from selection

**Internal State**:
```python
_sel_nodes: set[int]                    # Selected node IDs
_sel_edges: set[tuple[int, int]]        # Selected edges as node pairs
_sel_elems: dict[str, set[int]]         # {cell_type: {local_ids}}
_box_mode: str | None                   # None | "node" | "cell"
_polyline_active: bool                  # Polyline mode active
_polyline_nodes: list[int]              # Current polyline node sequence
_last_probe_pid: int | None             # Last clicked node ID
_last_probe_xy: tuple[float, float] | None  # Last clicked coordinates
_last_cell: tuple[str, int] | None      # (cell_type, local_id)
_last_probe_pid_history: list[int]      # Last 2 picks for edge creation
_boundary_edges: np.ndarray | None      # Cached boundary edges
_boundary_adj: dict[int, list[int]] | None  # Boundary adjacency graph
_boundary_nodes: np.ndarray | None      # Cached boundary node IDs
_boundary_nodes_xy: np.ndarray | None   # Cached boundary node coordinates
_bbox_diag: float | None                # Bounding box diagonal (for snap tolerance)
```

**Boundary Graph**: Built on-demand using `domain.boundary_ops.compute_boundary_edges()` to enable:
- Polyline shortest-path routing
- Component extraction via BFS
- Snap-to-boundary for near-boundary clicks

**2D View**: Uses `viz/vtk_interaction.py` for 2D-only interaction (no rotation).

### OutputWorkspace (`workspaces/output_workspace.py`)

Result visualization using PyVista:

```python
class OutputWorkspace:
    def set_result(self, meta, arrays, mesh=None):
        """Display solver results with cloud map visualization."""
    
    def shutdown(self) -> None:
        """Clean up VTK/Qt resources before app exit (avoids OpenGL errors on Windows)."""
```

**Controls**:
- **Registry list**: Select field to display (u, p, stress, etc.)
- **Step spinner**: Navigate through time steps
- **Field mode**: Auto or magnitude for vectors
- **Warp checkbox**: Deform mesh by displacement
- **Warp scale**: Amplification factor
- **Reset view**: Reset camera

**Probing Features**:
- **Point probe** (left-click): Shows node ID, coordinates, field value, and node set membership
- **Cell probe**: Shows cell ID, cell type, local element ID, and element set membership

**Lifecycle**:
- `shutdown()` is called by `MainWindow._shutdown_before_close()` before Qt window closes
- Properly disposes VTK plotter to avoid OpenGL context errors

**Post-Processing Features**:
- **Profile Line**: Extract field values along a user-defined line segment
  - Dialog to set start/end coordinates or "Use last two picks"
  - Configurable sample count
  - Optional line overlay in viewport
  - Opens `PlotDialog` with distance vs value plot
- **Time History**: Track field value at a single node/element across all steps
  - Requires prior point/cell pick to select location
  - Auto-maps step IDs to time values when available
  - Opens `PlotDialog` with time/step vs value plot
- **Export Image**: Screenshot current viewport to PNG
- **Export Steps -> PNG**: Batch export all steps as numbered PNG files

**Profile Management** (persistent):
- **Profile List**: Named profile lines stored in project
- **Pick 2 Points**: Interactive viewport picking to create profiles
- **Plot Selected**: Re-plot any saved profile
- **Edit Selected (drag)**: Drag profile endpoints in viewport
- **Remove Selected**: Delete profile from project

**Pin Management** (persistent):
- **Pin List**: Saved probe locations (nodes/elements)
- **Pin Last Probe (node)**: Save last clicked node as pin
- **Pin Last Cell (element)**: Save last clicked cell as pin
- **Remove Pin**: Delete pin from project

**UI State Persistence**:
```python
def set_ui_state(self, ui_state: dict[str, Any]) -> None:
    """Load per-project UI state (profiles/pins) from ProjectData.ui_state."""

def get_ui_state(self) -> dict[str, Any]:
    """Return JSON-serializable UI state for ProjectData.ui_state."""
```

Stored structure:
```json
{
  "output": {
    "profiles": [{"uid": "...", "name": "...", "p1": [x,y,z], "p2": [x,y,z], "reg": {...}, "step_id": 1}],
    "pins": [{"uid": "...", "kind": "node|element", "pid": 0, "cell_id": 0, "cell_type": "tri3", "local_id": 0, "label": "..."}]
  }
}
```

**Internal State**:
```python
_probe_history: list[dict]     # Last 10 probe picks (x, y, z, pid)
_last_probe_pid: int | None    # Last picked point ID (for time history)
_last_cell_id: int | None      # Last picked cell ID (for element history)
_last_probe_xyz: tuple | None  # Last picked coordinates
_last_cell_info: dict | None   # Last picked cell details
_profiles: list[dict]          # Saved profile lines
_pins: list[dict]              # Saved probe pins
_mode: str                     # "normal" | "profile_pick" | "profile_edit"
```

**Profile Editing** (persistent):
- **Edit Selected (drag)**: Drag profile endpoints in viewport
- Endpoints visualized as draggable widgets
- Auto-updates profile path when endpoints change
- Finish/Cancel buttons to complete or abort editing

**Pin Overlays**:
- Visual markers in viewport showing saved pin locations
- Different colors for node vs element pins
- Click pin markers to select/view pin details

**Shift+Click Cell Picking**:
- Hold Shift and left-click to pick cells directly
- Installs custom event filter for Shift+click detection
- Updates last picked cell for pin creation

**Context Menu** (right-click in viewer):
- Fit view
- Export image
- Profile management actions
- Pin management actions

**2D View Interaction**:
Uses `viz/vtk_interaction.py` to configure VTK for 2D-only interaction:
- No 3D rotation
- Middle mouse = pan
- Mouse wheel = zoom
- Left mouse = picking (no camera interaction)
- Right mouse = reserved for context menu
- Adds `_parent` weakref for PyVista compatibility

**Set Membership Tracking**:
```python
# Internal data structures for set lookup
_node_set_membership: dict[int, list[str]]  # node_id -> set names
_elem_set_membership: dict[str, dict[int, list[str]]]  # cell_type -> local_id -> set names
```

**Unit Support**:
- `set_unit_context(units)`: Set UnitContext for display conversion
- Scalar bar shows values in display units with unit label
- Probe readout converts coordinates to display units
- Result values (displacement, pressure) converted based on registry unit info

---

## Widget Editors

### AssignmentsEditor (`widgets/assignments_editor.py`)

Table editor for `request.assignments` (material mapping):

```python
@dataclass(frozen=True, slots=True)
class AssignmentOptions:
    element_sets: list[tuple[str, str]]  # (name, cell_type)
    materials: list[str]

class AssignmentsEditor:
    """
    Columns: uid, element_set, cell_type, material_id, extra(json)
    Features:
    - Dropdown combos populated from AssignmentOptions
    - Preserves unknown fields via 'extra' column
    - Table/JSON tabs with sync button
    """
    def set_options(self, options: AssignmentOptions) -> None: ...
    def set_assignments(self, assignments: list[dict]) -> None: ...
    def assignments(self) -> list[dict]: ...
```

### OutputRequestsEditor (`widgets/output_requests_editor.py`)

Table editor for `stage.output_requests` or global `request.output_requests`:

```python
@dataclass(frozen=True, slots=True)
class OutputRequestOptions:
    names: list[str]  # Available output field names from solver capabilities

class OutputRequestsEditor:
    """
    Columns: uid, name, location (node/element/ip), every_n, extra(json)
    Features:
    - Name dropdown populated from solver capabilities
    - Location dropdown: node, element, ip
    - Spinbox for every_n
    - Table/JSON tabs with sync button
    """
    def set_options(self, options: OutputRequestOptions) -> None: ...
    def set_requests(self, items: list[dict]) -> None: ...
    def requests(self) -> list[dict]: ...
```

### StageItemTableEditor (`widgets/stage_table_editor.py`)

Generic table editor for `stage.bcs` or `stage.loads`:

```python
@dataclass(frozen=True, slots=True)
class StageItemTableConfig:
    kind: str        # "bc" | "load"
    uid_prefix: str  # "bc" | "load"
    title: str
    default_field: str
    default_type: str

class StageItemTableEditor:
    """
    Columns: uid, field, type, set (dropdown), value (JSON)
    Features:
    - Set name dropdown populated from mesh sets
    - Preserves unknown fields
    - Table/JSON tabs with sync button
    """
    def set_set_options(self, names: list[str]) -> None: ...
    def set_items(self, items: list[dict]) -> None: ...
    def items(self) -> list[dict]: ...
```

---

## Dock Widgets

### ProjectDock (`widgets/docks/project_dock.py`)

Tree view of project structure with context menu support:
- Model settings
- Materials (with context menu: Add/Delete)
- Mesh info
- Sets (node/edge/element)
- Stages

**Signals**:
- `case_open_requested(Path)`: User wants to open a case
- `output_open_requested(Path)`: User wants to open results
- `selection_changed(dict)`: Tree selection changed

**Context Menu** (right-click on Materials or individual Material items):
- **Materials folder**: "Add material..." - Opens dialog to create new material
- **Material item**: "Delete material..." - Removes material with confirmation

The context menu is handled by `MainWindow._on_project_context_menu()`, which connects to the tree's `customContextMenuRequested` signal.

### PropertiesDock (`widgets/docks/properties_dock.py`)

Context-sensitive property editor with solver capabilities awareness:

**Pages**:
- Model properties (mode, gravity)
- Stage properties (type, steps, output requests, BCs, loads)
- Material properties (model, parameters) - **Enhanced with material catalog integration**
- Assignments (element set → material mapping)
- Global output requests

**Material Editor Enhancements**:
- **Model Combo Box**: Populated from material catalog (`all_models()`)
- **Behavior Display**: Shows behavior label from catalog
- **Parameter Editor**: Tree + JSON dual-view (using `JsonEditorWidget`)
- **Default Values**: Loads defaults from catalog when model changes
- **Parameter Metadata**: Shows labels and tooltips from catalog `meta`
- **Solver Mapping**: (Visible in catalog dialog, used by solver adapters)

**Solver Capabilities Integration**:
```python
def set_solver_capabilities(caps: dict[str, Any] | None) -> None:
    """Update UI based on solver capabilities."""
```

- Disables unsupported modes in model combo box (based on `capabilities.modes`)
- Disables unsupported analysis types in stage combo box (based on `capabilities.analysis_types`)
- Shows amber-colored warnings when current values are not supported
- Validates output request names against `capabilities.results/fields`
- "Add..." button for output requests opens `OutputRequestDialog` pre-populated with valid options

### StageDock (`widgets/docks/stage_dock.py`)

Stage management:
- Stage list with selection
- Add/Copy/Delete buttons

**Signals**:
- `stage_selected(uid)`: Stage selected
- `add_stage()`: Add button clicked
- `copy_stage(uid)`: Copy button clicked
- `delete_stage(uid)`: Delete button clicked

### LogDock (`widgets/docks/log_dock.py`)

Log message display with thread-safe signal handling:
- `append_info(msg)`: Add info message
- `attach_worker(worker)`: Connect to worker log signals via QObject slots

**Thread Safety**: Uses internal `_Slots` QObject to ensure UI updates happen in GUI thread.

### TasksDock (`widgets/docks/tasks_dock.py`)

Running task display with cancellation support:
- Progress bar with percentage
- Status label (Idle, Running, Failed, Canceled)
- "Cancel" button (enabled when worker is running)
- `attach_worker(worker)`: Connect to worker signals via QObject slots

**Thread Safety**: Uses internal `_Slots` QObject to ensure UI updates happen in GUI thread.

**Cancellation Flow**:
1. User clicks "Cancel" button
2. `TasksDock` calls `worker.cancel()`
3. Status label shows "Cancel requested..."
4. Worker detects cancellation via `should_cancel()` callback and stops

### MaterialCatalogDialog (`dialogs/material_catalog_dialog.py`)

Material catalog management dialog for editing user-defined material models.

**Features**:
- Model list with filter/search
- Tree + JSON dual-view editor (using `JsonEditorWidget`)
- Copy, Rename, Delete, Reset model operations
- Visual status indicators (Default, Modified, User-defined)
- Automatic backup before saving user catalog

**Layout**:
- Left: Model list with filter and action buttons
- Right: Model definition editor (Definition, Parameters, Metadata, Solver Mapping tabs)

**Operations**:
- **Copy**: Duplicate a model with a new name
- **Rename**: Change model name (with validation)
- **Delete**: Remove user-defined model (can't delete defaults)
- **Reset Model**: Revert user model to default catalog values

**Integration**:
- Opens from **Tools → Material Catalog...** menu
- After saving, catalog is reloaded and PropertiesDock material editors are refreshed

---

### JsonEditorWidget (`widgets/json_editor.py`)

Dual-view JSON editor widget with tree and raw JSON tabs.

**Features**:
- **Tree View**: Hierarchical editing with inline value editing
- **JSON View**: Raw JSON text editing with syntax highlighting
- Support for both object (`{}`) and array (`[]`) roots
- Add/delete items via toolbar buttons
- Bidirectional sync between tree and JSON views
- Auto-parsing of JSON values (numbers, booleans, arrays, objects)

**Toolbar Actions**:
- **Add group**: Add nested object
- **Add parameter**: Add key-value pair
- **Delete**: Remove selected item
- **JSON -> Tree**: Parse JSON text and update tree view

**Usage**:
Used by `MaterialCatalogDialog` and `PropertiesDock` for editing material parameters and catalog definitions.

**Tree Interaction**:
- Double-click or press F2 to edit values
- Supports JSON value parsing (e.g., `"123"` → `123`, `"true"` → `true`)
- Falls back to string if parsing fails

---

### GeometryDock (`widgets/docks/geometry_dock.py`)

Interactive polygon geometry editor with visual feedback:

**Features**:
- Visual display of polygon vertices and edges
- Draggable vertices for interactive editing
- Selection support for vertices and edges
- Visual highlighting of selected items (red color, thicker stroke)
- Info panel showing selected item details (UID, coordinates, edge labels)

**Selection State**:
```python
_selected: tuple[str, int] | None  # ("vertex"/"edge", index) or None
```

**Interaction**:
- Click vertex/edge to select
- Drag vertex to move it
- Selection shows UID and coordinates in info panel

**Methods**:
- `bind_model(model)`: Connect to ProjectModel for geometry updates
- `set_unit_context(units)`: Set UnitContext for coordinate display conversion
- `_set_polygon(poly, push_to_model)`: Update displayed polygon
- `_select(sel)`: Set selection and update highlighting
- `_apply_selection_style()`: Update visual styles based on selection

**Unit Support**:
- Coordinates and vertex/edge info display in user-selected display units
- Mouse position readout converts from base to display units

---

## Dialogs

### ImportMeshDialog (`dialogs/import_mesh_dialog.py`)

Mesh file import:
- File selection
- Format detection (via meshio)
- Preview statistics
- Returns imported mesh

### MeshQualityDialog (`dialogs/mesh_quality_dialog.py`)

Mesh quality statistics:
- Triangle count
- Min angle statistics (min, p50, p95)
- Aspect ratio max

### PrecheckDialog (`dialogs/precheck_dialog.py`)

Pre-run validation:
- Displays errors/warnings/info from precheck
- Allows proceed or cancel

### SetsDialog (`dialogs/sets_dialog.py`)

Set management:
- View all sets (node/edge/element)
- Edit set labels
- Delete sets

### UnitsDialog (`dialogs/units_dialog.py`)

Display unit preferences:
- Select display units for length (mm, cm, m, km)
- Select display units for pressure (Pa, kPa, MPa, GPa)
- "Project" option uses the project's declared unit system
- Changes are persisted in user settings

```python
@dataclass(frozen=True, slots=True)
class UnitsDialogResult:
    display_units: dict[str, str]  # {"length": "mm", "pressure": "kPa", ...}
```

### SolverDialog (`dialogs/solver_dialog.py`)

Solver selection and configuration:
- Choose between built-in "fake" solver or external Python module
- Enter Python module path for external solvers
- "Check & Show Capabilities" button to test solver loading
- Displays solver capabilities JSON

```python
@dataclass(frozen=True, slots=True)
class SolverDialogResult:
    solver_selector: str  # "fake" or "python:<module>"
```

### OutputRequestDialog (`dialogs/output_request_dialog.py`)

Add output requests to a stage based on solver capabilities:
- Multi-select list of available output fields (from solver capabilities)
- Location selector (node/element)
- "Every N" setting for sampling frequency
- Auto-generates UIDs for new output requests

```python
@dataclass(frozen=True, slots=True)
class OutputRequestDialogResult:
    output_requests: list[dict[str, Any]]  # List of output request dicts with uid, name, location, every_n
```

### BatchRunDialog (`dialogs/batch_run_dialog.py`)

GUI dialog for batch running multiple case folders:
- Cases root folder selection
- Solver selector input
- Optional baseline root for comparison
- JSON report path configuration
- Progress bar and log display
- Cancel button for stopping batch run

Uses `BatchRunWorker` for background execution.

### CompareOutputsDialog (`dialogs/compare_outputs_dialog.py`)

Visual comparison tool for two sets of solver outputs:
- Open two output folders (A and B)
- View common fields (intersection)
- Step-by-step comparison with step slider
- View modes: Diff (A-B), A only, B only
- PyVista-based cloud map visualization
- Diff statistics: min, max, mean, L2, Linf
- Export step-curve CSV for selected field

Features:
- Auto-loads mesh from sibling `mesh.npz`
- Supports both output folders and case folders
- Uses coolwarm colormap for diff visualization

### BatchReportDialog (`dialogs/batch_report_dialog.py`)

Viewer for batch run JSON reports:
- Load and parse `batch_report.json`
- Filter by status: success, failed, canceled
- Summary stats: total, success, failed, canceled counts
- Table columns: case, status, error_code, elapsed_s, rss_start/end/delta_mb, max_linf, max_l2, out_dir, diagnostics, solver, error
- Actions: Open Case, Open Output, Open Diagnostics Zip, Copy Selected Paths
- Double-click row to open output folder
- Callbacks for opening case/output in main window

```python
@dataclass(frozen=True, slots=True)
class BatchReportRecord:
    case_dir: Path
    status: str                     # "success" | "failed" | "canceled"
    solver_selector: str
    elapsed_s: float | None
    rss_start_mb: float | None      # Memory usage tracking
    rss_end_mb: float | None
    out_dir: Path | None
    diagnostics_zip: Path | None
    error_code: str | None
    error: str | None
    compare_max_linf: float | None  # Baseline comparison metrics
    compare_max_l2: float | None

def parse_batch_report(path: Path) -> list[BatchReportRecord]: ...
```

### IssuesDialog (`dialogs/issues_dialog.py`)

Simple dialog for displaying validation issues:
- Shows summary: Errors, Warnings, Info counts
- List widget with severity-prefixed messages
- Single OK button

```python
class IssuesDialog:
    def __init__(self, parent, *, title: str, issues: Iterable[PrecheckIssue], ok_text: str = "OK"): ...
    def exec(self) -> bool: ...
```

### PlotDialog (`dialogs/plot_dialog.py`)

Matplotlib-based plot dialog for time history and profile line plots:
- Uses `FigureCanvasQTAgg` for Qt integration
- Navigation toolbar for pan/zoom
- Export CSV and PNG buttons
- Supports multiple series with legend

```python
@dataclass(frozen=True, slots=True)
class PlotSeries:
    x: np.ndarray
    y: np.ndarray
    label: str | None = None

class PlotDialog:
    def __init__(self, parent, *, title, xlabel, ylabel, series: list[PlotSeries], 
                 note: str | None = None, default_csv_name: str, default_png_name: str): ...
```

**Solver Selector Formats**:
- `"fake"`: Built-in fake solver for testing
- `"python:<module>"`: Load solver from Python module (e.g., `python:geohpem_solver`)

**UI Elements**:
- Solver type combo box (Fake / Python module)
- Module name text field (enabled only for Python module type)
- Capabilities display area (read-only, shows JSON from `solver.capabilities()`)

---

## Workers

### SolveWorker (`workers/solve_worker.py`)

Background solver execution with cancellation support and diagnostics:

```python
class SolveWorker(QThread):
    """
    Signals:
        started()                      - Worker started
        progress(int, str)             - Progress update (0-100, message)
        finished()                     - Solver completed (success or fail)
        output_ready(Path)             - Results available at path
        log(str)                       - Log message
        failed(str, Path|None)         - Error text + diagnostics ZIP path
        canceled(Path|None)            - Diagnostics ZIP path
    """
    
    def __init__(self, case_dir: Path, solver_selector: str): ...
    def start(self) -> None: ...
    def cancel(self) -> None:
        """Request cancellation (best-effort). Solver must respect callbacks['should_cancel']."""
```

**Cancellation Flow**:
1. UI calls `worker.cancel()`
2. Worker sets internal `_cancel` flag
3. Before solver starts, if `_cancel` is True, raises `CancelledError`
4. During solver run, `callbacks['should_cancel']()` returns True
5. Solver raises `CancelledError` or exits early
6. Worker catches `CancelledError` specifically and emits `canceled` signal with diagnostics ZIP

**Diagnostics on Failure**:
When the solver fails, SolveWorker automatically creates a diagnostics ZIP:
- Environment info (Python, platform)
- Solver capabilities
- Error message and traceback
- Recent log messages
- Case inputs and outputs

Usage:
```python
worker = SolveWorker(case_dir=workdir, solver_selector="fake")
self.tasks_dock.attach_worker(worker)
self.log_dock.attach_worker(worker)
worker.output_ready.connect(self.open_output_folder)
worker.failed.connect(self._on_solver_failed)
worker.canceled.connect(self._on_solver_canceled)
worker.start()
```

### BatchRunWorker (`workers/batch_run_worker.py`)

Background batch runner for multiple case folders:

```python
class BatchRunWorker:
    """
    Signals:
        started()                      - Worker started
        finished()                     - Worker finished
        progress(int, str)             - Progress (0-100, message)
        log(str)                       - Log message
        report_ready(Path)             - JSON report written
        failed(str)                    - Error message
    """
    
    def __init__(self, root: Path, *, solver_selector: str, 
                 baseline_root: Path | None, report_path: Path): ...
    def start(self) -> None: ...
    def cancel(self) -> None: ...
```

Used by `BatchRunDialog` for non-blocking batch execution.

---

## Extending the GUI

### Adding a New Dock Widget

1. Create widget class in `widgets/docks/`:

```python
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout

class MyDock:
    def __init__(self) -> None:
        self.dock = QDockWidget("My Dock")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # ... add controls ...
        self.dock.setWidget(widget)
```

2. Add to `MainWindow.__init__()`:

```python
self.my_dock = MyDock()
self._win.addDockWidget(Qt.RightDockWidgetArea, self.my_dock.dock)
```

### Adding a New Dialog

1. Create dialog class in `dialogs/`:

```python
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Dialog")
        layout = QVBoxLayout(self)
        # ... add controls ...
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
```

2. Open from `MainWindow`:

```python
def _on_my_action(self):
    dlg = MyDialog(self._win)
    if dlg.exec() == QDialog.Accepted:
        # ... handle result ...
```

### Adding a New Menu Action

```python
# In MainWindow.__init__()
self._action_my = QAction("My Action...", self._win)
self._action_my.triggered.connect(self._on_my_action)

# Add to menu
menu_edit.addAction(self._action_my)
```

---

Last updated: 2024-12-26 (v11 - material catalog system, JSON editor, catalog dialog)

