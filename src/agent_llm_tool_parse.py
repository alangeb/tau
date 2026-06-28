"""Tool-call parsing engine for LLM output (extracted from agent_llm).

Contains:
- Constants: tag delimiters, protocol identifiers, thinking markers
- Regex patterns: 13 tool-call extraction patterns
- Handlers: kind-specific tool-call builders
- Postparse: llm_postparse() — recover missed tool calls and normalize thoughts

This module is intentionally separate from agent_llm to keep the HTTP client,
validation, data models, and invocation logic in their own focused modules.
Re-exported through agent_llm.py facade for backward compatibility.

CRITICAL: Keep token delimiters obfuscated via constants.
Do not inline raw tag literals or "simplify" this during refactors.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Callable

from agent_console import error, warning

# === CONSTANTS ===

# ---------------------------------------------------------------------------
# Delimiter primitives — build tag strings without inlining raw literals.
# ---------------------------------------------------------------------------
LT = "<"
LT_SLASH = LT + "/"
GT = ">"
LT_PIPE = LT + "|"
PIPE_GT = "|" + GT

# ---------------------------------------------------------------------------
# Shared protocol identifiers
# ---------------------------------------------------------------------------
FUNCTION = "function"
ARGUMENTS = "arguments"
TOOL = "tool"
TOOLCALL = "toolcall"
TOOL_CALL_ALT = "tool_call"
PARAMETER_ALT = "parameter"

# ---------------------------------------------------------------------------
# Anthropic-style tool-use markers (pipe-delimited)
# ---------------------------------------------------------------------------
TOOL_USE = "tool_use"
TOOL_USE_OPEN = f"{LT_PIPE}{TOOL_USE}{PIPE_GT}"
TOOL_USE_CLOSE = f"{LT_PIPE}/{TOOL_USE}{PIPE_GT}"

# ---------------------------------------------------------------------------
# Thought markers
# ---------------------------------------------------------------------------
BEGIN_OF_THOUGHT = f"{LT_PIPE}begin_of_thought{PIPE_GT}"
END_OF_THOUGHT = f"{LT_PIPE}end_of_thought{PIPE_GT}"

# XML thinking tag names
THINKING = "thinking"
THINK = "think"
REASON = "reason"
REASONING = "reasoning"


def _tag_pair(name: str) -> tuple[str, str]:
    """Return (open_tag, close_tag) for an XML-style tag."""
    return (f"{LT}{name}{GT}", f"{LT_SLASH}{name}{GT}")


THINKING_TAG_PAIRS: tuple[tuple[str, str], ...] = (
    _tag_pair(THINKING),
    _tag_pair(THINK),
    _tag_pair(REASON),
    _tag_pair(REASONING),
    (BEGIN_OF_THOUGHT, END_OF_THOUGHT),
)


def _incomplete_tag(name: str) -> tuple[str, str]:
    """Return (open, close) raw-tag strings for incomplete tool-call detection."""
    return (f"{LT}{name}{GT}", f"{LT_SLASH}{name}{GT}")


INCOMPLETE_TOOL_CALL_PATTERNS: tuple[str, ...] = (
    *_incomplete_tag("function_call"),
    *_incomplete_tag("name"),
    *_incomplete_tag(ARGUMENTS),
    *_incomplete_tag("TOOLCALL"),
    *_incomplete_tag(TOOL_CALL_ALT),
    *_incomplete_tag(FUNCTION),
    *_incomplete_tag(PARAMETER_ALT),
    *_incomplete_tag(TOOL),
    TOOL_USE_OPEN,
    TOOL_USE_CLOSE,
)

TOOL_CALL_PATTERNS: tuple[str, ...] = (
    f"{LT}function_call{GT}",
    f"{LT}name{GT}",
    f"{LT}{ARGUMENTS}{GT}",
    f"{LT}{TOOL}{GT}",
)

# === POSTPARSE ===

# ── Regex patterns for tool-call extraction ──────────────────────────────

__function_pattern__ = re.compile(
    rf"<{TOOLCALL}>[ \t\n\r]*<{FUNCTION}=(\w+)>(.+?)</{FUNCTION}>[ \t\n\r]*</{TOOLCALL}>",
    re.DOTALL,
)

__function_alt_pattern__ = re.compile(
    rf"<{TOOL_CALL_ALT}>[ \t\n\r]*<{FUNCTION}=(\w+)>(.+?)</{FUNCTION}>[ \t\n\r]*</{TOOL_CALL_ALT}>",
    re.DOTALL,
)

__parameter_alt_pattern__ = re.compile(
    rf"<{PARAMETER_ALT}=([a-zA-Z_]\w*)>[ \t\n\r]*(.*?)[ \t\n\r]*</{PARAMETER_ALT}>",
    re.DOTALL,
)

__anthropic_tool_pattern__ = re.compile(
    rf"{re.escape(TOOL_USE_OPEN)}[ \t\n\r]*{FUNCTION}=(\w+)>(.+?){re.escape(TOOL_USE_CLOSE)}",
    re.DOTALL,
)

# ── Direct XML-style tool call pattern ─────────────────────────────────────
# Matches: <tool_name attr="value" ...>...</tool_name> or <tool_name attr="value" .../>
# Also handles nested tags: <tool_name><inner attr="value"></inner></tool_name>
__direct_xml_pattern__ = re.compile(
    rf"<(\w+)"  # Opening tag with tool name (group 1)
    rf"(?:\s+[^>]*?)?"  # Optional attributes on the opening tag
    rf"(?:/>"  # Self-closing: <tool_name .../>
    rf"|(?:>(.*?)</\1>)"  # Or: <tool_name>...</tool_name> (group 2 = content)
    rf")",
    re.DOTALL,
)

# Regex to extract attribute="value" pairs from XML tags
__xml_attr_pattern__ = re.compile(r'(\w+)="([^"]*)"')

# ── Block-style tool call pattern (U+2591 LIGHT SHADE + >) ──────────────────
# Matches: ░tool_name\n{json_args}
# The ░> is used by some LLMs as a tool-call delimiter.
__block_delim_pattern__ = re.compile(
    r"\u2591>"  # ░> delimiter
    r"(\w+)"  # Tool name (group 1)
    r"\s*\n"  # Newline
    r"(\{[\s\S]*?\})"  # JSON arguments (group 2)
)

# ── Function-tag tool call pattern ───────────────────────────────────────────
# Matches: <|begin_of_function|>{"name": "X", "arguments": {...}}<|end_of_function|>
# Some LLMs output tool calls wrapped in <|begin_of_function|> / <|end_of_function|> tags.
__function_tag_pattern__ = re.compile(
    r"<\|begin_of_function\|>"  # Opening tag
    r"\s*"  # Optional whitespace
    r"(\{[\s\S]*?\})"  # JSON payload (group 1)
    r"\s*"  # Optional whitespace
    r"<\|end_of_function\|>"  # Closing tag
)

# ── Bash command pattern (flexible) ─────────────────────────────────────────
# Matches: <bash><cmd> "command"</cmd></bash> or <bash><cmd="command" /></bash>
# Handles both attribute-style and content-style bash commands.
__bash_flex_pattern__ = re.compile(
    r"<bash>"  # Opening bash tag
    r"[\s\S]*?"  # Any content (non-greedy)
    r"<cmd"  # Opening cmd tag
    r"(?:\s*=\s*\"([^\"]*)\")?"  # Optional cmd="value" attribute (group 1)
    r"(?:\s*>[\s\S]*?\"([^\"]*)\")?"  # Optional content: > "value" (group 2)
    r"[\s\S]*?"  # Any trailing content
    r"</cmd>"  # Closing cmd tag
    r"[\s\S]*?"  # Any trailing content
    r"</bash>"  # Closing bash tag
)

# ── Builtins-style tool call pattern ────────────────────────────────────────
# Matches: <builtins.tool_name params="{...}">
# Some LLMs output tool calls with a "builtins." prefix and params attribute.
__builtins_pattern__ = re.compile(
    r"<builtins\.(\w+)"  # Opening tag with builtins. prefix, capture tool name (group 1)
    r"\s+params="  # params= attribute
    r"\"(\{[^}]*\})\""  # JSON arguments in quotes (group 2)
    r">"  # Closing >
)

# ── Inline JSON tool call pattern ───────────────────────────────────────────
# Matches: <tool_name>{"key": "value"} (no closing tag, JSON directly after >)
# Some LLMs output tool calls as <tool_name>{JSON} without a closing tag.
__inline_json_pattern__ = re.compile(
    r"<(\w+)>"  # Opening tag with tool name (group 1)
    r"(\{[\s\S]*?\})"  # JSON arguments (group 2)
)

# ── Markdown code block tool call pattern ─────────────────────────────────
# Matches: ```json\n{"tool_name": "...", "arguments": {...}}\n```
__markdown_json_pattern__ = re.compile(
    rf"```(?:json)?\s*\n?"  # Opening ``` with optional 'json' tag and newline
    rf"(\{{[\s\S]*?\"tool_name\"\s*:\s*\"(\w+)\"[\s\S]*?\}})"  # JSON with tool_name (group 2)
    rf"[\s\S]*?```",  # Closing ```
    re.DOTALL,
)

# ── Direct subagent/fork task pattern ──────────────────────────────────────
# Matches: <subagent task="..."> or <fork task="...">
__subagent_task_pattern__ = re.compile(
    rf"<(subagent|fork)\s+task=\"([^\"]+)\"[>]?",
    re.DOTALL,
)

# ── tool_name/args XML pattern ──────────────────────────────────────────────
# Matches: <tool_name="file_write"><args>{...JSON...}</args></tool_name>
# This is a common format the LLM uses for tool calls.
# CRITICAL: Must be tried BEFORE __direct_xml_pattern__ to avoid matching
# the inner <args> tag first (which would extract "args" as the tool name).
__tool_name_args_pattern__ = re.compile(
    r'<tool_name="(\w+)">'  # tool_name="X" (group 1)
    r'[\s\S]*?'  # any content (non-greedy)
    r'<args>'  # opening args tag
    r'[\s\S]*?'  # any content before JSON
    r'(\{[\s\S]*?\})'  # JSON content (group 2)
    r'[\s\S]*?'  # any content after JSON
    r'</args>'  # closing args tag
    r'[\s\S]*?'  # trailing content
    r'</tool_name>',  # closing tag
    re.DOTALL,
)

# ── Bash wrapper pattern ────────────────────────────────────────────────────
# Matches: <bash><cmd="command here" /></bash> or <bash><cmd="command here"></cmd></bash>
# The LLM sometimes wraps shell commands in <bash> tags with a <cmd> attribute.
# CRITICAL: Must be tried BEFORE __direct_xml_pattern__ to avoid matching
# the inner <cmd> tag first (which would extract "cmd" as the tool name).
__bash_wrapper_pattern__ = re.compile(
    r'<bash>'  # Opening bash tag
    r'[\s]*'  # Optional whitespace
    r'<cmd'  # Opening cmd tag
    r'\s*=\s*"([^"]*)"'  # cmd="value" (group 1)
    r'[\s]*(?:/?>'  # Self-closing /> or just >
    r'|[\s]*>(?:[\s\S]*?)</cmd>)'  # Or: >...</cmd>
    r'[\s]*'  # Optional trailing whitespace
    r'</bash>',  # Closing bash tag
    re.DOTALL,
)

# ── Block-style tool call pattern ──────────────────────────────────────────
# Matches: `·tool_name\n  key: "value"\n  key2: "value2"\n)`
# This is the format the LLM sometimes uses for tool calls.
# The `·` is U+2591 LIGHT SHADE, rendered as a shaded box in terminals.
__block_tool_pattern__ = re.compile(
    rf"[·]\s*"  # Block start marker (U+2591 LIGHT SHADE)
    rf"(\w+)"  # Tool name (group 1)
    rf"(\n[ \t]*(?:\w+:\s*\"[^\"]*\"[,\s]*)*)?"  # Arguments as key: "value" pairs (group 2)
    rf"\)",  # Closing paren
    re.DOTALL,
)

__thought_pattern__ = re.compile(
    rf"{re.escape(BEGIN_OF_THOUGHT)}(.*?){re.escape(END_OF_THOUGHT)}",
    re.DOTALL,
)

# Maximum body length to prevent pathological over-consumption
ANTHROPIC_MAX_BODY_LEN = 10000

# ── Tool-call validation ─────────────────────────────────────────────────

def _is_valid_toolcall_params(params_json: str) -> bool:
    """Validate JSON-form tool-call payload shape.

    Accepts any non-empty JSON object.  The function name is already captured
    from the ``<function=NAME>`` tag — the body just needs to be a dict of
    arguments (or a dict with a nested ``"arguments"`` string, which is
    unwrapped by ``_build_toolcall``).
    """
    try:
        params = json.loads(params_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False

    if not isinstance(params, dict):
        return False

    # Accept plain argument dicts (e.g. {"file_path": "test.py"})
    # or wrapped dicts with "arguments" field (e.g. from real LLM output).
    if ARGUMENTS in params:
        try:
            args = json.loads(params[ARGUMENTS])
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
        return isinstance(args, dict)

    return True

# ── Parameter coercion ───────────────────────────────────────────────────

# Data-driven coercion table: (regex_pattern, coerce_fn)
# Order matters — first match wins.
_COERCION_RULES = [
    (re.compile(r"^true$", re.IGNORECASE), lambda _: True),
    (re.compile(r"^false$", re.IGNORECASE), lambda _: False),
    (re.compile(r"^(null|none)$", re.IGNORECASE), lambda _: None),
    (re.compile(r"^-?\d+$"), int),
    (re.compile(r"^-?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?$"), float),
]

def _coerce_parameter_value(value: str):
    """Coerce alternate-tag parameter text into a JSON-compatible value.

    Handles booleans, null, integers, floats, and falls back to trimmed string.
    """
    text = value.strip()
    for pattern, coerce_fn in _COERCION_RULES:
        if pattern.fullmatch(text):
            try:
                return coerce_fn(text)
            except (ValueError, TypeError):
                pass
    return text

def _extract_params_from_alt_function_body(function_body: str) -> dict | None:
    """Extract and coerce `PARAMETER_ALT` tags from an alternate function body.

    Returns None if no parameters are found.
    """
    args: dict = {}
    for match in __parameter_alt_pattern__.finditer(function_body):
        param_name = match.group(1)
        raw_value = match.group(2)
        args[param_name] = _coerce_parameter_value(raw_value)

    if not args:
        return None

    return args


def _extract_params_from_direct_xml(match: re.Match[str]) -> dict | None:
    """Extract arguments from a direct XML-style tool call match.

    Handles: <tool_name attr="value" ...>...</tool_name>
    Also extracts attributes from nested tags within the content.

    Returns None if no arguments are found.
    """
    func_name = match.group(1)
    content = match.group(2) or ""

    # Extract attributes from the full match (opening tag attributes)
    full_match = match.group(0)
    args: dict = {}

    # Get the opening tag portion (everything before content or self-closing)
    open_tag_end = full_match.index(">") if ">" in full_match else len(full_match)
    open_tag = full_match[:open_tag_end]

    # Extract attributes from opening tag
    for attr_match in __xml_attr_pattern__.finditer(open_tag):
        attr_name = attr_match.group(1)
        attr_value = attr_match.group(2)
        # Skip if attribute name is the same as the tag name
        if attr_name != func_name:
            args[attr_name] = _coerce_parameter_value(attr_value)

    # Extract attributes from nested tags in content
    if content:
        for attr_match in __xml_attr_pattern__.finditer(content):
            attr_name = attr_match.group(1)
            attr_value = attr_match.group(2)
            args[attr_name] = _coerce_parameter_value(attr_value)

    if not args:
        return None

    return args

# ── Tool-call builders ───────────────────────────────────────────────────

def _build_toolcall(func_name: str, args_source: str | dict) -> dict:
    """Build a canonical tool-call dict.

    ``args_source`` may be a raw JSON string or a pre-parsed dict.
    """
    if isinstance(args_source, dict):
        args_json = json.dumps(args_source)
    else:
        args_json = args_source  # already validated JSON string
        params = json.loads(args_json)
        if ARGUMENTS in params:
            args_json = params[ARGUMENTS]

    result = {
        "id": f"tc_{uuid.uuid4().hex[:16]}",
        "type": FUNCTION,
        FUNCTION: {
            "name": func_name,
            ARGUMENTS: args_json,
        },
        "message_status": "tool_calls",
    }
    return result

# ── Tool-call extraction ─────────────────────────────────────────────────

# Each entry: (compiled_regex, kind_label)
# CRITICAL: __tool_name_args_pattern__ and __bash_wrapper_pattern__ must come BEFORE
# __direct_xml_pattern__ to avoid matching inner tags first.
_TOOL_PATTERNS = [
    (__function_pattern__, "json_block"),
    (__function_alt_pattern__, "alt_parameters"),
    (__anthropic_tool_pattern__, "anthropic_tool"),
    (__tool_name_args_pattern__, "tool_name_args"),
    (__bash_wrapper_pattern__, "bash_wrapper"),
    (__bash_flex_pattern__, "bash_flex"),
    (__function_tag_pattern__, "function_tag"),
    (__builtins_pattern__, "builtins"),
    (__inline_json_pattern__, "inline_json"),
    (__direct_xml_pattern__, "direct_xml"),
    (__block_tool_pattern__, "block_tool"),
    (__markdown_json_pattern__, "markdown_json"),
    (__block_delim_pattern__, "block_delim"),
]


# Auto-derived: all pattern kinds that need tool-name validation.
# Excludes structural patterns (bash_wrapper, bash_flex, tool_name_args)
# which match specific syntax, not arbitrary tag names.
_VALIDATION_KINDS = frozenset(
    k for _, k in _TOOL_PATTERNS
) - frozenset({"bash_wrapper", "bash_flex", "tool_name_args"})


def _extract_params_from_block_tool(args_str: str) -> dict | None:
    """Parse block-style tool call arguments: 'key: "value"\nkey2: "value2"'.

    Handles:
    - key: "value"
    - key: value (unquoted)
    - key: 123, key: true, key: false
    """
    args: dict = {}
    # Match key: "value" or key: value pairs
    for m in re.finditer(r'(\w+):\s*"?([^"\n]*)"?', args_str):
        key = m.group(1)
        value = m.group(2).strip()
        if value:
            args[key] = _coerce_parameter_value(value)

    if not args:
        return None
    return args


# ── Kind-specific tool-call handlers ──────────────────────────────────────
# Each handler: (match, func_name, body) -> dict | None
# Returns None to skip this candidate; returns tool-call dict on success.

def _handle_json_block(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    if not _is_valid_toolcall_params(body):
        return None
    return _build_toolcall(func_name, body)


def _handle_anthropic_tool(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    if body is None:
        return None
    if len(body) > ANTHROPIC_MAX_BODY_LEN:
        return None
    args_dict = _extract_params_from_alt_function_body(body)
    if args_dict is None:
        return None
    return _build_toolcall(func_name, args_dict)


def _handle_direct_xml(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    args_dict = _extract_params_from_direct_xml(match)
    if args_dict is None:
        return None
    return _build_toolcall(func_name, args_dict)


def _handle_block_tool(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    args_dict = _extract_params_from_block_tool(body or "")
    if args_dict is None:
        return None
    return _build_toolcall(func_name, args_dict)


def _handle_markdown_json(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # body is the full JSON string, func_name is the tool_name from group 2
    try:
        json_obj = json.loads(body)
        args_dict = json_obj.get("arguments", {})
        if isinstance(args_dict, str):
            args_dict = json.loads(args_dict)
        if not isinstance(args_dict, dict):
            return None
        return _build_toolcall(func_name, args_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_tool_name_args(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <tool_name="X"><args>{JSON}</args></tool_name>
    # group(1) = tool name, group(2) = JSON string
    json_str = match.group(2) or "{}"
    try:
        args_dict = json.loads(json_str)
        if not isinstance(args_dict, dict):
            return None
        return _build_toolcall(match.group(1), args_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_bash_wrapper(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <bash><cmd="command here" /></bash>
    # group(1) = command string
    return _build_toolcall("bash", {"cmd": match.group(1)})


def _handle_bash_flex(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <bash><cmd> "command"</cmd></bash> or <bash><cmd="command" /></bash>
    # group(1) = cmd="value" attribute, group(2) = content "value"
    cmd_str = match.group(1) or match.group(2) or ""
    if not cmd_str:
        return None
    return _build_toolcall("bash", {"cmd": cmd_str})


def _handle_function_tag(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <|begin_of_function|>{"name": "X", "arguments": {...}}<|end_of_function|>
    # group(1) = JSON payload
    json_str = match.group(1) or "{}"
    try:
        json_obj = json.loads(json_str)
        name = json_obj.get("name", "")
        args_obj = json_obj.get("arguments", {})
        if not name:
            return None
        return _build_toolcall(name, args_obj)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_builtins(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <builtins.tool_name params="{...}">
    # group(1) = tool name (without builtins. prefix)
    # group(2) = JSON arguments
    json_str = match.group(2) or "{}"
    try:
        args_dict = json.loads(json_str)
        if not isinstance(args_dict, dict):
            return None
        return _build_toolcall(func_name, args_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_inline_json(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # <tool_name>{JSON} (no closing tag)
    # group(1) = tool name, group(2) = JSON arguments
    json_str = match.group(2) or "{}"
    try:
        args_dict = json.loads(json_str)
        if not isinstance(args_dict, dict):
            return None
        return _build_toolcall(func_name, args_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_block_delim(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    # ░tool_name\n{json_args}
    # group(1) = tool name, group(2) = JSON string
    json_str = match.group(2) or "{}"
    try:
        args_dict = json.loads(json_str)
        if not isinstance(args_dict, dict):
            return None
        return _build_toolcall(func_name, args_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _handle_alt_parameters(match: re.Match[str], func_name: str, body: str | None) -> dict | None:
    args_dict = _extract_params_from_alt_function_body(body)
    if args_dict is None:
        return None
    return _build_toolcall(func_name, args_dict)


# Dispatch table: kind -> handler
_TOOL_KIND_HANDLERS: dict[str, Callable[[re.Match[str], str, str | None], dict | None]] = {
    "json_block": _handle_json_block,
    "alt_parameters": _handle_alt_parameters,
    "anthropic_tool": _handle_anthropic_tool,
    "tool_name_args": _handle_tool_name_args,
    "bash_wrapper": _handle_bash_wrapper,
    "bash_flex": _handle_bash_flex,
    "function_tag": _handle_function_tag,
    "builtins": _handle_builtins,
    "inline_json": _handle_inline_json,
    "direct_xml": _handle_direct_xml,
    "block_tool": _handle_block_tool,
    "markdown_json": _handle_markdown_json,
    "block_delim": _handle_block_delim,
}

# Invariant: every pattern kind must have a handler
assert set(k for _, k in _TOOL_PATTERNS) == set(
    _TOOL_KIND_HANDLERS.keys()
), f"Pattern kinds mismatch: {set(k for _, k in _TOOL_PATTERNS) ^ set(_TOOL_KIND_HANDLERS.keys())}"


def _extract_toolcall(text: str, valid_tool_names: set[str] | None = None) -> tuple[dict | None, str, bool, str | None]:
    """Extract the first valid tool call from text.

    Searches for JSON, alternate-parameter, Anthropic-format, direct XML, block,
    markdown, and block-delimiter tool call patterns, validates them in text order,
    and returns the first valid one removed from text.

    Args:
        text: Text to search for tool calls in.
        valid_tool_names: Optional set of registered tool names. If provided,
            handlers that match arbitrary tag names will reject non-tool matches.

    Returns:
        (tool_call, cleaned_text, found, kind) where kind is the extraction pattern
        label (e.g. "direct_xml") or None if not found.
    """
    candidates: list[tuple[int, int, str, re.Match[str]]] = []

    for pattern, kind in _TOOL_PATTERNS:
        for match in pattern.finditer(text):
            candidates.append((match.start(), match.end(), kind, match))

    candidates.sort(key=lambda item: item[0])

    for start, end, kind, match in candidates:
        # CRITICAL: Do NOT access group(2) unconditionally — some patterns
        # (e.g., bash_wrapper) only have group(1).  Defer group access to
        # the kind-specific handler below.
        func_name = match.group(1)
        body = None
        try:
            body = match.group(2)
        except IndexError:
            pass  # Pattern has only one capture group; body stays None

        # Tool name validation: reject non-tool names for patterns that can match arbitrary tags.
        # These are patterns where the tool name is a free-form identifier that could match
        # anything (e.g., <foo>{...}, <function name="foo">). Patterns with structural
        # constraints (bash_wrapper, bash_flex) don't need validation since they match
        # specific command syntax, not arbitrary tag names.
        #
        # Auto-derived: all kinds EXCEPT structural patterns (bash_wrapper, bash_flex, tool_name_args).
        if valid_tool_names is not None and kind in _VALIDATION_KINDS:
            if func_name not in valid_tool_names:
                continue

        handler = _TOOL_KIND_HANDLERS[kind]
        tool_call = handler(match, func_name, body)
        if tool_call is None:
            continue

        cleaned_text = text[:start] + text[end:]
        return tool_call, cleaned_text, True, kind

    return None, text, False, None

# ── Thought extraction ───────────────────────────────────────────────────

def _extract_enclosed_thought(
    content: str,
    reasoning: str | None,
) -> tuple[str, str | None, bool]:
    """Move one enclosed thought segment from content into reasoning."""
    match = __thought_pattern__.search(content)
    if match is None:
        return content, reasoning, False

    moved_thought = match.group(1).strip()
    new_content = (content[: match.start()] + content[match.end() :]).strip()

    if moved_thought:
        if isinstance(reasoning, str) and reasoning.strip():
            new_reasoning = f"{reasoning.rstrip()}\n{moved_thought}"
        else:
            new_reasoning = moved_thought
    else:
        new_reasoning = reasoning

    return new_content, new_reasoning, True

# ── Logging helpers ──────────────────────────────────────────────────────

def _truncate_json(safe_dump: str, max_len: int = 500) -> str:
    """Truncate a JSON string at a safe syntactic boundary."""
    if len(safe_dump) <= max_len:
        return safe_dump
    truncated = safe_dump[:max_len]
    for safe_char in (",", "}", "]", '"'):
        last_pos = truncated.rfind(safe_char)
        if last_pos > max_len * 0.8:
            return truncated[: last_pos + 1] + "... (truncated)"
    return truncated + "... (truncated)"

def _log_extracted_tool_call(tool_call: dict, kind: str, context_snippet: str = "") -> None:
    """Log a warning for an extracted tool call (JSON truncated for readability)."""
    safe_dump = json.dumps(tool_call, ensure_ascii=False)
    truncated = _truncate_json(safe_dump)
    msg = f"⚙ postparse extracted tool call [{kind}]: {truncated}"
    if context_snippet:
        msg += f" | context: ...{context_snippet}..."
    warning(msg)

# ── Core postparse logic ─────────────────────────────────────────────────

def _extract_all_tool_calls(text: str, tool_calls: list[dict], valid_tool_names: set[str] | None = None) -> str:
    """Repeatedly extract tool calls from *text*, appending to *tool_calls*.

    Returns the cleaned text after all tool calls are removed.
    """
    while True:
        tool_call, text, found, kind = _extract_toolcall(text, valid_tool_names=valid_tool_names)
        if not found:
            break
        tool_calls.append(tool_call)
        _log_extracted_tool_call(tool_call, kind)
    return text.strip()

def llm_postparse(
    content: str,
    reasoning: str | None,
    tool_calls: list[dict],
    valid_tool_names: set[str] | None = None,
) -> tuple[str, str | None, list[dict]]:
    """Recover missed tool calls and normalize thought segments from LLM output.

    Extracts thought blocks from content into reasoning, then extracts tool calls
    from both content and reasoning text. Modifies ``tool_calls`` in place.

    Args:
        content: Raw content text from the LLM.
        reasoning: Separate reasoning channel content (may be None).
        tool_calls: List to append extracted tool calls to.
        valid_tool_names: Optional set of registered tool names. If provided,
            postparse will reject extracted calls for non-tool names.
    """
    if not isinstance(content, str):
        return content, reasoning, tool_calls

    _pp_t0 = time.perf_counter()
    _pp_input_bytes = len(content.encode("utf-8", errors="replace"))
    if isinstance(reasoning, str):
        _pp_input_bytes += len(reasoning.encode("utf-8", errors="replace"))

    # Move enclosed thoughts from content into reasoning
    while True:
        content, reasoning, moved = _extract_enclosed_thought(content, reasoning)
        if not moved:
            break

    # Extract tool calls from content
    content = _extract_all_tool_calls(content, tool_calls, valid_tool_names=valid_tool_names)

    # Extract tool calls from reasoning (if present)
    if isinstance(reasoning, str):
        reasoning = _extract_all_tool_calls(reasoning, tool_calls, valid_tool_names=valid_tool_names)

    _pp_elapsed = time.perf_counter() - _pp_t0

    # Threshold warnings — one-liner console + audit log (automatic via audit=True)
    if _pp_elapsed > 10.0:
        error(
            f"SLOW postparse: {_pp_elapsed:.1f}s | input={_pp_input_bytes}B"
        )
    elif _pp_elapsed > 1.0:
        warning(
            f"SLOW postparse: {_pp_elapsed:.1f}s | input={_pp_input_bytes}B"
        )

    return content, reasoning, tool_calls

__all__ = [
    # Delimiter primitives
    "LT", "LT_SLASH", "GT", "LT_PIPE", "PIPE_GT",
    # Protocol identifiers
    "FUNCTION", "ARGUMENTS", "TOOL", "TOOLCALL", "TOOL_CALL_ALT", "PARAMETER_ALT",
    # Anthropic-style markers
    "TOOL_USE", "TOOL_USE_OPEN", "TOOL_USE_CLOSE",
    # Thought markers
    "BEGIN_OF_THOUGHT", "END_OF_THOUGHT",
    "THINKING", "THINK", "REASON", "REASONING",
    "THINKING_TAG_PAIRS",
    "INCOMPLETE_TOOL_CALL_PATTERNS",
    "TOOL_CALL_PATTERNS",
    # Thresholds
    "ANTHROPIC_MAX_BODY_LEN",
    # Public API
    "llm_postparse",
]
