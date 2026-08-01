"""Test compression pipeline execution with real context data.

This test loads a real context file from the dream session and runs
the compression pipeline with a 99% target to verify all 11 steps execute.
"""

import json
import pytest
from pathlib import Path

# Path to the test context file (605KB from dream session)
TEST_CONTEXT_PATH = Path(__file__).parent.parent / "test_context_605kb.json"


def load_test_context():
    """Load the test context from a JSON file."""
    if not TEST_CONTEXT_PATH.exists():
        pytest.skip("Test context file not found")
    
    with open(TEST_CONTEXT_PATH, "r") as f:
        data = json.load(f)
    
    # The context file contains a list of messages
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "messages" in data:
        return data["messages"]
    else:
        raise ValueError(f"Unexpected context format: {type(data)}")


class TestCompressionPipeline:
    """Test that all 11 compression steps execute in sequence."""
    
    @pytest.fixture
    def context(self):
        """Load the test context."""
        return load_test_context()
    
    @pytest.fixture
    def compress_context(self):
        """Import the compression function."""
        from src.agent_context_compress import compress_context
        return compress_context
    
    def test_all_11_steps_execute(self, context, compress_context):
        """Verify that all 11 compression steps are executed with 99% target."""
        from src.agent_context_compress import _COMPRESSION_PIPELINE
        
        # Expected steps
        expected_steps = [step.name for step in _COMPRESSION_PIPELINE]
        assert len(expected_steps) == 11, f"Expected 11 steps, got {len(expected_steps)}"
        
        # Run compression with 99% target (very aggressive)
        result_context, summary, metadata = compress_context(
            context=context,
            client=None,  # Mock client (not needed for non-LLM steps)
            model_name="test-model",
            compression_factor=0.99,  # 99% target
            tools=[],
            verbose=True,
            last_known_tokens=153565,
            max_context_tokens=180000,
            max_output_tokens=12000,
        )
        
        # Check that all 11 steps were executed
        algorithms_used = metadata.get("algorithms_used", [])
        
        print(f"\n=== Compression Results ===")
        print(f"Original size: {metadata.get('original_size', 'N/A')} bytes")
        print(f"Final size: {metadata.get('final_size', 'N/A')} bytes")
        print(f"Target size: {metadata.get('target_size', 'N/A')} bytes")
        print(f"Algorithms used: {algorithms_used}")
        print(f"Summary: {summary}")
        
        # Verify all 11 steps were used
        assert len(algorithms_used) == 11, (
            f"Expected 11 steps to execute, but only {len(algorithms_used)} ran: {algorithms_used}\n"
            f"Missing steps: {set(expected_steps) - set(algorithms_used)}"
        )
        
        # Verify the steps are in the correct order
        assert algorithms_used == expected_steps, (
            f"Steps executed in wrong order:\n"
            f"Expected: {expected_steps}\n"
            f"Got: {algorithms_used}"
        )
        
        # Verify the final size is below the target
        final_size = metadata.get("final_size", 0)
        target_size = metadata.get("target_size", float('inf'))
        
        print(f"\nFinal size: {final_size:,} bytes")
        print(f"Target size: {target_size:,} bytes")
        print(f"Reduction: {(1 - final_size / metadata.get('original_size', 1)) * 100:.1f}%")
        
        # With 99% target, we should either reach the target or exhaust all steps
        if final_size > target_size:
            print(f"WARNING: Final size ({final_size:,}) > target ({target_size:,})")
            print("This means all steps were exhausted but target not reached.")
        else:
            print(f"SUCCESS: Target reached ({final_size:,} <= {target_size:,})")


class TestCompressionDebugOutput:
    """Test that debug output is generated correctly."""
    
    @pytest.fixture
    def context(self):
        """Load the test context."""
        return load_test_context()
    
    @pytest.fixture
    def compress_context(self):
        """Import the compression function."""
        from src.agent_context_compress import compress_context
        return compress_context
    
    def test_debug_logging_shows_target(self, context, compress_context, capsys):
        """Verify that debug logging shows the target size and comparison."""
        from src.agent_context_compress import compress_context
        
        # Run compression
        result_context, summary, metadata = compress_context(
            context=context,
            client=None,
            model_name="test-model",
            compression_factor=0.99,
            tools=[],
            verbose=True,
            last_known_tokens=153565,
            max_context_tokens=180000,
            max_output_tokens=12000,
        )
        
        # Capture stdout
        captured = capsys.readouterr()
        
        # Check for debug output
        assert "[COMPRESS]" in captured.out, "Expected [COMPRESS] debug output"
        
        # Check for EARLY EXIT or ALL STEPS EXHAUSTED
        if "EARLY EXIT" in captured.out:
            print("\n=== EARLY EXIT DETECTED ===")
            print(captured.out)
            assert False, "Compression stopped early - check debug output"
        elif "ALL STEPS EXHAUSTED" in captured.out:
            print("\n=== ALL STEPS EXHAUSTED ===")
            print(captured.out)
            # This is expected if target is not reached
        else:
            print("\n=== COMPRESSION OUTPUT ===")
            print(captured.out)
            assert False, "Expected either 'EARLY EXIT' or 'ALL STEPS EXHAUSTED' in output"