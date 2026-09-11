---
description: "see this image, analyze screenshot, load photo for vision model, validate image format and size, queue for context injection (also load: agent-browser, web-research, shell_scripting, freecad)"
keywords: see tool invocation, multimodal context injection, screenshot capture, JPEG PNG WebP format, vision model compatibility
name: image
category: multimedia
---

# Image Handling

## When
"see image", "analyze image", "look at picture", "vision model", "screenshot", "image"

## Tool
`see(path="image.jpg", description="optional")` — loads image, queues for context injection.

## Vision Model Support
- **Gemma 4**, **Qwen 3.6**: vision via multimodal input
- **Non-vision models**: error gracefully — do not retry `see`

## Error Handling
Model lacks vision: pop image user message, remove synthetic assistant turn, mark `see` result as error ("no vision capability").

## Gotchas
- Multiple `see` calls: all queued, injected together
- Mixed with other tools: `see` returns ack, images injected after all tools processed
- Max 10 MB per image
- Formats: JPEG, PNG, WebP, GIF, BMP, TIFF

## Helper
```bash
python3 skills/image/image_check.py <path>  # Validate format, size, dimensions
```

## Related Skills
- `agent-browser` — capture screenshots via browser automation
- `freecad` — wireframe screenshots for 3D verification
- `web-research` — extract visual content from web
- `documentation` — include images in docs
- `shell_scripting` — image file operations
