#!/usr/bin/env python3
# delegation.py — analyze task, spit out delegation strategy
# caveman style: no classes, no fluff, just logic
import sys
import re

# score task for each strategy, pick winner
def analyze(task):
    t = task.lower()
    # context needed? keywords that mean "i know the stuff"
    ctx_words = ["context", "conversation", "history", "above", "previous", "remember", "inherit", "memory", "know"]
    ctx_score = sum(1 for w in ctx_words if w in t)
    # long running? keywords that mean "takes forever"
    long_words = ["background", "async", "long", "overnight", "build", "train", "compile", "wait", "monitor"]
    long_score = sum(1 for w in long_words if w in t)
    # well defined? keywords that mean "self contained"
    well_words = ["review", "test", "analyze", "check", "lint", "format", "refactor", "edit", "write"]
    well_score = sum(1 for w in well_words if w in t)
    # pick strategy based on scores
    if long_score >= 2 or "async" in t or "background" in t:
        strategy = "background"
        reason = "task is long running or async — use tmux session"
    elif ctx_score >= 2 or "inherit" in t or "memory" in t:
        strategy = "fork"
        reason = "task needs conversation history — fork inherits context"
    elif well_score >= 1 or ctx_score == 0:
        strategy = "subagent"
        reason = "task is well defined — subagent is cheapest"
    else:
        strategy = "subagent"
        reason = "no strong signals — default to subagent (cheapest option)"
    return strategy, reason

def main():
    if len(sys.argv) < 2:
        print("usage: delegation.py 'task description'")
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    strategy, reason = analyze(task)
    print(f"TASK: {task}")
    print(f"STRATEGY: {strategy}")
    print(f"REASON: {reason}")
    # print example invocation
    if strategy == "subagent":
        print(f'INVOKE: subagent(task="{task}")')
    elif strategy == "fork":
        print(f'INVOKE: fork(task="{task}")')
    else:
        print(f'INVOKE: background_run(command="...")')

if __name__ == "__main__":
    main()
