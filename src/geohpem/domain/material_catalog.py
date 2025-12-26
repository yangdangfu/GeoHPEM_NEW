from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from shutil import copy2
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MaterialModel:
    name: str
    label: str
    behavior: str
    defaults: dict[str, Any]
    meta: dict[str, dict[str, str]]
    solver_mapping: dict[str, Any]
    description: str = ""


_DEFAULT_BEHAVIORS: dict[str, str] = {
    "elastic": "Elastic",
    "plastic": "Elasto-plastic",
    "poroelastic": "Poroelastic",
    "seepage": "Seepage",
    "custom": "Custom",
}

_DEFAULT_CATALOG_PATH = Path(__file__).with_name("materials_catalog.default.json")
_USER_CATALOG_PATH = Path.home() / ".geohpem" / "materials_catalog.user.json"

_CATALOG_CACHE: dict[str, Any] | None = None
_CATALOG_ERRORS: list[str] = []


def default_catalog_path() -> Path:
    return _DEFAULT_CATALOG_PATH


def user_catalog_path() -> Path:
    return _USER_CATALOG_PATH


def _read_catalog(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None


def read_user_catalog() -> dict[str, Any] | None:
    return _read_catalog(_USER_CATALOG_PATH)


def read_default_catalog() -> dict[str, Any]:
    return _read_catalog(_DEFAULT_CATALOG_PATH) or {"behaviors": _DEFAULT_BEHAVIORS, "models": []}


def default_model_dicts() -> dict[str, dict[str, Any]]:
    return _normalize_models(read_default_catalog().get("models"))


def write_user_catalog(data: dict[str, Any]) -> None:
    _USER_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _USER_CATALOG_PATH.exists():
        backup_dir = _USER_CATALOG_PATH.parent / "catalog_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{_USER_CATALOG_PATH.stem}.{stamp}.json"
        try:
            copy2(_USER_CATALOG_PATH, backup_path)
        except Exception:
            pass
    text = json.dumps(data, indent=2, ensure_ascii=False)
    _USER_CATALOG_PATH.write_text(text, encoding="utf-8")


def normalize_models(raw: Any) -> dict[str, dict[str, Any]]:
    return _normalize_models(raw)


def _normalize_models(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        out: dict[str, dict[str, Any]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            obj = dict(v)
            obj.setdefault("name", str(k))
            out[str(k)] = obj
        return out
    if isinstance(raw, list):
        out = {}
        for it in raw:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name", "")).strip()
            if not name:
                continue
            out[name] = dict(it)
        return out
    return {}


def _merge_catalogs(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base)
    behaviors = dict(_DEFAULT_BEHAVIORS)
    if isinstance(base.get("behaviors"), dict):
        behaviors.update({str(k): str(v) for k, v in base["behaviors"].items()})
    if override and isinstance(override.get("behaviors"), dict):
        behaviors.update({str(k): str(v) for k, v in override["behaviors"].items()})
    merged["behaviors"] = behaviors

    base_models = _normalize_models(base.get("models"))
    user_models = _normalize_models(override.get("models")) if override else {}

    for name, u in user_models.items():
        if name in base_models:
            merged_model = dict(base_models[name])
            merged_model.update(u)
            for key in ("defaults", "meta", "solver_mapping"):
                base_val = base_models[name].get(key)
                user_val = u.get(key)
                if isinstance(base_val, dict) and isinstance(user_val, dict):
                    merged_val = dict(base_val)
                    merged_val.update(user_val)
                    merged_model[key] = merged_val
                elif user_val is None:
                    merged_model[key] = base_val
            base_models[name] = merged_model
        else:
            base_models[name] = u
    merged["models"] = list(base_models.values())
    return merged


def validate_catalog(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["catalog: expected object"]
    behaviors = data.get("behaviors")
    if behaviors is not None and not isinstance(behaviors, dict):
        errors.append("behaviors: expected object")
    if isinstance(behaviors, dict):
        for k, v in behaviors.items():
            if not isinstance(k, str) or not k:
                errors.append("behaviors: keys must be non-empty strings")
                break
            if not isinstance(v, str):
                errors.append(f"behaviors.{k}: expected string label")
    models = data.get("models")
    if models is not None and not isinstance(models, list):
        errors.append("models: expected array")
        return errors
    if not isinstance(models, list):
        return errors
    seen: set[str] = set()
    for idx, model in enumerate(models):
        if not isinstance(model, dict):
            errors.append(f"models[{idx}]: expected object")
            continue
        name = model.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"models[{idx}].name: required string")
            continue
        if name in seen:
            errors.append(f"models[{idx}].name: duplicate '{name}'")
        seen.add(name)
        if "label" in model and not isinstance(model.get("label"), str):
            errors.append(f"models[{idx}].label: expected string")
        if "behavior" not in model or not isinstance(model.get("behavior"), str):
            errors.append(f"models[{idx}].behavior: required string")
        defaults = model.get("defaults")
        if defaults is not None and not isinstance(defaults, dict):
            errors.append(f"models[{idx}].defaults: expected object")
        meta = model.get("meta")
        if meta is not None and not isinstance(meta, dict):
            errors.append(f"models[{idx}].meta: expected object")
        if isinstance(meta, dict):
            for k, v in meta.items():
                if not isinstance(k, str):
                    errors.append(f"models[{idx}].meta: keys must be strings")
                    break
                if not isinstance(v, dict):
                    errors.append(f"models[{idx}].meta.{k}: expected object")
                    break
        solver_mapping = model.get("solver_mapping")
        if solver_mapping is not None and not isinstance(solver_mapping, dict):
            errors.append(f"models[{idx}].solver_mapping: expected object")
    return errors


def catalog_errors() -> list[str]:
    return list(_CATALOG_ERRORS)


def load_catalog(force: bool = False) -> dict[str, Any]:
    global _CATALOG_CACHE
    global _CATALOG_ERRORS
    if _CATALOG_CACHE is not None and not force:
        return _CATALOG_CACHE
    _CATALOG_ERRORS = []
    base = read_default_catalog()
    base_err = validate_catalog(base)
    if base_err:
        _CATALOG_ERRORS.extend([f"default: {e}" for e in base_err])
        base = {"behaviors": _DEFAULT_BEHAVIORS, "models": []}
    override = _read_catalog(_USER_CATALOG_PATH)
    if override is not None:
        user_err = validate_catalog(override)
        if user_err:
            _CATALOG_ERRORS.extend([f"user: {e}" for e in user_err])
            override = None
    _CATALOG_CACHE = _merge_catalogs(base, override)
    return _CATALOG_CACHE


def reload_catalog() -> dict[str, Any]:
    return load_catalog(force=True)


def behavior_options() -> list[tuple[str, str]]:
    behaviors = load_catalog().get("behaviors")
    if isinstance(behaviors, dict):
        return [(str(k), str(v)) for k, v in behaviors.items()]
    return list(_DEFAULT_BEHAVIORS.items())


def behavior_label(behavior: str) -> str:
    behaviors = load_catalog().get("behaviors")
    if isinstance(behaviors, dict):
        return str(behaviors.get(behavior, behavior))
    return _DEFAULT_BEHAVIORS.get(behavior, behavior)


def all_models() -> list[MaterialModel]:
    models = load_catalog().get("models")
    if not isinstance(models, list):
        return []
    out: list[MaterialModel] = []
    for it in models:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "")).strip()
        if not name:
            continue
        out.append(
            MaterialModel(
                name=name,
                label=str(it.get("label", name)),
                behavior=str(it.get("behavior", "custom")),
                defaults=copy.deepcopy(it.get("defaults", {})) if isinstance(it.get("defaults"), dict) else {},
                meta=copy.deepcopy(it.get("meta", {})) if isinstance(it.get("meta"), dict) else {},
                solver_mapping=copy.deepcopy(it.get("solver_mapping", {})) if isinstance(it.get("solver_mapping"), dict) else {},
                description=str(it.get("description", "")),
            )
        )
    return out


def behavior_for_model(model_name: str) -> str | None:
    for m in all_models():
        if m.name == model_name:
            return m.behavior
    return None


def model_by_name(model_name: str) -> MaterialModel | None:
    for m in all_models():
        if m.name == model_name:
            return m
    return None


def model_defaults(model_name: str) -> dict[str, Any] | None:
    m = model_by_name(model_name)
    return copy.deepcopy(m.defaults) if m else None


def model_meta(model_name: str) -> dict[str, dict[str, str]]:
    m = model_by_name(model_name)
    return copy.deepcopy(m.meta) if m else {}
