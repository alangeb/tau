#!/bin/bash
# grep_patterns.sh — common grep patterns for code investigation
# caveman style: one pattern per line, copy paste ready

# === BASIC PATTERNS ===
# recursive python search
grep -rn --include="*.py" "PATTERN" .
# exclude noise dirs
grep -rn --exclude-dir={venv,__pycache__,.git,node_modules,dist,build} "PATTERN" .
# multi-pattern or search
grep -rn -E "pat1|pat2|pat3" .
# count matches per file
grep -rn -c "PATTERN" .
# whole word only
grep -rn -w "exact_word" .
# skip binary files
grep -rn -I --binary-files=without-match "PATTERN" .
# file list only (pipe to xargs)
grep -rn -l "PATTERN" . --include="*.py" | head -50

# === CALLER / CALLEE PATTERNS ===
# find callers of a function (not the def itself)
grep -rn "function_name(" . --include="*.py" | grep -v "def function_name"
# find method callers on self
grep -rn "self\.method_name(" . --include="*.py"
# find callback registrations (assignments to function)
grep -rn "= function_name" . --include="*.py" | grep -v "def " | grep -v "import"
# find callback as string (e.g., callback="handle_event")
grep -rn 'callback=["\x27][^"\x27]*' . --include="*.py"
# find threading targets
grep -rn "target=function_name" . --include="*.py"
# find threading target as string
grep -rn 'target=["\x27]' . --include="*.py"

# === CLASS / STRUCTURE PATTERNS ===
# find class definitions
grep -rn "class \w" . --include="*.py"
# find all function definitions
grep -rn "def \w\+(" . --include="*.py"
# find __init__ methods
grep -rn "def __init__" . --include="*.py"

# === DEBUG / DEVELOPMENT PATTERNS ===
# find debug prints
grep -rn "print(" . --include="*.py" | grep -v "# "
# find breakpoints
grep -rn "breakpoint()\|import pdb\|pdb.set_trace" . --include="*.py"
# find TODO and FIXME markers
grep -rn -E "TODO|FIXME|HACK|XXX|BUG" . --include="*.py"

# === GIT DIFF PATTERNS ===
# search uncommitted changes for patterns
git diff HEAD | grep -E "print\(|breakpoint\(|import pdb"
# search staged changes
git diff --cached | grep -E "TODO|FIXME"
