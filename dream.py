#!/usr/bin/env python3
"""dream.py — Programmatic orchestrator for Tau self-improvement loop.

Replaces dream.sh + _dream prompt with explicit code. Handles all deterministic
operations (file ops, git, testing, timeout, logging) and invokes tau.py only
for LLM-driven work.

Usage:
    ./dream.sh [--n N] [--llm MODEL] [--dry-run]    ← via tmux wrapper (recommended)
    python3 dream.py [--n N] [--llm MODEL]          ← direct (no tmux, not recommended)

Options:
    --n N          Number of cycles (0 = infinite, default)
    --llm MODEL    LLM group (default: spark)
    --dry-run      Skip all LLM invocations, simulate everything
"""

import argparse
import atexit
import os
import select
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
PID_FILE = SCRIPT_DIR / "dream.pid"

TIMEOUT_SECONDS = 6 * 3600  # 6 hours per step
READ_POLL_SECONDS = 5  # how often to check shutdown flag while reading subprocess output

# ─── Single-instance lock ────────────────────────────────────────────────────

def _pid_exists(pid: int) -> bool:
    """Return True if a process with the given PID is running."""
    try:
        os.kill(pid, 0)  # sends no signal, just checks existence
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_lock() -> bool:
    """Acquire single-instance lock. Returns True if acquired, False if another instance is running."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if _pid_exists(pid):
                print(f"ERROR: dream.py already running (PID {pid})", file=sys.stderr)
                return False
            # Stale PID file — clean up
            PID_FILE.unlink(missing_ok=True)
        except (ValueError, FileNotFoundError):
            # Corrupted or race condition — try to clean up
            PID_FILE.unlink(missing_ok=True)

    # Write my PID
    PID_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    """Release single-instance lock."""
    PID_FILE.unlink(missing_ok=True)


# ─── Signal Handling ─────────────────────────────────────────────────────────

class ShutdownControl:
    """Graceful shutdown: SIGINT finishes current step, SIGTERM force-kills.

    Also tracks SIGHUP (terminal close) and SIGQUIT (Ctrl+\\) for observability.
    """

    def __init__(self):
        self.graceful_requested = False
        self.force_requested = False
        self.signal_received: str | None = None  # Track which signal triggered shutdown

    def handle_sigint(self, signum, frame):
        self.graceful_requested = True
        self.signal_received = "SIGINT"

    def handle_sigterm(self, signum, frame):
        self.force_requested = True
        self.signal_received = "SIGTERM"

    def handle_sighup(self, signum, frame):
        """Terminal closed or parent process died."""
        self.graceful_requested = True
        self.signal_received = "SIGHUP"

    def handle_sigquit(self, signum, frame):
        """Ctrl+\\ — treat as force shutdown."""
        self.force_requested = True
        self.signal_received = "SIGQUIT"

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

    def description(self) -> str:
        """Return human-readable shutdown reason for logging."""
        if self.signal_received:
            kind = "force" if self.force_requested else "graceful"
            return f"{kind} shutdown via {self.signal_received}"
        return "unknown shutdown"


shutdown = ShutdownControl()


def setup_signals():
    signal.signal(signal.SIGINT, shutdown.handle_sigint)
    signal.signal(signal.SIGTERM, shutdown.handle_sigterm)
    signal.signal(signal.SIGHUP, shutdown.handle_sighup)
    signal.signal(signal.SIGQUIT, shutdown.handle_sigquit)


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

    # ─── Step Result ─────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    name: str
    success: bool
    timed_out: bool = False
    elapsed: float = 0.0
    detail: str = ""


# ─── Tau Runner ──────────────────────────────────────────────────────────────

TAU_RETRY_COUNT = 2  # retries on crash (not timeout)
TAU_RETRY_DELAY = 30  # seconds between retries


def run_tau(
    command: str,
    llm_group: str,
    logger: Logger,
    dry_run: bool,
    timeout: int = TIMEOUT_SECONDS,
    retry_count: int = TAU_RETRY_COUNT,
    retry_delay: int = TAU_RETRY_DELAY,
) -> subprocess.CompletedProcess:
    """Run tau.py with a command, streaming output to terminal + log.

    Uses select() to poll the output pipe so shutdown signals can be handled
    during long-running tau invocations. Checks shutdown.check() every
    READ_POLL_SECONDS.

    On crash (non-zero exit), retries up to retry_count times with retry_delay
    between attempts. Timeouts are NOT retried (command is stuck).

    Returns CompletedProcess. Raises subprocess.TimeoutExpired on timeout.
    """
    if dry_run:
        logger.log("[DRY-RUN]", f"would run: tau.py --llm {llm_group} {command}")
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="DRY-RUN: skipped", stderr="")

    cmd = [str(TAU_BIN), "--llm", llm_group, command]

    for attempt in range(retry_count + 1):
        if attempt > 0:
            logger.log("[retry]", f"tau.py retry {attempt}/{retry_count} after {retry_delay}s delay (command: {command})")
            time.sleep(retry_delay)

        logger.log("[tau]", f"running (attempt {attempt+1}/{retry_count+1}): {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(SRC_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        logger.log("[tau]", f"started tau.py (PID {proc.pid}) — waiting for completion...")

        # Stream output live using select() so we can check for shutdown signals
        output_lines = []
        stdout_fd = proc.stdout.fileno()
        try:
            while True:
                # Check shutdown before each poll
                if shutdown.check():
                    logger.log("[shutdown]", f"{shutdown.was_requested()} shutdown requested — terminating tau.py (PID {proc.pid})")
                    _terminate_subprocess(proc, logger)
                    # Drain any remaining output
                    remaining = proc.stdout.read()
                    if remaining:
                        for line in remaining.rstrip("\n").split("\n"):
                            line = line.rstrip("\n")
                            output_lines.append(line)
                            print(f"  {line}", flush=True)
                            logger._write_log(f"  {line}\n")
                    raise subprocess.TimeoutExpired(cmd, 0, "\n".join(output_lines))

                # Use select to wait for output with a timeout
                try:
                    ready, _, _ = select.select([stdout_fd], [], [], READ_POLL_SECONDS)
                except (ValueError, OSError):
                    # File descriptor was closed (process exited)
                    break

                if not ready:
                    # No output for READ_POLL_SECONDS — loop back to check shutdown
                    continue

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

            logger.log("[tau]", f"tau.py (PID {proc.pid}) exited with code {proc.returncode}")

            if proc.returncode == 0:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=proc.returncode,
                    stdout="\n".join(output_lines),
                )

            # Non-zero exit — log crash details
            logger.log("[crash]", f"tau.py exited with code {proc.returncode} (attempt {attempt+1}/{retry_count+1})")
            # Log last 10 lines of output for debugging
            for line in output_lines[-10:]:
                logger.log("[crash-output]", line)

            # Don't retry on last attempt
            if attempt >= retry_count:
                logger.log("[crash]", f"tau.py failed after {retry_count+1} attempts — giving up")
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=proc.returncode,
                    stdout="\n".join(output_lines),
                )

        except subprocess.TimeoutExpired:
            raise
        except Exception:
            # Ensure process is cleaned up on any unexpected error
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            raise


def _terminate_subprocess(proc: subprocess.Popen, logger: Logger):
    """Gracefully terminate a subprocess: SIGINT first, SIGKILL after 10s."""
    if proc.poll() is not None:
        return  # already exited
    try:
        proc.terminate()  # SIGTERM
    except OSError:
        return
    # Wait up to 10 seconds for graceful exit
    for _ in range(100):
        if proc.poll() is not None:
            logger.log("[shutdown]", f"tau.py (PID {proc.pid}) terminated gracefully")
            return
        time.sleep(0.1)
    # Force kill if still alive
    logger.log("[shutdown]", f"tau.py (PID {proc.pid}) did not terminate — sending SIGKILL")
    proc.kill()
    proc.wait()


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
            if not f.exists():
                logger.log("[tasks]", f"{f.name} no longer in 1_todo — skipping (already handled)")
                continue
            move_task(f, "2_inprogress")

        # Run tau
        tau_ok = False
        timed_out = False
        try:
            proc = run_tau("/_taudotask", llm_group, logger, dry_run)
            tau_ok = (proc.returncode == 0)
        except subprocess.TimeoutExpired:
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
        except subprocess.TimeoutExpired:
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
    except subprocess.TimeoutExpired:
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


# ─── Log Rotation (Deterministic — No LLM) ────────────────────────────────────

def step_log_rotate(logger: Logger, git: GitHelper, dry_run: bool) -> StepResult:
    """Archive old session files, create symlinks, update registry.

    Deterministic operation — no LLM needed. Preserves --continue compatibility
    by creating symlinks in original locations.
    """
    t0 = time.time()
    step_name = "log_rotate"
    logger.header(f"Step: {step_name}")

    if dry_run:
        logger.log("[DRY-RUN]", "would run log rotation")
        return StepResult(step_name, True, elapsed=time.time() - t0, detail="dry-run")

    try:
        # Import here — dream.py runs from project root, src/ is on path
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from agent_session_registry import get_registry, LOG_DIR  # type: ignore
        import shutil

        registry = get_registry()

        # Read retention config from tau.json
        max_age_days = 30
        max_size_mb = 500
        archive_dir = LOG_DIR / "archive"

        try:
            tau_json = SRC_DIR / "tau.json"
            if tau_json.exists():
                config = __import__("json").loads(tau_json.read_text(encoding="utf-8"))
                retention = config.get("log_retention", {})
                max_age_days = retention.get("max_age_days", max_age_days)
                max_size_mb = retention.get("max_size_mb", max_size_mb)
                archive_path_str = retention.get("archive_dir", str(archive_dir))
                archive_dir = Path(archive_path_str)
                if not archive_dir.is_absolute():
                    archive_dir = Path.home() / archive_dir.expanduser()
        except Exception as e:
            logger.log("[warn]", f"Failed to read retention config: {e}")
        # Find sessions to archive (older than max_age_days)
        cutoff = time.time() - (max_age_days * 86400)
        active_cutoff = time.time() - 300  # 5 minutes — likely active

        sessions = registry.list_sessions(status="active")
        to_archive = []

        for s in sessions:
            ctx_path_str = s.get("context")
            if not ctx_path_str:
                continue
            try:
                mtime = Path(ctx_path_str).stat().st_mtime
                # Skip active sessions (modified in last 5 minutes)
                if mtime > active_cutoff:
                    continue
                if mtime < cutoff:
                    to_archive.append(s)
            except OSError:
                continue

        # Also check total log directory size
        if not to_archive:
            try:
                total_size = sum(
                    f.stat().st_size
                    for f in LOG_DIR.iterdir()
                    if f.is_file() and not f.name.endswith(".tmp")
                )
                if total_size > max_size_mb * 1024 * 1024:
                    to_archive = sessions[:20]
            except OSError:
                pass

        if not to_archive:
            logger.log(
                "[info]",
                f"No sessions to archive (age>{max_age_days}d, size<{max_size_mb}MB)",
            )
            return StepResult(
                step_name, True, elapsed=time.time() - t0, detail="nothing to archive"
            )

        logger.log("[info]", f"Archiving {len(to_archive)} session(s)...")

        archived = 0
        errors = 0

        for s in to_archive:
            prefix = s["prefix"]
            ctx_path = Path(s.get("context", ""))
            audit_path = Path(s.get("audit", "")) if s.get("audit") else None
            plan_path = Path(s.get("plan", "")) if s.get("plan") else None

            # Extract date from prefix ({ppid}_{YYYYMMDDHHMMSS}_{N})
            archive_date = "unknown"
            try:
                parts = prefix.split("_")
                if len(parts) >= 2 and len(parts[1]) >= 8:
                    ts = parts[1]
                    archive_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
            except Exception:
                pass

            dest_dir = archive_dir / archive_date
            dest_dir.mkdir(parents=True, exist_ok=True)

            files_to_move = [
                ("context", ctx_path),
                ("audit", audit_path),
                ("plan", plan_path),
            ]

            new_paths: dict[str, str] = {}
            for label, fpath in files_to_move:
                if not fpath or not fpath.exists():
                    continue

                # Skip already-archived files (symlinks) — prevents self-referencing loops
                if fpath.is_symlink():
                    real_target = fpath.resolve()
                    if real_target.exists():
                        logger.log("[skip]", f"{prefix}/{fpath.name} already archived -> {real_target}")
                    else:
                        logger.log("[cleanup]", f"{prefix}/{fpath.name} removing dangling symlink")
                        fpath.unlink()
                    continue

                dest = dest_dir / fpath.name
                try:
                    shutil.move(str(fpath), str(dest))
                    fpath.symlink_to(dest)
                    new_paths[label] = str(dest)
                    logger.log("[archive]", f"{prefix}/{fpath.name} -> archive/{archive_date}/")
                except Exception as e:
                    logger.log("[error]", f"Failed to archive {fpath}: {e}")
                    errors += 1
                    # Restore from dest if symlink failed
                    if dest.exists() and not fpath.exists():
                        try:
                            shutil.move(str(dest), str(fpath))
                        except Exception:
                            pass

            # Update registry
            if new_paths:
                registry.archive_session(prefix, new_paths)
                archived += 1

        logger.log("[summary]", f"Archived {archived} session(s), {errors} error(s)")
        logger.log("[summary]", f"Archive dir: {archive_dir}")

        # Clean up orphaned registry entries
        try:
            orphans = registry.cleanup_orphans()
            if orphans:
                logger.log("[cleanup]", f"Removed {orphans} orphaned registry entries")
        except Exception as e:
            logger.log("[warn]", f"Failed to cleanup orphans: {e}")

        return StepResult(
            step_name,
            errors == 0,
            elapsed=time.time() - t0,
            detail=f"archived={archived},errors={errors}",
        )

    except Exception as e:
        logger.log("[error]", f"Log rotation failed: {e}")
        logger.log("[traceback]", traceback.format_exc())
        return StepResult(
            step_name, False, elapsed=time.time() - t0, detail=str(e)
        )


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


def step_wiki(logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> StepResult:
    """Wiki maintenance: ingest unprocessed sessions, maintain structure."""
    return step_single(logger, git, llm_group, dry_run, "/_tauwiki", "wiki")


# ─── Cycle ───────────────────────────────────────────────────────────────────

def run_cycle(cycle_num: int, logger: Logger, git: GitHelper, llm_group: str, dry_run: bool) -> List[StepResult]:
    """Run one complete cycle of all 9 steps."""
    t0 = time.time()
    logger.header(f"━━━ Cycle {cycle_num} ━━━")
    all_results = []

    # 1. Process tasks
    all_results.extend(step_process_tasks(logger, git, llm_group, dry_run))
    if shutdown.check():
        return all_results

    # 1.5 Log rotation (deterministic, no LLM)
    all_results.append(step_log_rotate(logger, git, dry_run))
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
    # TODO: temporarily disabled until fixed
    #all_results.append(step_log_review(logger, git, llm_group, dry_run))

    # 8. Wiki maintenance
    # TODO: temporarily disabled until fixed
    #all_results.append(step_wiki(logger, git, llm_group, dry_run))

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

    # Acquire single-instance lock
    if not acquire_lock():
        sys.exit(1)

    # Setup logging
    logger = Logger(LOG_FILE, dry_run=args.dry_run)
    mode = " [DRY-RUN]" if args.dry_run else ""
    logger.header(f"dream.py started{mode} (llm={args.llm}, cycles={'inf' if args.n == 0 else args.n})")
    logger.log("[info]", f"cwd: {os.getcwd()}")
    logger.log("[info]", f"src: {SRC_DIR}")
    logger.log("[info]", f"tasks: {TASKS_DIR}")

    # Atexit handler — log ANY exit (normal, signal, exception)
    _exit_cycle = [0]  # Mutable container for atexit closure
    def _log_exit():
        """Log exit reason — called by atexit on any exit path."""
        try:
            elapsed = time.time() - logger.start_time
            h, rem = divmod(int(elapsed), 3600)
            m, s = divmod(rem, 60)
            reason = "unknown"
            if shutdown.signal_received:
                reason = shutdown.description()
            elif _exit_cycle[0] > 0 and args.n > 0 and _exit_cycle[0] >= args.n:
                reason = f"completed {_exit_cycle[0]} cycles"
            elif STOP_FILE.exists():
                reason = "stop file detected"
            logger.log("[exit]", f"dream.py exiting: {reason} (cycles={_exit_cycle[0]}, time={h:02d}:{m:02d}:{s:02d})")
        except Exception:
            pass  # atexit must not raise
    atexit.register(_log_exit)

    # Ensure task directories exist
    ensure_tasks_dirs()

    # Setup git
    git = GitHelper(SRC_DIR, logger, dry_run=args.dry_run)

    # Pre-flight: check git is clean
    if not args.dry_run:
        if not git.is_clean():
            status = git.get_status_short()
            logger.log("[ERROR]", f"Git not clean. Refusing to start.\n{status}")
            release_lock()
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
            _exit_cycle[0] = cycle  # Update for atexit handler
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
                logger.log("[shutdown]", f"{shutdown.description()} — exiting")
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
        release_lock()
        sys.exit(1)

    # Final summary
    logger.header("Dream loop ended")
    logger.log("[total]", f"Completed {cycle} cycles")
    h, rem = divmod(int(time.time() - logger.start_time), 3600)
    m, s = divmod(rem, 60)
    logger.log("[total]", f"Total time: {h:02d}:{m:02d}:{s:02d}")
    logger.log("[log]", f"Full log: {LOG_FILE}")

    # Release lock on clean exit
    release_lock()


if __name__ == "__main__":
    main()
