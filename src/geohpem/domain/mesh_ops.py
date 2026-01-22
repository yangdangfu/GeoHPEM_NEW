from __future__ import annotations

from typing import Any

import numpy as np


def collect_set_names(mesh: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for k in mesh.keys():
        if not isinstance(k, str):
            continue
        if k.startswith("node_set__"):
            names.add(k.split("__", 1)[1])
        elif k.startswith("edge_set__"):
            names.add(k.split("__", 1)[1])
        elif k.startswith("elem_set__"):
            rest = k.split("__", 1)[1]
            names.add(rest.split("__", 1)[0])
    return sorted(names)


def collect_element_sets(mesh: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Returns list of (element_set_name, cell_type) from keys like elem_set__NAME__tri3.
    """
    out: set[tuple[str, str]] = set()
    for k in mesh.keys():
        if not isinstance(k, str) or not k.startswith("elem_set__"):
            continue
        rest = k.split("__", 1)[1]
        parts = rest.split("__")
        if len(parts) >= 2:
            out.add((parts[0], parts[1]))
    return sorted(out)


def add_node_set(
    mesh: dict[str, Any], name: str, indices: np.ndarray
) -> dict[str, Any]:
    m = dict(mesh)
    m[f"node_set__{name}"] = np.asarray(indices, dtype=np.int32).reshape(-1)
    return m


def add_edge_set(mesh: dict[str, Any], name: str, edges: np.ndarray) -> dict[str, Any]:
    m = dict(mesh)
    m[f"edge_set__{name}"] = np.asarray(edges, dtype=np.int32).reshape(-1, 2)
    return m


def add_elem_set(
    mesh: dict[str, Any], name: str, cell_type: str, indices: np.ndarray
) -> dict[str, Any]:
    m = dict(mesh)
    m[f"elem_set__{name}__{cell_type}"] = np.asarray(indices, dtype=np.int32).reshape(
        -1
    )
    return m


def delete_set(mesh: dict[str, Any], key: str) -> dict[str, Any]:
    m = dict(mesh)
    if key in m:
        del m[key]
    return m


def rename_set(mesh: dict[str, Any], old_key: str, new_key: str) -> dict[str, Any]:
    if old_key == new_key:
        return dict(mesh)
    m = dict(mesh)
    if old_key not in m:
        raise KeyError(old_key)
    if new_key in m:
        raise KeyError(f"Target already exists: {new_key}")
    m[new_key] = m.pop(old_key)
    return m
