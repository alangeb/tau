#!/usr/bin/env python3
"""Tool template helper - generate tool templates."""

def generate_tool_template(name: str, description: str, args: list[dict] = None) -> str:
    """Generate a tool template."""
    args_code = ""
    if args:
        for arg in args:
            args_code += f"    {arg['name']}: {arg['type']} = Field(description=\"{arg['description']}\")\n"

    template = 'from __future__ import annotations\n\n'
    template += f'name = "{name}"\n'
    template += f'description = """{description}"""\n'
    template += 'timeout = 180\n\n'
    template += 'from pydantic import BaseModel, Field\n\n'
    template += 'class Args(BaseModel):\n'
    template += args_code or '    pass\n'
    template += '\ndef run(agent: \'TauErgon\', tool_call_id: str | None) -> str:\n'
    template += '    return "result"\n'
    return template


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "new_tool"
    description = sys.argv[2] if len(sys.argv) > 2 else "Brief description"
    template = generate_tool_template(name, description)
    print(template)
