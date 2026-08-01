#!/usr/bin/env python3
"""
Deep fork/subagent analysis across 10,000+ tau audit files.
Extracts: fork/subagent statistics, patterns, distributions, nesting, effectiveness.
"""

import sys
import re
import os
import json
from collections import Counter
from pathlib import Path

from _audit_parse import parse_line, strip_quotes


def analyze_single_audit(filepath):
    """Analyze a single audit file for fork/subagent data."""
    result = {
        'filepath': str(filepath),
        'basename': os.path.basename(filepath),
    }

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        result['error'] = 'read_failed'
        return result

    # Counters
    entry_types = Counter()
    fork_calls_content = 0
    subagent_calls_content = 0
    fork_tasks = []
    subagent_tasks = []

    for line in lines:
        record = parse_line(line)
        if record is not None:
            entry_types[record.record_type] += 1

            if record.record_type in ('FORK_START', 'SUBAGENT_START'):
                task = strip_quotes(record.fields.get('task', ''))
                if task and len(task) < 200:
                    if record.record_type == 'FORK_START':
                        fork_tasks.append(task)
                    else:
                        subagent_tasks.append(task)

    # Count from content patterns (separate pass for accuracy)
    fork_calls_content = 0
    subagent_calls_content = 0
    for line in lines:
        if line.startswith('  | '):
            fc, sc = _count_calls_in_text(line[4:])
            fork_calls_content += fc
            subagent_calls_content += sc

    # Compute max nesting from entry types
    max_nesting = 0
    for line in lines:
        record = parse_line(line)
        if record is not None:
            if record.record_type in ('FORK_START', 'SUBAGENT_START'):
                max_nesting = max(max_nesting, record.nesting)

    # Detect ghost sessions
    session_start_count = entry_types.get('SESSION_START', 0)
    fork_start_count = entry_types.get('FORK_START', 0)
    subagent_start_count = entry_types.get('SUBAGENT_START', 0)
    ghost_session = session_start_count > 5 and (fork_start_count + subagent_start_count) == 0

    result.update({
        'entry_types': dict(entry_types),
        'fork_calls_content': fork_calls_content,
        'subagent_calls_content': subagent_calls_content,
        'fork_tasks_sample': fork_tasks[:20],
        'subagent_tasks_sample': subagent_tasks[:20],
        'fork_start_entries': fork_start_count,
        'subagent_start_entries': subagent_start_count,
        'fork_end_entries': entry_types.get('FORK_END', 0),
        'subagent_end_entries': entry_types.get('SUBAGENT_END', 0),
        'max_nesting': max_nesting,
        'has_nesting_markers': max_nesting > 0,
        'ghost_session': ghost_session,
        'session_starts': session_start_count,
        'tool_call_count': entry_types.get('TOOL_CALL', 0),
        'tool_result_count': entry_types.get('TOOL_RESULT', 0),
        'total_lines': len(lines),
    })

    return result


def _count_calls_in_text(text: str) -> tuple[int, int]:
    """Count fork() and subagent() calls in a text block."""
    fork_count = len(re.findall(r'fork\(\s*task\s*=\s*["\']', text))
    subagent_count = len(re.findall(r'subagent\(\s*task\s*=\s*["\']', text))
    return fork_count, subagent_count


def categorize_task(task):
    """Categorize a fork/subagent task by type."""
    task_lower = task.lower()
    
    if any(w in task_lower for w in ['analyze', 'analysis', 'inspect', 'review', 'examine', 'look at', 'check']):
        return 'analysis'
    elif any(w in task_lower for w in ['code', 'implement', 'write', 'create', 'build', 'develop', 'function', 'class']):
        return 'code'
    elif any(w in task_lower for w in ['test', 'verify', 'validate', 'confirm', 'check if', 'ensure']):
        return 'testing'
    elif any(w in task_lower for w in ['grep', 'search', 'find', 'locate', 'scan', 'list']):
        return 'search'
    elif any(w in task_lower for w in ['edit', 'modify', 'change', 'update', 'fix', 'patch', 'refactor']):
        return 'edit'
    elif any(w in task_lower for w in ['file', 'read', 'cat', 'head', 'tail', 'ls', 'dir']):
        return 'file_ops'
    elif any(w in task_lower for w in ['git', 'commit', 'branch', 'diff', 'log']):
        return 'git'
    elif any(w in task_lower for w in ['run', 'execute', 'build', 'compile', 'make']):
        return 'execution'
    elif any(w in task_lower for w in ['compare', 'diff', 'versus', 'vs']):
        return 'comparison'
    elif any(w in task_lower for w in ['summarize', 'summary', 'overview', 'describe', 'explain']):
        return 'summary'
    elif any(w in task_lower for w in ['plan', 'design', 'architect', 'structure']):
        return 'planning'
    elif any(w in task_lower for w in ['write', 'doc', 'document', 'comment']):
        return 'documentation'
    else:
        return 'other'


def analyze_all_audit_files(audit_dir, sample_size=None):
    """Analyze all audit files in a directory."""
    audit_path = Path(audit_dir)
    audit_files = sorted(audit_path.glob('*.audit'))
    
    if sample_size and len(audit_files) > sample_size:
        # Take a representative sample
        step = len(audit_files) // sample_size
        audit_files = audit_files[::step][:sample_size]
    
    print(f"Analyzing {len(audit_files)} audit files...", file=sys.stderr)
    
    # Aggregate statistics
    total_files = len(audit_files)
    
    # Fork/subagent counters
    files_with_forks = 0
    files_with_subagents = 0
    files_with_both = 0
    files_with_neither = 0
    
    total_fork_calls = 0
    total_subagent_calls = 0
    total_fork_entries = 0
    total_subagent_entries = 0
    total_fork_ends = 0
    total_subagent_ends = 0
    
    all_fork_tasks = []
    all_subagent_tasks = []
    all_fork_durations = []
    all_subagent_durations = []
    all_nesting_depths = []
    
    nesting_distribution = Counter()
    task_type_dist = Counter()
    
    # Session characteristics
    sessions_with_deep_nesting = []  # nesting >= 3
    ghost_sessions = []
    
    # Effectiveness tracking (fork/subagent usage vs errors)
    fork_sessions_errors = []
    no_fork_sessions_errors = []
    
    # Progress tracking
    progress_interval = max(1, len(audit_files) // 20)
    
    for i, fpath in enumerate(audit_files):
        if (i + 1) % progress_interval == 0:
            print(f"  Progress: {i+1}/{len(audit_files)} ({(i+1)/len(audit_files)*100:.0f}%)", file=sys.stderr)
        
        result = analyze_single_audit(fpath)
        
        # Fork/subagent counts
        fork_calls = result.get('fork_calls_content', 0) + result.get('fork_start_entries', 0)
        subagent_calls = result.get('subagent_calls_content', 0) + result.get('subagent_start_entries', 0)
        
        has_fork = fork_calls > 0
        has_subagent = subagent_calls > 0
        
        if has_fork:
            files_with_forks += 1
            total_fork_calls += fork_calls
        if has_subagent:
            files_with_subagents += 1
            total_subagent_calls += subagent_calls
        if has_fork and has_subagent:
            files_with_both += 1
        if not has_fork and not has_subagent:
            files_with_neither += 1
        
        total_fork_entries += result.get('fork_start_entries', 0)
        total_subagent_entries += result.get('subagent_start_entries', 0)
        total_fork_ends += result.get('fork_end_entries', 0)
        total_subagent_ends += result.get('subagent_end_entries', 0)
        
        # Collect tasks
        all_fork_tasks.extend(result.get('fork_tasks_sample', []))
        all_subagent_tasks.extend(result.get('subagent_tasks_sample', []))
        
        # Collect durations
        all_fork_durations.extend(result.get('fork_durations', []))
        all_subagent_durations.extend(result.get('subagent_durations', []))
        
        # Collect nesting depths
        all_nesting_depths.extend(result.get('nesting_depths', []))
        depth = result.get('max_nesting', 0)
        if depth > 0:
            nesting_distribution[depth] += 1
        
        # Deep nesting detection
        if depth >= 3:
            sessions_with_deep_nesting.append({
                'file': result['basename'],
                'max_nesting': depth,
                'fork_calls': result.get('fork_start_entries', 0),
                'subagent_calls': result.get('subagent_start_entries', 0),
            })
        
        # Ghost session detection
        if result.get('ghost_session', False):
            ghost_sessions.append(result['basename'])
        
        # Error tracking for effectiveness comparison
        result.get('entry_types', {}).get('TOOL_RESULT', 0)
        # Count errors from content patterns
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                error_matches = len(re.findall(r'Error:|Exception:|Traceback|FAILED|failed to|timed out|timeout', content))
        except Exception:
            error_matches = 0
        
        if has_fork or has_subagent:
            fork_sessions_errors.append(error_matches)
        else:
            no_fork_sessions_errors.append(error_matches)
        
        # Categorize tasks
        for task in result.get('fork_tasks_sample', [])[:5]:
            task_type_dist[categorize_task(task)] += 1
        for task in result.get('subagent_tasks_sample', [])[:5]:
            task_type_dist[categorize_task(task)] += 1
    
    # Calculate statistics
    avg_fork_duration = sum(all_fork_durations) / len(all_fork_durations) if all_fork_durations else 0
    avg_subagent_duration = sum(all_subagent_durations) / len(all_subagent_durations) if all_subagent_durations else 0
    
    # Percentiles for durations
    def percentiles(data, percs=[25, 50, 75, 90, 95, 99]):
        if not data:
            return {p: 0 for p in percs}
        sorted_data = sorted(data)
        n = len(sorted_data)
        return {
            p: sorted_data[int(n * p / 100)] for p in percs
        }
    
    fork_dur_pcts = percentiles(all_fork_durations)
    subagent_dur_pcts = percentiles(all_subagent_durations)
    
    # Average errors comparison
    avg_errors_with_fork = sum(fork_sessions_errors) / len(fork_sessions_errors) if fork_sessions_errors else 0
    avg_errors_without_fork = sum(no_fork_sessions_errors) / len(no_fork_sessions_errors) if no_fork_sessions_errors else 0
    
    # Build result
    analysis = {
        'total_files': total_files,
        'files_with_forks': files_with_forks,
        'files_with_subagents': files_with_subagents,
        'files_with_both': files_with_both,
        'files_with_neither': files_with_neither,
        'total_fork_calls': total_fork_calls,
        'total_subagent_calls': total_subagent_calls,
        'total_fork_entries': total_fork_entries,
        'total_subagent_entries': total_subagent_entries,
        'total_fork_ends': total_fork_ends,
        'total_subagent_ends': total_subagent_ends,
        'fork_completion_rate': total_fork_ends / max(1, total_fork_entries),
        'subagent_completion_rate': total_subagent_ends / max(1, total_subagent_entries),
        'avg_fork_duration': avg_fork_duration,
        'avg_subagent_duration': avg_subagent_duration,
        'fork_duration_percentiles': fork_dur_pcts,
        'subagent_duration_percentiles': subagent_dur_pcts,
        'nesting_distribution': dict(nesting_distribution),
        'max_nesting_observed': max(nesting_distribution.keys()) if nesting_distribution else 0,
        'sessions_with_deep_nesting': sessions_with_deep_nesting[:20],
        'ghost_sessions_count': len(ghost_sessions),
        'ghost_sessions_sample': ghost_sessions[:20],
        'avg_errors_with_fork_or_subagent': avg_errors_with_fork,
        'avg_errors_without_fork_or_subagent': avg_errors_without_fork,
        'task_type_distribution': dict(task_type_dist),
        'top_fork_tasks': Counter(all_fork_tasks).most_common(30),
        'top_subagent_tasks': Counter(all_subagent_tasks).most_common(30),
        'fork_usage_rate': files_with_forks / max(1, total_files) * 100,
        'subagent_usage_rate': files_with_subagents / max(1, total_files) * 100,
        'both_usage_rate': files_with_both / max(1, total_files) * 100,
    }
    
    return analysis


def print_report(analysis):
    """Print comprehensive fork/subagent analysis report."""
    print("=" * 80)
    print("TAU AUDIT: COMPREHENSIVE FORK/SUBAGENT ANALYSIS REPORT")
    print("=" * 80)
    
    # Overview
    print(f"\n{'='*40}")
    print(f"1. OVERVIEW")
    print(f"{'='*40}")
    print(f"  Total audit files analyzed: {analysis['total_files']:,}")
    print(f"  Files with forks:           {analysis['files_with_forks']:,} ({analysis['fork_usage_rate']:.1f}%)")
    print(f"  Files with subagents:        {analysis['files_with_subagents']:,} ({analysis['subagent_usage_rate']:.1f}%)")
    print(f"  Files with both:             {analysis['files_with_both']:,} ({analysis['both_usage_rate']:.1f}%)")
    print(f"  Files with neither:          {analysis['files_with_neither']:,}")
    
    # Call counts
    print(f"\n{'='*40}")
    print(f"2. CALL FREQUENCY")
    print(f"{'='*40}")
    print(f"  Total fork calls (content):  {analysis['total_fork_calls']:,}")
    print(f"  Total subagent calls (content): {analysis['total_subagent_calls']:,}")
    print(f"  Total FORK_START entries:    {analysis['total_fork_entries']:,}")
    print(f"  Total SUBAGENT_START entries: {analysis['total_subagent_entries']:,}")
    print(f"  Total FORK_END entries:      {analysis['total_fork_ends']:,}")
    print(f"  Total SUBAGENT_END entries:  {analysis['total_subagent_ends']:,}")
    print(f"  Fork completion rate:        {analysis['fork_completion_rate']*100:.1f}%")
    print(f"  Subagent completion rate:    {analysis['subagent_completion_rate']*100:.1f}%")
    
    # Duration distributions
    print(f"\n{'='*40}")
    print(f"3. DURATION DISTRIBUTIONS")
    print(f"{'='*40}")
    print(f"  Fork avg:          {analysis['avg_fork_duration']:.1f}s")
    print(f"  Subagent avg:      {analysis['avg_subagent_duration']:.1f}s")
    print(f"\n  Fork duration percentiles:")
    for p, v in sorted(analysis['fork_duration_percentiles'].items()):
        print(f"    P{p:2d}: {v:.1f}s")
    print(f"\n  Subagent duration percentiles:")
    for p, v in sorted(analysis['subagent_duration_percentiles'].items()):
        print(f"    P{p:2d}: {v:.1f}s")
    
    # Nesting depth
    print(f"\n{'='*40}")
    print(f"4. NESTING DEPTH PATTERNS")
    print(f"{'='*40}")
    print(f"  Max nesting observed: {analysis['max_nesting_observed']}")
    print(f"\n  Nesting distribution:")
    for depth in sorted(analysis['nesting_distribution'].keys()):
        count = analysis['nesting_distribution'][depth]
        bar = '#' * min(count // max(1, count // 50), 50)
        print(f"    Depth {depth:2d}: {count:5d} sessions {bar}")
    
    if analysis['sessions_with_deep_nesting']:
        print(f"\n  Deep nesting sessions (nesting >= 3):")
        for s in analysis['sessions_with_deep_nesting'][:10]:
            print(f"    {s['file']}: max_nesting={s['max_nesting']}, "
                  f"forks={s['fork_calls']}, subagents={s['subagent_calls']}")
    
    # Task categorization
    print(f"\n{'='*40}")
    print(f"5. TASK CATEGORIZATION")
    print(f"{'='*40}")
    total_tasks = sum(analysis['task_type_distribution'].values())
    for task_type, count in sorted(analysis['task_type_distribution'].items(), key=lambda x: -x[1]):
        pct = count / max(1, total_tasks) * 100
        bar = '#' * min(int(pct / 2), 40)
        print(f"  {task_type:<15s}: {count:5d} ({pct:5.1f}%) {bar}")
    
    # Top task patterns
    print(f"\n{'='*40}")
    print(f"6. TOP FORK TASK PATTERNS")
    print(f"{'='*40}")
    for task, count in analysis['top_fork_tasks'][:15]:
        category = categorize_task(task)
        print(f"  [{category:>10s}] {task[:80]} (x{count})")
    
    print(f"\n{'='*40}")
    print(f"7. TOP SUBAGENT TASK PATTERNS")
    print(f"{'='*40}")
    for task, count in analysis['top_subagent_tasks'][:15]:
        category = categorize_task(task)
        print(f"  [{category:>10s}] {task[:80]} (x{count})")
    
    # Effectiveness comparison
    print(f"\n{'='*40}")
    print(f"8. FORK/SUBAGENT EFFECTIVENESS")
    print(f"{'='*40}")
    print(f"  Avg errors (sessions WITH fork/subagent): {analysis['avg_errors_with_fork_or_subagent']:.2f}")
    print(f"  Avg errors (sessions WITHOUT fork/subagent): {analysis['avg_errors_without_fork_or_subagent']:.2f}")
    if analysis['avg_errors_without_fork_or_subagent'] > 0:
        improvement = (analysis['avg_errors_without_fork_or_subagent'] - analysis['avg_errors_with_fork_or_subagent']) / analysis['avg_errors_without_fork_or_subagent'] * 100
        print(f"  Error reduction: {improvement:+.1f}%")
    else:
        print(f"  Error reduction: N/A (no errors in baseline)")
    
    # Ghost sessions
    print(f"\n{'='*40}")
    print(f"9. GHOST SESSIONS (bypassing fork/subagent)")
    print(f"{'='*40}")
    print(f"  Ghost sessions detected: {analysis['ghost_sessions_count']:,}")
    ghost_pct = analysis['ghost_sessions_count'] / max(1, analysis['total_files']) * 100
    print(f"  Ghost session rate: {ghost_pct:.1f}%")
    if analysis['ghost_sessions_sample']:
        print(f"\n  Sample ghost sessions:")
        for gs in analysis['ghost_sessions_sample'][:10]:
            print(f"    {gs}")
    
    # Summary
    print(f"\n{'='*40}")
    print(f"10. KEY INSIGHTS")
    print(f"{'='*40}")
    
    # Insights
    insights = []
    
    if analysis['fork_usage_rate'] > 50:
        insights.append(f"  [HIGH] Forks are used in {analysis['fork_usage_rate']:.0f}% of sessions")
    elif analysis['fork_usage_rate'] > 20:
        insights.append(f"  [MED] Forks are used in {analysis['fork_usage_rate']:.0f}% of sessions")
    else:
        insights.append(f"  [LOW] Forks are used in only {analysis['fork_usage_rate']:.0f}% of sessions")
    
    if analysis['subagent_usage_rate'] > analysis['fork_usage_rate']:
        insights.append(f"  [NOTE] Subagents ({analysis['subagent_usage_rate']:.0f}%) more common than forks ({analysis['fork_usage_rate']:.0f}%)")
    
    if analysis['max_nesting_observed'] >= 5:
        insights.append(f"  [DEEP] Nesting goes as deep as {analysis['max_nesting_observed']} levels")
    elif analysis['max_nesting_observed'] >= 3:
        insights.append(f"  [MODERATE] Nesting reaches {analysis['max_nesting_observed']} levels")
    
    if analysis['ghost_sessions_count'] > analysis['total_files'] * 0.3:
        insights.append(f"  [GHOST] {ghost_pct:.0f}% of sessions are ghost sessions (no fork/subagent logging)")
    
    if abs(analysis['avg_errors_with_fork_or_subagent'] - analysis['avg_errors_without_fork_or_subagent']) > 1:
        delta = analysis['avg_errors_with_fork_or_subagent'] - analysis['avg_errors_without_fork_or_subagent']
        if delta < 0:
            insights.append(f"  [GOOD] Fork/subagent use reduces errors by ~{abs(delta):.1f} per session")
        else:
            insights.append(f"  [WARN] Fork/subagent use correlates with {abs(delta):.1f} MORE errors per session")
    
    if analysis['fork_completion_rate'] < 0.9:
        insights.append(f"  [WARN] Fork completion rate is only {analysis['fork_completion_rate']*100:.0f}%")
    
    if analysis['subagent_completion_rate'] < 0.9:
        insights.append(f"  [WARN] Subagent completion rate is only {analysis['subagent_completion_rate']*100:.0f}%")
    
    # Find most common task type
    if analysis['task_type_distribution']:
        top_task = max(analysis['task_type_distribution'], key=analysis['task_type_distribution'].get)
        insights.append(f"  [PATTERN] Most common task type: {top_task} ({analysis['task_type_distribution'][top_task]} tasks)")
    
    if insights:
        for insight in insights:
            print(insight)
    else:
        print("  No significant patterns detected.")
    
    print(f"\n{'='*80}")
    print(f"END OF REPORT")
    print(f"{'='*80}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deep fork/subagent analysis of tau audit files')
    parser.add_argument('audit_dir', help='Directory containing .audit files')
    parser.add_argument('--sample', type=int, default=None, 
                       help='Sample size (default: all files)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.audit_dir):
        print(f"Error: {args.audit_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    analysis = analyze_all_audit_files(args.audit_dir, sample_size=args.sample)
    
    # Print report
    print_report(analysis)
    
    # Save JSON if requested
    if args.output:
        # Convert non-serializable types
        serializable = {}
        for k, v in analysis.items():
            if isinstance(v, Counter):
                serializable[k] = dict(v)
            elif isinstance(v, list):
                serializable[k] = v
            elif isinstance(v, dict):
                serializable[k] = v
            else:
                serializable[k] = v
        with open(args.output, 'w') as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"\nJSON results saved to {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
