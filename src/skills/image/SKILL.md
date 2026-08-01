---
name: image
description: "Load and analyze images — see tool, vision models, multimodal. Screenshot analysis, image inspection (also load: agent-browser, freecad, web-research, documentation, shell_scripting)"
category: multimodal
keywords: image, vision, screenshot, picture, photo, jpeg, png, webp, vision model
---

# Image Handling

## When
"see image", "analyze image", "look at picture", "vision model", "multimodal", "screenshot"

## Tool
`see(path="image.jpg", description="optional")` — loads image, queues for context injection.

## Vision Model Support
- **Gemma 4**, **Qwen 3.6**: Supports vision via multimodal input
- **Non-vision models**: Error gracefully — do not retry `see`

## Error Handling
If model lacks vision: pop image user message, remove synthetic assistant turn, mark `see` result as error ("no vision capability").

## Gotchas
- Multiple `see` calls: all queued, injected together
- Mixed with other tools: `see` returns ack, images injected after all tools processed
- Max 10 MB per image
- Formats: JPEG, PNG, WebP, GIF, BMP, TIFF

## Related Skills
- `agent-browser` — capture screenshots via browser automation
- `freecad` — wireframe screenshots for 3D verification
- `web-research` — extract visual content from web
- `documentation` — include images in docs
- `shell_scripting` — image file operations
