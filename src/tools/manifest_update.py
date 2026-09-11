"""Manifest update tool — update manifest sections with auto-verify."""

from __future__ import annotations

from tools import ToolContext, ToolMetadata

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

__all__ = ["Args", "run"]

# ── Constants ─────────────────────────────────────────────────────

_VERIFY_ALLOWLIST = frozenset({
    "grep", "ls", "pytest", "python3", "find", "cat", "head", "wc", "echo",
})

_VALID_SECTIONS = frozenset({
    "success_criteria", "subtasks", "progress", "status",
    # Plan-replacement actions (operate on subtasks section)
    "block", "unblock", "next", "delete", "clear",
})

_ACTION_SECTIONS = frozenset({"block", "unblock", "next", "delete", "clear"})

# Canonical regex for matching checklist lines: - [x], - [ ], - [?]
_CHECKLIST_RE = re.compile(r"- \[[ x\?]\]\s*(\d+)\.\s*(.*)")

# ── Tool metadata ─────────────────────────────────────────────────

metadata = ToolMetadata(
    name="manifest_update",
    description=(
        "Update sections in an existing manifest file with auto-verify. "
        "When items are marked complete [x], their Verify: `command` is run. "
        "Tracks retry state in .state.json file. "
        "Sections: success_criteria, subtasks, progress, status. "
        "Actions: block (mark [?]), unblock (restore [ ]), next (first pending), "
        "delete (remove by number), clear (empty subtasks). "
        "For actions, set section='block|unblock|next|delete|clear' and "
        "content='N' for the subtask number (or empty for next/clear)."
    ),
    max_size=32768,
)

# ── Args schema ───────────────────────────────────────────────────

@dataclass
class Args:
    path: str
    section: str
    content: str


# ── State helpers ─────────────────────────────────────────────────

def _state_path(manifest_path: Path) -> Path:
    """Return the .state.json path alongside the manifest."""
    return manifest_path.with_name(manifest_path.stem + ".state.json")


def _load_state(state_file: Path) -> dict:
    """Load retry state from .state.json, returning empty dict on miss."""
    if not state_file.exists():
        return {}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_state(state_file: Path, state: dict) -> None:
    """Persist retry state to .state.json."""
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass


def _item_to_key(line: str) -> str:
    """Derive a stable key from a checklist line.

    Examples:
        '- [x] 1. Write tests'  -> 'subtask_1'
        '- [ ] 3. Deploy'       -> 'subtask_3'
    """
    m = re.search(r"- \[[ x]\] (\d+)\.\s*", line)
    if m:
        return f"subtask_{m.group(1)}"
    # Fallback: hash-like key from first 40 chars
    return f"item_{line[:40].strip().replace(' ', '_').replace('.', '_')}"


# ── Verification ──────────────────────────────────────────────────

def _extract_verify_command(line: str) -> str | None:
    """Extract a Verify: `command` from a checklist line."""
    m = re.search(r"Verify:\s*`([^`]+)`", line)
    return m.group(1) if m else None


def _run_verification(cmd: str, timeout: int = 60) -> tuple[bool, str]:
    """Run an allowlisted verification command via subprocess.

    Returns (success, output_or_error).
    """
    # Safety: allowlist check on the base command
    parts = cmd.split()
    if not parts:
        return False, "Empty command"

    base = Path(parts[0]).name
    if base not in _VERIFY_ALLOWLIST:
        return False, f"Command '{base}' not in allowlist: {_VERIFY_ALLOWLIST}"

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, (result.stdout or "").strip()[:2000]
        return False, (result.stderr or result.stdout or "Non-zero exit").strip()[:2000]
    except subprocess.TimeoutExpired:
        return False, f"Verification timed out after {timeout}s"
    except OSError as exc:
        return False, f"OS error: {exc}"


# ── Diff helpers ──────────────────────────────────────────────────

def _find_completed_items(old_section: str, new_section: str) -> list[str]:
    """Diff old vs new section to find items flipped from [ ] to [x].

    Returns list of newly completed lines (from new_section).
    """
    old_lines = old_section.splitlines()
    new_lines = new_section.splitlines()

    # Build sets of completed items by stripped content (ignoring checkbox)
    def _content(line: str) -> str:
        return re.sub(r"^-\s*\[[ x]\]\s*", "", line).strip()

    old_completed = {_content(l) for l in old_lines if re.match(r"^-\s*\[x\]", l)}
    new_completed = {_content(l) for l in new_lines if re.match(r"^-\s*\[x\]", l)}

    newly_completed_content = new_completed - old_completed

    # Return the full lines from new_section that are newly completed
    return [
        line for line in new_lines
        if re.match(r"^-\s*\[x\]", line)
        and _content(line) in newly_completed_content
    ]


# ── Section update ────────────────────────────────────────────────

def _section_header(section: str) -> str:
    """Map section name to markdown header."""
    mapping = {
        "success_criteria": "## Success Criteria",
        "subtasks": "## Subtasks",
        "progress": "## Progress",
        "status": "## Status",
    }
    return mapping.get(section, f"## {section.replace('_', ' ').title()}")


def _extract_section(content: str, section: str) -> str | None:
    """Extract the text between a section header and the next header (or EOF)."""
    header = _section_header(section)
    pattern = re.compile(
        rf"(?m)^{re.escape(header)}\s*\n(.*?)(?=\n## |\Z)",
        re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1).rstrip() if m else None


def _replace_section(content: str, section: str, new_content: str) -> str:
    """Replace a section's body in the manifest content."""
    header = _section_header(section)
    pattern = re.compile(
        rf"({re.escape(header)}\s*\n.*?)(?=\n## |\Z)",
        re.DOTALL,
    )
    replacement = f"{header}\n{new_content}"
    result = pattern.sub(replacement, content, count=1)
    if result == content:
        raise ValueError(f"Could not match section '{section}' for replacement")
    return result


# ── Plan-replacement action helpers ────────────────────────────────

def _parse_subtask_number(line: str) -> int | None:
    """Extract subtask number from a checklist line."""
    m = _CHECKLIST_RE.match(line)
    return int(m.group(1)) if m else None


def _find_subtask_line(lines: list[str], num: int) -> int | None:
    """Find index of subtask line by number, or None."""
    for i, line in enumerate(lines):
        if _parse_subtask_number(line) == num:
            return i
    return None


def _action_block(lines: list[str], num: int) -> tuple[list[str], str]:
    """Block subtask N: change [ ] or [x] to [?]."""
    idx = _find_subtask_line(lines, num)
    if idx is None:
        return lines, f"Subtask {num} not found"
    if re.match(r"- \[\?]", lines[idx]):
        return lines, f"Subtask {num} is already blocked"
    new_lines = list(lines)  # copy to avoid mutating original
    new_lines[idx] = re.sub(r"- \[[ x]\]", "- [?]", new_lines[idx], count=1)
    return new_lines, f"Blocked subtask {num}"


def _action_unblock(lines: list[str], num: int) -> tuple[list[str], str]:
    """Unblock subtask N: change [?] back to [ ]."""
    idx = _find_subtask_line(lines, num)
    if idx is None:
        return lines, f"Subtask {num} not found"
    if not re.match(r"- \[\?]", lines[idx]):
        return lines, f"Subtask {num} is not blocked"
    new_lines = list(lines)  # copy to avoid mutating original
    new_lines[idx] = re.sub(r"- \[\?]", "- [ ]", new_lines[idx], count=1)
    return new_lines, f"Unblocked subtask {num}"


def _action_next(lines: list[str]) -> str:
    """Return first pending ([ ] or [?]) subtask."""
    for line in lines:
        if re.match(r"- \[[ \?]\]", line):
            return f"Next pending: {line.strip()}"
    return "No pending subtasks — all complete or blocked"


def _action_delete(lines: list[str], num: int) -> tuple[list[str], str]:
    """Delete subtask N."""
    idx = _find_subtask_line(lines, num)
    if idx is None:
        return lines, f"Subtask {num} not found"
    new_lines = list(lines)  # copy to avoid mutating original
    del new_lines[idx]
    return new_lines, f"Deleted subtask {num}"


def _action_clear(lines: list[str]) -> tuple[list[str], str]:
    """Clear all subtasks (only checklist lines)."""
    checklist_lines = [l for l in lines if _CHECKLIST_RE.match(l)]
    count = len(checklist_lines)
    return [], f"Cleared {count} subtask(s)"


def _apply_action(section: str, old_section_text: str, content: str) -> tuple[str | None, str]:
    """Apply a plan-replacement action to the subtasks section.

    Returns (new_section_text_or_None, result_message).
    If new_section_text is None, no file write needed (e.g., next, or no-op).
    """
    lines = old_section_text.splitlines()

    if section == "block":
        try:
            num = int(content.strip())
        except (ValueError, AttributeError):
            return None, f"Error: Invalid subtask number: '{content}'"
        new_lines, msg = _action_block(lines, num)
        if new_lines is lines:
            return None, msg  # no-op (already blocked or not found)
        return "\n".join(new_lines), msg

    if section == "unblock":
        try:
            num = int(content.strip())
        except (ValueError, AttributeError):
            return None, f"Error: Invalid subtask number: '{content}'"
        new_lines, msg = _action_unblock(lines, num)
        if new_lines is lines:
            return None, msg  # no-op (not blocked or not found)
        return "\n".join(new_lines), msg

    if section == "next":
        return None, _action_next(lines)

    if section == "delete":
        try:
            num = int(content.strip())
        except (ValueError, AttributeError):
            return None, f"Error: Invalid subtask number: '{content}'"
        new_lines, msg = _action_delete(lines, num)
        if new_lines is lines:
            return None, msg  # not found
        return "\n".join(new_lines), msg

    if section == "clear":
        new_lines, msg = _action_clear(lines)
        return "\n".join(new_lines), msg

    return None, f"Unknown action: {section}"


# ── Run ───────────────────────────────────────────────────────────

def run(
    path: str,
    section: str,
    content: str,
    _ctx: ToolContext | None = None,
) -> str:
    """Update a manifest section with optional auto-verification."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None

    # Validate section name
    section_lower = section.lower().replace(" ", "_")
    if section_lower not in _VALID_SECTIONS:
        return (
            f"Error: Invalid section '{section}'. "
            f"Valid sections: {', '.join(sorted(_VALID_SECTIONS))}"
        )
    section = section_lower

    # Resolve manifest path
    manifest_path = Path(path).resolve()
    if not manifest_path.exists():
        return f"Error: Manifest file not found: {manifest_path}"
    if not manifest_path.is_file():
        return f"Error: Not a file: {manifest_path}"

    # Read manifest
    try:
        old_content = manifest_path.read_text(encoding="utf-8")
    except IOError as exc:
        return f"Error: Cannot read manifest: {exc}"

    # Special handling for status — lives in frontmatter, not a section
    if section == "status":
        # Update frontmatter status field
        status_pattern = re.compile(r'^(status:\s*)"[^"]*"', re.MULTILINE)
        new_status = content.strip().strip('"')
        replacement = f'\\g<1>"{new_status}"'
        new_content = status_pattern.sub(replacement, old_content)
        if new_content == old_content:
            return f"Error: Could not find status field in manifest frontmatter"
        manifest_path.write_text(new_content, encoding="utf-8")
        return f"Updated status to '{new_status}' in {manifest_path}"

    # Plan-replacement actions operate on subtasks section
    if section in _ACTION_SECTIONS:
        old_subtasks = _extract_section(old_content, "subtasks")
        if old_subtasks is None:
            return "Error: No 'subtasks' section found in manifest"
        new_text, msg = _apply_action(section, old_subtasks, content)
        if new_text is not None:
            # Write updated subtasks section
            try:
                new_content = _replace_section(old_content, "subtasks", new_text)
                manifest_path.write_text(new_content + "\n", encoding="utf-8")
            except ValueError as exc:
                return f"Error: {exc}"
            except IOError as exc:
                return f"Error: Cannot write manifest: {exc}"
        return f"{msg} in {manifest_path}"

    # Check section exists
    old_section = _extract_section(old_content, section)
    if old_section is None:
        return f"Error: Section '{section}' not found in manifest. " \
               f"Expected header: {_section_header(section)}"

    # Auto-verify for checklist sections
    if section in ("success_criteria", "subtasks"):
        completed = _find_completed_items(old_section, content)
        if completed:
            state_file = _state_path(manifest_path)
            state = _load_state(state_file)

            for line in completed:
                cmd = _extract_verify_command(line)
                if not cmd:
                    continue

                key = _item_to_key(line)
                entry = state.get(key, {})
                status = entry.get("status", "pending")
                retries_left = entry.get("retries_left", 2)

                # Skip already-verified items
                if status == "verified":
                    continue

                # Run verification
                ok, output = _run_verification(cmd)

                if ok:
                    state[key] = {"status": "verified", "retries_left": 0}
                else:
                    if retries_left > 0:
                        state[key] = {
                            "status": "retrying",
                            "retries_left": retries_left - 1,
                            "last_error": output[:500],
                        }
                        _save_state(state_file, state)
                        return (
                            f"Verification failed for '{line.strip()[:60]}': {output[:200]}. "
                            f"Retries remaining: {retries_left - 1}. "
                            f"Re-run manifest_update to retry."
                        )
                    else:
                        state[key] = {
                            "status": "failed",
                            "retries_left": 0,
                            "last_error": output[:500],
                        }
                        _save_state(state_file, state)
                        return (
                            f"Verification FAILED for '{line.strip()[:60]}': {output[:200]}. "
                            f"No retries remaining. Mark as FAILED or fix and retry."
                        )

            # All verifications passed — persist state
            _save_state(state_file, state)

    # Write updated section
    try:
        new_content = _replace_section(old_content, section, content)
        manifest_path.write_text(new_content + "\n", encoding="utf-8")
    except ValueError as exc:
        return f"Error: {exc}"
    except IOError as exc:
        return f"Error: Cannot write manifest: {exc}"

    return f"Updated '{section}' in {manifest_path}"
