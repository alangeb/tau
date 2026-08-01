# Phase 3: Skill Findability Audit — Part B (27 Skills, N-Z + underscore)

## Legend
- ✅ Bidirectional link confirmed
- ❌ Missing bidirectional link (one-way only)
- ⚠️ Keyword concern
- 💡 Suggestion

---

## 1. project-onboard

**Description:** `Understand new project — info, pyscan, pyanalyze, plan, initial reads. Project overview, explore codebase, kickoff (also load: code-review-workflow, review, info, file-ops, shell_scripting)`

**Keywords that would trigger:** "understand project", "new project", "explore codebase", "project overview", "kickoff"
- ✅ Good: "understand", "new project", "explore", "codebase", "overview", "kickoff"
- ⚠️ Missing: "what is this", "codebase tour", "onboard me", "project structure"

**Related Skills listed:** code-review-workflow, review, python_best_practices, dependency_management, readme_template, idea

**Cross-reference check:**
- ↔ code-review-workflow: ✅ (code-review-workflow lists review, python_best_practices, ast-grep, code-simplifier — but NOT project-onboard directly. However, project-onboard → code-review-workflow is ONE-WAY ❌)
- ↔ review: ✅ (review lists project-onboard)
- ↔ python_best_practices: ✅ (pbp lists project-onboard)
- ↔ dependency_management: ✅ (dep_mgmt lists project-onboard)
- ↔ readme_template: ✅ (readme_template lists project-onboard)
- ↔ idea: ✅ (idea lists project-onboard)

**Missing cross-references:**
- ❌ `code-review-workflow` does NOT link back to `project-onboard`
- Should link to `info` (listed in "also load" but not in Related Skills section)

**Suggested description improvement:**
```
Understand new project — pyscan, pyanalyze, plan, initial reads. Project overview, explore codebase, kickoff, what is this codebase, project structure
```

---

## 2. python_best_practices

**Description:** `Python linting, code formatting, type checking — ruff, black, mypy sequence (also load: code-review-workflow, review, git, code-simplifier, file-ops, shell_scripting)`

**Keywords that would trigger:** "python linting", "code formatting", "ruff", "black", "mypy", "type check", "fix style", "format code"
- ✅ Good: "linting", "formatting", "type checking", "ruff", "black", "mypy"
- ⚠️ Missing: "code style", "pep8", "python style", "auto-fix"

**Related Skills listed:** code-review-workflow, review, code-simplifier, dependency_management, project-onboard, git-verify, git

**Cross-reference check:**
- ↔ code-review-workflow: ✅
- ↔ review: ✅
- ↔ code-simplifier: ✅
- ↔ dependency_management: ✅ (dep_mgmt lists python_best_practices)
- ↔ project-onboard: ✅
- ↔ git-verify: ❌ (git-verify lists code-review-workflow, review — NOT python_best_practices)
- ↔ git: ✅ (git lists python_best_practices)

**Missing cross-references:**
- ❌ `git-verify` does NOT link back to `python_best_practices`

**Suggested description improvement:**
```
Python linting, code formatting, type checking — ruff, black, mypy. Code style, pep8, auto-fix, python style guide
```

---

## 3. python_debugging

**Description:** `Debug Python — background sessions, breakpoints, trace execution, interactive pdb (also load: bug_investigation, background)`

**Keywords that would trigger:** "debug python", "pdb", "breakpoint", "trace execution", "interactive debugging"
- ✅ Good: "debug", "pdb", "breakpoint", "trace", "interactive"
- ⚠️ Missing: "python crash", "python error", "find bug", "traceback analysis"

**Related Skills listed:** bug_investigation, code-review-workflow, background

**Cross-reference check:**
- ↔ bug_investigation: ✅ (bug_investigation lists python_debugging)
- ↔ code-review-workflow: ❌ (code-review-workflow does NOT list python_debugging)
- ↔ background: ✅ (background lists... let me check — background lists tmux_monitoring, test-suite-monitor, context_management, tau_testsuite — NOT python_debugging ❌)

**Missing cross-references:**
- ❌ `code-review-workflow` does NOT link back to `python_debugging`
- ❌ `background` does NOT link back to `python_debugging`
- Should link to `tau_audit` (for log-based debugging)

**Suggested description improvement:**
```
Debug Python — background sessions, breakpoints, trace execution, interactive pdb. Python crash, traceback, find bug, error investigation
```

---

## 4. readme_template

**Description:** `README structure — tool/command/skill documentation patterns. Readme, documentation template, project readme (also load: project-onboard, skill_template, command_template)`

**Keywords that would trigger:** "write readme", "readme structure", "document project", "update readme"
- ✅ Good: "readme", "documentation", "template", "project"
- ⚠️ Missing: "write documentation", "project docs", "readme.md"

**Related Skills listed:** project-onboard, skill_template, command_template, documentation

**Cross-reference check:**
- ↔ project-onboard: ✅
- ↔ skill_template: ✅
- ↔ command_template: ✅ (command_template lists skill_template, tool_template, caveman, _taudoc — NOT readme_template ❌)
- ↔ documentation: ✅ (documentation lists _taudoc, readme_template)

**Missing cross-references:**
- ❌ `command_template` does NOT link back to `readme_template`

**Suggested description improvement:**
```
README structure — tool/command/skill documentation patterns. Write readme, documentation template, project readme, readme.md format
```

---

## 5. reference

**Description:** `Tau quick reference — commands, configs, patterns, audit log patterns (also load: command_template, shell_scripting, skill_template)`

**Keywords that would trigger:** "quick reference", "cheat sheet", "tau commands", "tau config", "tau patterns"
- ✅ Good: "quick reference", "commands", "config", "patterns"
- ⚠️ Missing: "tau overview", "how does tau work", "tau basics"

**Related Skills listed:** command_template, shell_scripting, skill_template, tau_audit

**Cross-reference check:**
- ↔ command_template: ❌ (command_template lists skill_template, tool_template, caveman, _taudoc — NOT reference)
- ↔ shell_scripting: ✅
- ↔ skill_template: ✅
- ↔ tau_audit: ❌ (tau_audit lists info, bug_investigation, context_management, shell_scripting, error-recovery, dream, tauskillmaintenance, git-advanced, skill_template, wiki, performance — NOT reference)

**Missing cross-references:**
- ❌ `command_template` does NOT link back to `reference`
- ❌ `tau_audit` does NOT link back to `reference`

**Suggested description improvement:**
```
Tau quick reference — commands, configs, patterns, audit log patterns. Cheat sheet, tau overview, how tau works, tau basics
```

---

## 6. review

**Description:** `Code review process — detailed analysis, inventory, improvement plan (also load: code-review-workflow, python_best_practices, ast-grep, code-simplifier, git, project-onboard)`

**Keywords that would trigger:** "code review", "review code quality", "assess code", "evaluate code", "deep review"
- ✅ Good: "code review", "review code", "assess code", "evaluate code"
- ⚠️ Missing: "review this", "check this code", "quality check"

**Related Skills listed:** code-review-workflow, python_best_practices, ast-grep, code-simplifier, git, project-onboard, git-verify

**Cross-reference check:**
- ↔ code-review-workflow: ✅
- ↔ python_best_practices: ✅
- ↔ ast-grep: ✅ (ast-grep lists review)
- ↔ code-simplifier: ✅
- ↔ git: ✅
- ↔ project-onboard: ✅
- ↔ git-verify: ❌ (git-verify lists code-review-workflow, review — wait, it DOES list review ✅)

**Missing cross-references:**
- ❌ `spec` lists `review` as related but `review` does NOT list `spec` (should for spec-driven workflow)

**Suggested description improvement:**
```
Code review process — detailed analysis, inventory, improvement plan. Review this, check this code, quality assessment, code evaluation
```

---

## 7. search-replace

**Description:** `Find and replace patterns across files — grep, file_read, file_edit, verify. Text substitution, bulk edit, refactoring (also load: ast-grep, file-ops, code-review-workflow, git-verify)`

**Keywords that would trigger:** "find and replace", "update pattern", "bulk edit", "rename variable", "change all occurrences"
- ✅ Good: "find and replace", "bulk edit", "rename", "refactoring"
- ⚠️ Missing: "search and replace", "global replace", "find all"

**Related Skills listed:** ast-grep, code-review-workflow, git-verify, file-ops, shell_scripting

**Cross-reference check:**
- ↔ ast-grep: ✅ (ast-grep lists search-replace)
- ↔ code-review-workflow: ❌ (code-review-workflow does NOT list search-replace)
- ↔ git-verify: ❌ (git-verify lists code-review-workflow, review — NOT search-replace)
- ↔ file-ops: ✅ (file-ops lists search-replace)
- ↔ shell_scripting: ✅

**Missing cross-references:**
- ❌ `code-review-workflow` does NOT link back to `search-replace`
- ❌ `git-verify` does NOT link back to `search-replace`

**Suggested description improvement:**
```
Find and replace patterns across files — grep, file_read, file_edit, verify. Search and replace, text substitution, bulk edit, global replace, refactoring
```

---

## 8. security-audit

**Description:** `Security checks — API keys, config permissions, sensitive data in logs. Security, vulnerability scan, secrets, sensitive data (also load: bug_investigation, code-review-workflow)`

**Keywords that would trigger:** "security check", "dependency audit", "secrets scan", "sensitive files", "vulnerability check"
- ✅ Good: "security", "vulnerability", "secrets", "sensitive", "API key"
- ⚠️ Missing: "security scan", "leaked credentials", "exposed keys"

**Related Skills listed:** dependency_management, bug_investigation, code-review-workflow, git

**Cross-reference check:**
- ↔ dependency_management: ❌ (dep_mgmt lists python_best_practices, project-onboard — NOT security-audit)
- ↔ bug_investigation: ✅ (bug_investigation lists... let me check — bug_investigation lists code-review-workflow, ast-grep, graphify, python_debugging, think — NOT security-audit ❌)
- ↔ code-review-workflow: ❌ (code-review-workflow does NOT list security-audit)
- ↔ git: ✅ (git lists security-audit)

**Missing cross-references:**
- ❌ `dependency_management` does NOT link back to `security-audit`
- ❌ `bug_investigation` does NOT link back to `security-audit`
- ❌ `code-review-workflow` does NOT link back to `security-audit`

**Suggested description improvement:**
```
Security checks — API keys, config permissions, sensitive data in logs. Security scan, vulnerability, secrets, leaked credentials, exposed keys, sensitive data
```

---

## 9. shell_scripting

**Description:** `Tau bash patterns — audit log processing, test output parsing, worktree operations. Shell script, awk, sed, grep, find (also load: background, reference, search-replace, file-ops)`

**Keywords that would trigger:** "bash pattern", "audit log processing", "test output parsing", "shell one-liner", "bash script"
- ✅ Good: "bash", "shell", "script", "awk", "sed", "grep", "find"
- ✅ Very comprehensive keyword list

**Related Skills listed:** background, agent-browser, tau_audit, tau_testsuite, command_template, search-replace, reference, file-ops

**Cross-reference check:**
- ↔ background: ✅
- ↔ agent-browser: ✅ (agent-browser lists shell_scripting)
- ↔ tau_audit: ✅
- ↔ tau_testsuite: ✅
- ↔ command_template: ❌ (command_template lists skill_template, tool_template, caveman, _taudoc — NOT shell_scripting)
- ↔ search-replace: ✅
- ↔ reference: ✅
- ↔ file-ops: ✅

**Missing cross-references:**
- ❌ `command_template` does NOT link back to `shell_scripting`

**Suggested description improvement:**
No significant changes needed. Description is already comprehensive.

---

## 10. signal-cli

**Description:** `Signal CLI and JSON-RPC API — send/receive messages, daemon setup, account management. Signal messenger, messaging, chat automation (also load: background)`

**Keywords that would trigger:** "send signal message", "signal CLI", "signal daemon", "receive signal"
- ✅ Good: "signal", "messenger", "messaging", "chat", "send message"
- ⚠️ Niche skill — unlikely to be accidentally triggered, which is fine

**Related Skills listed:** shell_scripting, background

**Cross-reference check:**
- ↔ shell_scripting: ❌ (shell_scripting does NOT list signal-cli)
- ↔ background: ❌ (background does NOT list signal-cli)

**Missing cross-references:**
- ❌ `shell_scripting` does NOT link back to `signal-cli` (arguably OK since signal-cli is niche)
- ❌ `background` does NOT link back to `signal-cli`

**Suggested description improvement:**
No significant changes needed. Niche skill with appropriate specificity.

---

## 11. skill_template

**Description:** `Create and modify skills — format, structure, helper (also load: tool_template, command_template, caveman, _taudoc, readme_template, documentation)`

**Keywords that would trigger:** "create skill", "skill format", "new skill", "skill template", "write skill"
- ✅ Good: "create skill", "skill format", "new skill", "skill template"
- ⚠️ Missing: "add skill", "define skill", "skill structure"

**Related Skills listed:** tool_template, command_template, tauskillmaintenance, caveman, _taudoc, tau_audit, dream, task_creation, reference, readme_template

**Cross-reference check:**
- ↔ tool_template: ✅
- ↔ command_template: ✅
- ↔ tauskillmaintenance: ✅
- ↔ caveman: ✅ (caveman lists skill_template)
- ↔ _taudoc: ✅
- ↔ tau_audit: ❌ (tau_audit lists skill_template ✅)
- ↔ dream: ✅ (dream lists... dream lists task, task_creation, _taudoc, tauskillmaintenance, tau_audit — NOT skill_template ❌)
- ↔ task_creation: ✅ (task_creation lists skill_template)
- ↔ reference: ❌ (reference lists command_template, shell_scripting, skill_template ✅)
- ↔ readme_template: ✅

**Missing cross-references:**
- ❌ `dream` does NOT link back to `skill_template`

**Suggested description improvement:**
```
Create and modify skills — format, structure, helper. Add skill, define skill, skill structure, skill creation
```

---

## 12. swe_bench

**Description:** `SWE-bench workflow — fix agent, eval pipeline, analysis, artifacts (also load: docker, background, bug_investigation, tau_audit, git)`

**Keywords that would trigger:** "SWE-bench", "SWE-lite", "SWE-live", "fix agent", "eval pipeline", "patch creation"
- ✅ Good: "SWE-bench", "SWE-lite", "SWE-live", "fix agent", "eval", "patch", "benchmark"
- ⚠️ Missing: "SWE benchmark", "evaluation pipeline"

**Related Skills listed:** docker, background, bug_investigation, tau_audit, git

**Cross-reference check:**
- ↔ docker: ❌ (docker lists background, bug_investigation — NOT swe_bench)
- ↔ background: ❌ (background does NOT list swe_bench)
- ↔ bug_investigation: ❌ (bug_investigation lists code-review-workflow, ast-grep, graphify, python_debugging, think — NOT swe_bench)
- ↔ tau_audit: ❌ (tau_audit does NOT list swe_bench)
- ↔ git: ❌ (git does NOT list swe_bench)

**Missing cross-references:**
- ❌ `docker` does NOT link back to `swe_bench` (should, since SWE-bench is a major docker use case)
- ❌ `background` does NOT link back to `swe_bench`
- ❌ `bug_investigation` does NOT link back to `swe_bench`
- ❌ `tau_audit` does NOT link back to `swe_bench`
- ❌ `git` does NOT link back to `swe_bench`

**Suggested description improvement:**
```
SWE-bench workflow — fix agent, eval pipeline, analysis, artifacts. SWE benchmark, evaluation pipeline, patch creation, test case
```

---

## 13. task

**Description:** `Task framework — lifecycle, verification, state management. Task files, dream execution, idea-to-task pipeline, status verification (also load: dream, idea, task_creation, _taudoc)`

**Keywords that would trigger:** "task status", "verify task", "is task done", "task framework", "task lifecycle"
- ✅ Very comprehensive keyword list (task, tasks, task framework, task lifecycle, task status, task verification, task state, dream task, idea, idea capture, task queue, task done, task failed, task inprogress, task todo, automate, automation, task file, task completion, task review, task check, verify task, is task done, task progress)
- ⚠️ OVERLOADED: This description has ~25 keywords, risking false positives. Consider splitting "idea" keywords to `idea` skill.

**Related Skills listed:** dream, idea, task_creation, _taudoc, wiki

**Cross-reference check:**
- ↔ dream: ✅
- ↔ idea: ✅
- ↔ task_creation: ✅
- ↔ _taudoc: ❌ (_taudoc lists tau_audit, skill_template, command_template, documentation, task, dream ✅ — actually _taudoc DOES list task)
- ↔ wiki: ✅

**Missing cross-references:**
- Should link to `plan_template` (task planning is closely related)

**Suggested description improvement:**
```
Task framework — lifecycle, verification, state management. Task files, dream execution, idea-to-task pipeline, status verification, task queue
```
Remove "idea" keywords (overlap with `idea` skill). Keep task-focused keywords.

---

## 14. task_creation

**Description:** `Create tasks for dream execution — .md files in tasks/1_todo/. Queue task, schedule improvement, defer work (also load: task, dream, idea, skill_template)`

**Keywords that would trigger:** "create task", "new task", "queue task", "schedule improvement", "defer work"
- ✅ Good: "create task", "new task", "queue task", "schedule improvement"
- ⚠️ Missing: "add task", "defer task", "schedule task"

**Related Skills listed:** task, dream, idea, skill_template, wiki

**Cross-reference check:**
- ↔ task: ✅
- ↔ dream: ✅
- ↔ idea: ✅
- ↔ skill_template: ✅
- ↔ wiki: ✅

**Missing cross-references:**
- Should link to `plan_template` (task creation relates to planning)

**Suggested description improvement:**
```
Create tasks for dream execution — .md files in tasks/1_todo/. Queue task, add task, schedule improvement, defer work, schedule task
```

---

## 15. tau_audit

**Description:** `Analyze Tau log files — agent behavior, errors, loops, tool usage (also load: bug_investigation, _taudoc, shell_scripting, tauskillmaintenance)`

**Keywords that would trigger:** "analyze audit", "audit file", "context file", "tau log", "session review", "agent behavior"
- ✅ Good: "audit", "analyze", "logs", "session", "behavior", "errors", "loops", "tool usage"
- ⚠️ Missing: "session analysis", "what happened", "debug session"

**Related Skills listed:** info, bug_investigation, context_management, shell_scripting, error-recovery, dream, tauskillmaintenance, git-advanced, skill_template, wiki, performance

**Cross-reference check:**
- ↔ info: ❌ (info lists context_management, tau_audit ✅ — actually info DOES list tau_audit)
- ↔ bug_investigation: ❌ (bug_investigation lists code-review-workflow, ast-grep, graphify, python_debugging, think — NOT tau_audit)
- ↔ context_management: ❌ (context_management lists background, think, info — NOT tau_audit)
- ↔ shell_scripting: ✅
- ↔ error-recovery: ❌ (error-recovery lists bug_investigation, tau_audit ✅ — actually error-recovery DOES list tau_audit)
- ↔ dream: ❌ (dream lists task, task_creation, _taudoc, tauskillmaintenance, tau_audit ✅ — actually dream DOES list tau_audit)
- ↔ tauskillmaintenance: ✅
- ↔ git-advanced: ❌ (git-advanced lists git, bug_investigation, tau_audit ✅ — actually git-advanced DOES list tau_audit)
- ↔ skill_template: ❌ (skill_template lists tool_template, command_template, tauskillmaintenance, caveman, _taudoc, tau_audit ✅ — actually skill_template DOES list tau_audit)
- ↔ wiki: ✅
- ↔ performance: ❌ (performance lists bug_investigation, tau_audit ✅ — actually performance DOES list tau_audit)

**Missing cross-references:**
- ❌ `bug_investigation` does NOT link back to `tau_audit` (should, since audit logs help investigate bugs)
- ❌ `context_management` does NOT link back to `tau_audit`

**Suggested description improvement:**
```
Analyze Tau log files — agent behavior, errors, loops, tool usage. Session analysis, what happened, debug session, audit log, tau logs
```

---

## 16. _taudoc

**Description:** `Maintain TauErgon docs — designs/, TAU.md, AGENT.md (also load: tau_audit, skill_template, documentation, command_template, dream)`

**Keywords that would trigger:** "update docs", "documentation structure", "designs folder", "TAU.md", "AGENT.md"
- ✅ Good: "documentation", "doc structure", "tau docs", "design documents"
- ⚠️ Missing: "update documentation", "sync docs", "maintain docs", "doc maintenance"

**Related Skills listed:** tau_audit, skill_template, command_template, documentation, task, dream

**Cross-reference check:**
- ↔ tau_audit: ✅
- ↔ skill_template: ✅
- ↔ command_template: ✅
- ↔ documentation: ✅ (documentation lists _taudoc)
- ↔ task: ✅ (task lists _taudoc)
- ↔ dream: ✅ (dream lists _taudoc)

**Missing cross-references:**
- Should link to `readme_template` (documentation structure is related)

**Suggested description improvement:**
```
Maintain TauErgon docs — designs/, TAU.md, AGENT.md. Update documentation, sync docs, doc maintenance, documentation structure
```

---

## 17. tauskillmaintenance

**Description:** `Periodic skill maintenance — 7-phase audit, cross-reference check, gap analysis, helper file audit, usage tracking (also load: skill_template, command_template, caveman, tau_audit, dream, tool_template, grep_tool, context_management, file-ops, shell_scripting, code-review-workflow, plan_template, info, background, image, web-research, think, wiki)`

**Keywords that would trigger:** "skill audit", "maintain skills", "update skills", "skill maintenance", "review skills"
- ✅ Good: "skill maintenance", "skill audit", "skill quality", "skill review"
- ⚠️ "also load" list is OVERLOADED (18 skills). This is excessive and dilutes the purpose.

**Related Skills listed:** skill_template, command_template, tool_template, caveman, tau_audit, dream, wiki

**Cross-reference check:**
- ↔ skill_template: ✅
- ↔ command_template: ❌ (command_template lists skill_template, tool_template, caveman, _taudoc — NOT tauskillmaintenance)
- ↔ tool_template: ✅
- ↔ caveman: ✅
- ↔ tau_audit: ✅
- ↔ dream: ❌ (dream lists task, task_creation, _taudoc, tauskillmaintenance ✅ — actually dream DOES list tauskillmaintenance)
- ↔ wiki: ❌ (wiki lists dream, task, task_creation, web-research, documentation, graphify — NOT tauskillmaintenance)

**Missing cross-references:**
- ❌ `command_template` does NOT link back to `tauskillmaintenance`
- ❌ `wiki` does NOT link back to `tauskillmaintenance`

**Suggested description improvement:**
Trim the "also load" list to 5-7 most critical skills:
```
Periodic skill maintenance — 7-phase audit, cross-reference check, gap analysis, helper file audit, usage tracking (also load: skill_template, tau_audit, dream, tool_template, command_template, caveman)
```

---

## 18. tau_testsuite

**Description:** `Tool test suite guide — run tests, fast A2A tests, structured testcases, helpers. Sanity check, test runner (also load: test-suite-monitor, dependency_management, background)`

**Keywords that would trigger:** "create test", "test suite", "write test case", "test structure", "test helpers"
- ✅ Good: "test suite", "run tests", "sanity check", "test runner"
- ⚠️ Missing: "write tests", "test cases", "test automation" in description (only in keywords)

**Related Skills listed:** test-suite-monitor, background, shell_scripting, dependency_management

**Cross-reference check:**
- ↔ test-suite-monitor: ✅
- ↔ background: ✅
- ↔ shell_scripting: ✅
- ↔ dependency_management: ❌ (dependency_management lists python_best_practices, project-onboard — NOT tau_testsuite)

**Missing cross-references:**
- ❌ `dependency_management` does NOT link back to `tau_testsuite`

**Suggested description improvement:**
```
Tool test suite guide — run tests, write tests, fast A2A tests, structured testcases, helpers. Sanity check, test runner, test automation
```

---

## 19. test-suite-monitor

**Description:** `Run test suite in background, monitor progress, detect completion, report results (also load: background, tau_testsuite, tmux_monitoring)`

**Keywords that would trigger:** "run tests", "monitor tests", "run test suite", "background tests"
- ✅ Good: "test", "suite", "monitor", "background", "run tests", "progress", "completion"
- ⚠️ Missing: "watch tests", "test progress"

**Related Skills listed:** background, tmux_monitoring, tau_testsuite

**Cross-reference check:**
- ↔ background: ✅
- ↔ tmux_monitoring: ✅
- ↔ tau_testsuite: ✅

**Missing cross-references:**
- Should link to `shell_scripting` (test output parsing uses shell)

**Suggested description improvement:**
```
Run test suite in background, monitor progress, detect completion, report results. Watch tests, test progress, background testing
```

---

## 20. think

**Description:** `Deep reasoning tool — stuck loops, mid-execution reassessment, complex planning. Think hard, deep analysis (also load: context_management, bug_investigation, plan_template)`

**Keywords that would trigger:** "think hard", "deep analysis", "stuck in loop", "reassess", "complex planning"
- ⚠️ Description is VAGUE. Users say "I'm stuck", "help me figure this out", "think through this" — description should include these phrases.
- ⚠️ Missing: "I'm stuck", "figure this out", "analyze situation"

**Related Skills listed:** context_management, bug_investigation, plan_template

**Cross-reference check:**
- ↔ context_management: ✅
- ↔ bug_investigation: ❌ (bug_investigation lists code-review-workflow, ast-grep, graphify, python_debugging, think ✅ — actually bug_investigation DOES list think)
- ↔ plan_template: ❌ (plan_template lists code-review-workflow, idea, think ✅ — actually plan_template DOES list think)

**Missing cross-references:**
- Should link to `tau_audit` (for loop detection via logs)

**Suggested description improvement:**
```
Deep reasoning tool — stuck loops, mid-execution reassessment, complex planning. I'm stuck, think through this, deep analysis, figure this out, analyze situation
```

---

## 21. tmux_monitoring

**Description:** `Monitor tmux sessions — polling intervals, completion detection, anti-patterns (also load: background, test-suite-monitor)`

**Keywords that would trigger:** "monitor tmux", "poll background", "check session status", "background monitoring"
- ✅ Good: "tmux", "monitor", "session", "polling", "background", "completion"
- ⚠️ Missing: "wait for background", "check background task"

**Related Skills listed:** background, test-suite-monitor

**Cross-reference check:**
- ↔ background: ✅
- ↔ test-suite-monitor: ✅

**Missing cross-references:**
- Should link to `tau_testsuite` (test monitoring uses tmux)
- Should link to `shell_scripting` (shell patterns for monitoring)

**Suggested description improvement:**
```
Monitor tmux sessions — polling intervals, completion detection, anti-patterns. Wait for background, check background task, session monitoring
```

---

## 22. tool_template

**Description:** `Create agent tools — dataclass Args, run() function, ToolMetadata. Create tool, tool format, new tool, tool definition, custom tool (also load: skill_template, command_template)`

**Keywords that would trigger:** "create tool", "tool format", "new tool", "tool template", "write tool"
- ✅ Good: "tool", "create tool", "tool format", "tool definition", "custom tool"
- ⚠️ Missing: "add tool", "define tool", "tool creation"

**Related Skills listed:** tauskillmaintenance, skill_template, command_template

**Cross-reference check:**
- ↔ tauskillmaintenance: ✅
- ↔ skill_template: ✅
- ↔ command_template: ✅

**Missing cross-references:**
- Should link to `caveman` (tool descriptions should be concise)

**Suggested description improvement:**
```
Create agent tools — dataclass Args, run() function, ToolMetadata. Create tool, add tool, tool format, new tool, tool definition, custom tool, tool creation
```

---

## 23. web-research

**Description:** `Web research — search, lookup, fetch, crawl (also load: agent-browser, graphify, image)`

**Keywords that would trigger:** "search web", "look up", "research topic", "find information", "web search"
- ✅ Good: "web", "search", "lookup", "research", "find", "browse", "google"
- ⚠️ Missing: "look up information", "find on web", "search online"

**Related Skills listed:** image, agent-browser, shell_scripting, tau_audit, graphify

**Cross-reference check:**
- ↔ image: ❌ (image lists agent-browser, web-research ✅ — actually image DOES list web-research)
- ↔ agent-browser: ✅ (agent-browser lists web-research)
- ↔ shell_scripting: ✅
- ↔ tau_audit: ❌ (tau_audit does NOT list web-research)
- ↔ graphify: ✅ (graphify lists web-research)

**Missing cross-references:**
- ❌ `tau_audit` does NOT link back to `web-research` (arguably OK, not closely related)

**Suggested description improvement:**
```
Web research — search, lookup, fetch, crawl. Look up information, find on web, search online, web search, browse internet
```

---

## 24. wiki

**Description:** `Local LLM-searchable wiki — store, retrieve, organize, maintain knowledge (also load: dream, task, task_creation, web-research, documentation, graphify, tau_audit)`

**Keywords that would trigger:** "store information", "add to wiki", "search wiki", "wiki structure", "retrieve knowledge"
- ✅ Very comprehensive keyword list (wiki, knowledge base, store information, retrieve knowledge, maintain wiki, local wiki, wiki add, wiki search, wiki maintain, wiki structure, wiki organize, session ingest, audit ingest, query, lint, ingest, maintain, cleanup)
- ⚠️ Slightly overloaded but appropriate for a multi-purpose skill

**Related Skills listed:** dream, task, task_creation, web-research, documentation, graphify

**Cross-reference check:**
- ↔ dream: ✅
- ↔ task: ✅
- ↔ task_creation: ✅
- ↔ web-research: ✅
- ↔ documentation: ✅ (documentation lists _taudoc, readme_template — NOT wiki ❌)
- ↔ graphify: ❌ (graphify lists bug_investigation, web-research, code-review-workflow — NOT wiki)

**Missing cross-references:**
- ❌ `documentation` does NOT link back to `wiki`
- ❌ `graphify` does NOT link back to `wiki`
- ❌ `tauskillmaintenance` does NOT link back to `wiki` (wiki is in tauskillmaintenance's also-load but not in Related Skills)

**Suggested description improvement:**
No significant changes needed. Description is already comprehensive.

---

## 25. spec

**Description:** `Spec-driven development workflow (also load: review, git)`

**Keywords that would trigger:** "spec-driven", "spec workflow", "write spec", "implement from spec"
- ⚠️ Description is TOO NARROW. Missing: "design spec", "acceptance criteria", "TDD", "spec first", "specification"
- ⚠️ Only 2 "also load" entries — should include more related skills

**Related Skills listed:** review, git

**Cross-reference check:**
- ↔ review: ❌ (review does NOT list spec)
- ↔ git: ❌ (git does NOT list spec)

**Missing cross-references:**
- ❌ `review` does NOT link back to `spec`
- ❌ `git` does NOT link back to `spec`
- Should link to `task_creation` (specs drive tasks)
- Should link to `plan_template` (specs are plans)
- Should link to `code-review-workflow` (spec review)

**Suggested description improvement:**
```
Spec-driven development workflow. Design spec, acceptance criteria, specification, TDD, spec first, implement from spec (also load: review, git, task_creation, plan_template, code-review-workflow)
```

---

## 26. _taudoc (already covered above as #16)

---

## 27. (No additional skills — _taudoc was #16, spec was #25)

---

# SUMMARY OF FINDINGS

## Bidirectional Link Gaps (One-Way References)

| Skill A → Skill B | Skill B → Skill A | Status |
|---|---|---|
| project-onboard → code-review-workflow | ❌ | MISSING |
| python_best_practices → git-verify | ❌ | MISSING |
| python_debugging → code-review-workflow | ❌ | MISSING |
| python_debugging → background | ❌ | MISSING |
| readme_template → command_template | ❌ | MISSING |
| reference → command_template | ❌ | MISSING |
| reference → tau_audit | ❌ | MISSING |
| search-replace → code-review-workflow | ❌ | MISSING |
| search-replace → git-verify | ❌ | MISSING |
| security-audit → dependency_management | ❌ | MISSING |
| security-audit → bug_investigation | ❌ | MISSING |
| security-audit → code-review-workflow | ❌ | MISSING |
| shell_scripting → command_template | ❌ | MISSING |
| signal-cli → shell_scripting | ❌ | MISSING (acceptable, niche) |
| signal-cli → background | ❌ | MISSING (acceptable, niche) |
| skill_template → dream | ❌ | MISSING |
| swe_bench → docker | ❌ | MISSING |
| swe_bench → background | ❌ | MISSING |
| swe_bench → bug_investigation | ❌ | MISSING |
| swe_bench → tau_audit | ❌ | MISSING |
| swe_bench → git | ❌ | MISSING |
| tau_audit → bug_investigation | ❌ | MISSING |
| tau_audit → context_management | ❌ | MISSING |
| tauskillmaintenance → command_template | ❌ | MISSING |
| tauskillmaintenance → wiki | ❌ | MISSING |
| tau_testsuite → dependency_management | ❌ | MISSING |
| think → tau_audit | ❌ | MISSING (should add) |
| tmux_monitoring → tau_testsuite | ❌ | MISSING (should add) |
| tool_template → caveman | ❌ | MISSING (should add) |
| web-research → tau_audit | ❌ | MISSING (acceptable) |
| wiki → documentation | ❌ | MISSING |
| wiki → graphify | ❌ | MISSING |
| spec → review | ❌ | MISSING |
| spec → git | ❌ | MISSING |

**Total one-way references found: 35**

## Description Quality Issues

| Skill | Issue | Priority |
|---|---|---|
| `spec` | Too narrow, missing key terms | HIGH |
| `think` | Vague, missing user phrases | HIGH |
| `task` | Overloaded with keywords (25+) | MEDIUM |
| `tauskillmaintenance` | "also load" list too long (18 skills) | MEDIUM |
| `tau_testsuite` | Missing "write tests" in description | LOW |
| `reference` | Missing "cheat sheet" in description | LOW |
| `swe_bench` | Missing "SWE benchmark" in description | LOW |
| `security-audit` | Missing "security scan" in description | LOW |
| `web-research` | Missing "look up information" in description | LOW |

## Structural Recommendations

1. **Trim "also load" lists**: Skills like `tauskillmaintenance` (18 entries) should be reduced to 5-7 most critical dependencies.
2. **Fix bidirectional links**: 35 one-way references should be made bidirectional (or explicitly marked as directional).
3. **Standardize description format**: All descriptions should follow: `Core purpose — key actions/tools. Natural-language trigger phrases (also load: related_skills)`.
4. **Reduce keyword overlap**: `task` and `dream` have overlapping keywords; `task` should focus on task management, `dream` on orchestration.
5. **Add missing cross-references**: Several skills reference related concepts but don't link them (e.g., `spec` → `plan_template`, `tmux_monitoring` → `tau_testsuite`).
