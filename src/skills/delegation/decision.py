#!/usr/bin/env python3
"""decision.py — Recommend delegation strategy: subagent vs fork vs background.
Usage: python3 skills/delegation/decision.py <description>
Considers: context needed, isolation, sync vs async, complexity.
"""
import sys, re

def recommend(desc):
    d = desc.lower()
    
    # Background for long-running, independent
    bg_keywords = ['run tests', 'wait for', 'monitor', 'long-running', 'build', 'compile', 'install']
    if any(kw in d for kw in bg_keywords):
        return 'background', 'Long-running/independent — use background_* tools'
    
    # Fork for context-dependent
    fork_keywords = ['context', 'conversation', 'knowledge', 'this project', 'current state', 'inherit']
    if any(kw in d for kw in fork_keywords):
        return 'fork', 'Needs conversation context — use fork'
    
    # Subagent for isolated, well-defined
    sub_keywords = ['isolate', 'fresh', 'clean', 'simple', 'well-defined', 'independent', 'separate']
    if any(kw in d for kw in sub_keywords):
        return 'subagent', 'Isolated task — use subagent (cheapest)'
    
    # Default: subagent for well-defined, fork for complex
    if len(d.split()) > 20:
        return 'fork', 'Complex task — use fork for context'
    return 'subagent', 'Well-defined task — use subagent'

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 skills/delegation/decision.py <task description>")
        print("\nOptions:")
        print("  subagent  — Isolated, blank slate, cheapest")
        print("  fork      — Inherits context, expensive")
        print("  background — Async, independent, no context cost")
        sys.exit(0)
    
    desc = ' '.join(sys.argv[1:])
    method, reason = recommend(desc)
    print(f"{method}: {reason}")

if __name__ == '__main__':
    main()
