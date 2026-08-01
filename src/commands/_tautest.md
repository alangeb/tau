---
description: Test
---
Your mission is to test tau bot (yourself).
You test by running `tau.py` with parameters. Examples:
```bash
./tau.py --llm spark "Hi"
./tau.py --llm spark "test prompt 1" "test prompt 2"
./tau.py --llm spark "X=5, just remember" "do you still remember the value of X?"
```
Always directly run it for your tests. Use `--llm spark` (or the LLM group specified by dream.py).
For your tests, first ensure you understand what to test. Then use your plan tool to make a test plan. Extensively use fork and subagent for your work.
If you find issues, fix them, regardless of whether they are pre-existing or not. Never fix symptoms, always fix the root cause. If you can't find the root cause of an issue, report it in your final report, lets work on it together.
Carefully review your changes. Be very critical. Improve on your changes. Run sanity (no pre-existing issues allowed).
