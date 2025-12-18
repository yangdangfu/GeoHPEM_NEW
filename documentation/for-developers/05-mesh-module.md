# Mesh Module

The `mesh` module handles mesh import, conversion, generation, and quality analysis.

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Mesh Format](#mesh-format)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)

---

## Overview

GeoHPEM uses a simple, NumPy-based mesh format stored as `.npz` files. The mesh module provides:

- **Import**: Convert external mesh formats (via meshio) to GeoHPEM format
- **Conversion**: Transform meshio mesh objects to Contract format
- **Quality**: Analyze mesh quality metrics
- **Generation**: Create meshes from geometry (via pygmsh, placeholder)

---

## Module Structure

```
mesh/
├── __init__.py
├── convert.py          # meshio → Contract conversion
├── import_mesh.py      # High-level import API
├── quality.py          # Quality metrics
└── generate_pygmsh.py  # Mesh generation (placeholder)
```

---

## Mesh Format

### Contract NPZ Structure

The mesh is stored as a NumPy compressed archive with these arrays:

| Key | Shape | Type | Description |
|-----|-------|------|-------------|
| `points` | (N, 2) | float64 | Node coordinates |
| `cells_tri3` | (M, 3) | int32 | Triangle connectivity |
| `cells_quad4` | (K, 4) | int32 | Quadrilateral connectivity |
| `node_set__<name>` | (L,) | int32 | Node indices |
| `edge_set__<name>` | (E, 2) | int32 | Edge node pairs |
| `elem_set__<name>__<type>` | (F,) | int32 | Element indices |

### Supported Cell Types

| Type | Contract Key | Nodes per Cell |
|------|--------------|----------------|
| Triangle | `cells_tri3` | 3 |
| Quadrilateral | `cells_quad4` | 4 |

### Set Naming Convention

Sets are identified by NPZ keys following patterns:

```
node_set__<name>         # Node set
edge_set__<name>         # Edge set (pairs of nodes)
elem_set__<name>__tri3   # Element set (triangles)
elem_set__<name>__quad4  # Element set (quads)
```

Example:
```python
{
    "points": np.array([[0,0], [1,0], [1,1], [0,1]]),
    "cells_tri3": np.array([[0,1,2], [0,2,3]]),
    "node_set__bottom": np.array([0, 1]),
    "edge_set__left": np.array([[0, 3]]),
    "elem_set__soil__tri3": np.array([0, 1]),
}
```

---

## API Reference

### Convert Functions (`convert.py`)

```python
@dataclass(frozen=True, slots=True)
class ImportReport:
    """Summary of imported mesh."""
    points: int                      # Number of nodes
    cells: dict[str, int]            # Cell counts by type
    node_sets: dict[str, int]        # Node set sizes
    edge_sets: dict[str, int]        # Edge set sizes
    element_sets: dict[str, int]     # Element set sizes

def meshio_to_contract(mesh) -> tuple[dict[str, Any], ImportReport]:
    """
    Convert a meshio.Mesh to GeoHPEM Contract format.
    
    Args:
        mesh: meshio.Mesh object
    
    Returns:
        (contract_mesh, report): Tuple of mesh dict and import report
    
    Supported conversions:
        - points → points (N, 2) - 3D points truncated to 2D
        - triangle → cells_tri3
        - quad → cells_quad4
        - Physical groups (gmsh:physical) → sets
    
    Physical group mapping:
        - dim=0 (vertex) → node_set__<name>
        - dim=1 (line)   → edge_set__<name>
        - dim=2 (surface)→ elem_set__<name>__<type>
    """
```

### Import Functions (`import_mesh.py`)

```python
def import_with_meshio(path: str | Path) -> dict[str, Any]:
    """
    Import a mesh file via meshio.
    
    Args:
        path: Path to mesh file (any format supported by meshio)
    
    Returns:
        Contract mesh dict
    
    Raises:
        RuntimeError: If meshio is not installed
    
    Supported formats (via meshio):
        - GMSH (.msh)
        - Abaqus (.inp)
        - VTK (.vtk, .vtu)
        - STL (.stl)
        - And many more...
    """

def import_with_meshio_report(path: str | Path) -> tuple[dict[str, Any], ImportReport]:
    """
    Import a mesh file with detailed report.
    
    Args:
        path: Path to mesh file
    
    Returns:
        (mesh, report): Contract mesh and import statistics
    """
```

### Quality Functions (`quality.py`)

```python
@dataclass(frozen=True, slots=True)
class TriangleQualityStats:
    """Summary statistics for triangle mesh quality."""
    count: int                 # Number of triangles
    min_angle_deg_min: float   # Minimum angle (worst case)
    min_angle_deg_p50: float   # Median minimum angle
    min_angle_deg_p95: float   # 95th percentile minimum angle
    aspect_ratio_max: float    # Maximum aspect ratio (max_edge/min_edge)

def triangle_quality(
    points: np.ndarray,
    tri3: np.ndarray
) -> tuple[np.ndarray, np.ndarray, TriangleQualityStats]:
    """
    Compute quality metrics for triangular mesh.
    
    Args:
        points: (N, 2) node coordinates
        tri3: (M, 3) triangle connectivity
    
    Returns:
        (min_angles, aspect_ratios, stats):
            - min_angles: (M,) minimum interior angle per triangle (degrees)
            - aspect_ratios: (M,) max_edge/min_edge per triangle
            - stats: Summary statistics
    
    Quality guidelines:
        - Good mesh: min_angle_deg_min > 20°
        - Excellent mesh: min_angle_deg_p50 > 30°
        - Aspect ratio < 3 is generally good
    """
```

---

## Usage Examples

### Importing a GMSH File

```python
from pathlib import Path
from geohpem.mesh.import_mesh import import_with_meshio_report

# Import mesh
mesh, report = import_with_meshio_report(Path("model.msh"))

print(f"Points: {report.points}")
print(f"Cells: {report.cells}")
print(f"Node sets: {report.node_sets}")
print(f"Edge sets: {report.edge_sets}")
print(f"Element sets: {report.element_sets}")
```

### Analyzing Mesh Quality

```python
from geohpem.mesh.quality import triangle_quality

# Get quality metrics
min_angles, aspect_ratios, stats = triangle_quality(
    mesh["points"],
    mesh["cells_tri3"]
)

print(f"Triangle count: {stats.count}")
print(f"Worst min angle: {stats.min_angle_deg_min:.1f}°")
print(f"Median min angle: {stats.min_angle_deg_p50:.1f}°")
print(f"95th percentile min angle: {stats.min_angle_deg_p95:.1f}°")
print(f"Max aspect ratio: {stats.aspect_ratio_max:.2f}")

# Find problematic elements
bad_elements = np.where(min_angles < 15)[0]
print(f"Elements with angle < 15°: {len(bad_elements)}")
```

### Manual Mesh Creation

```python
import numpy as np

# Create a simple mesh manually
mesh = {
    "points": np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
        [0.5, 0.5],
    ], dtype=float),
    
    "cells_tri3": np.array([
        [0, 1, 4],
        [1, 2, 4],
        [2, 3, 4],
        [3, 0, 4],
    ], dtype=np.int32),
    
    "node_set__center": np.array([4], dtype=np.int32),
    "node_set__boundary": np.array([0, 1, 2, 3], dtype=np.int32),
    "edge_set__bottom": np.array([[0, 1]], dtype=np.int32),
    "elem_set__all__tri3": np.array([0, 1, 2, 3], dtype=np.int32),
}
```

### Converting from meshio

```python
import meshio
from geohpem.mesh.convert import meshio_to_contract

# Load with meshio
msh = meshio.read("model.msh")

# Convert to Contract format
mesh, report = meshio_to_contract(msh)
```

---

## Physical Groups (GMSH)

When importing GMSH files, physical groups are automatically converted to sets:

### GMSH GEO Example

```
// Points
Point(1) = {0, 0, 0};
Point(2) = {1, 0, 0};
Point(3) = {1, 1, 0};
Point(4) = {0, 1, 0};

// Lines
Line(1) = {1, 2};  // bottom
Line(2) = {2, 3};  // right
Line(3) = {3, 4};  // top
Line(4) = {4, 1};  // left

// Surface
Line Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Physical groups
Physical Line("bottom") = {1};
Physical Line("left") = {4};
Physical Surface("soil") = {1};
```

### Resulting Contract Mesh

```python
{
    "points": [...],
    "cells_tri3": [...],
    "edge_set__bottom": np.array([[0, 1], ...]),  # From Physical Line("bottom")
    "edge_set__left": np.array([[3, 0], ...]),    # From Physical Line("left")
    "elem_set__soil__tri3": np.array([...]),      # From Physical Surface("soil")
}
```

---

## Design Notes

### Why NPZ Format?

1. **Efficiency**: Binary format, fast I/O
2. **Compression**: Built-in compression support
3. **NumPy Native**: Direct array access without conversion
4. **Portability**: Standard format, works across platforms

### Why Separate Cell Types?

Mixing cell types in a single array requires complex indexing. Separate arrays:
- Simplify element assembly
- Enable type-specific operations
- Match solver expectations

### Set Naming Convention

The `__` separator in set names:
- Provides namespacing (`node_set__`, `edge_set__`, `elem_set__`)
- Allows parsing set type and name programmatically
- Avoids conflicts with user-defined names

---

## Dependencies

| Dependency | Required For | Installation |
|------------|--------------|--------------|
| NumPy | Core functionality | Always installed |
| meshio | Mesh import | `pip install meshio` |
| pygmsh | Mesh generation | `pip install pygmsh` |

---

Last updated: 2024-12-18

