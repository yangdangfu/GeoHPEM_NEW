# Units Module

The `units` module provides unit conversion and display unit management for GeoHPEM.

## Table of Contents

1. [Overview](#overview)
2. [Supported Units](#supported-units)
3. [API Reference](#api-reference)
4. [Usage Examples](#usage-examples)
5. [Design Notes](#design-notes)

---

## Overview

GeoHPEM uses a two-layer unit system:

1. **Base Units**: The units used by stored data (from `request.unit_system`)
2. **Display Units**: User-selected units for UI display (persisted in settings)

This allows data to remain in the project's declared units while allowing users to view values in their preferred units.

---

## Supported Units

### Length

| Unit | SI Factor | Description |
|------|-----------|-------------|
| `mm` | 0.001 | Millimeter |
| `cm` | 0.01 | Centimeter |
| `m` | 1.0 | Meter (SI base) |
| `km` | 1000.0 | Kilometer |

### Force

| Unit | SI Factor | Description |
|------|-----------|-------------|
| `N` | 1.0 | Newton (SI base) |
| `kN` | 1000.0 | Kilonewton |
| `MN` | 1,000,000.0 | Meganewton |

### Time

| Unit | SI Factor | Description |
|------|-----------|-------------|
| `s` | 1.0 | Second (SI base) |
| `min` | 60.0 | Minute |
| `h` | 3600.0 | Hour |

### Pressure

| Unit | SI Factor | Description |
|------|-----------|-------------|
| `Pa` | 1.0 | Pascal (SI base) |
| `kPa` | 1000.0 | Kilopascal |
| `MPa` | 1,000,000.0 | Megapascal |
| `GPa` | 1,000,000,000.0 | Gigapascal |

---

## API Reference

### Conversion Functions

```python
def conversion_factor(unit_from: str, unit_to: str) -> float:
    """
    Get the factor to convert from one unit to another.
    
    Args:
        unit_from: Source unit
        unit_to: Target unit
    
    Returns:
        Multiplication factor (value_to = value_from * factor)
    
    Raises:
        KeyError: If either unit is unknown
        ValueError: If units are incompatible (different kinds)
    
    Example:
        >>> conversion_factor("m", "mm")
        1000.0
        >>> conversion_factor("kPa", "Pa")
        1000.0
    """

def convert_value(value: float, unit_from: str, unit_to: str) -> float:
    """Convert a single value between units."""

def convert_array(arr: Any, unit_from: str, unit_to: str) -> np.ndarray:
    """Convert a numpy array between units (returns new array if factor != 1)."""
```

### Unit Context

```python
@dataclass(frozen=True, slots=True)
class UnitContext:
    """
    Unit conversion context for display.
    
    Attributes:
        base: Units used by stored numbers (from request.unit_system)
        display: User-selected display units (overrides base)
    """
    base: dict[str, str]      # {"length": "m", "pressure": "kPa", ...}
    display: dict[str, str]   # {"length": "mm", ...} (partial override)
    
    def base_unit(self, kind: str, default: str | None = None) -> str | None:
        """Get base unit for a kind (e.g., "length")."""
    
    def display_unit(self, kind: str, default: str | None = None) -> str | None:
        """Get display unit for a kind (falls back to base)."""
    
    def factor_base_to_display(self, kind: str) -> float:
        """Get conversion factor from base to display units."""
    
    def format_value(self, kind: str, value: float | None, *, precision: int = 6) -> str:
        """Format a value with conversion and unit suffix."""
    
    def convert_base_to_display(self, kind: str, value: float) -> float:
        """Convert a value from base to display units."""
    
    def convert_display_to_base(self, kind: str, value: float) -> float:
        """Convert a value from display to base units."""
```

### Utility Functions

```python
def request_unit_system(request: dict[str, Any]) -> dict[str, str]:
    """
    Extract unit system from request.
    
    Returns:
        Dict like {"length": "m", "pressure": "kPa", ...}
    """

def available_units_for_kind(kind: str) -> list[str]:
    """
    Get available units for a unit kind.
    
    Args:
        kind: "length", "pressure", "force", or "time"
    
    Returns:
        List of unit strings in preferred order
    
    Example:
        >>> available_units_for_kind("length")
        ['mm', 'cm', 'm', 'km']
    """

def infer_kind_from_unit(unit: str) -> str | None:
    """
    Infer the kind from a unit string.
    
    Example:
        >>> infer_kind_from_unit("kPa")
        'pressure'
    """

def normalize_unit_system(unit_system: dict[str, str]) -> dict[str, str]:
    """Validate and clean a unit system dict, keeping only known units."""

def merge_display_units(
    base: dict[str, str],
    overrides: dict[str, str] | None,
    *,
    allowed_kinds: Iterable[str] = ("length", "pressure", "force", "time"),
) -> dict[str, str]:
    """
    Merge display unit overrides with base units.
    
    The special value "project" means "use base unit" (no override).
    """
```

---

## Usage Examples

### Basic Conversion

```python
from geohpem.units import conversion_factor, convert_value, convert_array
import numpy as np

# Convert single value
length_mm = convert_value(1.5, "m", "mm")  # 1500.0

# Convert array
coords_m = np.array([[0, 0], [1, 0], [0.5, 1]])
coords_mm = convert_array(coords_m, "m", "mm")
```

### Using UnitContext

```python
from geohpem.units import UnitContext

# Create context
ctx = UnitContext(
    base={"length": "m", "pressure": "kPa"},
    display={"length": "mm"}  # Override length only
)

# Convert values
x_display = ctx.convert_base_to_display("length", 1.5)  # 1500.0
p_display = ctx.convert_base_to_display("pressure", 100)  # 100.0 (no override)

# Format with unit
print(ctx.format_value("length", 1.5))  # "1500 mm"
print(ctx.format_value("pressure", 100))  # "100 kPa"
```

### Extracting from Request

```python
from geohpem.units import request_unit_system, normalize_unit_system

request = {
    "schema_version": "0.1",
    "unit_system": {"force": "kN", "length": "m", "time": "s", "pressure": "kPa"},
    ...
}

# Extract and normalize
units = normalize_unit_system(request_unit_system(request))
# {"force": "kN", "length": "m", "time": "s", "pressure": "kPa"}
```

### GUI Integration

```python
from geohpem.units import UnitContext, merge_display_units, normalize_unit_system, request_unit_system

# In MainWindow
def _apply_unit_context_from_request(self, request):
    base = normalize_unit_system(request_unit_system(request))
    base.setdefault("length", "m")
    base.setdefault("pressure", "kPa")
    
    display_pref = self._settings.get_display_units()
    display = merge_display_units(base, display_pref)
    
    self._unit_context = UnitContext(base=base, display=display)
    
    # Propagate to widgets
    self.geometry_dock.set_unit_context(self._unit_context)
    self.workspace_stack.get("output").set_unit_context(self._unit_context)
```

---

## Design Notes

### Why Two-Layer Units?

1. **Data Integrity**: Stored data remains in project units, no re-saving needed
2. **User Preference**: Different users may prefer different display units
3. **Persistence**: Display preferences are saved in user settings, not project

### Unit Policy (Contract v0.1)

- `request.unit_system` declares the units of stored numbers
- Solver receives/returns numbers in these units (pass-through)
- GUI converts only for display; editing rounds back to base units
- Future: Contract v0.2 may introduce internal SI normalization

### Adding New Units

To add a new unit:

1. Add entry to `_UNIT_TO_SI` dict in `units.py`:
   ```python
   "ft": ("length", 0.3048),  # feet
   ```

2. Optionally add to preferred order in `available_units_for_kind()`

3. Update documentation

---

Last updated: 2024-12-18

