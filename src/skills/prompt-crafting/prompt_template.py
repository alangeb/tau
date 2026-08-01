#!/usr/bin/env python3
"""Generate delegation prompt templates for subagent, fork, and background tasks."""
import argparse
import sys

SUBAGENT_TEMPLATE = """TASK: {task}
CONTEXT: [add file paths, code snippets, current state]
CONSTRAINTS: [add limits, what not to do]
OUTPUT: [add expected format]
VERIFY: [add how to confirm done]"""

FORK_TEMPLATE = """FOCUS ON: {task}
SKIP: [don't re-explain what it already knows]
DELIVER: [add specific output expected]"""

BACKGROUND_TEMPLATE = """Command: {task}
Keywords for wait: "success|error|done|FAILED|Traceback"
# Ensure command is self-contained, idempotent, outputs status clearly"""

VAGUE_WORDS = {"fix", "the", "code", "it", "this", "that", "stuff", "thing", "things"}

def generate_prompt(kind: str, task: str) -> str:
    """Generate a prompt template for the given delegation kind."""
    templates = {"subagent": SUBAGENT_TEMPLATE, "fork": FORK_TEMPLATE, "background": BACKGROUND_TEMPLATE}
    if kind not in templates:
        print(f"Unknown kind: {kind}. Use: subagent, fork, background", file=sys.stderr)
        sys.exit(1)
    return templates[kind].format(task=task)

def check_prompt(prompt: str) -> tuple[str, list[str]]:
    """Rate prompt quality. Returns (grade, issues)."""
    issues = []
    words = set(w.lower().strip(".,:;") for w in prompt.split())
    
    if len(prompt) < 20:
        issues.append("Too short — add details")
    if len(prompt) < 5:
        issues.append("Too few words — be specific")
    vague_count = sum(1 for w in words if w in VAGUE_WORDS)
    if vague_count > len(words) * 0.5 and len(words) > 0:
        issues.append(f"{vague_count}/{len(words)} words are vague — add specifics")
    if not any(c in prompt for c in [".py", ".js", ".ts", ".md", "/"]):
        issues.append("No file paths — add context")
    if not any(w in prompt.lower() for w in ["test", "verify", "check", "confirm", "done"]):
        issues.append("No success criteria — add verify step")
    
    if len(issues) == 0:
        grade = "A"
    elif len(issues) == 1:
        grade = "B"
    elif len(issues) <= 3:
        grade = "C"
    else:
        grade = "F"
    
    return grade, issues

def main():
    parser = argparse.ArgumentParser(description="Generate delegation prompt templates")
    parser.add_argument("kind", nargs="?", choices=["subagent", "fork", "background"],
                        help="Delegation kind")
    parser.add_argument("task", nargs="?", default="", help="Task description")
    parser.add_argument("--check", type=str, help="Check prompt quality")
    
    args = parser.parse_args()
    
    if args.check:
        grade, issues = check_prompt(args.check)
        print(f"Grade: {grade}/A")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Prompt looks good!")
        return
    
    if not args.kind or not args.task:
        parser.print_help()
        print("\nExamples:", file=sys.stderr)
        print('  prompt_template.py subagent "fix bug in auth.py"', file=sys.stderr)
        print('  prompt_template.py fork "refactor database layer"', file=sys.stderr)
        print('  prompt_template.py --check "fix the code"', file=sys.stderr)
        sys.exit(1)
    
    print(generate_prompt(args.kind, args.task))

if __name__ == "__main__":
    main()
