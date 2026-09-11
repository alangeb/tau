"""Compression pipeline definition.

Declarative pipeline of compression steps. Each step references an impl function
directly — the orchestrator calls ``_compress_wrapper`` with the impl function.

This module isolates the impl function imports so that ``__init__.py`` only
exposes the public wrapper functions (used by tests) and the pipeline tuple.
"""

from __future__ import annotations

from agent_context_compress.steps.framework import CompressionStep

# Import impl functions — used ONLY for pipeline registration.
# Tests use the public wrapper functions (compress_*) instead.
from agent_context_compress.steps.prune_images import _compress_prune_images_impl
from agent_context_compress.steps.oversized_tool_redaction import _compress_oversized_tool_redaction_impl
from agent_context_compress.steps.drop_reasoning import _compress_drop_reasoning_impl
from agent_context_compress.steps.last_transaction import _compress_last_transaction_impl
from agent_context_compress.steps.tool_pruning import _compress_tool_pruning_impl
from agent_context_compress.steps.redact_blocks import _compress_redact_blocks_impl
from agent_context_compress.steps.full_reset import _compress_full_reset_impl
from agent_context_compress.steps.conversation_summary import _compress_conversation_summary_impl
from agent_context_compress.steps.blind_truncate import _compress_blind_truncate_impl


__all__ = ["_COMPRESSION_PIPELINE"]


# Pipeline references impl functions directly.  ``_compress_wrapper`` is called
# in the orchestrator loop, forwarding ``step.kwargs`` to each impl.  The public
# wrapper functions (``compress_*``) are kept for backward-compatible testing.

_COMPRESSION_PIPELINE: tuple[CompressionStep, ...] = (
    CompressionStep("PRUNE_IMAGES", _compress_prune_images_impl),
    CompressionStep("OVERSIZED_TOOL_REDACTION", _compress_oversized_tool_redaction_impl),
    CompressionStep("DROP_REASONING", _compress_drop_reasoning_impl),
    CompressionStep("LAST_TRANSACTION", _compress_last_transaction_impl),
    CompressionStep("TOOL_PRUNING", _compress_tool_pruning_impl, kwargs={"use_boundary": True}),
    CompressionStep("REDACT_BLOCKS", _compress_redact_blocks_impl, kwargs={"use_boundary": True}),
    CompressionStep("TOOL_PRUNING_FULL", _compress_tool_pruning_impl, kwargs={"use_boundary": False}),
    CompressionStep("REDACT_BLOCKS_FULL", _compress_redact_blocks_impl, kwargs={"use_boundary": False}),
    CompressionStep("FULL_RESET", _compress_full_reset_impl),
    CompressionStep("CONVERSATION_SUMMARY", _compress_conversation_summary_impl),
    CompressionStep("BLIND_TRUNCATE", _compress_blind_truncate_impl),
)
