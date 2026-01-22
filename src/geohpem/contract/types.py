from __future__ import annotations

from typing import Any, Protocol

JsonDict = dict[str, Any]
ArrayDict = dict[str, Any]


class SolverProtocol(Protocol):
    def capabilities(self) -> JsonDict: ...

    def solve(
        self,
        request: JsonDict,
        mesh: ArrayDict,
        callbacks: JsonDict | None = None,
    ) -> tuple[JsonDict, ArrayDict]: ...
