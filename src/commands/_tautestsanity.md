---
description: Test Sanity
---

## Purpose
Run sanity tests. There are no errors allowed — no pre-existing errors.

## Instructions

### Phase 1: Sanity Testing
Specifically run `./sanity.sh`.
There are no errors allowed — no pre-existing errors.
Carefully inspect all output of sanity. Look for issues, warnings that are not expected, errors reported. Be critical. Never remove a warning or error print, this would be working on the symptom, we don't do that.
Note: A certain amount of yellow cache notifications are allowed and expected, this is diagnostic, we can leave them in place.

**IMPORTANT: Use the tool-calling interface for all actions. Do NOT output slash commands as text — they will not be executed.**

### Phase 2: Testing
Run pytests, sanity tests. Fix code if it is broken.
Report on what was done.
