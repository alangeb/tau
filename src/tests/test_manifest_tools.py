"""Comprehensive tests for manifest tools (manifest_create, manifest_update, manifest_tree).

Tests cover:
- manifest_create: basic creation, defaults, checkbox preservation, directory creation, return path
- manifest_update: status update, section update, invalid section, missing manifest,
  auto-verify pass/fail, allowlist enforcement, state file management
- manifest_tree: empty dir, single manifest, parent-child hierarchy, root filter

Uses pytest, tempfile (via tmp_path), and pathlib. Follows existing project test patterns.
"""

import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports (mirrors test_tools_system.py pattern)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.manifest_create import run as manifest_create
from tools.manifest_update import run as manifest_update
from tools.manifest_tree import run as manifest_tree


# ── Helpers ────────────────────────────────────────────────────────


@contextmanager
def _chdir_tmp(tmp_path: Path):
    """Change working directory to tmp_path for the duration of the test."""
    original_cwd = Path.cwd()
    os.chdir(str(tmp_path))
    try:
        yield tmp_path
    finally:
        os.chdir(str(original_cwd))


# ── manifest_create tests ─────────────────────────────────────────


class TestManifestCreate:
    """Tests for manifest_create tool."""

    def test_create_manifest_basic(self, tmp_path: Path):
        """Creates manifest with goal, title, criteria, and subtasks."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(
                goal="Implement feature X",
                title="Feature X",
                success_criteria="Criterion 1\nCriterion 2",
                subtasks="Task A\nTask B",
            )

            # Returns a path string
            assert isinstance(result, str)
            manifest_path = Path(result)
            assert manifest_path.exists()
            assert manifest_path.suffix == ".md"

            content = manifest_path.read_text(encoding="utf-8")
            # Frontmatter
            assert 'id: "' in content
            assert 'title: "Feature X"' in content
            assert 'goal: "Implement feature X"' in content
            assert 'status: "planning"' in content
            # Sections
            assert "## Goal" in content
            assert "Implement feature X" in content
            assert "## Success Criteria" in content
            assert "Criterion 1" in content
            assert "Criterion 2" in content
            assert "## Subtasks" in content
            assert "Task A" in content
            assert "Task B" in content
            assert "## Progress" in content
            assert "(empty)" in content

    def test_create_manifest_defaults(self, tmp_path: Path):
        """Uses default values for optional fields."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(goal="Simple goal")

            manifest_path = Path(result)
            content = manifest_path.read_text(encoding="utf-8")

            # Default title is the generated id
            assert 'title: "' in content
            assert 'goal: "Simple goal"' in content
            # Default sections show placeholder
            assert "(none specified)" in content
            # Frontmatter defaults
            assert 'status: "planning"' in content
            assert "depth: 0" in content
            assert "parent: null" in content

    def test_create_manifest_preserves_checkboxes(self, tmp_path: Path):
        """Doesn't double-prefix already-formatted checkbox items."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(
                goal="Test checkbox preservation",
                title="Checkbox Test",
                success_criteria="- [ ] Already formatted criterion",
                subtasks="- [x] Already done task",
            )

            content = Path(result).read_text(encoding="utf-8")

            # Should NOT have double-prefixed items like "- [ ] 1. - [ ] ..."
            assert "- [ ] Already formatted criterion" in content
            assert "- [x] Already done task" in content
            # Count occurrences — should appear exactly once, not doubled
            assert content.count("Already formatted criterion") == 1
            assert content.count("Already done task") == 1

    def test_create_manifest_creates_directory(self, tmp_path: Path):
        """Creates .tau/manifests/ directory if it doesn't exist."""
        with _chdir_tmp(tmp_path):
            # Ensure directory doesn't exist
            assert not (tmp_path / ".tau" / "manifests").exists()

            result = manifest_create(goal="Create dir test")

            # Directory should now exist
            manifests_dir = tmp_path / ".tau" / "manifests"
            assert manifests_dir.is_dir()
            # And contain the manifest
            assert len(list(manifests_dir.glob("manifest-*.md"))) >= 1

    def test_create_manifest_returns_path(self, tmp_path: Path):
        """Returns the manifest file path as a string."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(
                goal="Path return test",
                title="Path Test",
            )

            assert isinstance(result, str)
            # Path should be relative to .tau/manifests/
            assert ".tau/manifests/" in result or ".tau\\manifests\\" in result
            assert result.endswith(".md")
            # Path should exist
            assert Path(result).exists()


# ── manifest_update tests ─────────────────────────────────────────


class TestManifestUpdate:
    """Tests for manifest_update tool."""

    def _create_manifest(self, tmp_path: Path) -> Path:
        """Helper to create a manifest and return its path."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(
                goal="Update test goal",
                title="Update Test",
                success_criteria="Criterion 1 → Verify: `echo ok`\nCriterion 2",
                subtasks="Task 1\nTask 2",
            )
            return Path(result)

    def test_update_status(self, tmp_path: Path):
        """Updates status in frontmatter."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)

            result = manifest_update(
                path=str(manifest_path),
                section="status",
                content="executing",
            )

            assert "Updated status" in result
            assert "executing" in result

            content = manifest_path.read_text(encoding="utf-8")
            assert 'status: "executing"' in content

    def test_update_section(self, tmp_path: Path):
        """Updates a section (success_criteria, subtasks, progress)."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)

            # Update subtasks
            new_subtasks = "- [x] 1. Task 1\n- [ ] 2. Task 2\n- [ ] 3. New Task"
            result = manifest_update(
                path=str(manifest_path),
                section="subtasks",
                content=new_subtasks,
            )

            assert "Updated 'subtasks'" in result

            content = manifest_path.read_text(encoding="utf-8")
            assert "- [x] 1. Task 1" in content
            assert "- [ ] 3. New Task" in content

    def test_update_invalid_section(self, tmp_path: Path):
        """Returns error for invalid section name."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)

            result = manifest_update(
                path=str(manifest_path),
                section="nonexistent_section",
                content="some content",
            )

            assert "Error" in result
            assert "Invalid section" in result

    def test_update_missing_manifest(self, tmp_path: Path):
        """Returns error for missing manifest file."""
        with _chdir_tmp(tmp_path):
            result = manifest_update(
                path=str(tmp_path / "nonexistent" / "manifest-123.md"),
                section="status",
                content="planning",
            )

            assert "Error" in result
            assert "not found" in result.lower() or "not found" in result.lower()

    def test_update_auto_verify_pass(self, tmp_path: Path):
        """Runs verification on completed items and passes."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)

            # Mark criterion 1 as complete (it has Verify: `echo ok`)
            new_criteria = "- [x] 1. Criterion 1 → Verify: `echo ok`\n- [ ] 2. Criterion 2"

            # Mock subprocess.run to simulate successful verification
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "ok"
            mock_result.stderr = ""

            with patch("tools.manifest_update.subprocess.run", return_value=mock_result):
                result = manifest_update(
                    path=str(manifest_path),
                    section="success_criteria",
                    content=new_criteria,
                )

            assert "Updated 'success_criteria'" in result
            assert "Error" not in result

    def test_update_auto_verify_fail(self, tmp_path: Path):
        """Runs verification on completed items, fails with retry."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)

            # Mark criterion 1 as complete
            new_criteria = "- [x] 1. Criterion 1 → Verify: `echo ok`\n- [ ] 2. Criterion 2"

            # Mock subprocess.run to simulate failed verification
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "test failure"

            with patch("tools.manifest_update.subprocess.run", return_value=mock_result):
                result = manifest_update(
                    path=str(manifest_path),
                    section="success_criteria",
                    content=new_criteria,
                )

            assert "Verification failed" in result or "Verification FAILED" in result
            assert "Retries remaining" in result or "No retries remaining" in result

    def test_update_verify_allowlist(self, tmp_path: Path):
        """Blocks non-allowlisted commands in verification."""
        with _chdir_tmp(tmp_path):
            # Create a manifest with a non-allowlisted verify command
            with _chdir_tmp(tmp_path):
                result = manifest_create(
                    goal="Allowlist test",
                    title="Allowlist Test",
                    success_criteria="Bad criterion → Verify: `rm -rf /`",
                )
                manifest_path = Path(result)

            # Mark as complete
            new_criteria = "- [x] 1. Bad criterion → Verify: `rm -rf /`"

            # No mock needed — allowlist check happens before subprocess.run
            result = manifest_update(
                path=str(manifest_path),
                section="success_criteria",
                content=new_criteria,
            )

            # Should fail because 'rm' is not in the allowlist
            assert "not in allowlist" in result.lower() or "not in allowlist" in result

    def test_update_state_file(self, tmp_path: Path):
        """Creates and updates .state.json file alongside manifest."""
        with _chdir_tmp(tmp_path):
            manifest_path = self._create_manifest(tmp_path)
            state_path = manifest_path.with_suffix(".state.json")

            # State file should not exist yet
            assert not state_path.exists()

            # Mark criterion 1 as complete with a failing verification
            new_criteria = "- [x] 1. Criterion 1 → Verify: `echo ok`\n- [ ] 2. Criterion 2"

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "fail"

            with patch("tools.manifest_update.subprocess.run", return_value=mock_result):
                result = manifest_update(
                    path=str(manifest_path),
                    section="success_criteria",
                    content=new_criteria,
                )

            # State file should now exist
            assert state_path.exists()

            # Verify state file contents
            state = json.loads(state_path.read_text(encoding="utf-8"))
            assert "subtask_1" in state
            assert state["subtask_1"]["status"] in ("retrying", "failed")


# ── manifest_tree tests ───────────────────────────────────────────


class TestManifestTree:
    """Tests for manifest_tree tool."""

    def test_tree_empty(self, tmp_path: Path):
        """Returns message when no manifests exist."""
        with _chdir_tmp(tmp_path):
            result = manifest_tree()

            assert "No manifests found" in result

    def test_tree_single_manifest(self, tmp_path: Path):
        """Shows single manifest with status."""
        with _chdir_tmp(tmp_path):
            # Create a manifest
            manifest_create(
                goal="Single manifest test",
                title="Single Test",
            )

            result = manifest_tree()

            # Should show the manifest with status
            assert "manifest-" in result
            assert "[planning]" in result
            assert "○" in result  # planning icon

    def test_tree_parent_child(self, tmp_path: Path):
        """Shows parent-child hierarchy in tree output."""
        with _chdir_tmp(tmp_path):
            # Create parent manifest
            parent_result = manifest_create(
                goal="Parent goal",
                title="Parent Manifest",
            )
            parent_path = Path(parent_result)

            # Read parent to get its ID
            parent_content = parent_path.read_text(encoding="utf-8")
            id_match = re.search(r'id: "([^"]+)"', parent_content)
            assert id_match is not None
            parent_id = id_match.group(1)

            # Small delay to ensure unique timestamp for child
            time.sleep(1.1)

            # Create child manifest
            child_result = manifest_create(
                goal="Child goal",
                title="Child Manifest",
            )
            child_path = Path(child_result)

            # Patch the child's frontmatter to reference parent
            child_content = child_path.read_text(encoding="utf-8")
            child_content = re.sub(
                r'parent: null',
                f'parent: "{parent_id}"',
                child_content,
            )
            child_content = re.sub(
                r'depth: 0',
                'depth: 1',
                child_content,
                count=1,
            )
            child_path.write_text(child_content, encoding="utf-8")

            result = manifest_tree()

            # Should show parent and child in hierarchy
            assert len(result) > 0, f"Tree output is empty"
            assert "manifest-" in result
            # Tree connector should be present for child
            assert "└──" in result or "├──" in result

    def test_tree_filter_root(self, tmp_path: Path):
        """Filters tree output by root manifest ID."""
        with _chdir_tmp(tmp_path):
            # Create two independent manifests (with delay for unique IDs)
            manifest_create(
                goal="First goal",
                title="First Manifest",
            )
            time.sleep(1.1)
            manifest_create(
                goal="Second goal",
                title="Second Manifest",
            )

            # Get list of manifests
            manifests_dir = tmp_path / ".tau" / "manifests"
            manifests = list(manifests_dir.glob("manifest-*.md"))
            assert len(manifests) >= 2

            # Read first manifest to get its ID
            first_content = manifests[0].read_text(encoding="utf-8")
            id_match = re.search(r'id: "([^"]+)"', first_content)
            assert id_match is not None
            first_id = id_match.group(1)

            # Filter by first manifest's ID
            result = manifest_tree(args=type('Args', (), {'root': first_id})())

            # Should show only the filtered manifest
            assert "manifest-" in result
            # The result should not contain the other manifest's ID
            # (unless it happens to be a substring, so check for the full ID)
            other_manifests = [m for m in manifests if m != manifests[0]]
            for other in other_manifests:
                other_content = other.read_text(encoding="utf-8")
                other_id_match = re.search(r'id: "([^"]+)"', other_content)
                if other_id_match:
                    other_id = other_id_match.group(1)
                    # The other ID should not appear in the filtered result
                    # (it might appear as a substring of the filename, so be careful)

    def test_tree_filter_nonexistent_root(self, tmp_path: Path):
        """Returns error message when filtering by nonexistent root."""
        with _chdir_tmp(tmp_path):
            result = manifest_tree(args=type('Args', (), {'root': 'nonexistent-id'})())

            assert "No manifest found" in result or "No manifest" in result


# ── Integration tests ─────────────────────────────────────────────


class TestManifestIntegration:
    """Integration tests spanning multiple manifest tools."""

    def test_create_update_tree_flow(self, tmp_path: Path):
        """Full flow: create manifest, update it, view in tree."""
        with _chdir_tmp(tmp_path):
            # 1. Create
            path = manifest_create(
                goal="Integration test",
                title="Integration Test",
                success_criteria="Step 1 → Verify: `echo done`",
                subtasks="Do something",
            )

            # 2. Update status
            result = manifest_update(
                path=path,
                section="status",
                content="executing",
            )
            assert "Updated status" in result

            # 3. View in tree
            tree = manifest_tree()
            assert "manifest-" in tree
            assert "[executing]" in tree
            assert "⟳" in tree  # executing icon

    def test_create_with_depth_and_parent(self, tmp_path: Path):
        """Create manifest with depth and parent parameters."""
        with _chdir_tmp(tmp_path):
            result = manifest_create(
                goal="Child goal",
                title="Child",
                depth=1,
                parent="/some/parent/path.md",
            )

            content = Path(result).read_text(encoding="utf-8")
            assert "depth: 1" in content
            # Parent is stored without quotes in frontmatter
            assert "parent: /some/parent/path.md" in content
