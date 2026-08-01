#!/usr/bin/env python3
"""Context management delegation helper — analyze context usage and recommend delegation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DECISION_MATRIX = {"needs_context": "fork", "needs_isolation": "subagent", "fire_and_forget": "background"}
COST = {"background": 1, "subagent": 5, "fork": 100}  # relative token overhead
THRESHOLDS = [
    (0, 30, "normal", "No action needed"),
    (30, 50, "caution", "Start delegating non-critical tasks"),
    (50, 70, "warning", "AGGRESSIVELY delegate via subagent/background"),
    (70, 85, "critical", "STOP non-critical work; delegate everything"),
    (85, 100, "danger", "Compression imminent — delegate immediately"),
]


def choose_delegation(needs_context: bool = False, needs_isolation: bool = False, async_ok: bool = False) -> str:
    """Choose best delegation method. Returns: 'background', 'subagent', or 'fork'."""
    if async_ok:
        return "background"
    if needs_isolation:
        return "subagent"
    return "fork" if needs_context else "subagent"


def calculate_context_usage(info_output: str) -> dict:
    """Parse info tool output and return context stats (tokens, percentage, status)."""
    result: dict = {"tokens": 0, "token_limit": 180000, "percentage": 0.0, "bytes": 0, "status": "unknown"}
    m = re.search(r'Token Usage:\s*(\d+)\s*/\s*(\d+)\s*tokens\s*\((\d+\.?\d*)%', info_output)
    if m:
        result["tokens"], result["token_limit"], result["percentage"] = int(m.group(1)), int(m.group(2)), float(m.group(3))
    m = re.search(r'Context Size:\s*(\d+)\s*bytes', info_output)
    if m:
        result["bytes"] = int(m.group(1))
    for low, high, status, _ in THRESHOLDS:
        if low <= result["percentage"] < high:
            result["status"] = status
            break
    return result


def recommend_delegation(context_pct: float, task_description: str = "") -> dict:
    """Recommend delegation strategy based on context usage percentage and task type.
    
    Returns dict with method, reason, urgency, context_pct, estimated_cost.
    """
    rec: dict = {"method": "subagent", "reason": "", "urgency": "normal", "context_pct": context_pct, "estimated_cost": 0}
    for low, high, status, action in THRESHOLDS:
        if low <= context_pct < high:
            rec["urgency"], rec["reason"] = status, action
            break
    task_lower = task_description.lower()
    if context_pct < 30:
        rec["method"] = "background" if any(w in task_lower for w in ("async", "build", "test", "long")) else \
            "fork" if any(w in task_lower for w in ("context", "memory", "history", "continue")) else "subagent"
    elif context_pct < 70:
        rec["method"] = "background" if any(w in task_lower for w in ("async", "build", "test")) else "subagent"
    else:
        rec["method"] = "background"
        rec["reason"] = "Context critical — use background to avoid context growth"
    rec["estimated_cost"] = COST.get(rec["method"], 5)
    return rec


def estimate_output_size(path: str, tool: str = "pyscan") -> dict:
    """Estimate tool output size to help decide on compact=True. Returns recommended_params."""
    p = Path(path)
    if not p.exists():
        return {"error": f"Path not found: {path}"}
    files = list(p.glob("**/*.py")) if p.is_dir() else ([p] if p.is_file() else [])
    file_count = len(files)
    result: dict = {"path": str(path), "file_count": file_count, "tool": tool, "recommended_params": {}}
    if tool == "pyscan":
        if file_count >= 200:
            result["recommended_params"] = {"compact": True, "max_files": min(20, file_count // 5)}
        elif file_count >= 50:
            result["recommended_params"] = {"compact": True}
    elif tool == "grep":
        result["recommended_params"] = {"max_results": min(50, file_count * 2)}
    return result


def format_delegation_call(method: str, task: str, **kwargs) -> str:
    """Format a delegation call as Python code string."""
    if method == "background":
        return f'background_run(command={task!r}, timeout={kwargs.pop("timeout", 300)}, keywords={kwargs.pop("keywords", "error|done|FAILED|SUCCESS")!r})'
    elif method == "fork":
        return f'fork(task={task!r})'
    return f'subagent(task={task!r})'


def main() -> None:
    if len(sys.argv) < 2:
        thresholds = [{"range": f"{l}-{h}%", "status": s, "action": a} for l, h, s, a in THRESHOLDS]
        print(json.dumps({"decision_matrix": DECISION_MATRIX, "costs": COST, "thresholds": thresholds}, indent=2))
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "analyze":
        info_output = Path(args[0]).read_text() if args else sys.stdin.read()
        print(json.dumps(calculate_context_usage(info_output), indent=2))
    elif cmd == "recommend":
        pct = float(args[0]) if args else 50.0
        task = args[1] if len(args) > 1 else ""
        print(json.dumps(recommend_delegation(pct, task), indent=2))
    elif cmd == "estimate":
        path = args[0] if args else "."
        tool = args[1] if len(args) > 1 else "pyscan"
        print(json.dumps(estimate_output_size(path, tool), indent=2))
    elif cmd == "format":
        method = args[0] if args else "subagent"
        task = args[1] if len(args) > 1 else "example task"
        print(format_delegation_call(method, task))
    else:
        print(f"Usage: {sys.argv[0]} {{analyze|recommend|estimate|format}} [args...]")
        sys.exit(1)


if __name__ == "__main__":
    main()
