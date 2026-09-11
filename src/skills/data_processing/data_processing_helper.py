#!/usr/bin/env python3
"""Data processing helper — detect format, stats, and convert between JSON/CSV/YAML."""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def detect_format(file_path: str) -> dict:
    """Detect file format by extension and content. Returns format, confidence, details."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
    ext = p.suffix.lower()
    content = p.read_text(errors="replace").strip()[:500]
    result = {"file": str(p), "extension": ext, "format": "unknown", "confidence": 0.0}
    # Extension-based
    ext_map = {".json": "json", ".csv": "csv", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml"}
    if ext in ext_map:
        result["format"], result["confidence"] = ext_map[ext], 0.8
    # Content-based override
    if content.startswith("{") or content.startswith("["):
        try:
            json.loads(content)
            result["format"], result["confidence"] = "json", 0.95
        except json.JSONDecodeError:
            pass
    if "," in content and ext not in (".json",):
        lines = content.split("\n")
        if len(lines) > 1 and all(lines[0].count(",") == line.count(",") for line in lines[:5]):
            result["format"], result["confidence"] = "csv", 0.7
    if content.startswith("---") or (":" in content and "  " in content):
        result["format"] = "yaml"
        result["confidence"] = max(result["confidence"], 0.6)
    if "<" in content and ">" in content:
        result["format"] = "xml"
        result["confidence"] = max(result["confidence"], 0.6)
    return result


def get_stats(file_path: str) -> dict:
    """Get stats for a data file. Returns format, rows, columns, size_kb."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
    content = p.read_text(errors="replace")
    size_kb = round(p.stat().st_size / 1024, 1)
    fmt = detect_format(str(p))["format"]
    result = {"file": str(p), "format": fmt, "size_kb": size_kb, "lines": content.count("\n") + 1}
    if fmt == "json":
        try:
            data = json.loads(content)
            if isinstance(data, list):
                result["rows"] = len(data)
                result["columns"] = len(data[0].keys()) if data and isinstance(data[0], dict) else 0
            elif isinstance(data, dict):
                result["keys"] = len(data)
        except json.JSONDecodeError:
            result["error"] = "Invalid JSON"
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        result["rows"] = len(rows)
        result["columns"] = len(rows[0].keys()) if rows else 0
    elif fmt == "yaml" and HAS_YAML:
        try:
            data = yaml.safe_load(content)
            if isinstance(data, list):
                result["rows"] = len(data)
            elif isinstance(data, dict):
                result["keys"] = len(data)
        except Exception as e:
            result["error"] = str(e)
    return result


def convert_file(in_path: str, out_path: str) -> dict:
    """Auto-convert between JSON, CSV, YAML. Returns status."""
    in_fmt = detect_format(in_path)["format"]
    out_fmt = Path(out_path).suffix.lstrip(".").lower()
    if out_fmt == "yml":
        out_fmt = "yaml"
    if in_fmt == "unknown":
        return {"error": f"Cannot detect input format: {in_path}"}
    content = Path(in_path).read_text(errors="replace")
    # Load data
    if in_fmt == "json":
        data = json.loads(content)
    elif in_fmt == "csv":
        data = list(csv.DictReader(io.StringIO(content)))
    elif in_fmt == "yaml" and HAS_YAML:
        data = yaml.safe_load(content)
    else:
        return {"error": f"Unsupported input format: {in_fmt}"}
    # Write output
    if out_fmt == "json":
        Path(out_path).write_text(json.dumps(data, indent=2, default=str))
    elif out_fmt == "csv" and isinstance(data, list):
        with open(out_path, "w", newline="") as f:
            if data:
                w = csv.DictWriter(f, fieldnames=data[0].keys())
                w.writeheader()
                w.writerows(data)
    elif out_fmt == "yaml" and HAS_YAML:
        Path(out_path).write_text(yaml.safe_dump(data, default_flow_style=False))
    else:
        return {"error": f"Unsupported output format: {out_fmt}"}
    return {"status": "ok", "input": in_fmt, "output": out_fmt, "source": in_path, "target": out_path}


def main():
    if len(sys.argv) < 2:
        print("Usage: data_processing_helper.py <detect|stats|convert> <args...>")
        print("  detect <file>              — Detect file format")
        print("  stats <file>               — Get file stats (rows, columns, size)")
        print("  convert <in> <out>         — Convert between JSON/CSV/YAML")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "detect" and len(sys.argv) >= 3:
        result = detect_format(sys.argv[2])
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif cmd == "stats" and len(sys.argv) >= 3:
        result = get_stats(sys.argv[2])
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif cmd == "convert" and len(sys.argv) >= 4:
        result = convert_file(sys.argv[2], sys.argv[3])
        for k, v in result.items():
            print(f"  {k}: {v}")
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
