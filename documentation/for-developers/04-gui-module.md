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
├── dialogs/                  # Modal dialogs
│   ├── import_mesh_dialog.py # Mesh import
│   ├── mesh_quality_dialog.py# Quality statistics
│   ├── precheck_dialog.py    # Pre-run validation
│   └── sets_dialog.py        # Set management
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
    def get_last_project(self) -> Path | None: ...
    def set_last_project(self, path: Path) -> None: ...
    def get_recent_projects(self) -> list[Path]: ...
    def add_recent_project(self, path: Path) -> None: ...
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

Generic undo/redo support:

```python
@dataclass(frozen=True, slots=True)
class UndoCommand:
    name: str
    undo: Callable[[], None]
    redo: Callable[[], None]

class UndoStack:
    def push_and_redo(self, command: UndoCommand) -> None: ...
    def undo(self) -> None: ...
    def redo(self) -> None: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def clear(self) -> None: ...
```

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

Editing view for model setup:

```python
class InputWorkspace:
    """
    MVP placeholder - will contain:
    - Mesh visualization
    - Interactive editing tools
    - BC/Load visualization
    """
```

### OutputWorkspace (`workspaces/output_workspace.py`)

Result visualization using PyVista:

```python
class OutputWorkspace:
    def set_result(self, meta, arrays, mesh=None):
        """
        Display solver results.
        
        Features:
        - Registry list (available fields)
        - Step slider
        - Field mode (auto/magnitude)
        - Warp by displacement
        - Point probing
        """
```

**Controls**:
- **Registry list**: Select field to display (u, p, stress, etc.)
- **Step spinner**: Navigate through time steps
- **Field mode**: Auto or magnitude for vectors
- **Warp checkbox**: Deform mesh by displacement
- **Warp scale**: Amplification factor
- **Reset view**: Reset camera

---

## Dock Widgets

### ProjectDock (`widgets/docks/project_dock.py`)

Tree view of project structure:
- Model settings
- Materials
- Mesh info
- Sets (node/edge/element)
- Stages

**Signals**:
- `case_open_requested(Path)`: User wants to open a case
- `output_open_requested(Path)`: User wants to open results
- `selection_changed(dict)`: Tree selection changed

### PropertiesDock (`widgets/docks/properties_dock.py`)

Context-sensitive property editor:
- Model properties (mode, gravity)
- Stage properties (type, steps, BCs, loads)
- Material properties (model, parameters)

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

Log message display:
- `append_info(msg)`: Add info message
- `append_error(msg)`: Add error message
- `attach_worker(worker)`: Connect to worker log signals

### TasksDock (`widgets/docks/tasks_dock.py`)

Running task display:
- Progress bar
- Cancel button
- `attach_worker(worker)`: Connect to worker progress

### GeometryDock (`widgets/docks/geometry_dock.py`)

Geometry tree (when using polygon-based geometry definition).

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

---

## Workers

### SolveWorker (`workers/solve_worker.py`)

Background solver execution:

```python
class SolveWorker(QThread):
    """
    Signals:
        progress(float, str)  - Progress update (0-1, message)
        finished()            - Solver completed
        error(str)            - Error occurred
        output_ready(Path)    - Results available at path
        log(str)              - Log message
    """
    
    def __init__(self, case_dir: Path, solver_selector: str): ...
```

Usage:
```python
worker = SolveWorker(case_dir=workdir, solver_selector="fake")
self.tasks_dock.attach_worker(worker)
self.log_dock.attach_worker(worker)
worker.output_ready.connect(self.open_output_folder)
worker.start()
```

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

Last updated: 2024-12-18

