# GeoHPEM Developer Guide

Welcome to the GeoHPEM developer documentation. This guide provides comprehensive information for developers working on or extending the GeoHPEM project.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Overview](#project-overview)
3. [Documentation Index](#documentation-index)
4. [Development Workflow](#development-workflow)
5. [Code Style](#code-style)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Conda (recommended for environment management)

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd GeoHPEM_NEW

# Create conda environment
conda env create -f environment.yml
conda activate geohpem

# Install in development mode
pip install -e .
```

### Running the Application

```bash
# Launch GUI
python -m geohpem gui

# Or using CLI
geohpem gui

# Run with a specific case folder
geohpem gui --open path/to/case

# Run solver on a case folder
geohpem run path/to/case --solver fake
```

### Project Structure

```
src/geohpem/
├── __init__.py          # Version info
├── __main__.py          # Entry point for `python -m geohpem`
├── cli.py               # CLI parser (subcommands: about, gui, run, contract-example)
├── main.py              # Simple GUI launcher
├── app/                 # Application layer (precheck, run_case)
├── contract/            # Solver contract (I/O, validation, schemas)
├── domain/              # Domain models
├── geometry/            # Geometry primitives (polygon2d)
├── gui/                 # Qt GUI (PySide6)
│   ├── app.py           # Qt application entry
│   ├── main_window.py   # Main window controller
│   ├── model/           # State management (project, selection, undo)
│   ├── workspaces/      # Input/Output workspaces
│   ├── widgets/         # Dock widgets
│   ├── dialogs/         # Modal dialogs
│   └── workers/         # Background workers
├── mesh/                # Mesh I/O and quality
├── post/                # Post-processing (TBD)
├── project/             # Project file management (.geohpem, case folders)
├── solver_adapter/      # Solver loading and fake solver
├── util/                # Utilities (IDs, logging)
└── viz/                 # Visualization (VTK/PyVista conversion)
```

---

## Project Overview

GeoHPEM is a geotechnical simulation platform with the following key characteristics:

### Design Principles

1. **Separation of Concerns**: Clear boundaries between UI, business logic, and solver.
2. **Contract-Based Solver Interface**: Solvers communicate via a well-defined JSON/NPZ contract.
3. **Flexible Deployment**: Supports GUI, CLI, and headless modes.
4. **Undo/Redo Support**: All model changes are undoable.
5. **Project Portability**: `.geohpem` files are self-contained ZIP archives.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Project** | A complete simulation setup (request + mesh + results) |
| **Request** | JSON configuration (model, materials, stages, BCs, loads) |
| **Mesh** | NumPy arrays stored in NPZ format (points, cells, sets) |
| **Contract** | The interface specification between GUI and solver |
| **Stage** | A simulation phase with its own BCs, loads, and steps |
| **Workspace** | UI view mode (Input for editing, Output for results) |

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [01-architecture-overview.md](01-architecture-overview.md) | System architecture and data flow |
| [02-contract-module.md](02-contract-module.md) | Solver contract specification |
| [03-project-module.md](03-project-module.md) | Project file management |
| [04-gui-module.md](04-gui-module.md) | GUI architecture and components |
| [05-mesh-module.md](05-mesh-module.md) | Mesh handling and conversion |
| [06-solver-adapter-module.md](06-solver-adapter-module.md) | Solver loading and fake solver |
| [07-app-module.md](07-app-module.md) | Application layer services |

---

## Development Workflow

### Before Making Changes

1. **Check git status**: Review recent changes that might affect your work.
   ```bash
   git status
   git log --oneline -10
   ```

2. **Update documentation**: If your changes affect documented behavior, update the corresponding documentation files.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=geohpem
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/geohpem/
```

---

## Code Style

### General Guidelines

- Use `from __future__ import annotations` in all modules
- Prefer dataclasses for data containers
- Use type hints consistently
- Keep functions focused and small

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `project_model.py` |
| Classes | PascalCase | `ProjectModel` |
| Functions | snake_case | `load_geohpem()` |
| Constants | UPPER_SNAKE | `DEFAULT_EXT` |
| Private | _prefixed | `_clone_request()` |

### Import Order

```python
from __future__ import annotations

# Standard library
import json
from pathlib import Path
from typing import Any

# Third-party
import numpy as np
from PySide6.QtWidgets import QMainWindow

# Local
from geohpem.contract.io import read_case_folder
from geohpem.project.types import ProjectData
```

---

## Contributing

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Update documentation if needed
4. Submit a pull request

---

Last updated: 2024-12-18

