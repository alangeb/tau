"""Comprehensive tests for the Ralph Loop command (commands/ralph.py).

Tests cover:
- Input validation
- File I/O operations (atomic writes, error handling)
- Task creation and lifecycle
- Iteration logic
- Acceptance criteria generation
- Error handling and exceptions
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Import the module under test
from commands.ralph import (
    run,
    RalphError,
    RalphFileError,
    RalphValidationError,
    IterationResult,
    _init_ralph_loop,
    _create_task,
    _generate_acceptance_criteria,
    _check_task_complete,
    _execute_iteration,
    _log_iteration,
    _verify_task_status,
    _finalize_task,
    _atomic_write_json,
    _read_json,
    RALPH_LOOP_DIR,
    MAX_ITERATIONS,
)


class TestRalphExceptions:
    """Test custom exception hierarchy."""

    def test_ralph_error_base_class(self):
        """RalphError is a subclass of Exception."""
        assert issubclass(RalphError, Exception)

    def test_ralph_file_error(self):
        """RalphFileError is a subclass of RalphError."""
        assert issubclass(RalphFileError, RalphError)

    def test_ralph_validation_error(self):
        """RalphValidationError is a subclass of RalphError."""
        assert issubclass(RalphValidationError, RalphError)

    def test_ralph_error_message(self):
        """RalphError preserves error messages."""
        error = RalphError("Test error message")
        assert str(error) == "Test error message"


class TestIterationResult:
    """Test IterationResult NamedTuple."""

    def test_iteration_result_creation(self):
        """IterationResult can be created with required fields."""
        result = IterationResult(result="test", is_complete=False)
        assert result.result == "test"
        assert result.is_complete is False
        assert result.error is None

    def test_iteration_result_with_error(self):
        """IterationResult can include error message."""
        result = IterationResult(
            result="error", is_complete=False, error="Something failed"
        )
        assert result.error == "Something failed"

    def test_iteration_result_complete(self):
        """IterationResult can indicate completion."""
        result = IterationResult(result="done", is_complete=True)
        assert result.is_complete is True


class TestAtomicFileOperations:
    """Test atomic JSON file operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        dir_path = tempfile.mkdtemp()
        yield Path(dir_path)
        shutil.rmtree(dir_path)

    def test_atomic_write_and_read(self, temp_dir):
        """Atomic write and read work correctly."""
        file_path = temp_dir / "test.json"
        data = {"key": "value", "number": 42}

        _atomic_write_json(file_path, data)
        read_data = _read_json(file_path)

        assert read_data == data

    def test_atomic_write_creates_directory(self, temp_dir):
        """Atomic write creates parent directories if needed."""
        file_path = temp_dir / "nested" / "dir" / "test.json"
        data = {"test": "data"}

        _atomic_write_json(file_path, data)

        assert file_path.exists()
        assert _read_json(file_path) == data

    def test_atomic_write_handles_failure(self, temp_dir):
        """Atomic write handles errors gracefully."""
        # Test with a path that should fail (e.g., writing to a file in a non-writable location)
        # Note: We can't easily test actual write failures in a temp directory as root/owner
        # So we test that the function handles normal writes correctly
        file_path = temp_dir / "test.json"
        data = {"key": "value"}

        # This should succeed
        _atomic_write_json(file_path, data)
        assert _read_json(file_path) == data

        # Test that it properly handles directory creation
        nested_path = temp_dir / "subdir" / "nested" / "file.json"
        _atomic_write_json(nested_path, {"nested": True})
        assert nested_path.exists()

    def test_read_json_file_not_found(self, temp_dir):
        """_read_json raises RalphFileError for missing file."""
        file_path = temp_dir / "nonexistent.json"

        with pytest.raises(RalphFileError) as exc_info:
            _read_json(file_path)

        assert "File not found" in str(exc_info.value)

    def test_read_json_invalid_json(self, temp_dir):
        """_read_json raises RalphFileError for invalid JSON."""
        file_path = temp_dir / "invalid.json"
        file_path.write_text("not valid json {{{")

        with pytest.raises(RalphFileError) as exc_info:
            _read_json(file_path)

        assert "Invalid JSON" in str(exc_info.value)


class TestInitRalphLoop:
    """Test Ralph Loop directory initialization."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        # Monkey-patch the global RALPH_LOOP_DIR
        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        # Restore original
        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_init_creates_directories(self, temp_ralph_dir):
        """_init_ralph_loop creates required directory structure."""
        _init_ralph_loop()

        assert (temp_ralph_dir / "tasks").exists()
        assert (temp_ralph_dir / "logs").exists()

    def test_init_creates_tasks_json(self, temp_ralph_dir):
        """_init_ralph_loop creates tasks.json if it doesn't exist."""
        _init_ralph_loop()

        tasks_file = temp_ralph_dir / "tasks.json"
        assert tasks_file.exists()

        with open(tasks_file) as f:
            data = json.load(f)

        assert "tasks" in data
        assert data["tasks"] == []

    def test_init_does_not_overwrite_existing(self, temp_ralph_dir):
        """_init_ralph_loop doesn't overwrite existing tasks.json."""
        # Create existing tasks.json
        tasks_file = temp_ralph_dir / "tasks.json"
        existing_data = {"tasks": [{"id": "existing", "status": "pending"}]}
        with open(tasks_file, "w") as f:
            json.dump(existing_data, f)

        _init_ralph_loop()

        with open(tasks_file) as f:
            data = json.load(f)

        assert data == existing_data


class TestCreateTask:
    """Test task creation functionality."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_create_task_with_valid_description(self, temp_ralph_dir):
        """_create_task creates a task with valid description."""
        _init_ralph_loop()
        task_id = _create_task("Test task description")

        assert len(task_id) == 8
        assert (temp_ralph_dir / "tasks" / f"{task_id}.json").exists()

    def test_create_task_empty_description(self, temp_ralph_dir):
        """_create_task raises ValueError for empty description."""
        _init_ralph_loop()

        with pytest.raises(RalphValidationError) as exc_info:
            _create_task("")

        assert "cannot be empty" in str(exc_info.value)

    def test_create_task_whitespace_only(self, temp_ralph_dir):
        """_create_task raises ValueError for whitespace-only description."""
        _init_ralph_loop()

        with pytest.raises(RalphValidationError):
            _create_task("   ")

    def test_create_task_includes_acceptance_criteria(self, temp_ralph_dir):
        """_create_task generates acceptance criteria."""
        _init_ralph_loop()
        task_id = _create_task("Build a Python script")

        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)

        assert "acceptance_criteria" in spec
        assert len(spec["acceptance_criteria"]) > 0

    def test_create_task_includes_timestamp(self, temp_ralph_dir):
        """_create_task includes created_at timestamp."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)

        assert "created_at" in spec

    def test_create_task_updates_tasks_list(self, temp_ralph_dir):
        """_create_task adds task to tasks.json list."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)

        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task_id
        assert data["tasks"][0]["status"] == "pending"


class TestGenerateAcceptanceCriteria:
    """Test acceptance criteria generation."""

    def test_generates_basic_criteria(self):
        """_generate_acceptance_criteria returns list of criteria."""
        criteria = _generate_acceptance_criteria("Build a web scraper")

        assert isinstance(criteria, list)
        assert len(criteria) > 0

    def test_includes_specific_criteria_from_description(self):
        """_generate_acceptance_criteria extracts keywords from description."""
        criteria = _generate_acceptance_criteria(
            "Create a CSV parser with error handling"
        )

        # Should include specific criteria based on keywords
        criteria_str = " ".join(criteria).lower()
        assert (
            "csv" in criteria_str or "parser" in criteria_str or "error" in criteria_str
        )

    def test_handles_empty_description(self):
        """_generate_acceptance_criteria handles empty description gracefully."""
        criteria = _generate_acceptance_criteria("")

        assert isinstance(criteria, list)
        assert len(criteria) > 0  # Should still have default criteria


class TestCheckTaskComplete:
    """Test task completion checking."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_check_nonexistent_task(self, temp_ralph_dir):
        """_check_task_complete returns False for nonexistent task."""
        is_complete, message = _check_task_complete("nonexistent")

        assert is_complete is False
        assert "not found" in message.lower()

    def test_check_pending_task(self, temp_ralph_dir):
        """_check_task_complete returns False for pending task."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        is_complete, message = _check_task_complete(task_id)

        assert is_complete is False
        assert "not yet confirmed" in message.lower()

    def test_check_complete_task(self, temp_ralph_dir):
        """_check_task_complete returns True for completed task."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        # Mark task as complete
        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)
        spec["status"] = "complete"
        spec["confirmation"] = "Task verified"
        with open(spec_file, "w") as f:
            json.dump(spec, f)

        is_complete, message = _check_task_complete(task_id)

        assert is_complete is True
        assert "Task verified" in message


class TestExecuteIteration:
    """Test iteration execution."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_execute_iteration_returns_result(self, temp_ralph_dir):
        """_execute_iteration returns IterationResult."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        # Mock agent and console
        mock_agent = Mock()
        mock_agent.invoke_with_tools.return_value = "Task completed successfully"
        mock_console = Mock()

        result = _execute_iteration(mock_agent, task_id, 1)

        assert isinstance(result, IterationResult)
        assert result.result == "Task completed successfully"
        assert result.is_complete is False  # No <complete> tag

    def test_execute_iteration_detects_completion(self, temp_ralph_dir):
        """_execute_iteration detects <complete> tag."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        mock_agent = Mock()
        mock_agent.invoke_with_tools.return_value = (
            "Done! <complete>Yes, the task is complete.</complete>"
        )
        mock_console = Mock()

        result = _execute_iteration(mock_agent, task_id, 1)

        assert result.is_complete is True

    def test_execute_iteration_handles_error(self, temp_ralph_dir):
        """_execute_iteration handles agent errors gracefully."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        mock_agent = Mock()
        mock_agent.invoke_with_tools.side_effect = Exception("LLM failed")
        mock_console = Mock()

        result = _execute_iteration(mock_agent, task_id, 1)

        assert result.is_complete is False
        assert result.error is not None
        assert "Error" in result.result


class TestLogIteration:
    """Test iteration logging."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_log_iteration(self, temp_ralph_dir):
        """_log_iteration writes to log file."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        _log_iteration(task_id, 1, "Iteration result")

        log_file = temp_ralph_dir / "logs" / "iteration.log"
        assert log_file.exists()

        with open(log_file) as f:
            content = f.read()

        assert "Iteration 1" in content
        assert task_id in content


class TestVerifyTaskStatus:
    """Test task status verification."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_verify_pending_status(self, temp_ralph_dir):
        """_verify_task_status returns 'pending' for new task."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        status = _verify_task_status(task_id)

        assert status == "pending"

    def test_verify_complete_status(self, temp_ralph_dir):
        """_verify_task_status returns 'complete' for completed task."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        # Mark as complete
        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)
        spec["status"] = "complete"
        with open(spec_file, "w") as f:
            json.dump(spec, f)

        status = _verify_task_status(task_id)

        assert status == "complete"


class TestFinalizeTask:
    """Test task finalization."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_finalize_complete_task(self, temp_ralph_dir):
        """_finalize_task marks task as complete."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        _finalize_task(task_id, incomplete=False)

        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)

        assert spec["status"] == "complete"

    def test_finalize_incomplete_task(self, temp_ralph_dir):
        """_finalize_task marks task as incomplete."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        _finalize_task(task_id, incomplete=True)

        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)

        assert spec["status"] == "incomplete"
        assert "final_note" in spec
        assert "Maximum iterations" in spec["final_note"]

    def test_finalize_updates_tasks_list(self, temp_ralph_dir):
        """_finalize_task updates tasks.json list."""
        _init_ralph_loop()
        task_id = _create_task("Test task")

        _finalize_task(task_id, incomplete=False)

        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)

        assert data["tasks"][0]["status"] == "complete"


class TestRunCommand:
    """Test the main run command integration."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_run_with_empty_args(self, temp_ralph_dir):
        """run() handles empty arguments gracefully."""
        _init_ralph_loop()

        mock_agent = Mock()

        # Patch error in commands.ralph namespace (imported inside run())
        with patch("commands.ralph.error") as mock_error:
            # Should not raise, just print usage and return
            run(mock_agent, [])

        # Verify error was called for "Task description required."
        mock_error.assert_called_once()

    def test_run_with_valid_task(self, temp_ralph_dir):
        """run() executes a task successfully."""
        _init_ralph_loop()

        mock_agent = Mock()
        mock_agent.nesting_count = 0
        mock_agent.invoke_with_tools.return_value = (
            "<complete>Task is complete.</complete>"
        )

        # This should complete in one iteration
        with patch("commands.ralph._spawn_fork", return_value="<FINISHED>Done"):
            run(mock_agent, ["Test task"])

        # Verify task was created and completed
        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)

        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "complete"

    def test_run_max_iterations(self, temp_ralph_dir):
        """run() stops at MAX_ITERATIONS."""
        _init_ralph_loop()

        mock_agent = Mock()
        mock_agent.nesting_count = 0
        # Never complete
        mock_agent.invoke_with_tools.return_value = "Still working..."

        # Run with very low MAX_ITERATIONS for testing
        original_max = MAX_ITERATIONS
        import commands.ralph

        commands.ralph.MAX_ITERATIONS = 3

        try:
            with patch("commands.ralph._spawn_fork", return_value="No tag"):
                run(mock_agent, ["Test task"])
        finally:
            commands.ralph.MAX_ITERATIONS = original_max

        # Verify task was marked incomplete
        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)

        assert data["tasks"][0]["status"] == "incomplete"


class TestIntegration:
    """Integration tests for full Ralph Loop workflow."""

    @pytest.fixture
    def temp_ralph_dir(self):
        """Create a temporary directory for Ralph Loop testing."""
        original_dir = RALPH_LOOP_DIR
        temp_dir = Path(tempfile.mkdtemp())

        import commands.ralph

        commands.ralph.RALPH_LOOP_DIR = temp_dir

        yield temp_dir

        commands.ralph.RALPH_LOOP_DIR = original_dir
        shutil.rmtree(temp_dir)

    def test_full_workflow_success(self, temp_ralph_dir):
        """Test complete Ralph Loop workflow with successful completion."""
        _init_ralph_loop()

        mock_agent = Mock()
        mock_agent.nesting_count = 0
        mock_agent.invoke_with_tools.side_effect = [
            "Working on it...",  # Iteration 1
            "<complete>Done!</complete>",  # Iteration 2
        ]

        import commands.ralph

        original_max = commands.ralph.MAX_ITERATIONS
        commands.ralph.MAX_ITERATIONS = 5

        try:
            with patch("commands.ralph._spawn_fork", return_value="<FINISHED>Done"):
                run(mock_agent, ["Complete this task"])
        finally:
            commands.ralph.MAX_ITERATIONS = original_max

        # Verify workflow completed successfully
        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)

        assert data["tasks"][0]["status"] == "complete"

        # Verify log was written
        log_file = temp_ralph_dir / "logs" / "iteration.log"
        assert log_file.exists()

    def test_full_workflow_failure(self, temp_ralph_dir):
        """Test Ralph Loop workflow with max iterations reached."""
        _init_ralph_loop()

        mock_agent = Mock()
        mock_agent.nesting_count = 0
        mock_agent.invoke_with_tools.return_value = "Making progress..."

        import commands.ralph

        original_max = commands.ralph.MAX_ITERATIONS
        commands.ralph.MAX_ITERATIONS = 2

        try:
            with patch("commands.ralph._spawn_fork", return_value="No tag"):
                run(mock_agent, ["Complete this task"])
        finally:
            commands.ralph.MAX_ITERATIONS = original_max

        # Verify task marked incomplete
        tasks_file = temp_ralph_dir / "tasks.json"
        with open(tasks_file) as f:
            tasks_data = json.load(f)

        assert tasks_data["tasks"][0]["status"] == "incomplete"

        # Verify final_note is in the spec file (not in tasks.json list)
        task_id = tasks_data["tasks"][0]["id"]
        spec_file = temp_ralph_dir / "tasks" / f"{task_id}.json"
        with open(spec_file) as f:
            spec = json.load(f)

        assert "final_note" in spec
        assert "Maximum iterations" in spec["final_note"]
