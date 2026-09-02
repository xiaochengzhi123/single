from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import sympy as sp

from signaltutor.schemas.tools import ToolResult


def evidence_id(tool_name: str) -> str:
    return f"{tool_name}:{uuid4().hex[:12]}"


def success_result(tool_name: str, result: Any, **metadata: Any) -> ToolResult:
    expr = sp.sympify(result) if not isinstance(result, str) else None
    return ToolResult(
        success=True,
        tool_name=tool_name,
        evidence_id=evidence_id(tool_name),
        result_text=str(result),
        result_latex=sp.latex(expr) if expr is not None else None,
        metadata=metadata,
    )


def failure_result(tool_name: str, code: str, exc: Exception) -> ToolResult:
    return ToolResult(
        success=False,
        tool_name=tool_name,
        evidence_id=evidence_id(tool_name),
        error_code=code,
        error_message=str(exc),
    )


async def with_timeout(
    func: Callable[..., Any], *args: Any, timeout: float = 8, **kwargs: Any
) -> Any:
    return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
