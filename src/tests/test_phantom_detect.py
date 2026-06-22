"""Tests for phantom tool call detection."""

import pytest
from agent_phantom_detect import (
    PhantomRules,
    PhantomMatch,
    detect_phantoms,
    strip_phantoms,
    _score_phantom,
)


class TestScorePhantom:
    """Test phantom scoring logic."""

    @pytest.fixture
    def rules(self):
        return PhantomRules()

    @pytest.fixture
    def known_tools(self):
        return frozenset(["bash", "file_read", "file_write", "end_turn", "git"])

    def test_whitelist_tag_not_phantom(self, rules):
        """HTML tags should score 0.0."""
        score, reasons = _score_phantom("code", "some code", rules)
        assert score == 0.0
        assert reasons == []

    def test_suffix_pattern_detected(self, rules):
        """*_command suffix should trigger detection."""
        score, reasons = _score_phantom("bash_command", "git add .", rules)
        assert score >= rules.confidence_threshold
        assert any("suffix" in r for r in reasons)

    def test_prefix_pattern_detected(self, rules):
        """cmd_* prefix should trigger detection."""
        score, reasons = _score_phantom("cmd_bash", "ls -la", rules)
        assert score >= rules.confidence_threshold
        assert any("prefix" in r for r in reasons)

    def test_command_keyword_detected(self, rules):
        """Shell commands in body should trigger detection."""
        score, reasons = _score_phantom("some_tag", "git commit -m 'test'", rules)
        assert score >= rules.confidence_threshold
        assert any("keyword" in r for r in reasons)

    def test_tool_proximity_detected(self, rules, known_tools):
        """Tag close to real tool name should trigger detection."""
        score, reasons = _score_phantom("bash", "ls", rules, known_tools)
        # Exact match to tool name
        assert score >= rules.confidence_threshold

    def test_levenshtein_proximity(self, rules, known_tools):
        """Tag similar to real tool (Levenshtein) should trigger."""
        score, reasons = _score_phantom("endturn", "ENDTURN", rules, known_tools)
        assert score >= rules.confidence_threshold
        assert any("close to tool" in r for r in reasons)

    def test_substring_containment(self, rules, known_tools):
        """Tag containing tool name should trigger."""
        score, reasons = _score_phantom("bash_command", "ls", rules, known_tools)
        assert score >= rules.confidence_threshold


class TestDetectPhantoms:
    """Test phantom detection in content."""

    @pytest.fixture
    def rules(self):
        return PhantomRules()

    @pytest.fixture
    def known_tools(self):
        return frozenset(["bash", "file_read", "file_write", "end_turn", "git"])

    def test_bash_command_detected(self, rules, known_tools):
        """<bash_command> should be detected as phantom."""
        content = "Let me run this: <bash_command>git add .</bash_command>"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        assert len(phantoms) >= 1
        assert phantoms[0].tag_name == "bash_command"

    def test_nested_tags_detected(self, rules, known_tools):
        """Multiple phantom tags should all be detected."""
        content = "<cmd_run>ls</cmd_run> and <tool_exec>cat file</tool_exec>"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        assert len(phantoms) >= 2

    def test_clean_content_no_phantoms(self, rules, known_tools):
        """Clean content should not trigger detection."""
        content = "This is a normal response with no tool calls."
        phantoms = detect_phantoms(content, None, rules, known_tools)
        assert len(phantoms) == 0

    def test_html_whitelist_not_detected(self, rules, known_tools):
        """HTML tags should not be detected as phantoms."""
        content = "Here's some code: <code>print('hello')</code>"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        assert len(phantoms) == 0

    def test_reasoning_channel_detected(self, rules, known_tools):
        """Phantoms in reasoning should be detected."""
        content = "Normal content."
        reasoning = "I should run <bash_command>git status</bash_command>"
        phantoms = detect_phantoms(content, reasoning, rules, known_tools)
        assert len(phantoms) >= 1

    def test_both_channels_detected(self, rules, known_tools):
        """Phantoms in both channels should all be detected."""
        content = "Run <cmd_git>add .</cmd_git>"
        reasoning = "Then <tool_commit>-m 'fix'</tool_commit>"
        phantoms = detect_phantoms(content, reasoning, rules, known_tools)
        assert len(phantoms) >= 2

    def test_disabled_rules_no_detection(self, known_tools):
        """Disabled rules should not detect anything."""
        rules = PhantomRules(enabled=False)
        content = "<bash_command>git add .</bash_command>"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        assert len(phantoms) == 0


class TestStripPhantoms:
    """Test phantom stripping."""

    @pytest.fixture
    def rules(self):
        return PhantomRules()

    @pytest.fixture
    def known_tools(self):
        return frozenset(["bash", "file_read", "file_write", "end_turn", "git"])

    def test_strip_from_content(self, rules, known_tools):
        """Phantoms should be removed from content."""
        content = "Run <bash_command>git add .</bash_command> now"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        stripped_content, stripped_reasoning = strip_phantoms(
            content, None, phantoms,
        )
        assert "bash_command" not in stripped_content
        assert stripped_reasoning is None

    def test_strip_from_reasoning(self, rules, known_tools):
        """Phantoms should be removed from reasoning."""
        content = "Normal content."
        reasoning = "I should run <bash_command>git status</bash_command>"
        phantoms = detect_phantoms(content, reasoning, rules, known_tools)
        stripped_content, stripped_reasoning = strip_phantoms(
            content, reasoning, phantoms,
        )
        assert "bash_command" not in stripped_reasoning

    def test_strip_multiple(self, rules, known_tools):
        """Multiple phantoms should all be stripped."""
        content = "<cmd_run>ls</cmd_run> and <tool_exec>cat</tool_exec>"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        stripped_content, _ = strip_phantoms(content, None, phantoms)
        assert "cmd_run" not in stripped_content
        assert "tool_exec" not in stripped_content

    def test_strip_preserves_surrounding_text(self, rules, known_tools):
        """Non-phantom text should be preserved."""
        content = "Hello <bash_command>git add</bash_command> world"
        phantoms = detect_phantoms(content, None, rules, known_tools)
        stripped_content, _ = strip_phantoms(content, None, phantoms)
        assert "Hello" in stripped_content
        assert "world" in stripped_content


class TestPhantomRules:
    """Test rule file loading and defaults."""

    def test_default_rules(self):
        """Default rules should be enabled with sensible defaults."""
        rules = PhantomRules()
        assert rules.enabled
        assert rules.confidence_threshold == 0.6
        assert rules.levenshtein_threshold == 2
        assert "_command" in rules.suffix_patterns
        assert "git" in rules.command_keywords

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        rules = PhantomRules(confidence_threshold=0.8)
        assert rules.confidence_threshold == 0.8

    def test_disabled_rules(self):
        """Disabled rules should not detect anything."""
        rules = PhantomRules(enabled=False)
        assert not rules.enabled
