#!/usr/bin/env python3
"""dream.py — Programmatic orchestrator for Tau self-improvement loop.

Replaces dream.sh + _dream prompt with explicit code. Handles all deterministic
operations (file ops, git, testing, timeout, logging) and invokes tau.py only
for LLM-driven work.

Usage:
    dream.py [--n N] [--llm MODEL] [--dry-run]

Options:
    --n N          Number of cycles (0 = infinite, default)
    --llm MODEL    LLM group (default: spark)
    --dry-run      Skip all LLM invocations, simulate everything
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import List

# ─── Constants ───────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR / "src"
TAU_BIN = SRC_DIR / "tau.py"
TASKS_DIR = SCRIPT_DIR / "tasks"
LOG_FILE = SCRIPT_DIR / "dream.log"
STOP_FILE = SCRIPT_DIR / "dream.stop"

TIMEOUT_SECONDS = 6 * 3600  # 6 hours per step
PYTEST_CMD = "python3 -m pytest tests/ --tb=short -q"
SANITY_CMD = "./sanity.sh"

# ─── Signal Handling ─────────────────────────────────────────────────────────

class ShutdownControl:
    """Graceful shutdown: SIGINT finishes current step, SIGTERM force-kills."""

    def __init__(self):
        self.graceful_requested = False
        self.force_requested = False

    def handle_sigint(self, signum, frame):
        self.graceful_requested = True

    def handle_sigterm(self, signum, frame):
        self.force_requested = True

    def check(self):
        """Return True if any shutdown was requested."""
        return self.graceful_requested or self.force_requested

    def was_requested(self):
        """Return type of shutdown requested."""
        if self.force_requested:
            return "force"
        if self.graceful_requested:
            return "graceful"
        return None


shutdown = ShutdownControl()


def setup_signals():
    signal.signal(signal.SIGINT, shutdown.handle_sigint)
    signal.signal(signal.SIGTERM, shutdown.handle_sigterm)


# ─── Logger ──────────────────────────────────────────────────────────────────

class Logger:
    """Dual output: terminal + dream.log. Tracks timing."""

    def __init__(self, log_path: Path, dry_run: bool = False):
        self.log_path = log_path
        self.dry_run = dry_run
        self.start_time = time.time()
        # Clear log on start (fresh each run)
        log_path.write_text("")

    def _elapsed(self) -> str:
        secs = int(time.time() - self.start_time)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _fmt(self, prefix: str, msg: str) -> str:
        ts = time.strftime("%H:%M:%S")
        elapsed = self._elapsed()
        line = f"[{ts}] +{elapsed} {prefix} {msg}"
        return line

    def log(self, prefix: str, msg: str):
        line = self._fmt(prefix, msg)
        print(line, flush=True)
        self._write_log(line + "\n")

    def _write_log(self, text: str):
        with open(self.log_path, "a") as f:
            f.write(text)

    def header(self, title: str):
        sep = "=" * 70
        for line in [sep, title, sep]:
            formatted = self._fmt("", line)
            print(formatted, flush=True)
            self._write_log(formatted + "\n")

    def step_result(self, step: str, status: str, elapsed: float):
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏰", "SKIP": "⏭️", "REVERT": "↩️"}.get(status, "?")
        self.log(f"[{icon} {step}]", f"{status} ({time_str})")


# ─── Git Helpers ─────────────────────────────────────────────────────────────

class GitHelper:
    """Git operations: status, commit, revert."""

    def __init__(self, cwd: Path, logger: Logger, dry_run: bool = False):
        self.cwd = cwd
        self.log = logger
        self.dry_run = dry_run

    def _run(self, cmd: list, capture: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(self.cwd),
            capture_output=capture,
            text=True,
            timeout=30,
        )

    def is_clean(self) -> bool:
        """Check if working tree is clean (no uncommitted changes)."""
        try:
            r = self._run(["git", "status", "--porcelain"])
            return r.stdout.strip() == ""
        except Exception:
            return False

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            r = self._run(["git", "diff", "--quiet"], capture=False)
            return r.returncode != 0
        except Exception:
            return False

    def get_status_short(self) -> str:
        r = self._run(["git", "status", "--short"])
        return r.stdout.strip()

    def commit(self, msg: str):
        """Commit all changes."""
        if self.dry_run:
            self.log.log("[DRY-RUN]", f"would commit: {msg}")
            return
        self._run(["git", "add", "-A"])
        self._run(["git", "commit", "-m", msg])
        self.log.log("[git]", f"committed: {msg}")

    def revert(self):
        """Revert all uncommitted changes."""
        if self.dry_run:
            self.log.log("[DRY-RUN]", "would revert all changes")
            return
        self._run(["git", "checkout", "--", "."])
        self._run(["git", "clean", "-fd"])
        self.log.log("[git]", "reverted all changes")

    def assert_clean(self, step_name: str) -> bool:
        """Assert working tree is clean. Return False if not."""
        if not self.is_clean():
            status = self.get_status_short()
            self.log.log("[WARN]", f"Git not clean before {step_name}: {status}")
            return False
        return True


# ─── Step Result ─────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    name: str
    success: bool
    timed_out: bool = False
    elapsed: float = 0.0
    detail: str = ""


# ─── Tau Runner ──────────────────────────────────────────────────────────────

def run_tau(
    command: str,
    llm_group: str,
    logger: Logger,
    dry_run: bool,
    timeout: int = TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    """Run tau.py with a command, streaming output to terminal + log.

    Returns CompletedProcess. Raises subprocess.TimeoutError on timeout.
    """
    if dry_run:
        logger.log("[DRY-RUN]", f"would run: tau.py --llm {llm_group} {command}")
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="DRY-RUN: skipped", stderr="")

    cmd = [str(TAU_BIN), "--llm", llm_group, command]
    logger.log("[tau]", f"running: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(SRC_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Stream output live
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip("\n")
            output_lines.append(line)
            # Print to terminal (prefixed for clarity)
            print(f"  {line}", flush=True)
            # Also to log
            logger._write_log(f"  {line}\n")

        proc.wait(timeout=timeout)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode,
            stdout="\n".join(output_lines),
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise


def run_tests(logger: Logger, dry_run: bool) -> tuple:
    """Run pytest + sanity.sh. Returns (pytest_ok, sanity_ok)."""
    if dry_run:
        logger.log("[DRY-RUN]", "would run: pytest + sanity.sh")
        return True, True

    # Run pytest
    logger.log("[test]", "running pytest...")
    pytest_ok = False
    try:
        r = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "--tb=short", "-q"],
            cwd=str(SRC_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
        pytest_ok = r.returncode == 0
        logger.log("[test]", f"pytest: {'PASS' if pytest_ok else 'FAIL'} (exit={r.returncode})")
        if not pytest_ok:
            lines = r.stdout.strip().split("\n")[-20:]
            for line in lines:
                logger.log("[pytest]", line)
    except subprocess.TimeoutExpired:
        logger.log("[test]", "pytest: TIMEOUT")
        pytest_ok = False

    # Run sanity.sh
    logger.log("[test]", "running sanity.sh...")
    sanity_ok = False
    try:
        r = subprocess.run(
            ["bash", "sanity.sh"],
            cwd=str(SRC_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
        sanity_ok = r.returncode == 0
        logger.log("[test]", f"sanity: {'PASS' if sanity_ok else 'FAIL'} (exit={r.returncode})")
        if not sanity_ok:
            lines = r.stdout.strip().split("\n")[-20:]
            for line in lines:
                logger.log("[sanity]", line)
    except subprocess.TimeoutExpired:
        logger.log("[test]", "sanity: TIMEOUT")
        sanity_ok = False

    return pytest_ok, sanity_ok


# ─── Task Management ─────────────────────────────────────────────────────────

def ensure_tasks_dirs():
    """Create task directories if they don't exist."""
    for subdir in ["1_todo", "2_inprogress", "3_done", "3_failed"]:
        d = TASKS_DIR / subdir
        d.mkdir(parents=True, exist_ok=True)


def get_todo_files() -> List[Path]:
    """Get .md files from 1_todo."""
    return sorted(TASKS_DIR.glob("1_todo/*.md"))


def move_task(src: Path, dest_subdir: str):
    """Move a task file to a subdirectory."""
    dest = TASKS_DIR / dest_subdir / src.name
    shutil.move(str(src), str(dest))


# ─── Step Functions ──────────────────────────────────────────────────────────

def step_process_tasks(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> List[StepResult]:
    """Process all tasks in 1_todo: pick up, implement, test, commit/revert, move."""
    results = []
    files = get_todo_files()
    if not files:
        logger.log("[tasks]", "no tasks in 1_todo — skipping")
        results.append(StepResult("process_tasks", True, elapsed=0, detail="no tasks"))
        return results

    for f in files:
        if shutdown.check():
            break

        step_name = f"task:{f.stem}"
        t0 = time.time()

        # Move to inprogress (skip in dry-run to avoid side effects)
        logger.log("[tasks]", f"picking up: {f.name}")
        if not dry_run:
            move_task(f, "2_inprogress")

        # Run tau
        tau_ok = False
        timed_out = False
        try:
            proc = run_tau("/_taudotask", llm_group, logger, dry_run)
            tau_ok = (proc.returncode == 0)
        except subprocess.TimeoutError:
            logger.log("[timeout]", f"{step_name}: tau timed out after {TIMEOUT_SECONDS}s")
            timed_out = True

        # Test
        if not dry_run:
            pytest_ok, sanity_ok = run_tests(logger, dry_run)
            all_ok = tau_ok and pytest_ok and sanity_ok
        else:
            all_ok = True

        # Commit or revert
        if dry_run:
            logger.log("[DRY-RUN]", f"would commit: dream: task {f.stem}")
            results.append(StepResult(step_name, True, elapsed=time.time() - t0, detail="dry-run"))
        elif all_ok:
            git.commit(f"dream: task {f.stem}")
            task_file = TASKS_DIR / "2_inprogress" / f.name
            if task_file.exists():
                move_task(task_file, "3_done")
            else:
                logger.log("[tasks]", f"{f.name} already moved to 3_done (tau handled it)")
            results.append(StepResult(step_name, True, elapsed=time.time() - t0, detail="committed"))
        else:
            git.revert()
            task_file = TASKS_DIR / "2_inprogress" / f.name
            if task_file.exists():
                move_task(task_file, "3_failed")
            else:
                logger.log("[tasks]", f"{f.name} not in 2_inprogress — skipping move to 3_failed")
            status = "timeout" if timed_out else "test_fail"
            results.append(StepResult(step_name, False, elapsed=time.time() - t0, detail=status))

        logger.step_result(step_name, "PASS" if all_ok else ("TIMEOUT" if timed_out else "FAIL"), time.time() - t0)

    return results


def step_rearch(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool, n: int = 3) -> List[StepResult]:
    """Run re-architecture n times."""
    results = []
    for i in range(n):
        if shutdown.check():
            break

        step_name = f"rearch:{i+1}/{n}"
        t0 = time.time()
        logger.header(f"Step: {step_name}")

        # Run tau
        tau_ok = False
        timed_out = False
        try:
            proc = run_tau("/_taurearch", llm_group, logger, dry_run)
            tau_ok = (proc.returncode == 0)
        except subprocess.TimeoutError:
            logger.log("[timeout]", f"{step_name}: tau timed out after {TIMEOUT_SECONDS}s")
            timed_out = True
            tau_ok = False

        # Test
        if not dry_run:
            pytest_ok, sanity_ok = run_tests(logger, dry_run)
            all_ok = tau_ok and pytest_ok and sanity_ok
        else:
            all_ok = True

        # Commit or revert
        if dry_run:
            logger.log("[DRY-RUN]", f"would commit: dream: rearch {i+1}/{n}")
            results.append(StepResult(step_name, True, elapsed=time.time() - t0, detail="dry-run"))
        elif all_ok:
            git.commit(f"dream: rearch {i+1}/{n}")
            results.append(StepResult(step_name, True, elapsed=time.time() - t0, detail="committed"))
        else:
            git.revert()
            status = "timeout" if timed_out else ("test_fail" if not tau_ok else "commit_fail")
            results.append(StepResult(step_name, False, elapsed=time.time() - t0, detail=status))

        logger.step_result(step_name, "PASS" if all_ok else ("TIMEOUT" if timed_out else "FAIL"), time.time() - t0)

    return results


def step_single(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool, command: str, step_name: str) -> StepResult:
    """Generic single-step: run tau command, test, commit/revert."""
    t0 = time.time()
    logger.header(f"Step: {step_name}")

    tau_ok = False
    timed_out = False
    try:
        proc = run_tau(command, llm_group, logger, dry_run)
        tau_ok = (proc.returncode == 0)
    except subprocess.TimeoutError:
        logger.log("[timeout]", f"{step_name}: tau timed out after {TIMEOUT_SECONDS}s")
        timed_out = True
        tau_ok = False

    # Test
    if not dry_run:
        pytest_ok, sanity_ok = run_tests(logger, dry_run)
        all_ok = tau_ok and pytest_ok and sanity_ok
    else:
        all_ok = True

    # Commit or revert
    if dry_run:
        logger.log("[DRY-RUN]", f"would commit: dream: {step_name}")
        result = StepResult(step_name, True, elapsed=time.time() - t0, detail="dry-run")
    elif all_ok:
        git.commit(f"dream: {step_name}")
        result = StepResult(step_name, True, elapsed=time.time() - t0, detail="committed")
    else:
        git.revert()
        status = "timeout" if timed_out else ("test_fail" if not tau_ok else "commit_fail")
        result = StepResult(step_name, False, elapsed=time.time() - t0, detail=status)

    logger.step_result(step_name, "PASS" if all_ok else ("TIMEOUT" if timed_out else "FAIL"), time.time() - t0)
    return result


def step_test_commands(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    return step_single(logger, git, llm_group, dry_run, "/_tautestcommands", "test_commands")


def step_test_sanity(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    return step_single(logger, git, llm_group, dry_run, "/_tautestsanity", "test_sanity")


def step_skill_maintenance(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    return step_single(logger, git, llm_group, dry_run, "/_tauskillmaintenance", "skill_maintenance")


def step_doc_sync(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    return step_single(logger, git, llm_group, dry_run, "/_taudoc", "doc_sync")


def step_log_review(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    return step_single(logger, git, llm_group, dry_run, "/_taulogreview", "log_review")


# ─── Cycle ───────────────────────────────────────────────────────────────────

def run_cycle(cycle_num: int, logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> List[StepResult]:
    """Run one complete cycle of all 7 steps."""
    t0 = time.time()
    logger.header(f"━━━ Cycle {cycle_num} ━━━")
    all_results = []

    # 1. Process tasks
    all_results.extend(step_process_tasks(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 2. Re-architecture (x3)
    all_results.extend(step_rearch(logger, git, llm_group, dry_run, n=3))
    if shutdown.check():
        return all_results

    # 3. Test commands
    all_results.append(step_test_commands(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 4. Test sanity
    all_results.append(step_test_sanity(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 5. Skill maintenance
    all_results.append(step_skill_maintenance(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 6. Doc sync
    all_results.append(step_doc_sync(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 7. Log review
    all_results.append(step_log_review(logger, git, llm_group, dry_run))

    elapsed = time.time() - t0
    h, rem = divmod(int(elapsed), 3600)
    m, s = divmod(rem, 60)
    passed = sum(1 for r in all_results if r.success)
    total = len(all_results)
    logger.header(f"━━━ Cycle {cycle_num} complete ({h:02d}:{m:02d}:{s:02d}, {passed}/{total} passed) ━━━")

    return all_results


# ─── Main ────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Dream loop — programmatic Tau self-improvement orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    dream.py                  # run forever, spark LLM
    dream.py --n 3           # 3 cycles
    dream.py --llm deepseek  # use deepseek
    dream.py --dry-run       # simulate without LLM calls
    dream.py --n 1 --dry-run # single dry-run cycle
""",
    )
    p.add_argument("--n", type=int, default=0, help="Number of cycles (0 = infinite, default)")
    p.add_argument("--llm", default="spark", help="LLM group (default: spark)")
    p.add_argument("--dry-run", action="store_true", help="Skip LLM invocations, simulate everything")
    return p.parse_args()


def main():
    args = parse_args()
    setup_signals()

    # Setup logging
    logger = Logger(LOG_FILE, dry_run=args.dry_run)
    mode = " [DRY-RUN]" if args.dry_run else ""
    logger.header(f"dream.py started{mode} (llm={args.llm}, cycles={'inf' if args.n == 0 else args.n})")
    logger.log("[info]", f"cwd: {os.getcwd()}")
    logger.log("[info]", f"src: {SRC_DIR}")
    logger.log("[info]", f"tasks: {TASKS_DIR}")

    # Ensure task directories exist
    ensure_tasks_dirs()

    # Setup git
    git = GitHelper(SRC_DIR, logger, dry_run=args.dry_run)

    # Pre-flight: check git is clean
    if not args.dry_run:
        if not git.is_clean():
            status = git.get_status_short()
            logger.log("[ERROR]", f"Git not clean. Refusing to start.\n{status}")
            sys.exit(1)
        logger.log("[git]", "working tree clean")

    cycle = 0
    try:
        while True:
            # Check stop file
            if STOP_FILE.exists():
                logger.log("[stop]", f"stop file detected: {STOP_FILE}")
                break

            cycle += 1
            results = run_cycle(cycle, logger, git, args.llm, args.dry_run)

            # Summary
            passed = sum(1 for r in results if r.success)
            total = len(results)
            failed = [r for r in results if not r.success]
            if failed:
                logger.log("[summary]", f"Failed steps: {', '.join(r.name for r in failed)}")

            logger.log("[cycle]", f"Cycle {cycle}: {passed}/{total} passed")

            # Check limits
            if args.n > 0 and cycle >= args.n:
                logger.log("[done]", f"Reached {args.n} cycles")
                break

            # Check shutdown
            if shutdown.check():
                kind = shutdown.was_requested()
                logger.log("[shutdown]", f"{kind} shutdown requested — exiting")
                break

            # Brief pause between cycles
            if not args.dry_run:
                logger.log("[wait]", "pausing 10s before next cycle...")
                time.sleep(10)
    except Exception:
        tb = traceback.format_exc()
        logger.log("[CRASH]", f"Unhandled exception after {cycle} cycle(s):\n{tb}")
        # Also print to stderr so it's visible in terminal
        print(f"\n!!! DREAM CRASH (logged to {LOG_FILE}):\n{tb}", file=sys.stderr, flush=True)
        sys.exit(1)

    # Final summary
    logger.header("Dream loop ended")
    logger.log("[total]", f"Completed {cycle} cycles")
    h, rem = divmod(int(time.time() - logger.start_time), 3600)
    m, s = divmod(rem, 60)
    logger.log("[total]", f"Total time: {h:02d}:{m:02d}:{s:02d}")
    logger.log("[log]", f"Full log: {LOG_FILE}")


if __name__ == "__main__":
    main()
