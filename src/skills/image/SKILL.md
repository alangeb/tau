---
name: image
description: Load and analyze images — see tool, vision models, multimodal context injection. Image, see tool, vision, multimodal, analyze image, look at image, screenshot, picture, visual (also load: agent-browser, web-research, freecad, shell_scripting)
category: multimodal
keywords: image, vision, screenshot, picture, photo, jpeg, png, webp, vision model
---

# Image Handling

## When
"see image", "analyze image", "look at picture", "vision model", "multimodal", "screenshot", "visual analysis"

## Tool
`see(path="image.jpg", description="optional")` — loads image, queues for context injection.

## Workflow
1. `see(path="...")` — queue image
2. Synthetic user message injected with image
3. LLM processes in next turn
4. Describe findings

## Vision Model Support
- **Gemma 4**: Supports vision via multimodal input
- **Qwen 3.6**: Supports vision via multimodal input
- **Non-vision models**: Error gracefully — do not retry `see`

## Error Handling
If model lacks vision: pop image user message, remove synthetic assistant turn, mark `see` result as error ("no vision capability").

## Gotchas
- Multiple `see` calls in one message: all queued, injected together
- Mixed with other tool calls: `see` returns ack, images injected after all tools processed
- Max 10 MB per image
- Formats: JPEG, PNG, WebP, GIF, BMP, TIFF

## Related Skills
- `agent-browser` — capture screenshots via browser automation
- `freecad` — wireframe screenshots for 3D verification
- `web-research` — extract visual content from web
- `shell_scripting` — image file operations
