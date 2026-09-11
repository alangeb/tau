---
name: data_processing
description: "Parse and process structured data: JSON, CSV, YAML, XML — query, filter, convert formats (also load: shell_scripting, pyprep, grep_tool)"
keywords: json parse, csv process, yaml transform, xml parse, data query, filter data, convert format, structured data, data pipeline
category: development
---

# Data Processing

## When
"parse json" | "process csv" | "transform yaml" | "data query" | "convert format" | "structured data" | "data pipeline" | "xml parse"

## Audit Log Processing
See `shell_scripting` + `tau_audit` for patterns. Parse `~/.local/tau/log/*.audit`.

## Graph Data
```bash
python3 -c "import json; d=json.load(open('graphify-out/graph.json')); print(len(d['nodes']))"
```

## Skill Data
Parse skills/*/SKILL.md — YAML frontmatter + markdown body.
```bash
python3 -c "
import yaml, glob
for f in sorted(glob.glob('skills/*/SKILL.md')):
    fm = yaml.safe_load(open(f).read().split('---')[1])
    print(f'{fm[\"name\"]:25s} {fm.get(\"category\",\"?\")}')"
```

## Helper
```bash
python3 skills/data_processing/data_processing_helper.py detect <file>    # Detect format
python3 skills/data_processing/data_processing_helper.py stats <file>      # Rows, columns
python3 skills/data_processing/data_processing_helper.py convert <in> <out>  # Auto-convert
```

## Related Skills
- `shell_scripting` — pipe commands, awk, sed
- `pyprep` — Python scripting patterns
- `grep_tool` — search within structured data
- `file-ops` — file read/write operations
- `web-research` — fetch and parse web data
- `tau_audit` — analyze session logs

