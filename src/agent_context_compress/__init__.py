"""Context compression algorithms for LLM conversation management.

Eleven pipeline steps applied until target size is reached. Nine functions
implement these steps — `compress_tool_pruning` and `compress_redact_blocks`
each serve two steps via the `use_boundary` parameter.

1. compress_prune_images — replace image content blocks with text placeholders
2. compress_oversized_tool_redaction — redact single oversized tool results
3. compress_drop_reasoning — strip reasoning fields from assistant messages
4. compress_last_transaction — LLM summarization of completed turns
5. compress_tool_pruning — replace large tool outputs with placeholders (50% boundary)
6. compress_redact_blocks — strip intermediate messages from completed blocks (50% boundary)
7. compress_tool_pruning (use_boundary=False) — same as #5, scans entire context
8. compress_redact_blocks (use_boundary=False) — same as #6, scans entire context
9. compress_full_reset — full context rebuild (last resort)
10. compress_conversation_summary — deterministic conversation restructuring (fallback)
11. compress_blind_truncate — truncate summary from beginning (guaranteed fit)

ARCHITECTURE:

- Fixed 50% boundary: protects recent messages (current task state).
  Steps 2-6 operate within the boundary. Steps 7-8 ignore it.
- Right-to-left scanning: preserves KV cache prefix (step 4).
  Steps 5-8 scan left-to-right from index 0.
- Parameter consistency: same model/tools/params across compression calls.
- Compression prompt stability: prompts must not change between calls.

LOGGING:

- Console: One-liner per pipeline step via compression_step_summary().
- Audit: Per-action detail via audit_writer.compress_start/action/step_end().
- Errors/warnings: Continue via _verbose() / warning() as before.

MODULAR DESIGN:

Each compression algorithm is extracted into its own module under steps/.
This module provides the orchestrator (compress_context). Pipeline registration
lives in pipeline.py to keep impl function imports out of this namespace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Direct imports from focused source modules.

from agent_context_compress.steps.framework import (
    # Data classes
    CompressionContext,
    CompressionStep,
    # Wrapper
    _compress_wrapper,
    _verbose,
)

from agent_context_compress.steps.utils import (
    # Constants
    MAX_ITERATIONS,
    MIN_BLOCK_SIZE,
    OVERSIZED_THRESHOLD,
    PRUNE_THRESHOLD,
    SUMMARY_TOOL_RESULT_MAX_BYTES,
    # Helpers used by compress_context orchestrator
    _build_action_summary,
    _calculate_context_bytes,
    _format_success,
    compute_compression_target_bytes,
    # Helper re-exported for testing (used by test_context_validation_fixes.py)
    _has_unresolved_tool_calls,
)

# Console output
from agent_console import echo

# Console display — compression_step_summary is only used in the orchestrator
# (compress_context), not in shared utilities.
from agent_console import compression_step_summary

# Individual compression algorithms (public wrappers for testing/composition)
from agent_context_compress.steps.prune_images import compress_prune_images
from agent_context_compress.steps.oversized_tool_redaction import compress_oversized_tool_redaction
from agent_context_compress.steps.drop_reasoning import compress_drop_reasoning
from agent_context_compress.steps.last_transaction import compress_last_transaction
from agent_context_compress.steps.tool_pruning import compress_tool_pruning
from agent_context_compress.steps.redact_blocks import compress_redact_blocks
from agent_context_compress.steps.full_reset import compress_full_reset
from agent_context_compress.steps.conversation_summary import compress_conversation_summary
from agent_context_compress.steps.blind_truncate import compress_blind_truncate

from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS


__all__ = [
    # Data classes
    "CompressionStep",
    "CompressionContext",
    # Constants
    "MAX_ITERATIONS",
    "MIN_BLOCK_SIZE",
    "OVERSIZED_THRESHOLD",
    "PRUNE_THRESHOLD",
    "SUMMARY_TOOL_RESULT_MAX_BYTES",
    # Orchestrator
    "compress_context",
    # Helper (public for testing)
    "compute_compression_target_bytes",
    # Individual compression algorithms (public for testing/composition)
    "compress_prune_images",
    "compress_oversized_tool_redaction",
    "compress_drop_reasoning",
    "compress_last_transaction",
    "compress_tool_pruning",
    "compress_redact_blocks",
    "compress_full_reset",
    "compress_conversation_summary",
    "compress_blind_truncate",
    # Private helpers re-exported for testing only (prefix _ indicates internal)
    "_calculate_context_bytes",
    "_compress_wrapper",
    "_has_unresolved_tool_calls",
]


# --- Pipeline Registry ---

# Pipeline definition moved to pipeline.py to keep impl function imports
# out of this module's namespace.  Only the pipeline tuple is imported here.
from agent_context_compress.pipeline import _COMPRESSION_PIPELINE


# --- Orchestrator ---

def compress_context(
    context: list[dict],
    client: Any,
    model_name: str,
    compression_factor: float,
    tools: list[dict],
    extra_kwargs: dict[str, Any] | None = None,
    verbose: bool = False,
    log_file: Path | None = None,
    audit_writer: Any = None,
    last_known_tokens: int | None = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> tuple[list[dict], str, dict[str, Any]]:
    """Run compression algorithms in sequence until target size is reached.

    Pipeline (least to most aggressive):
    1.  PRUNE_IMAGES — replace image content blocks with text placeholders
    2.  OVERSIZED_TOOL_REDACTION — redact single oversized tool results
    3.  DROP_REASONING — strip reasoning fields from assistant messages
    4.  LAST_TRANSACTION — LLM summarization of completed turns
    5.  TOOL_PRUNING — replace large tool outputs with placeholders (50% boundary)
    6.  REDACT_BLOCKS — strip intermediate messages from completed blocks (50% boundary)
    7.  TOOL_PRUNING_FULL — same as #5 but scans entire context (no boundary)
    8.  REDACT_BLOCKS_FULL — same as #6 but scans entire context (no boundary)
    9.  FULL_RESET — full context rebuild (last resort)
    10. CONVERSATION_SUMMARY — deterministic conversation restructuring (fallback)
    11. BLIND_TRUNCATE — truncate summary from beginning (guaranteed fit)

    Stops early if target is reached.  Original context preserved if all fail.
    """
    original_size = _calculate_context_bytes(context)
    original_message_count = len(context)
    target_size = compute_compression_target_bytes(
        original_size,
        compression_factor,
        last_known_tokens,
        max_context_tokens,
        max_output_tokens,
    )

    if audit_writer is not None:
        audit_writer.compress_pipeline_start(original_size, target_size, compression_factor, last_known_tokens)

    if verbose:
        byte_target = int(original_size * (1 - compression_factor))
        if last_known_tokens is not None and last_known_tokens > 0:
            echo(f"[COMPRESS] ORCHESTRATOR: {original_message_count} msgs, {original_size:,} bytes → target {compression_factor*100:.0f}% ({byte_target:,} bytes), token-aware target: {target_size:,} bytes (tokens: {last_known_tokens})")
        else:
            echo(f"[COMPRESS] ORCHESTRATOR: {original_message_count} msgs, {original_size:,} bytes → target {compression_factor*100:.0f}% ({target_size:,} bytes)")

    result = list(context)
    algorithms_used: list[str] = []
    bytes_per_algo: dict[str, int] = {}

    total_steps = len(_COMPRESSION_PIPELINE)

    for idx, step in enumerate(_COMPRESSION_PIPELINE, 1):
        # Forward all params so LLM-based steps (last_transaction, full_reset)
        # can reach _invoke_llm_with_retry_compression via kwargs
        result, step_metadata = _compress_wrapper(
            step.name, step.impl_fn, result, target_size, verbose, audit_writer,
            client=client, model_name=model_name, tools=tools,
            extra_kwargs=extra_kwargs, log_file=log_file,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
            **step.kwargs,
        )
        size = step_metadata["bytes_after"]
        msg_count = step_metadata["msgs_after"]
        action_summary = _build_action_summary(step_metadata["actions"])

        # Always emit console one-liner for this step
        compression_step_summary(
            step_name=step_metadata["step_name"],
            step_idx=idx,
            total_steps=total_steps,
            bytes_before=step_metadata["bytes_before"],
            msgs_before=step_metadata["msgs_before"],
            bytes_after=step_metadata["bytes_after"],
            msgs_after=step_metadata["msgs_after"],
            action_summary=action_summary,
            status=step_metadata["status"],
        )

        if verbose:
            _verbose(f"[STEP {idx}/{total_steps} {step.name}] Entry: {step_metadata['msgs_before']} msgs, {step_metadata['bytes_before']:,} bytes")
            _verbose(f"[STEP {idx}/{total_steps} {step.name}] Exit: {msg_count} msgs, {size:,} bytes")

        algorithms_used.append(step.name)
        bytes_per_algo[step.name] = step_metadata["bytes_before"] - step_metadata["bytes_after"]

        if size <= target_size:
            # Debug: log why we're exiting early
            echo(f"[COMPRESS] EARLY EXIT at step {idx}/{total_steps} ({step.name}): size={size:,} <= target={target_size:,} (reduction={(1-size/original_size)*100:.1f}%, target={compression_factor*100:.0f}%)")
            summary, metadata = _format_success(
                step.name, size, original_size, compression_factor, msg_count,
                algorithms_used, verbose,
            )
            return result, summary, metadata

    # All steps exhausted — return final result
    echo(f"[COMPRESS] ALL STEPS EXHAUSTED: size={size:,} > target={target_size:,} (reduction={(1-size/original_size)*100:.1f}%, target={compression_factor*100:.0f}%)")
    if verbose and bytes_per_algo:
        for algo_name, saved in bytes_per_algo.items():
            _verbose(f"  :: {algo_name}: saved {saved:,} bytes")

    final_summary = f"FINAL: {algorithms_used[-1] if algorithms_used else 'NONE'} ({size:,} bytes)"

    if verbose:
        echo(f"\n{'='*70}")
        echo("  COMPRESSION COMPLETE - FINAL")
        echo(f"{'='*70}\n")
        reduction_pct = (1 - size / original_size) * 100 if original_size > 0 else 0
        _verbose(f"    Original: {original_size:,} bytes -> {size:,} bytes")
        _verbose(f"    Reduction: {reduction_pct:.1f}% (target was {compression_factor*100:.0f}%)")
        _verbose(f"    Algorithms used: {' + '.join(algorithms_used)}")
        _verbose(f"    Final context: {size:,} bytes, {msg_count} messages\n")

    metadata = {
        "bytes_before": original_size,
        "bytes_after": size,
        "algorithms_used": algorithms_used,
        "bytes_per_algo": bytes_per_algo,
    }

    # --- Final verification: print error if target not achieved ---
    if size > target_size:
        echo(
            f"\n{'='*70}\n"
            f"  COMPRESSION TARGET NOT MET — ROOT CAUSE INVESTIGATION\n"
            f"{'='*70}\n"
            f"  Original size:   {original_size:,} bytes\n"
            f"  Target size:     {target_size:,} bytes (compression_factor={compression_factor})\n"
            f"  Achieved size:   {size:,} bytes\n"
            f"  Reduction:       {(1-size/original_size)*100:.1f}% (need {compression_factor*100:.0f}%)\n"
            f"  Gap:             {size - target_size:,} bytes above target\n"
            f"  Algorithms used: {' + '.join(algorithms_used)}\n"
            f"  Bytes saved:     {sum(bytes_per_algo.values()):,} bytes\n"
            f"{'='*70}\n"
        )
        if audit_writer is not None:
            audit_writer.compress_pipeline_end(size, algorithms_used, sum(bytes_per_algo.values()))

    return result, final_summary, metadata
