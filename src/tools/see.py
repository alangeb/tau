"""Vision tool — load an image and queue it for post-batch injection.

Images are validated, base64-encoded, and queued in `agent._queued_images`.
After the tool batch completes, the framework injects all queued images as
a single multimodal user message, maintaining clean OpenAI alternation.

Vision capability is cached (`agent._vision_supported`) to avoid repeated
errors on non-vision models.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tools import ToolMetadata

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Constants ────────────────────────────────────────────────────────────

VISION_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB hard limit

# Magic bytes for common image formats
_IMAGE_MAGIC: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF", b"WEBP"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/bmp": [b"BM"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],
}


def _validate_image_magic(raw_bytes: bytes) -> str | None:
    """Return MIME type if magic bytes match a known image format, else None."""
    for mime_type, magics in _IMAGE_MAGIC.items():
        for magic in magics:
            if raw_bytes[: len(magic)] == magic:
                return mime_type
    return None


# ── Tool interface ──────────────────────────────────────────────────────

metadata = ToolMetadata(
    name="see",
    description=(
        "Load an image file and queue it for injection into the conversation "
        "context. Images are injected after all tool calls complete, as a single "
        "multimodal user message. Supports JPEG, PNG, WebP, GIF, BMP, and TIFF. "
        "Max 10 MB. Requires a vision-capable model; returns an error immediately "
        "if the model has been confirmed as vision-incompatible."
    ),
    aliases_cmd=["view", "view_image", "image"],
    aliases_arg={"file": "path", "image": "path", "image_path": "path"},
    max_size=8192,  # Small — tool returns brief confirmation
    timeout=30,
)


# ── Args schema ───────────────────────────────────────────────────────────

@dataclass
class Args:
    path: str = field(metadata={"description": "Path to image file (absolute or relative)"})
    description: str = field(default="", metadata={"description": "Optional text description to accompany the image"})


# ── Execution ─────────────────────────────────────────────────────────────

def run(
    path: str,
    agent: "TauErgon",
    tool_call_id: str | None = None,
    description: str = "",
) -> str:
    """Load image and queue for post-batch injection.

    Does NOT inject into context during execution (that would break OpenAI
    alternation mid-batch). Instead, the image is queued and injected after
    all tool calls complete.
    """
    # Check vision capability cache — fail fast if known unsupported
    if agent._vision_supported is False:
        return (
            "Error: This model does not support vision. "
            "Do not call see again."
        )

    image_path = Path(path).resolve()

    # Validate file exists
    if not image_path.is_file():
        return f"Error: File not found: {image_path}"

    # Read raw bytes
    try:
        raw_bytes = image_path.read_bytes()
    except OSError as e:
        return f"Error reading file: {e}"

    # Size limit
    if len(raw_bytes) > VISION_MAX_SIZE_BYTES:
        mb = len(raw_bytes) / (1024 * 1024)
        return f"Error: Image too large ({mb:.1f} MB). Max 10 MB."

    # Validate magic bytes
    detected_mime = _validate_image_magic(raw_bytes)
    if detected_mime is None:
        return f"Error: Not a recognized image file: {image_path.name}"

    # Determine MIME type (prefer detected magic bytes over extension guess)
    mime_type = detected_mime

    # Encode as base64
    b64_data = base64.b64encode(raw_bytes).decode("ascii")
    data_uri = f"data:{mime_type};base64,{b64_data}"

    # Queue for post-batch injection
    # Each entry: (data_uri, mime_type, description, tool_call_id)
    if tool_call_id is None:
        tool_call_id = ""
    agent._queued_images.append((data_uri, mime_type, description, tool_call_id))

    file_size_kb = len(raw_bytes) / 1024
    return (
        f"Queued: {image_path.name} ({file_size_kb:.1f} KB, {mime_type}). "
        f"Will be injected after tool batch completes."
    )
