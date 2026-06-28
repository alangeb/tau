# Image/Vision Integration Gap Analysis
# Files: agent_console.py (facade), agent_console_messages.py, agent_console_display.py, agent_llm_tool_parse.py, agent_input.py

## Summary
The codebase has **zero** vision/multimodal support in the console display and input pipeline. All three files assume message content is always a `str`. When LLMs return multimodal content (list of dicts with `type: "image_url"` or `type: "text"`), these functions will silently break or display garbled output.

---

## 1. agent_console_messages.py (agent_console.py facade delegates here)

### Key Function: `assistant_message_display` (line 92)
```python
assistant_message_display = _msg("success", "[ASSISTANT] {}")
```

**Problem:** This is a declarative template that calls `str.format()` on content. If content is a list (multimodal), `format()` will produce `"[ASSISTANT] [{'type': 'text', 'text': '...'}, {'type': 'image_url', ...}]"` — unreadable garbage.

**Gap:** No handling for `content: str | list[dict]`.

**Fix:** Replace with a proper function that extracts text from multimodal content:
```python
def assistant_message_display(content: str | list[dict] | None) -> None:
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        content = " ".join(parts)
    display_success(f"[ASSISTANT] {content}")
```

### Key Function: `user_echo` (line 91)
```python
user_echo = _msg("info", ">>> {}", writer=lambda t: sys.stdout.write(f"{t}\n"))
```

**Problem:** Same issue — assumes `str`. User input with image references (e.g., "Look at this image: /path/to/img.png") would work as strings, but if content becomes a multimodal list, it breaks.

**Fix:** Same pattern — extract text parts from list content.

---

## 2. agent_console_display.py

### `context_dump` (lines 121-129)
```python
def context_dump(title: str, lines_data: list[dict]) -> None:
    ...
    sys.stdout.write(f"{color}{idx + 1}. [{role}]{tool_info} {color}{content}{Colors.RESET}\n")
```

**Problem:** Line 129 writes `content` directly. If content is a list of multimodal parts, `f"{content}"` produces Python repr of the list.

**Fix:** Use `_extract_text_content()` helper (already exists in agent_context.py:1425) or inline extraction:
```python
text_content = _extract_text_for_display(content)
sys.stdout.write(f"{color}{idx + 1}. [{role}]{tool_info} {color}{text_content}{Colors.RESET}\n")
```

### `context_list_display` (lines 184-200+)
**Problem:** `last_user` extraction assumes string content. Line 194: `last_user = ctx.get("last_user", "")` — if content was a list, this would be the list repr.

### `agent_status` (lines 257-323)
**Problem:** `/status` display shows context message count and token count but has **no indication** of multimodal content. No image count, no vision token tracking.

**Fix:** Add vision/image stats to AgentStatus dataclass and display.

### `print_context_status` (lines 325-360+)
**Problem:** Same — single-line status bar has no vision indicators.

---

## 3. agent_llm_tool_parse.py

### `llm_postparse` (lines 738-789)
```python
def llm_postparse(
    content: str,
    reasoning: str | None,
    tool_calls: list[dict],
    ...
) -> tuple[str, str | None, list[dict]]:
    if not isinstance(content, str):
        return content, reasoning, tool_calls
```

**Problem 1 — Early return on non-string:** Line 756 silently returns non-string content without processing. If content is a multimodal list like `[{"type": "text", "text": "..."}, {"type": "image_url", ...}]`, the function does nothing and returns it as-is. Tool calls embedded in the text portion are never extracted.

**Problem 2 — No image extraction:** Even if content is a string, the function never looks for image references (base64 data, file paths, URLs) that might be embedded in LLM output.

**Problem 3 — Return type mismatch:** Returns `tuple[str, ...]` but content could be `list[dict]` — type annotation is wrong.

**Fix:**
```python
def llm_postparse(
    content: str | list[dict],
    reasoning: str | None,
    tool_calls: list[dict],
    ...
) -> tuple[str | list[dict], str | None, list[dict]]:
    if isinstance(content, list):
        # Extract text parts for tool-call scanning
        text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        text_content = " ".join(text_parts)
        # Extract image URLs
        images = [c for c in content if c.get("type") == "image_url"]
        # Run postparse on text portion
        text_content, reasoning, tool_calls = llm_postparse(text_content, reasoning, tool_calls, ...)
        # Reconstruct multimodal content
        for i, c in enumerate(content):
            if c.get("type") == "text":
                c["text"] = text_content  # replace with cleaned text
        return content, reasoning, tool_calls
    ...
```

---

## 4. agent_input.py

### `InputMessage` (agent_models.py:12-44)
```python
@dataclass
class InputMessage:
    source: str
    content: str  # <-- TYPE IS str, not str | list[dict]
```

**Problem:** `content` field is typed as `str`. Cannot carry multimodal input (e.g., user sends "Look at this screenshot" + image file).

**Fix:** Change to `content: str | list[dict]` and add image attachment field.

### `_read_context_metadata` (lines 124-141)
```python
content = msg.get("content", "")
if len(content) > 80:
    content = content[:77] + "..."
```

**Problem:** Line 137 calls `len()` on content — fails if content is a list. Line 138 does string slicing on content — fails if content is a list.

**Fix:** Use `_extract_text_content()` before length check.

### `_process_input` (lines 377-423)
```python
def _process_input(self, msg: InputMessage) -> str | None:
    ...
    last_assistant = self.agent.context.get_last_assistant()
    ...
    return last_assistant
```

**Problem 1:** `msg.content` is assumed `str` throughout. Line 382: `msg.content.strip()` — fails on list content.

**Problem 2:** `get_last_assistant()` returns raw content which could be a list (multimodal). Then line 354: `assistant_message_display(result)` passes it to the display function which can't handle lists.

**Fix:** Add multimodal-aware extraction before display.

### `_start_input_thread` (lines 223-270)
**Problem:** Input thread reads from stdin as text lines. No mechanism to accept image file paths or base64 data as input.

---

## 5. Cross-cutting: `get_last_assistant` (agent_context.py:1134)
```python
def get_last_assistant(self) -> str | None:
    for msg in reversed(self._messages):
        if msg.get("role") == "assistant":
            return msg.get("content")
```

**Problem:** Return type says `str | None` but `msg["content"]` could be a list for multimodal messages.

**Fix:** Return `str | list[dict] | None` and handle in callers.

---

## PRIORITY FIXES (ranked by impact)

### P0 — Critical (breaks on multimodal content)
1. **`assistant_message_display`** (agent_console_messages.py:92) — Replace `_msg` template with function that handles list content
2. **`llm_postparse`** (agent_llm_tool_parse.py:738) — Handle list content, extract tool calls from text parts
3. **`get_last_assistant`** (agent_context.py:1134) — Fix return type and callers

### P1 — High (silent data loss)
4. **`InputMessage.content`** (agent_models.py:16) — Extend type to support multimodal
5. **`_read_context_metadata`** (agent_input.py:124) — Handle list content for context preview
6. **`context_dump`** (agent_console_display.py:121) — Extract text from multimodal content

### P2 — Medium (missing features)
7. **`agent_status`** (agent_console_display.py:257) — Add vision/image stats
8. **`user_echo`** (agent_console_messages.py:91) — Handle multimodal user input display

### P3 — Nice to have
9. **`_start_input_thread`** — Support image file path input
10. **`print_context_status`** — Add vision indicators to status bar

---

## EXISTING HELPER (already available)
`_extract_text_content()` in agent_context.py:1425-1433 handles str vs list content:
```python
def _extract_text_content(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return " ".join(parts)
    return ""
```
This helper should be made public and used consistently across all display functions.
