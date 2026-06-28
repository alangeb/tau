#!/usr/bin/env python3
"""Create a task file in tasks/1_todo/."""
import sys, os, datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: task_create.py <title> [priority: high|medium|low]")
        sys.exit(1)
    
    title = " ".join(sys.argv[1:-1]) if len(sys.argv) > 3 else sys.argv[1]
    priority = sys.argv[-1] if sys.argv[-1] in ("high", "medium", "low") else "medium"
    
    slug = title.lower().replace(" ", "-").replace("_", "-")[:50]
    month = datetime.date.today().strftime("%Y-%m")
    
    todo_dir = os.path.expanduser("tasks/1_todo")
    os.makedirs(todo_dir, exist_ok=True)
    
    path = os.path.join(todo_dir, f"{slug}.md")
    if os.path.exists(path):
        print(f"Exists: {path}")
        sys.exit(1)
    
    content = f"""---
id: "{slug}"
title: "{title}"
priority: "{priority}"
created: "{month}"
---

# Task: {title}

## What
[Problem or improvement needed]

## Target
[Component/file/system affected]

## Approach
[How to implement, if known]

## Success Criteria
[Definition of done]

## Testing
[How to verify]
"""
    open(path, 'w').write(content)
    print(f"Created: {path}")

if __name__ == "__main__":
    main()
