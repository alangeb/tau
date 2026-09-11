"""Agent loop module.

Extracted from agent_core.py to isolate the core LLM tool-calling loop
into its own module. This reduces the coupling of agent_core.py and makes
the loop logic easier to reason about independently.

The run_loop function encapsulates the main agent interaction loop:
call LLM, execute tool calls, repeat until final response.

EOT (End-of-Turn) protocol is documented in designs/EOT.md.
"""
from __future__ import annotations

import json
import traceback

from agent_console import (
    assistant_message_display,
    context_validation_display,
    error,
    print_context_status,
    reasoning,
    warning,
)
from agent_eot_protection import (
    _ACCIDENTAL_EOT_BUDGET,
    _looks_like_malformed_tool_call,
    ACCIDENTAL_EOT,
)
from agent_lifecycle import AgentLifecycle
from agent_llm_invoke import _invoke_llm_with_retry
from agent_llm_models import DEFAULT_MAX_OUTPUT_TOKENS, LLMCallConfig
from agent_tool_executor import execute_tool_batch, _emit_a2a_chunk


# --- Helpers ---


def _parse_end_turn_args(raw_args) -> dict:
    """Parse end_turn tool call arguments into a dict.

    Handles both string (JSON) and dict inputs, returning empty dict on failure.
    """
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args) if raw_args.strip() else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return raw_args if isinstance(raw_args, dict) else {}


def _resolve_end_turn_message(end_turn_args: dict, agent, held: dict | None) -> str:
    """Resolve the final message text from end_turn args and fallback sources.

    Priority: end_turn message > held text > last substantive response > default.

    The end_turn message is rejected if it is essentially just the ENDOFTURN
    sentinel (short message containing the sentinel). This prevents the LLM
    from overwriting a held substantive response during EOT confirmation by
    calling end_turn(message="ENDOFTURN").
    """
    message = end_turn_args.get("message", "").strip()
    if message and len(message) >= 2:
        # Reject messages that are essentially just the ENDOFTURN sentinel.
        # Allow up to 4 arbitrary extra characters (2 before + 2 after).
        if not (
            len(message) <= len(ACCIDENTAL_EOT) + 4
            and ACCIDENTAL_EOT.upper() in message.upper()
        ):
            return message
    if held and held.get("text"):
        return held["text"]
    if agent.last_substantive_response:
        return agent.last_substantive_response
    return "[end_turn — no message]"


def _post_tool_call_checks(agent):
    """Run shared post-tool-call checks: reflection, force end, interrupt, escalation.

    Returns:
        ``True`` — loop should ``continue``
        ``None`` — loop should ``break`` (interrupted)
        ``str`` — loop should ``return`` with this value (force_end_turn)
        ``False`` — loop should ``continue`` (normal)
    """
    # Post-batch image injection
    agent._inject_queued_images()

    # Count this as a tool-loop step
    agent.reflection_scheduler.tick()

    info = agent.loop_detector.get_escalation_info()
    # Signal distress so scheduler narrows interval
    if info["escalation_level"] >= 1 or agent._session.has_error_burst():
        agent.reflection_scheduler.on_distress()

    # Check reflection — periodic OR reactive
    if agent.reflection_scheduler.should_reflect():
        agent.reflection_scheduler.mark_reflection_started()
        agent._loop_escalation.inject_reflection()
        return True
    if agent.reflection_scheduler.should_reflect_reactive(
        has_loop_warning=info["escalation_level"] >= 1,
        has_error_burst=agent._session.has_error_burst(),
    ):
        agent.reflection_scheduler.mark_reflection_started()
        agent._loop_escalation.inject_reflection()
        return True

    # Check for forced end-of-turn (set by any tool)
    if agent.force_end_turn is not None:
        agent.context.close_turn(agent.force_end_turn)
        return agent.force_end_turn

    # Check for interrupt after tool execution
    if AgentLifecycle.is_interrupted():
        agent.context.close_turn("[Interrupted]")
        return None  # break

    errors = agent.context.validate_tool_resolution()
    if errors:
        for err in errors:
            warning(f"Tool resolution warning: {err}")

    # Check for loop escalation after tool batch
    if not agent._loop_escalation.handle_loop_escalation():
        if agent.force_end_turn is not None:
            agent.context.close_turn(agent.force_end_turn)
            return agent.force_end_turn

    return False


def run_loop(agent: 'TauErgon') -> str:
    """Core loop: call LLM, execute tool calls, repeat until final response.

    CRITICAL OPENAI COMPLIANCE REQUIREMENT:
    The context MUST already end with a user message when this method is called.
    This method does NOT append any messages before the LLM call.

    Message alternation invariant maintained throughout:
      - After LLM returns tool_calls: assistant(tool_calls) -> tool results -> loop
      - After LLM returns plain text: potential EOT -> confirmation -> accept or rewind
      - After forced end-of-turn: assistant(force_end_turn) -> turn complete

    EOT FLOW (see designs/EOT.md for full contract):
      1. LLM returns plain text without tool calls
      2. Check for self-confirming ENDOFTURN sentinel → turn ends immediately
      3. Check for slash commands → dispatch, stay in turn
      4. Check for restricted nesting (T/K) → accept, turn ends
      5. Check budget → if exhausted, force close turn
      6. Enter confirmation round: inject synthetic user message
      7. LLM replies: sentinel → accept; tool calls → rewind; text → stack
      8. end_turn tool call (sole) → resolve message, close turn

    This method is safe to call when the context ends with:
      - A user message (normal entry point)
      - A tool message (after tool execution, looping back to LLM)

    Do NOT call this if the context ends with an assistant message, as that
    would indicate an incomplete turn that should be closed first.

    Args:
        agent: The TauErgon agent instance to run the loop on.

    Returns:
        The final assistant response text (or error message).
    """
    agent.loop_detector.reset()
    agent.force_end_turn: str | None = None
    agent.last_substantive_response: str | None = None
    agent._eot_protection.reset()

    # Early entry reflection (microplan) before first LLM call
    if (
        agent.reflection_scheduler.cfg.enabled
        and agent.reflection_scheduler.cfg.initial_think
    ):
        agent._loop_escalation.inject_early_reflection()

    while True:
        if AgentLifecycle.is_exit_requested():
            agent.context.close_turn("[Session ended]")
            break

        if AgentLifecycle.is_interrupted():
            agent.context.close_turn("[Interrupted]")
            break

        # Check for parent control commands at turn boundary
        agent._process_control_queue()

        # Re-check lifecycle after control queue (forceful terminate may have set exit)
        if AgentLifecycle.is_exit_requested():
            agent.context.close_turn("[Session ended]")
            break

        all_tools = agent.get_all_tools()

        errors = agent.context.validate()
        if errors:
            last = agent.context[-1] if agent.context else None
            last_role = last.get("role", "empty") if last else "empty"
            context_validation_display(errors, context_len=len(agent.context),
                                       last_role=last_role)

            # ── Pre-LLM compression: escalate threshold based on loop warnings ──
            # Compress BEFORE the LLM call when escalation is detected.
            # This prevents the LLM from ever operating on bloated context,
            # which is the root cause of many loops. At higher escalation levels,
            # we compress more aggressively to break the loop — KV cache loss
            # is acceptable when breaking a stuck loop is the priority.
            if agent.loop_detector.escalation_level >= 1:
                # Dynamic threshold: 85% normal, 65% at level 1, 35% at level 2+
                if agent.loop_detector.escalation_level >= 2:
                    compress_threshold = 0.35
                else:
                    compress_threshold = 0.65
                # Check if context is above threshold before LLM call
                if agent._session.last_exact_context_tokens is not None and agent._session.last_exact_context_tokens > 0:
                    current_tokens = agent._session.last_exact_context_tokens
                else:
                    current_tokens = agent.context.estimate_tokens()
                if current_tokens / agent.max_context_tokens >= compress_threshold:
                    warning(
                        f"[Pre-LLM compression] Context at {current_tokens/agent.max_context_tokens:.0%} "
                        f"of max (threshold={compress_threshold:.0%}, "
                        f"escalation_level={agent.loop_detector.escalation_level}) — compressing"
                    )
                    agent.context.compress(0.30, agent, agent.get_all_tools())

        try:
            extra_kwargs = agent.resolve_group_params()

            config = LLMCallConfig(
                log_on_failure=True,
                log_file=agent._session.audit_file,
                context=agent.context,
                extra_kwargs=extra_kwargs,
                compress_client=agent.client,
                compress_model=agent.model_name,
                compress_tools=all_tools,
                compress_extra_kwargs=extra_kwargs,
                compress_audit_writer=agent._session.audit_writer,
                agent=agent,
                max_context_tokens=agent.max_context_tokens,
                max_output_tokens=agent.max_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
            )
            # Defensive: client should never be None after __init__ or _rebuild_client.
            # If we get here, something went wrong with initialization (e.g., SimpleOpenAIClient
            # constructor failed silently or self.client was set to None by external code).
            if agent.client is None:
                error(
                    "LLM client is None — cannot invoke LLM. "
                    "This indicates a configuration or initialization failure. "
                    "Check LLM group settings and base_url."
                )
                raise ValueError(
                    "agent.client is None. LLM group '"
                    f"{agent.current_group_name}' may have invalid configuration."
                )

            resp, compressed = _invoke_llm_with_retry(
                agent.client,
                agent.model_name,
                agent.context,
                all_tools,
                "auto",
                stream=False,
                config=config,
                valid_tool_names=set(agent.available_tool_names),
            )
            # LLM call succeeded — clear vision recovery tracking.
            # Images are now safely in context; no recovery needed.
            agent._last_injected_tool_call_ids.clear()

            response_text = resp.text
            reasoning_content = resp.reasoning
            call_stats = resp.stats

            # Record content quality for adaptive interval
            agent.reflection_scheduler.record_llm_response(
                assistant_bytes=len(response_text or ""),
                reasoning_bytes=len(reasoning_content or ""),
            )

            # Persist compressed context back to agent context.
            if compressed is not None:
                agent.context.set_messages(compressed)

            # Transform resp.tool_calls (SDK + postparse-recovered) into executor format.
            tool_calls = []
            for tc in resp.tool_calls:
                args_str = tc["function"]["arguments"] or ""
                try:
                    args_dict = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    args_dict = {}
                tool_calls.append(
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "args": args_str,
                        "args_dict": args_dict,
                    }
                )

            # Token fields may be None when the API does not report usage.
            # Use ``or 0`` for arithmetic; store raw (possibly None) for display.
            agent._session.record_call_stats(call_stats)

            print_context_status(agent.get_status())

            if reasoning_content:
                reasoning(reasoning_content.strip())
            if response_text:
                assistant_message_display(response_text.strip())
                # Emit A2A chunk for assistant text
                if response_text.strip():
                    _emit_a2a_chunk(agent, "assistant", {"content": response_text.strip()})

            # Compression check: use API tokens when available, fall back to
            # estimation (including pending message) when not.  This MUST happen
            # BEFORE appending the assistant message, so we estimate the
            # post-append context size to avoid lagging estimates.
            pending = (
                len(response_text or "") + len(reasoning_content or "")
            ) // 3 + 15
            if (
                agent._session.last_exact_context_tokens is not None
                and agent._session.last_exact_context_tokens > 0
            ):
                total_tokens = agent._session.last_exact_context_tokens + pending
            else:
                total_tokens = agent.context.estimate_tokens(pending)
            compress_threshold = 0.85

            if (
                agent.max_context_tokens > 0
                and total_tokens / agent.max_context_tokens >= compress_threshold
            ):
                agent.context.compress(0.30, agent, agent.get_all_tools())

            # Track substantive response for best-effort fallback.
            # Updated on EVERY valid plain text response (not just the first).
            # This ensures last_substantive_response is the MOST RECENT valid
            # response, allowing the LLM to revise/improve its answer across turns.
            # Strip ENDOFTURN sentinel if present so it doesn't leak into fallbacks.
            if (
                response_text
                and response_text.strip()
                and len(response_text.strip()) >= 3  # Minimum length
                and not _looks_like_malformed_tool_call(response_text)  # Not malformed
                and response_text.strip().upper() != ACCIDENTAL_EOT.upper()  # Not EOT sentinel
            ):
                _, stripped = agent._eot_protection.check_confirmation(
                    response_text.strip()
                )
                agent.last_substantive_response = stripped or response_text.strip()

            if tool_calls:
                # ── end_turn: sole tool call → immediate EOT ──────────────
                # If the ONLY tool call is end_turn, resolve it immediately
                # and close the turn.  end_turn MUST be the only tool call;
                # if mixed with other tools, the others execute and end_turn
                # is silently filtered out.
                if len(tool_calls) == 1 and tool_calls[0]["name"] == "end_turn":
                    # Sole end_turn call — always accept as EOT.
                    if agent._eot_protection.is_in_confirmation:
                        held = agent._eot_protection._eot_confirmation_stack[-1] if agent._eot_protection._eot_confirmation_stack else None
                        # Pop the LLM's assistant response (current turn)
                        msgs = agent.context._messages
                        if msgs and msgs[-1].get("role") == "assistant":
                            msgs.pop()
                        agent._eot_protection.pop_all_confirmations()

                        final_text = _resolve_end_turn_message(
                            _parse_end_turn_args(tool_calls[0].get("args", "")),
                            agent, held,
                        )
                        agent.context.append_assistant(final_text, reasoning=held.get("reasoning") if held else None)
                    else:
                        final_text = _resolve_end_turn_message(
                            _parse_end_turn_args(tool_calls[0].get("args", "")),
                            agent, None,
                        )
                        agent.context.append_assistant(final_text, reasoning=reasoning_content)

                    agent.context.close_turn(final_text)
                    agent._session.audit_writer.assistant(final_text)

                    # Display the final answer after end_turn.
                    # The answer may have been displayed during the LLM call
                    # (if response_text was present), but end_turn can also carry
                    # the answer in its `message` argument, which was NOT displayed.
                    # Displaying here ensures the answer is always visible.
                    if final_text:
                        assistant_message_display(final_text)

                    return final_text

                # ── end_turn mixed with other tools → filter it out ───────
                # end_turn MUST be sole tool call; if mixed, silently skip it.
                original_count = len(tool_calls)
                tool_calls = [tc for tc in tool_calls if tc["name"] != "end_turn"]
                if len(tool_calls) < original_count:
                    warning("end_turn mixed with other tool calls — end_turn silently filtered out (must be sole call)")

                # We have tool calls — check if we're in a confirmation round
                # where we had potential EOT messages held.
                if agent._eot_protection.is_in_confirmation:
                    # LLM returned tool calls during confirmation — rewind!
                    confirmed, stripped_text = agent._eot_protection.check_confirmation(
                        response_text
                    )
                    if confirmed:
                        warning(
                            "LLM returned both confirmation sentinel AND tool calls — "
                            "treating as tool calls (rewind). This should not happen."
                        )
                        agent._session.audit_writer.assistant(
                            "WARNING: LLM returned both confirmation sentinel and tool calls"
                        )
                    if stripped_text is not None:
                        agent._eot_protection.set_latest_text(stripped_text)
                    agent._eot_protection.rewind_with_tools(
                        tool_calls, reasoning_content
                    )

                execute_tool_batch(tool_calls, agent, reasoning=reasoning_content, audit_writer=agent._session.audit_writer)

                result = _post_tool_call_checks(agent)
                if result is True:
                    continue
                if result is None:
                    break  # interrupted
                if isinstance(result, str):
                    return result  # force_end_turn
                continue

            # ── No tool calls: potential end-of-turn ────────────────────────────────────
            # Check force_end_turn before EOT protection (e.g., +stop from user steering)
            if agent.force_end_turn is not None:
                agent.context.close_turn(agent.force_end_turn)
                return agent.force_end_turn

            # Check for slash commands first — dispatch them before EOT logic.
            # If in a confirmation round, pop only synthetic user messages (not
            # the assistant) to keep context ending with assistant, avoiding
            # consecutive user messages when command handler appends user(task).
            if response_text and response_text.strip().startswith("/"):
                cmd_full = response_text.strip()
                cmd_name = cmd_full.split()[0] if cmd_full.strip() else ""
                if cmd_name:
                    if agent._eot_protection.is_in_confirmation:
                        agent._eot_protection.pop_synthetic_only()
                    agent._handle_command(cmd_name, cmd_full)
                    continue

            # Check if we're in a confirmation round (EOT confirmation stack not empty)
            if agent._eot_protection.is_in_confirmation:
                # For T/K nesting types, skip confirmation and accept response directly
                if agent._is_restricted_nesting():
                    confirmed, stripped_text = agent._eot_protection.check_confirmation(
                        response_text
                    )
                    if confirmed and stripped_text is not None:
                        agent._eot_protection.set_latest_text(stripped_text)
                    # Accept with whatever we have
                    return agent._eot_protection.accept_confirmation()
                # We're in a confirmation round — check for sentinel response
                confirmed, stripped_text = agent._eot_protection.check_confirmation(
                    response_text
                )
                if confirmed:
                    # --- Audit: log sentinel response ---
                    sentinel_preview = (response_text or "")[:40].replace("\n", " ")
                    agent._session.audit_writer.eot_confirm_sentinel(
                        sentinel_preview, stripped_text is not None
                    )
                    # Update latest stack entry with stripped text (if any)
                    if stripped_text is not None:
                        agent._eot_protection.set_latest_text(stripped_text)
                    # LLM confirmed EOT with sentinel
                    return agent._eot_protection.accept_confirmation()
                # LLM didn't confirm — stack another confirmation request
                # Don't pop the LLM's response yet — we'll pop it when we pop the stack
                agent._eot_protection.handle_potential_eot(response_text, reasoning_content)
                continue

            # Not in confirmation round:
            # ENDOFTURN at end of a substantial reply IS self-confirming —
            # check for it BEFORE falling through to accidental-EOT protection.
            confirmed, stripped_text = agent._eot_protection.check_confirmation(
                response_text
            )
            if confirmed:
                final_text = stripped_text or agent.last_substantive_response or ""
                sentinel_preview = (response_text or "")[:40].replace("\n", " ")
                agent._session.audit_writer.eot_self_confirmed(
                    sentinel_preview, stripped_text is not None
                )
                agent.context.append_assistant(final_text, reasoning=reasoning_content)
                agent.context.close_turn(final_text)
                agent._session.audit_writer.assistant(final_text)
                if final_text:
                    assistant_message_display(final_text)
                return final_text

            # For T (think) and K (skill) nesting types, accept basic end-of-turn
            # without requiring the ENDOFTURN sentinel confirmation.
            if agent._is_restricted_nesting():
                final_text = response_text or agent.last_substantive_response or ""
                agent.context.append_assistant(final_text, reasoning=reasoning_content)
                agent.context.close_turn(final_text)
                agent._session.audit_writer.assistant(final_text)

                # Display the final answer for restricted nesting (think/skill mode).
                # These modes skip EOT confirmation, so the answer must be displayed here.
                if final_text:
                    assistant_message_display(final_text)

                return final_text

            # Inject accidental EOT protection: ask LLM to confirm or continue.
            if agent._eot_protection.increment_and_check_budget():
                warning(
                    f"[Accidental EOT budget exhausted ({_ACCIDENTAL_EOT_BUDGET} attempts), "
                    f"force-closing turn.]"
                )
                agent.context.close_turn(
                    "[Accidental EOT budget exhausted — turn forced closed]"
                )
                best_response = agent.last_substantive_response or response_text or ""
                agent._session.audit_writer.assistant(best_response)

                # Display the best available response before returning.
                if best_response:
                    assistant_message_display(best_response)

                return best_response

            # Hold the potential EOT message and inject confirmation request
            agent._eot_protection.handle_potential_eot(response_text, reasoning_content)
            continue

        except Exception as e:  # pylint: disable=W0718
            if isinstance(e, (MemoryError, RecursionError)):
                error(f"[FATAL] {type(e).__name__}: {e}")
                raise  # No recovery possible — process state is undefined

            # Clear stale EOT confirmation state on error
            agent._eot_protection.reset()

            traceback.print_exc()

            error_detail = f"{type(e).__name__}: {e}"
            error_lower = error_detail.lower()
            if "timeout" in error_lower or "timed out" in error_lower:
                error_response = (
                    f"Error: Failed to invoke model after retries - {error_detail}"
                )
            else:
                error_response = f"Error: Failed to invoke model - {error_detail}"

            agent._session.audit_writer.assistant(error_response)
            agent.context.append_assistant(error_response, None)
            error(f"[ERROR] {error_response}")
            return error_response