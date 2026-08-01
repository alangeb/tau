#!/usr/bin/env python3
"""Validate a spec file against the review checklist."""
import sys, re, os


def validate(path: str) -> tuple[bool, list[str], list[str]]:
    if not os.path.exists(path):
        return False, [f"File not found: {path}"], []

    with open(path) as f:
        content = f.read()

    fails, warns = [], []

    # Extract frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        fails.append("Missing YAML frontmatter")
        return False, fails, warns

    fm = fm_match.group(1)
    for key in ['name:', 'status:', 'area:', 'depends:', 'related:']:
        if key not in fm:
            fails.append(f"Missing frontmatter field: {key.strip(':')}")

    # Check sections exist and are non-empty
    sections = [
        '## Problem', '## Solution', '## Non-Goals',
        '## Acceptance Criteria', '## Files Affected',
        '## Edge Cases', '## Rollback'
    ]
    for section in sections:
        if section not in content:
            fails.append(f"Missing section: {section.replace('## ', '')}")
        else:
            # Check section is non-empty (has content after header before next header)
            idx = content.index(section) + len(section)
            next_header = content.find('\n## ', idx)
            if next_header == -1:
                next_header = len(content)
            section_content = content[idx:next_header].strip()
            if not section_content:
                fails.append(f"Empty section: {section.replace('## ', '')}")

    # Count acceptance criteria
    criteria = re.findall(r'^- \[[ x]\] ', content, re.MULTILINE)
    if not criteria:
        fails.append("No acceptance criteria found (use '- [ ] ' format)")
    elif len(criteria) > 10:
        fails.append(f"Too many acceptance criteria: {len(criteria)} (max 10, split into multiple specs)")

    # Check Given-When-Then format (warning only)
    criteria_lines = re.findall(r'^- \[[ x]\] (.+)', content, re.MULTILINE)
    non_gwt = [c for c in criteria_lines if not re.search(r'Given.*When.*Then', c, re.IGNORECASE)]
    if non_gwt:
        warns.append(f"{len(non_gwt)} criterion(s) not in Given-When-Then format")

    # Count files affected
    fa_section = content.split('## Files Affected')
    if len(fa_section) > 1:
        fa_content = fa_section[1].split('\n## ')[0]
        files = re.findall(r'^- `[^`]+`', fa_content, re.MULTILINE)
        if not files:
            fails.append("No files listed in Files Affected section")
        elif len(files) > 5:
            fails.append(f"Too many files affected: {len(files)} (max 5, split into multiple specs)")

    # Check status matches directory location
    status_match = re.search(r'status:\s*(\w+)', fm)
    if status_match:
        status = status_match.group(1)
        spec_dir = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if status == 'active' and spec_dir != 'active':
            fails.append(f"Status is 'active' but file is in '{spec_dir}/' directory")
        elif status == 'completed' and spec_dir != 'completed':
            fails.append(f"Status is 'completed' but file is in '{spec_dir}/' directory")

    # Check dependencies exist in completed/
    depends_match = re.search(r'depends:\s*(.+)', fm)
    if depends_match:
        deps = [d.strip() for d in depends_match.group(1).split(',') if d.strip().lower() != 'none']
        # Find the specs/ directory relative to the spec file
        spec_dir = os.path.dirname(os.path.abspath(path))
        specs_root = None
        current = spec_dir
        while current != '/':
            if os.path.basename(current) == 'specs':
                specs_root = current
                break
            current = os.path.dirname(current)

        if specs_root:
            completed_dir = os.path.join(specs_root, 'completed')
            for dep in deps:
                # Search for a file containing this spec name
                found = False
                if os.path.isdir(completed_dir):
                    for f in os.listdir(completed_dir):
                        if dep in f:
                            found = True
                            break
                if not found:
                    fails.append(f"Dependency not completed: '{dep}' (not found in specs/completed/)")

    return len(fails) == 0, fails, warns


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path or os.path.isdir(path):
        print("Usage: validate_spec.py <spec-file>")
        sys.exit(1)
    ok, fails, warns = validate(path)

    # Print results from validate() return values (no re-computation)
    if ok:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")
    print()

    for f in fails:
        print(f"FAIL: {f}")
    for w in warns:
        print(f"WARN: {w}")

    print()
    summary = f"{len(fails)} fail(s), {len(warns)} warning(s)"
    if ok:
        print(f"Spec is ready for implementation. {summary}")
        sys.exit(0)
    else:
        print(f"Fix failures before implementing. {summary}")
        sys.exit(1)
