#!/usr/bin/env python3
"""Tool template helper - generate tool templates using dataclass."""

def generate_tool_template(name: str, description: str, args: list[dict] = None) -> str:
    """Generate a tool template with standardized signature."""
    args_code = ""
    arg_defaults = ""
    if args:
        for arg in args:
            default = arg.get('default', '""')
            args_code += f"    {arg['name']}: {arg['type']} = field(default={default}, description=\"{arg['description']}\")\n"
            arg_defaults += f"{arg['name']}: {arg['type']} = {default}, "

    template = 'from __future__ import annotations\n\n'
    template += 'from tools import ToolContext, ToolMetadata\n'
    template += 'from dataclasses import dataclass, field\n\n'
    template += 'metadata = ToolMetadata(\n'
    template += f'    name="{name}",\n'
    template += f'    description="""{description}""",\n'
    template += ')\n\n'
    template += '@dataclass\n'
    template += 'class Args:\n'
    template += args_code or '    pass\n'
    template += f'\ndef run({arg_defaults}_ctx: ToolContext | None = None) -> str:\n'
    template += '    agent = _ctx.agent if _ctx else None\n'
    template += '    tool_call_id = _ctx.tool_call_id if _ctx else None\n'
    template += '    return "result"\n'
    return template


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "new_tool"
    description = sys.argv[2] if len(sys.argv) > 2 else "Brief description"
    template = generate_tool_template(name, description)
    print(template)
