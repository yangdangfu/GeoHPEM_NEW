from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from geohpem.app.errors import CancelledError
from geohpem.contract.errors import ContractError


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    code: str
    message: str
    details: dict[str, Any] | None = None


_CODE_RE = re.compile(r"[^A-Za-z0-9_]+")


def normalize_error_code(code: str) -> str:
    code = (code or "").strip()
    if not code:
        return "UNKNOWN"
    code = code.replace("-", "_").replace(" ", "_")
    code = _CODE_RE.sub("_", code)
    code = re.sub(r"_+", "_", code).strip("_")
    return code.upper() or "UNKNOWN"


def map_exception(exc: BaseException) -> ErrorInfo:
    """
    Map exceptions into a standardized (code, message, details) triple.

    Solver teams can raise custom exceptions with attributes:
      - code / error_code: str
      - details / payload: dict
    """
    if isinstance(exc, CancelledError):
        return ErrorInfo(code="CANCELED", message=str(exc) or "Cancelled by user")
    if isinstance(exc, ContractError):
        return ErrorInfo(code="CONTRACT", message=str(exc))
    if isinstance(exc, FileNotFoundError):
        return ErrorInfo(code="IO_NOT_FOUND", message=str(exc))
    if isinstance(exc, PermissionError):
        return ErrorInfo(code="IO_PERMISSION", message=str(exc))
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return ErrorInfo(code="SOLVER_IMPORT", message=str(exc))

    # Custom solver exceptions (best-effort).
    code = None
    for attr in ("code", "error_code"):
        try:
            v = getattr(exc, attr, None)
            if isinstance(v, str) and v.strip():
                code = v.strip()
                break
        except Exception:
            continue

    details: dict[str, Any] | None = None
    for attr in ("details", "payload"):
        try:
            v = getattr(exc, attr, None)
            if isinstance(v, dict):
                details = v
                break
        except Exception:
            continue

    if code:
        return ErrorInfo(
            code=normalize_error_code(code),
            message=str(exc) or normalize_error_code(code),
            details=details,
        )

    # Generic fallback.
    return ErrorInfo(code="SOLVER_RUNTIME", message=str(exc) or exc.__class__.__name__)
