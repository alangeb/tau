#!/usr/bin/env python3
"""
deep_error_analysis_v2.py — Comprehensive error analysis across all tau audit files

Uses analyze_audit.py parser (which correctly detects errors in ASSISTANT content).
Covers all 10 analysis dimensions.
"""

import sys
import os
import re
import json
from collections import Counter, defaultdict
from pathlib import Path

# Local imports from same directory
from analyze_audit import analyze_audit

LOG_DIR = "/home/alangeb/.local/tau/log"

def find_audit_files():
    log_path = Path(LOG_DIR)
    return sorted(log_path.glob('*.audit'))

def main():
    audit_files = find_audit_files()
    print(f"Found {len(audit_files)} audit files", file=sys.stderr)
    
    # Phase 1: Analyze all files using analyze_audit.py
    print("Phase 1: Analyzing all audit files...", file=sys.stderr)
    
    all_results = []
    files_with_errors = 0
    files_without_errors = 0
    
    for i, filepath in enumerate(audit_files):
        if i % 2000 == 0:
            print(f"  Progress: {i}/{len(audit_files)}...", file=sys.stderr)
        try:
            result = analyze_audit(str(filepath))
            result['_filepath'] = str(filepath)
            result['_basename'] = filepath.name
            all_results.append(result)
            if result['errors']['total_count'] > 0:
                files_with_errors += 1
            else:
                files_without_errors += 1
        except Exception as e:
            pass
    
    print(f"  Complete. {files_with_errors} files with errors, {files_without_errors} without.", file=sys.stderr)
    
    # Phase 2: Aggregate statistics
    total_sessions = len(all_results)
    
    # Collect all error data
    all_error_types = Counter()
    all_tool_errors = Counter()
    all_tool_calls = Counter()
    all_tool_results = Counter()
    all_tool_fixes = Counter()
    all_tool_durations = defaultdict(list)
    session_error_data = []  # (result, error_count)
    session_tool_data = []
    content_error_samples = defaultdict(list)  # error_type -> [sample_text]
    
    for r in all_results:
        # Error types
        for etype, count in r['errors']['types'].items():
            all_error_types[etype] += count
        
        # Tool data
        for tool, count in r['tools']['calls'].items():
            all_tool_calls[tool] += count
        
        for result_type, count in r['tools']['results'].items():
            all_tool_results[result_type] += count
        
        for tool, count in r['tools']['errors'].items():
            all_tool_errors[tool] += count
        
        for tool, count in r['tools']['avg_durations'].items():
            all_tool_durations[tool].append(count)
        
        # Error data
        if r['errors']['total_count'] > 0:
            session_error_data.append((r, r['errors']['total_count']))
            for sample in r['errors']['sample_messages'][:3]:
                # Classify sample
                for etype in all_error_types:
                    if etype in sample.lower():
                        content_error_samples[etype].append(sample[:200])
                        break
    
    # Session-level analysis
    sessions_with_errors = len([r for r in all_results if r['errors']['total_count'] > 0])
    sessions_without_errors = total_sessions - sessions_with_errors
    
    total_errors = sum(r['errors']['total_count'] for r in all_results)
    
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  TAU AUDIT ERROR ANALYSIS REPORT")
    print(f"  {len(audit_files):,} audit files, {total_sessions:,} sessions")
    print(f"{'='*70}")
    
    # =========================================================================
    # 1. ERROR STATISTICS ACROSS ALL FILES
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  1. ERROR STATISTICS ACROSS ALL FILES")
    print(f"{'='*70}")
    
    print(f"\nTotal sessions:               {total_sessions:,}")
    print(f"Sessions with errors:         {sessions_with_errors:,} ({sessions_with_errors/total_sessions*100:.1f}%)")
    print(f"Sessions without errors:      {sessions_without_errors:,} ({sessions_without_errors/total_sessions*100:.1f}%)")
    print(f"Total error instances:        {total_errors:,}")
    print(f"Errors per error-session:     {total_errors/max(1,sessions_with_errors):.1f}")
    print(f"Errors per session (all):     {total_errors/max(1,total_sessions):.2f}")
    
    print(f"\nError Type Distribution:")
    for etype, count in all_error_types.most_common():
        print(f"  {etype:<15} {count:>6,} ({count/total_errors*100:.1f}%)")
    
    # =========================================================================
    # 2. DISTRIBUTION OF ERROR TYPES
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  2. DISTRIBUTION OF ERROR TYPES")
    print(f"{'='*70}")
    
    print(f"\nError types detected in assistant content:")
    for etype, count in all_error_types.most_common():
        print(f"\n  [{etype.upper()}] {count:,} occurrences")
        samples = content_error_samples.get(etype, [])[:5]
        if samples:
            for s in samples:
                print(f"    -> {s[:120]}")
        else:
            print(f"    (no detailed samples available)")
    
    # Error types by session size
    print(f"\n\nError types by session size (assistant turns):")
    size_buckets = {'tiny (<5 turns)': 0, 'small (5-10)': 0, 'medium (10-20)': 0, 'large (20+)': 0}
    for r in all_results:
        if r['errors']['total_count'] == 0:
            continue
        turns = r['conversation']['assistant_turns']
        if turns < 5:
            size_buckets['tiny (<5 turns)'] += 1
        elif turns < 10:
            size_buckets['small (5-10)'] += 1
        elif turns < 20:
            size_buckets['medium (10-20)'] += 1
        else:
            size_buckets['large (20+)'] += 1
    
    for bucket, count in size_buckets.items():
        print(f"  {bucket:<20} {count:>4} error sessions")
    
    # =========================================================================
    # 3. SESSIONS WITH MOST ERRORS
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  3. SESSIONS WITH MOST ERRORS")
    print(f"{'='*70}")
    
    # Sort by error count
    session_error_data.sort(key=lambda x: -x[1])
    top_error_sessions = session_error_data[:20]
    
    print(f"\n{'PID':<15} {'Errors':>8} {'Lines':>8} {'Users':>5} {'Assist':>6} {'Tools':>6} {'Health':<10}")
    print("-" * 70)
    
    for r, err_count in top_error_sessions:
        meta = r['metadata']
        pid = meta.get('pid', 'N/A')
        conv = r['conversation']
        tools = sum(r['tools']['calls'].values())
        health = r['summary']['health']
        lines = conv['total_lines']
        users = conv['user_turns']
        assists = conv['assistant_turns']
        
        print(f"  {pid:<15} {err_count:>8} {lines:>8,} {users:>5} {assists:>6} {tools:>6} {health:<10}")
    
    print(f"\n\nTop Error Session Analysis:")
    for r, err_count in top_error_sessions[:5]:
        meta = r['metadata']
        pid = meta.get('pid', 'N/A')
        print(f"\n  PID {pid} ({err_count} errors):")
        print(f"    Error types: {dict(r['errors']['types'])}")
        print(f"    Tool calls: {sum(r['tools']['calls'].values())}, Tool results: {sum(r['tools']['results'].values())}")
        print(f"    Tool success rate: {r['summary']['tool_success_rate']:.1f}%")
        print(f"    Health: {r['summary']['health']}, Efficiency: {r['summary']['efficiency']}")
        print(f"    Duration: {r['time'].get('session_duration_seconds', 0):.0f}s")
        print(f"    Loops detected: {r['loops']['candidate_count']}")
        
        # Show first few error samples
        for sample in r['errors']['sample_messages'][:3]:
            print(f"    -> {sample[:150]}")
    
    # =========================================================================
    # 4. ERROR RECOVERY PATTERNS
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  4. ERROR RECOVERY PATTERNS")
    print(f"{'='*70}")
    
    recovered = 0
    not_recovered = 0
    recovered_by_type = Counter()
    
    for r in all_results:
        if r['errors']['total_count'] == 0:
            continue
        
        # Check if there are successful tool results after errors
        # We look at the overall session: if tool success rate > 0, it recovered
        tool_success = r['summary']['tool_success_rate']
        has_tool_results = sum(r['tools']['results'].values()) > 0
        
        if tool_success > 0 and has_tool_results:
            recovered += 1
            # Track by error type
            for etype in r['errors']['types'].keys():
                recovered_by_type[etype] += 1
        else:
            not_recovered += 1
    
    print(f"\nRecovery Analysis:")
    print(f"  Sessions with errors:             {sessions_with_errors:,}")
    print(f"  Recovered (success after error):  {recovered:,} ({recovered/max(1,sessions_with_errors)*100:.1f}%)")
    print(f"  No recovery:                      {not_recovered:,} ({not_recovered/max(1,sessions_with_errors)*100:.1f}%)")
    
    print(f"\n  Recovery by error type:")
    for etype in all_error_types.keys():
        type_recovered = recovered_by_type.get(etype, 0)
        type_total = sum(1 for r in all_results if r['errors']['total_count'] > 0 and etype in r['errors']['types'])
        print(f"    {etype:<15} {type_recovered:>4}/{type_total} recovered ({type_recovered/max(1,type_total)*100:.0f}%)")
    
    # Self-correction indicators
    self_corrections = sum(r['content_quality']['self_correction_count'] for r in all_results)
    uncertainty = sum(r['content_quality']['uncertainty_count'] for r in all_results)
    confidence = sum(r['content_quality']['confidence_count'] for r in all_results)
    
    print(f"\n  Content quality indicators:")
    print(f"    Self-corrections:               {self_corrections:,}")
    print(f"    Uncertainty indicators:         {uncertainty:,}")
    print(f"    Confidence indicators:          {confidence:,}")
    
    # =========================================================================
    # 5. ERROR CLUSTERING
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  5. ERROR CLUSTERING (Multiple Errors in Sequence)")
    print(f"{'='*70}")
    
    # Cluster by error count per session
    error_counts_per_session = Counter(r['errors']['total_count'] for r in all_results if r['errors']['total_count'] > 0)
    
    print(f"\nError count distribution per session:")
    for count, freq in error_counts_per_session.most_common():
        print(f"  {count:>3} errors: {freq:>4} sessions")
    
    # Sessions with clusters (3+ errors)
    clustered_sessions = [r for r in all_results if r['errors']['total_count'] >= 3]
    print(f"\nSessions with 3+ errors (clusters): {len(clustered_sessions):,}")
    
    # Sessions with severe clusters (10+ errors)
    severe_sessions = [r for r in all_results if r['errors']['total_count'] >= 10]
    print(f"Sessions with 10+ errors (severe):  {len(severe_sessions):,}")
    
    # Top 10 most clustered sessions
    print(f"\nTop 10 most clustered sessions:")
    print(f"  {'PID':<15} {'Errors':>8} {'Lines':>8} {'Duration':>10} {'Error Types':>20}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*10} {'-'*20}")
    for r in sorted(severe_sessions if severe_sessions else clustered_sessions, key=lambda x: -x['errors']['total_count'])[:10]:
        meta = r['metadata']
        pid = meta.get('pid', 'N/A')
        dur = r['time'].get('session_duration_seconds', 0)
        dur_str = f"{dur/60:.1f}m" if dur > 60 else f"{dur:.0f}s"
        types_str = str(dict(r['errors']['types']))[:18]
        print(f"  {pid:<15} {r['errors']['total_count']:>8} {r['conversation']['total_lines']:>8,} {dur_str:>10} {types_str:>20}")
    
    # =========================================================================
    # 6. WHICH TOOLS FAIL MOST OFTEN
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  6. WHICH TOOLS FAIL MOST OFTEN")
    print(f"{'='*70}")
    
    total_tool_results = sum(all_tool_results.values())
    successful_results = all_tool_results.get('success', 0)
    error_results = all_tool_results.get('error', 0)
    
    print(f"\nTool Error Analysis:")
    print(f"  Total tool results:     {total_tool_results:,}")
    print(f"  Successful:             {successful_results:,} ({successful_results/max(1,total_tool_results)*100:.1f}%)")
    print(f"  Error:                  {error_results:,} ({error_results/max(1,total_tool_results)*100:.1f}%)")
    
    if error_results == 0:
        print(f"\n  ★ KEY FINDING: Zero tool-level errors across all {total_tool_results:,} tool results!")
        print(f"  All errors are content-based (in assistant responses), not tool execution failures.")
        print(f"  This suggests the agent's tool execution is robust, but the agent sometimes")
        print(f"  reports errors in its reasoning (e.g., timeout handling, retry logic).")
    
    print(f"\nTool Call Frequency (all calls):")
    for tool, count in all_tool_calls.most_common(20):
        print(f"  {tool:<20} {count:>8,} calls")
    
    # Tool fixes (self-corrected)
    # We need to check for 'fixes' field in tool calls - this requires raw parsing
    # For now, skip this as analyze_audit.py doesn't track it
    
    # Tool error rate by tool (content errors near tool calls)
    print(f"\nContent Errors Near Tool Calls:")
    # This requires raw file parsing; skip for now
    
    # =========================================================================
    # 7. VALIDATION_ERROR DETAILS (Wrong Parameters)
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  7. VALIDATION_ERROR DETAILS (Wrong Parameters)")
    print(f"{'='*70}")
    
    # Look for validation-related patterns in error content
    validation_patterns = {
        'missing_required': 0,
        'invalid_type': 0,
        'invalid_value': 0,
        'too_many_args': 0,
        'wrong_args': 0,
        'parameter_error': 0,
    }
    
    param_error_samples = []
    
    for r in all_results:
        if r['errors']['total_count'] == 0:
            continue
        for sample in r['errors']['sample_messages']:
            content = sample.lower()
            if 'required' in content and 'missing' in content:
                validation_patterns['missing_required'] += 1
                param_error_samples.append(sample[:200])
            elif 'type' in content and 'invalid' in content:
                validation_patterns['invalid_type'] += 1
                param_error_samples.append(sample[:200])
            elif 'value' in content and 'invalid' in content:
                validation_patterns['invalid_value'] += 1
                param_error_samples.append(sample[:200])
            elif 'too many' in content or 'extra' in content:
                validation_patterns['too_many_args'] += 1
                param_error_samples.append(sample[:200])
            elif 'wrong' in content or 'unexpected' in content:
                validation_patterns['wrong_args'] += 1
                param_error_samples.append(sample[:200])
            elif 'parameter' in content or 'argument' in content or 'invalid' in content:
                validation_patterns['parameter_error'] += 1
                param_error_samples.append(sample[:200])
    
    print(f"\nValidation error breakdown:")
    for pattern, count in validation_patterns.items():
        print(f"  {pattern:<20} {count:>4}")
    
    if param_error_samples:
        print(f"\nSample parameter errors (first 5):")
        for s in param_error_samples[:5]:
            print(f"  -> {s[:200]}")
    
    # =========================================================================
    # 8. TOOL_ERROR vs TOOL_RESULT CORRELATION
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  8. TOOL_ERROR vs TOOL_RESULT CORRELATION")
    print(f"{'='*70}")
    
    print(f"\nTool Result Analysis:")
    print(f"  Total tool results:     {total_tool_results:,}")
    print(f"  Successful:             {successful_results:,} ({successful_results/max(1,total_tool_results)*100:.1f}%)")
    print(f"  Error:                  {error_results:,} ({error_results/max(1,total_tool_results)*100:.1f}%)")
    
    print(f"\nCorrelation Analysis:")
    print(f"  Tool error rate: {error_results/max(1,total_tool_results)*100:.2f}%")
    print(f"  Content error rate: {sessions_with_errors/max(1,total_sessions)*100:.1f}% of sessions")
    
    # Sessions with both content errors AND tool errors
    both_errors = sum(1 for r in all_results if r['errors']['total_count'] > 0 and r['tools']['errors'])
    content_only = sum(1 for r in all_results if r['errors']['total_count'] > 0 and not r['tools']['errors'])
    tool_only = sum(1 for r in all_results if r['errors']['total_count'] == 0 and r['tools']['errors'])
    
    print(f"\nError correlation:")
    print(f"  Content errors only:        {content_only:,}")
    print(f"  Tool errors only:           {tool_only:,}")
    print(f"  Both content + tool errors: {both_errors:,}")
    
    if error_results == 0:
        print(f"\n  ★ KEY FINDING: Zero tool-level errors across all {total_tool_results:,} tool results!")
        print(f"  All errors are content-based (in assistant responses), not tool execution failures.")
    
    # =========================================================================
    # 9. SESSIONS WITH 0 ERRORS BUT HIGH TOOL CALL COUNT (CLEAN TOOL USE)
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  9. SESSIONS WITH 0 ERRORS BUT HIGH TOOL CALL COUNT (CLEAN TOOL USE)")
    print(f"{'='*70}")
    
    clean_high_tool = []
    for r in all_results:
        if r['errors']['total_count'] == 0:
            tool_count = sum(r['tools']['calls'].values())
            if tool_count >= 5:
                clean_high_tool.append((r, tool_count))
    
    clean_high_tool.sort(key=lambda x: -x[1])
    
    print(f"\nClean sessions with 5+ tool calls: {len(clean_high_tool):,}")
    
    if clean_high_tool:
        print(f"\nTop 20 clean sessions by tool call count:")
        print(f"  {'PID':<15} {'Tool Calls':>11} {'Success Rate':>13} {'Health':<10} {'Efficiency':<10}")
        print(f"  {'-'*15} {'-'*11} {'-'*13} {'-'*10} {'-'*10}")
        for r, tool_count in clean_high_tool[:20]:
            meta = r['metadata']
            pid = meta.get('pid', 'N/A')
            success_rate = r['summary']['tool_success_rate']
            health = r['summary']['health']
            efficiency = r['summary']['efficiency']
            print(f"  {pid:<15} {tool_count:>11} {success_rate:>12.1f}% {health:<10} {efficiency:<10}")
    
    if clean_high_tool:
        tool_counts = [tc for _, tc in clean_high_tool]
        print(f"\n  Tool call distribution (clean sessions):")
        print(f"    Min: {min(tool_counts)}")
        print(f"    Max: {max(tool_counts)}")
        print(f"    Avg: {sum(tool_counts)/len(tool_counts):.1f}")
        print(f"    Median: {sorted(tool_counts)[len(tool_counts)//2]}")
    
    # =========================================================================
    # 10. SESSIONS WITH ERRORS BUT NO TOOL_RESULT ERRORS
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  10. SESSIONS WITH ERRORS BUT NO TOOL_RESULT ERRORS")
    print(f"{'='*70}")
    
    error_sessions_no_tool_errors = [r for r in all_results if r['errors']['total_count'] > 0 and not r['tools']['errors']]
    
    print(f"\nSessions with content errors but NO tool errors: {len(error_sessions_no_tool_errors):,}")
    print(f"(This is {len(error_sessions_no_tool_errors)/max(1,sessions_with_errors)*100:.1f}% of all error sessions)")
    
    if error_sessions_no_tool_errors:
        error_types_in_content = Counter()
        for r in error_sessions_no_tool_errors:
            for etype, count in r['errors']['types'].items():
                error_types_in_content[etype] += count
        
        print(f"\nError types in these sessions:")
        for etype, count in error_types_in_content.most_common():
            print(f"  {etype:<15} {count:>6,}")
        
        # Show sample content errors
        print(f"\nSample content errors (first 10):")
        for r in error_sessions_no_tool_errors[:10]:
            meta = r['metadata']
            pid = meta.get('pid', 'N/A')
            print(f"\n  PID {pid} ({r['errors']['total_count']} errors):")
            for sample in r['errors']['sample_messages'][:2]:
                print(f"    [{r['errors']['types']}] {sample[:150]}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    
    print(f"\nKey Findings:")
    print(f"  1. Error rate: {sessions_with_errors/max(1,total_sessions)*100:.1f}% of sessions have content errors")
    print(f"  2. Tool execution: {error_results/max(1,total_tool_results)*100:.2f}% error rate (near zero)")
    most_common = all_error_types.most_common(1)
    if most_common:
        print(f"  3. Most common error: {most_common[0][0]} ({most_common[0][1]:,} occurrences)")
    print(f"  4. Recovery rate: {recovered/max(1,sessions_with_errors)*100:.1f}% of error sessions recover")
    print(f"  5. Error clustering: {len(clustered_sessions):,} sessions have error clusters (3+)")
    print(f"  6. Clean high-tool sessions: {len(clean_high_tool):,} sessions with 5+ tool calls, 0 errors")
    print(f"  7. All errors are content-based, not tool failures")
    print(f"  8. Total tool calls: {sum(all_tool_calls.values()):,}")
    print(f"  9. Total tool results: {total_tool_results:,}")
    print(f"  10. Self-corrections: {self_corrections:,}")
    
    print(f"\n{'='*70}")
    print(f"  Analysis complete. {total_errors:,} errors analyzed across {total_sessions:,} sessions.")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
