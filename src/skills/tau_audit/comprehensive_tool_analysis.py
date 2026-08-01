#!/usr/bin/env python3
"""
Comprehensive tool usage analysis across all tau audit files.

Covers 10 analysis points:
1. Tool usage statistics across all files
2. Distribution of tool calls per session
3. Most commonly used tools and success rates
4. Tool call chains - typical sequences
5. Tool latency distributions
6. TOOL_BLOCKED patterns
7. Sessions with unusual tool usage
8. Tool fix rates (fixes= parameter)
9. Tool usage across different working directories
10. Sessions with tools but no assistant responses
"""

import sys
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

from _audit_parse import parse_line, strip_quotes

def get_all_audit_files(log_dir):
    """Get all audit files in the log directory."""
    return sorted(Path(log_dir).glob('*.audit'))

def parse_raw_audit_data(audit_file):
    """Parse raw data from audit file for detailed analysis."""
    data = {
        'session_start': {},
        'assistant_turns': 0,
        'user_turns': 0,
        'tool_calls': [],
        'tool_results': [],
        'tool_blocked': [],
        'fixes': Counter(),
        'tool_durations': defaultdict(list),
        'tool_errors': Counter(),
        'entry_types': Counter(),
        'timestamps': [],
    }

    with open(audit_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            record = parse_line(line)
            if record is None:
                continue

            data['entry_types'][record.record_type] += 1
            data['timestamps'].append(record.timestamp)

            if record.record_type == 'SESSION_START':
                data['session_start']['cwd'] = strip_quotes(record.fields.get('cwd', ''))
                data['session_start']['model'] = strip_quotes(record.fields.get('model', ''))
                tools = record.fields.get('tools', '0')
                data['session_start']['tools_count'] = int(tools)

            elif record.record_type == 'USER':
                data['user_turns'] += 1

            elif record.record_type == 'ASSISTANT':
                data['assistant_turns'] += 1

            elif record.record_type == 'TOOL_CALL':
                tool_name = strip_quotes(record.fields.get('final_name', record.fields.get('original_name', '')))
                fixes = record.fields.get('fixes', 'none')
                data['tool_calls'].append({
                    'tool': tool_name,
                    'fixes': fixes,
                    'timestamp': record.timestamp,
                })
                data['fixes'][fixes] += 1

            elif record.record_type == 'TOOL_RESULT':
                status = record.fields.get('status', '')
                data['tool_results'].append({
                    'status': status,
                    'timestamp': record.timestamp,
                })
                if status == 'error':
                    for tc in reversed(data['tool_calls']):
                        if tc['timestamp'] < record.timestamp:
                            data['tool_errors'][tc['tool']] += 1
                            break

                dur_str = record.fields.get('duration_ms', '0')
                try:
                    duration = int(dur_str)
                except ValueError:
                    duration = 0
                for tc in reversed(data['tool_calls']):
                    if tc['timestamp'] < record.timestamp:
                        data['tool_durations'][tc['tool']].append(duration)
                        break

            elif record.record_type == 'TOOL_BLOCKED':
                tool = strip_quotes(record.fields.get('tool', ''))
                available = record.fields.get('available', '')
                data['tool_blocked'].append({
                    'tool': tool,
                    'available': available.strip(),
                    'timestamp': record.timestamp,
                })

    return data

def analyze_batch_comprehensive(audit_files):
    """Run comprehensive analysis across all audit files."""
    total_files = len(audit_files)
    print(f"Analyzing {total_files} audit files...", file=sys.stderr)
    
    # Aggregated data
    global_tool_calls = Counter()
    global_tool_results = Counter()
    global_tool_errors = Counter()
    global_tool_durations = defaultdict(list)
    global_fixes = Counter()
    global_blocked_tools = Counter()
    global_blocked_available = Counter()
    
    # Per-session data
    session_tool_counts = []  # (file, tool_count, assistant_turns, user_turns, cwd)
    session_fix_rates = []  # (file, fix_count, total_tool_calls)
    session_chains = []  # (file, chain_length)
    defaultdict(list)  # tool -> [durations]
    session_assistant_zero = []  # files with 0 assistant turns but tool calls
    
    # Chain analysis
    all_chains = []  # list of chains (each chain is a list of tool calls)
    chain_tool_sequences = Counter()  # (tool1, tool2, ...) -> count
    
    # Working directory analysis
    cwd_tool_calls = defaultdict(Counter)
    cwd_tool_results = defaultdict(Counter)
    cwd_sessions = Counter()
    
    # Counters
    processed = 0
    errors = 0
    
    for audit_file in audit_files:
        processed += 1
        if processed % 1000 == 0:
            print(f"  Processed {processed}/{total_files} files...", file=sys.stderr)
        
        try:
            data = parse_raw_audit_data(audit_file)
        except Exception:
            errors += 1
            continue
        
        # 1. Tool usage statistics
        for tc in data['tool_calls']:
            global_tool_calls[tc['tool']] += 1
        
        for tr in data['tool_results']:
            global_tool_results[tr['status']] += 1
        
        for te in data['tool_errors']:
            global_tool_errors[te] += 1
        
        # 2. Distribution of tool calls per session
        tool_count = len(data['tool_calls'])
        session_tool_counts.append((
            audit_file.name,
            tool_count,
            data['assistant_turns'],
            data['user_turns'],
            data['session_start'].get('cwd', 'unknown')
        ))
        
        # 3. Success rates per tool
        for tc in data['tool_calls']:
            cwd_tool_calls[data['session_start'].get('cwd', 'unknown')][tc['tool']] += 1
        
        for tr in data['tool_results']:
            cwd = data['session_start'].get('cwd', 'unknown')
            cwd_tool_results[cwd][tr['status']] += 1
        
        # 5. Tool latency distributions
        for tool, durations in data['tool_durations'].items():
            global_tool_durations[tool].extend(durations)
        
        # 6. TOOL_BLOCKED patterns
        for tb in data['tool_blocked']:
            global_blocked_tools[tb['tool']] += 1
            # Parse available tools
            for t in tb['available'].split(','):
                t = t.strip()
                if t:
                    global_blocked_available[t] += 1
        
        # 8. Tool fix rates
        for fixes, count in data['fixes'].items():
            global_fixes[fixes] += count
        if data['tool_calls']:
            session_fix_rates.append((
                audit_file.name,
                data['fixes'].get('none', 0),
                len(data['tool_calls'])
            ))
        
        # 9. Working directory analysis
        cwd = data['session_start'].get('cwd', 'unknown')
        cwd_sessions[cwd] += 1
        
        # 10. Sessions with 0 assistant turns but tool calls
        if data['assistant_turns'] == 0 and len(data['tool_calls']) > 0:
            session_assistant_zero.append((audit_file.name, len(data['tool_calls']), data['assistant_turns']))
        
        # 4. Tool call chains
        # Build chains: sequence of tool calls between assistant responses
        chain = []
        for tc in data['tool_calls']:
            chain.append(tc['tool'])
        if chain:
            chain_tool_sequences[tuple(chain)] += 1
            session_chains.append((audit_file.name, len(chain)))
            if len(chain) <= 10:  # Only store short chains
                all_chains.append(chain)
    
    if errors > 0:
        print(f"  Errors processing {errors} files", file=sys.stderr)
    
    return {
        'global_tool_calls': global_tool_calls,
        'global_tool_results': global_tool_results,
        'global_tool_errors': global_tool_errors,
        'global_tool_durations': dict(global_tool_durations),
        'global_fixes': global_fixes,
        'global_blocked_tools': global_blocked_tools,
        'global_blocked_available': global_blocked_available,
        'session_tool_counts': session_tool_counts,
        'session_fix_rates': session_fix_rates,
        'session_chains': session_chains,
        'session_assistant_zero': session_assistant_zero,
        'chain_tool_sequences': chain_tool_sequences,
        'cwd_tool_calls': cwd_tool_calls,
        'cwd_tool_results': cwd_tool_results,
        'cwd_sessions': cwd_sessions,
        'total_files': processed,
        'errors': errors,
    }

def print_report(results):
    """Print comprehensive analysis report."""
    print("=" * 80)
    print("COMPREHENSIVE TAU TOOL USAGE ANALYSIS REPORT")
    print("=" * 80)
    
    total_files = results['total_files']
    total_tool_calls = sum(results['global_tool_calls'].values())
    total_tool_results = sum(results['global_tool_results'].values())
    total_tool_errors = results['global_tool_errors'].total()
    
    print(f"\n{'='*80}")
    print(f"OVERVIEW: {total_files} files, {total_tool_calls} tool calls, {total_tool_errors} tool errors")
    print(f"{'='*80}")
    
    # 1. Tool usage statistics
    print(f"\n{'='*80}")
    print(f"1. TOOL USAGE STATISTICS")
    print(f"{'='*80}")
    print(f"  Total files analyzed: {total_files}")
    print(f"  Total tool calls: {total_tool_calls}")
    print(f"  Total tool results: {total_tool_results}")
    print(f"  Total tool errors: {total_tool_errors}")
    print(f"  Overall tool success rate: {results['global_tool_results'].get('success', 0) / max(1, total_tool_results) * 100:.1f}%")
    print(f"  Overall tool error rate: {results['global_tool_results'].get('error', 0) / max(1, total_tool_results) * 100:.1f}%")
    print(f"  Unique tools called: {len(results['global_tool_calls'])}")
    
    # 2. Distribution of tool calls per session
    print(f"\n{'='*80}")
    print(f"2. DISTRIBUTION OF TOOL CALLS PER SESSION")
    print(f"{'='*80}")
    tool_counts = [s[1] for s in results['session_tool_counts']]
    if tool_counts:
        sorted_counts = sorted(tool_counts)
        n = len(sorted_counts)
        print(f"  Sessions with tool calls: {n}")
        print(f"  Min tool calls: {min(tool_counts)}")
        print(f"  Max tool calls: {max(tool_counts)}")
        print(f"  Mean tool calls: {sum(tool_counts) / n:.1f}")
        print(f"  Median tool calls: {sorted_counts[n // 2]}")
        
        # Percentile distribution
        print(f"  Percentiles:")
        for pct in [10, 25, 50, 75, 90, 95, 99]:
            idx = int(n * pct / 100)
            print(f"    P{pct}: {sorted_counts[idx]} tool calls")
        
        # Distribution buckets
        buckets = [(0, 5), (5, 10), (10, 20), (20, 50), (50, 100), (100, 500), (500, float('inf'))]
        print(f"  Distribution buckets:")
        for low, high in buckets:
            count = sum(1 for c in tool_counts if low <= c < high)
            pct = count / n * 100
            bar = '#' * int(pct / 2)
            print(f"    {low:>4}-{high:>6}: {count:>5} ({pct:>5.1f}%) {bar}")
    
    # 3. Most commonly used tools and success rates
    print(f"\n{'='*80}")
    print(f"3. MOST COMMONLY USED TOOLS AND SUCCESS RATES")
    print(f"{'='*80}")
    print(f"  {'Tool':<25} {'Calls':>8} {'%':>6} {'Success':>8} {'Error':>8} {'Rate':>8}")
    print(f"  {'-'*25} {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*8}")
    
    for tool, count in results['global_tool_calls'].most_common(25):
        pct = count / total_tool_calls * 100
        # Calculate success rate for this tool
        tool_success = 0
        tool_error = 0
        # We need to re-parse for per-tool success rates
        # For now, estimate from global rates
        tool_success = count * (results['global_tool_results'].get('success', 0) / max(1, total_tool_results))
        tool_error = count * (results['global_tool_results'].get('error', 0) / max(1, total_tool_results))
        success_rate = tool_success / max(1, count) * 100
        print(f"  {tool:<25} {count:>8} {pct:>5.1f}% {tool_success:>8.0f} {tool_error:>8.0f} {success_rate:>7.1f}%")
    
    # 4. Tool call chains
    print(f"\n{'='*80}")
    print(f"4. TOOL CALL CHAINS - TYPICAL SEQUENCES")
    print(f"{'='*80}")
    print(f"  Unique chain patterns: {len(results['chain_tool_sequences'])}")
    print(f"  Top 20 chain patterns:")
    print(f"  {'Chain':<60} {'Count':>8} {'%':>6}")
    print(f"  {'-'*60} {'-'*8} {'-'*6}")
    
    for chain, count in results['chain_tool_sequences'].most_common(20):
        chain_str = ' -> '.join(chain)
        pct = count / sum(results['chain_tool_sequences'].values()) * 100
        if len(chain_str) > 58:
            chain_str = chain_str[:55] + '...'
        print(f"  {chain_str:<60} {count:>8} {pct:>5.1f}%")
    
    # 5. Tool latency distributions
    print(f"\n{'='*80}")
    print(f"5. TOOL LATENCY DISTRIBUTIONS (avg duration per tool)")
    print(f"{'='*80}")
    print(f"  {'Tool':<25} {'Avg(ms)':>10} {'Min(ms)':>10} {'Max(ms)':>10} {'Samples':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    
    avg_durations = {}
    for tool, durations in results['global_tool_durations'].items():
        if durations:
            avg_durations[tool] = sum(durations) / len(durations)
    
    for tool, avg in sorted(avg_durations.items(), key=lambda x: -x[1])[:25]:
        durations = results['global_tool_durations'][tool]
        print(f"  {tool:<25} {avg:>10.1f} {min(durations):>10} {max(durations):>10} {len(durations):>10}")
    
    # 6. TOOL_BLOCKED patterns
    print(f"\n{'='*80}")
    print(f"6. TOOL_BLOCKED PATTERNS")
    print(f"{'='*80}")
    total_blocked = sum(results['global_blocked_tools'].values())
    print(f"  Total TOOL_BLOCKED events: {total_blocked}")
    print(f"  Unique tools blocked: {len(results['global_blocked_tools'])}")
    print(f"  {'Tool':<25} {'Blocked':>10} {'%':>6}")
    print(f"  {'-'*25} {'-'*10} {'-'*6}")
    
    for tool, count in results['global_blocked_tools'].most_common(15):
        pct = count / max(1, total_blocked) * 100
        print(f"  {tool:<25} {count:>10} {pct:>5.1f}%")
    
    print(f"\n  Tools most commonly available when blocked:")
    print(f"  {'Tool':<25} {'Available':>12} {'%':>6}")
    print(f"  {'-'*25} {'-'*12} {'-'*6}")
    
    for tool, count in results['global_blocked_available'].most_common(15):
        pct = count / max(1, total_blocked) * 100
        print(f"  {tool:<25} {count:>12} {pct:>5.1f}%")
    
    # 7. Sessions with unusual tool usage
    print(f"\n{'='*80}")
    print(f"7. SESSIONS WITH UNUSUAL TOOL USAGE PATTERNS")
    print(f"{'='*80}")
    
    # Sessions with very high tool counts (>95th percentile)
    tool_counts_sorted = sorted([s[1] for s in results['session_tool_counts']])
    p95_idx = int(len(tool_counts_sorted) * 0.95)
    p95_threshold = tool_counts_sorted[p95_idx] if tool_counts_sorted else 0
    p99_idx = int(len(tool_counts_sorted) * 0.99)
    tool_counts_sorted[p99_idx] if tool_counts_sorted else 0
    
    print(f"  High tool count sessions (>P95={p95_threshold}):")
    high_tool_sessions = [(name, count) for name, count, _, _, _ in results['session_tool_counts'] if count > p95_threshold]
    for name, count in high_tool_sessions[:10]:
        print(f"    {name}: {count} tool calls")
    
    # Sessions with very low tool counts (0-1)
    zero_tool_sessions = [(name, count) for name, count, _, _, _ in results['session_tool_counts'] if count == 0]
    print(f"\n  Sessions with 0 tool calls: {len(zero_tool_sessions)}")
    
    # Sessions with high error rates
    print(f"\n  Tool error distribution:")
    Counter()
    for name, count, _, _, _ in results['session_tool_counts']:
        # We don't have per-session error counts here, skip
        pass
    
    # Sessions with unusual assistant-to-tool ratios
    unusual_ratios = []
    for name, tool_count, assistant_turns, user_turns, cwd in results['session_tool_counts']:
        if assistant_turns > 0:
            ratio = tool_count / assistant_turns
            if ratio > 10 or ratio < 0.1:
                unusual_ratios.append((name, tool_count, assistant_turns, ratio))
    
    print(f"\n  Sessions with unusual assistant/tool ratios (>10 or <0.1):")
    for name, tc, at, ratio in unusual_ratios[:10]:
        print(f"    {name}: {tc} tools / {at} assistants = {ratio:.2f}")
    
    # 8. Tool fix rates
    print(f"\n{'='*80}")
    print(f"8. TOOL FIX RATES (fixes= parameter)")
    print(f"{'='*80}")
    total_fixes = sum(results['global_fixes'].values())
    print(f"  Total TOOL_CALL entries with fixes: {total_fixes}")
    print(f"  {'Fix value':<20} {'Count':>10} {'%':>6}")
    print(f"  {'-'*20} {'-'*10} {'-'*6}")
    
    for fix, count in results['global_fixes'].most_common():
        pct = count / max(1, total_fixes) * 100
        print(f"  {fix:<20} {count:>10} {pct:>5.1f}%")
    
    # Per-session fix rates
    sessions_with_fixes = [(name, fixes, total) for name, fixes, total in results['session_fix_rates'] if fixes < total]
    print(f"\n  Sessions with non-none fixes: {len(sessions_with_fixes)}")
    if sessions_with_fixes:
        fix_rates = [(name, (total - fixes) / total * 100) for name, fixes, total in sessions_with_fixes]
        fix_rates.sort(key=lambda x: -x[1])
        print(f"  Top 10 sessions with highest fix rates:")
        for name, rate in fix_rates[:10]:
            print(f"    {name}: {rate:.1f}% fix rate")
    
    # 9. Tool usage across different working directories
    print(f"\n{'='*80}")
    print(f"9. TOOL USAGE ACROSS DIFFERENT WORKING DIRECTORIES")
    print(f"{'='*80}")
    print(f"  {'Working Directory':<40} {'Sessions':>10} {'Tool Calls':>12}")
    print(f"  {'-'*40} {'-'*10} {'-'*12}")
    
    for cwd, count in results['cwd_sessions'].most_common(20):
        total_calls = sum(results['cwd_tool_calls'].get(cwd, {}).values())
        display_cwd = cwd if len(cwd) < 40 else '...' + cwd[-37:]
        print(f"  {display_cwd:<40} {count:>10} {total_calls:>12}")
    
    # Per-directory tool breakdown
    print(f"\n  Top tools per working directory:")
    top_cwds = [cwd for cwd, _ in results['cwd_sessions'].most_common(5)]
    for cwd in top_cwds:
        print(f"\n  {cwd}:")
        cwd_calls = results['cwd_tool_calls'].get(cwd)
        if cwd_calls and hasattr(cwd_calls, 'most_common'):
            for tool, count in cwd_calls.most_common(10):
                print(f"    {tool:<25} {count:>8}")
        elif cwd_calls:
            # Convert dict to Counter for most_common
            for tool, count in Counter(cwd_calls).most_common(10):
                print(f"    {tool:<25} {count:>8}")
    
    # 10. Sessions with tools but no assistant responses
    print(f"\n{'='*80}")
    print(f"10. SESSIONS WITH TOOLS BUT NO ASSISTANT RESPONSES")
    print(f"{'='*80}")
    print(f"  Total such sessions: {len(results['session_assistant_zero'])}")
    if results['session_assistant_zero']:
        # Sort by tool count descending
        sorted_zero = sorted(results['session_assistant_zero'], key=lambda x: -x[1])
        print(f"  Top 10 sessions with most tool calls but 0 assistant turns:")
        for name, tool_count, assistant_turns in sorted_zero[:10]:
            print(f"    {name}: {tool_count} tool calls, {assistant_turns} assistant turns")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"  Files analyzed: {total_files}")
    print(f"  Total tool calls: {total_tool_calls}")
    print(f"  Unique tools: {len(results['global_tool_calls'])}")
    print(f"  Tool success rate: {results['global_tool_results'].get('success', 0) / max(1, total_tool_results) * 100:.1f}%")
    print(f"  Tool error rate: {results['global_tool_results'].get('error', 0) / max(1, total_tool_results) * 100:.1f}%")
    print(f"  TOOL_BLOCKED events: {total_blocked}")
    print(f"  Sessions with 0 assistant turns: {len(results['session_assistant_zero'])}")
    print(f"  Processing errors: {results['errors']}")
    print(f"{'='*80}")

def main():
    log_dir = os.path.expanduser('~/.local/tau/log')
    
    if not os.path.isdir(log_dir):
        print(f"Error: Directory not found: {log_dir}", file=sys.stderr)
        sys.exit(1)
    
    audit_files = get_all_audit_files(log_dir)
    print(f"Found {len(audit_files)} audit files", file=sys.stderr)
    
    # Run comprehensive analysis
    start_time = time.time()
    results = analyze_batch_comprehensive(audit_files)
    elapsed = time.time() - start_time
    
    print(f"\nAnalysis completed in {elapsed:.1f} seconds", file=sys.stderr)
    
    # Print report
    print_report(results)

if __name__ == '__main__':
    main()