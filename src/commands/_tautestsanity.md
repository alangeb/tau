---
description: Test Sanity
---

## Purpose
Run sanity tests. There are no errors allowed — no pre-existing errors.

## Instructions

### Phase 1: Sanity Testing
Run the sanity test suite using the absolute path to the script:
```
bash /home/user/tau/src/sanity.sh
```
Or from the `src/` directory:
```
bash sanity.sh
```

There are no errors allowed — no pre-existing errors.
Carefully inspect all output of sanity. Look for issues, warnings that are not expected, errors reported. Be critical. Never remove a warning or error print, this would be working on the symptom, we don't do that.
Note: A certain amount of yellow cache notifications are allowed and expected, this is diagnostic, we can leave them in place.

**IMPORTANT: Use the tool-calling interface for all actions. Do NOT output slash commands as text — they will not be executed.**

### Phase 2: Testing
Run pytests, sanity tests. Fix code if it is broken.
Report on what was done.
