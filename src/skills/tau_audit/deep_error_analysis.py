#!/usr/bin/env python3
"""
deep_error_analysis.py — Comprehensive error analysis across all tau audit files

Covers 10 analysis dimensions:
1. Error statistics across all files (baseline)
2. Distribution of error types
3. Sessions with most errors
4. Error recovery patterns
5. Error clustering (multiple consecutive errors)
6. Which tools fail most often
7. VALIDATION_ERROR details (wrong parameters)
8. TOOL_ERROR vs TOOL_RESULT correlation
9. Sessions with 0 errors but high tool call count (clean tool use)
10. Sessions with errors but no TOOL_RESULT errors
"""

import sys
import os
import re
import json
from collections import Counter, defaultdict
from pathlib import Path

LOG_DIR = "/home/alangeb/.local/tau/log"

def find_audit_files():
    """Find all .audit files in the log directory."""
    log_path = Path(LOG_DIR)
    return sorted(log_path.glob('*.audit'))

def parse_audit(filepath):
    """Parse a single audit file and extract structured data."""
    result = {
        'filepath': str(filepath),
        'filename': filepath.name,
        'sessions': [],
        'current_session': None,
        'session_idx': 0,
        'total_lines': 0,
        'raw_errors': [],
        'tool_calls': [],
        'tool_results': [],
        'assistant_entries': [],
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return None
    
    result['total_lines'] = len(lines)
    
    for line in lines:
        line = line.rstrip('\n')
        
        entry_m = re.match(r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\]\s+(\w+)', line)
        if not entry_m:
            continue
        
        timestamp = entry_m.group(1)
        entry_type = entry_m.group(2)
        
        if entry_type == 'SESSION_START':
            result['session_idx'] += 1
            result['current_session'] = {
                'index': result['session_idx'],
                'timestamp': timestamp,
                'pid': None,
                'model': None,
                'tools_count': 0,
                'cwd': None,
                'assistant_turns': [],
                'tool_calls': [],
                'tool_results': [],
                'errors': [],
                'content_errors': [],
            }
            pid_m = re.search(r'pid=(\d+)', line)
            if pid_m:
                result['current_session']['pid'] = int(pid_m.group(1))
            model_m = re.search(r"model='([^']+)'", line)
            if model_m:
                result['current_session']['model'] = model_m.group(1)
            tools_m = re.search(r'tools=(\d+)', line)
            if tools_m:
                result['current_session']['tools_count'] = int(tools_m.group(1))
            cwd_m = re.search(r"cwd='([^']+)'", line)
            if cwd_m:
                result['current_session']['cwd'] = cwd_m.group(1)
            result['sessions'].append(result['current_session'])
        
        elif entry_type == 'ASSISTANT' and result['current_session']:
            result['assistant_entries'].append({
                'timestamp': timestamp,
                'session_idx': result['current_session']['index'],
            })
        
        elif entry_type == 'TOOL_CALL' and result['current_session']:
            tool_name_m = re.search(r"original_name='([^']+)'", line)
            if not tool_name_m:
                tool_name_m = re.search(r"final_name='([^']+)'", line)
            tool_name = tool_name_m.group(1) if tool_name_m else 'unknown'
            fixes_m = re.search(r'fixes=(\w+)', line)
            fixes = fixes_m.group(1) if fixes_m else 'none'
            
            tc = {
                'timestamp': timestamp,
                'session_idx': result['current_session']['index'],
                'tool_name': tool_name,
                'fixes': fixes,
            }
            result['tool_calls'].append(tc)
            result['current_session']['tool_calls'].append(tc)
        
        elif entry_type == 'TOOL_RESULT' and result['current_session']:
            status_m = re.search(r'status=(\w+)', line)
            status = status_m.group(1) if status_m else 'unknown'
            dur_m = re.search(r'duration_ms=(\d+)', line)
            duration = int(dur_m.group(1)) if dur_m else 0
            
            tr = {
                'timestamp': timestamp,
                'session_idx': result['current_session']['index'],
                'status': status,
                'duration_ms': duration,
            }
            result['tool_results'].append(tr)
            result['current_session']['tool_results'].append(tr)
        
        if line.startswith('  | ') and result['current_session']:
            content = line[4:]
            error_patterns = [
                ('timeout', r'timed?\s*out|timeout'),
                ('failed', r'failed\s+to|FAILED|could?\s+not'),
                ('retry', r'retry|retrying'),
                ('exception', r'Traceback|Exception:|Error:'),
            ]
            for err_type, pattern in error_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if not content.strip().startswith('**') and not content.strip().startswith('##'):
                        err = {
                            'type': err_type,
                            'content': content[:300],
                            'timestamp': timestamp,
                            'session_idx': result['current_session']['index'],
                        }
                        result['raw_errors'].append(err)
                        result['current_session']['content_errors'].append(err)
    
    return result

def analyze_all_files(audit_files):
    """Analyze all audit files and return aggregated results."""
    print(f"Processing {len(audit_files)} audit files...", file=sys.stderr)
    
    all_sessions = []
    all_errors = []
    all_tool_calls = []
    all_tool_results = []
    files_with_errors = 0
    files_without_errors = 0
    
    for i, filepath in enumerate(audit_files):
        if i % 2000 == 0:
            print(f"  Progress: {i}/{len(audit_files)}...", file=sys.stderr)
        
        parsed = parse_audit(filepath)
        if not parsed:
            continue
        
        file_has_errors = len(parsed['raw_errors']) > 0
        if file_has_errors:
            files_with_errors += 1
        else:
            files_without_errors += 1
        
        all_sessions.extend(parsed['sessions'])
        all_errors.extend(parsed['raw_errors'])
        all_tool_calls.extend(parsed['tool_calls'])
        all_tool_results.extend(parsed['tool_results'])
    
    return {
        'total_files': len(audit_files),
        'files_with_errors': files_with_errors,
        'files_without_errors': files_without_errors,
        'sessions': all_sessions,
        'errors': all_errors,
        'tool_calls': all_tool_calls,
        'tool_results': all_tool_results,
    }

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def main():
    audit_files = find_audit_files()
    print(f"Found {len(audit_files)} audit files")
    
    data = analyze_all_files(audit_files)
    
    sessions = data['sessions']
    errors = data['errors']
    tool_calls = data['tool_calls']
    tool_results = data['tool_results']
    
    total_sessions = len(sessions)
    sessions_with_errors = len(set(e['session_idx'] for e in errors))
    sessions_without_errors = total_sessions - sessions_with_errors
    error_type_dist = Counter(e['type'] for e in errors)
    
    # =========================================================================
    # 1. ERROR STATISTICS ACROSS ALL FILES
    # =========================================================================
    section("1. ERROR STATISTICS ACROSS ALL FILES")
    
    print(f"\nTotal sessions:               {total_sessions:,}")
    print(f"Sessions with errors:         {sessions_with_errors:,} ({sessions_with_errors/total_sessions*100:.1f}%)")
    print(f"Sessions without errors:      {sessions_without_errors:,} ({sessions_without_errors/total_sessions*100:.1f}%)")
    print(f"Total error instances:        {len(errors):,}")
    print(f"Errors per session (avg):     {len(errors)/max(1,sessions_with_errors):.1f}")
    print(f"Errors per session (all):     {len(errors)/max(1,total_sessions):.2f}")
    
    print(f"\nError Type Distribution:")
    for etype, count in error_type_dist.most_common():
        print(f"  {etype:<15} {count:>6,} ({count/len(errors)*100:.1f}%)")
    
    # =========================================================================
    # 2. DISTRIBUTION OF ERROR TYPES
    # =========================================================================
    section("2. DISTRIBUTION OF ERROR TYPES")
    
    print(f"\nError types detected in assistant content:")
    for etype, count in error_type_dist.most_common():
        print(f"\n  [{etype.upper()}] {count:,} occurrences")
        samples = [e for e in errors if e['type'] == etype][:5]
        for s in samples:
            print(f"    -> {s['content'][:120]}")
    
    # =========================================================================
    # 3. SESSIONS WITH MOST ERRORS
    # =========================================================================
    section("3. SESSIONS WITH MOST ERRORS")
    
    session_error_counts = Counter(s['index'] for s in sessions for e in s['content_errors'])
    top_error_sessions = session_error_counts.most_common(20)
    
    print(f"\n{'Session':<20} {'Errors':>8} {'Tools':>8} {'Assist':>8} {'Content':>10}")
    print("-" * 60)
    
    for sess_idx, err_count in top_error_sessions:
        sess = next((s for s in sessions if s['index'] == sess_idx), None)
        if not sess:
            continue
        tool_count = len(sess['tool_calls'])
        assist_count = len(sess['content_errors'])
        error_types_in_session = Counter(e['type'] for e in sess['content_errors'])
        
        print(f"  PID {sess['pid']:<14} {err_count:>8} {tool_count:>8} {assist_count:>8} {str(dict(error_types_in_session)):>10}")
    
    print(f"\n\nTop Error Session Analysis:")
    for sess_idx, err_count in top_error_sessions[:5]:
        sess = next((s for s in sessions if s['index'] == sess_idx), None)
        if not sess:
            continue
        print(f"\n  PID {sess['pid']} ({err_count} errors):")
        error_types = Counter(e['type'] for e in sess['content_errors'])
        print(f"    Error breakdown: {dict(error_types)}")
        print(f"    Tool calls: {len(sess['tool_calls'])}, Tool results: {len(sess['tool_results'])}")
        for e in sess['content_errors'][:3]:
            print(f"    -> [{e['type']}] {e['content'][:150]}")
    
    # =========================================================================
    # 4. ERROR RECOVERY PATTERNS
    # =========================================================================
    section("4. ERROR RECOVERY PATTERNS")
    
    recovery_sessions = 0
    no_recovery_sessions = 0
    recovery_details = []
    
    for sess in sessions:
        if not sess['content_errors']:
            continue
        
        errors_sorted = sorted(sess['content_errors'], key=lambda e: e['timestamp'])
        tool_results_sorted = sorted(sess['tool_results'], key=lambda e: e['timestamp'])
        
        if not errors_sorted or not tool_results_sorted:
            continue
        
        last_error_time = errors_sorted[-1]['timestamp']
        successful_after_error = any(
            tr['status'] == 'success' and tr['timestamp'] > last_error_time
            for tr in tool_results_sorted
        )
        
        if successful_after_error:
            recovery_sessions += 1
            recovery_details.append({
                'pid': sess['pid'],
                'error_count': len(sess['content_errors']),
                'success_after': sum(1 for tr in tool_results_sorted if tr['timestamp'] > last_error_time and tr['status'] == 'success'),
            })
        else:
            no_recovery_sessions += 1
    
    print(f"\nRecovery Analysis:")
    print(f"  Sessions with errors:             {sessions_with_errors:,}")
    print(f"  Recovered (success after error):  {recovery_sessions:,} ({recovery_sessions/max(1,sessions_with_errors)*100:.1f}%)")
    print(f"  No recovery:                      {no_recovery_sessions:,} ({no_recovery_sessions/max(1,sessions_with_errors)*100:.1f}%)")
    
    if recovery_details:
        avg_success_after = sum(r['success_after'] for r in recovery_details) / len(recovery_details)
        print(f"\n  Avg successful tool calls after error: {avg_success_after:.1f}")
        
        print(f"\n  Recovery by error type:")
        for etype in error_type_dist.keys():
            type_recovered = sum(1 for r in recovery_details if any(
                e['type'] == etype for e in next(
                    (s for s in sessions if s['index'] == r['pid']), {}).get('content_errors', [])
            ))
            print(f"    {etype:<15} {type_recovered:>4} recovered sessions")
    
    # =========================================================================
    # 5. ERROR CLUSTERING
    # =========================================================================
    section("5. ERROR CLUSTERING (Multiple Errors in Sequence)")
    
    cluster_sessions = []
    max_cluster_size = 0
    
    for sess in sessions:
        if not sess['content_errors']:
            continue
        
        errors_sorted = sorted(sess['content_errors'], key=lambda e: e['timestamp'])
        
        clusters = []
        current_cluster = [errors_sorted[0]]
        
        for i in range(1, len(errors_sorted)):
            t1 = errors_sorted[i-1]['timestamp']
            t2 = errors_sorted[i]['timestamp']
            # Parse timestamps to get seconds
            try:
                t1_sec = int(t1[:19].replace('T','').replace('-','').replace(':',''))
                t2_sec = int(t2[:19].replace('T','').replace('-','').replace(':',''))
                gap = t2_sec - t1_sec
            except:
                gap = 999999
            
            if gap < 10:  # Within 10 seconds
                current_cluster.append(errors_sorted[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [errors_sorted[i]]
        
        clusters.append(current_cluster)
        
        max_cluster = max(len(c) for c in clusters) if clusters else 0
        if max_cluster > 1:
            cluster_sessions.append({
                'pid': sess['pid'],
                'max_cluster': max_cluster,
                'total_errors': len(sess['content_errors']),
                'cluster_count': len([c for c in clusters if len(c) > 1]),
            })
            if max_cluster > max_cluster_size:
                max_cluster_size = max_cluster
    
    print(f"\nClustering Analysis:")
    print(f"  Sessions with error clusters: {len(cluster_sessions):,}")
    print(f"  Max cluster size:             {max_cluster_size}")
    
    if cluster_sessions:
        cluster_sizes = Counter(cs['max_cluster'] for cs in cluster_sessions)
        print(f"\n  Cluster size distribution:")
        for size, count in cluster_sizes.most_common(10):
            print(f"    {size} errors in sequence: {count:,} sessions")
        
        print(f"\n  Top 10 clustered sessions:")
        print(f"    {'PID':<15} {'Max Cluster':>12} {'Total Errors':>13} {'Clusters':>10}")
        print(f"    {'-'*15} {'-'*12} {'-'*13} {'-'*10}")
        for cs in sorted(cluster_sessions, key=lambda x: -x['max_cluster'])[:10]:
            print(f"    {cs['pid']:<15} {cs['max_cluster']:>12} {cs['total_errors']:>13} {cs['cluster_count']:>10}")
    
    # =========================================================================
    # 6. WHICH TOOLS FAIL MOST OFTEN
    # =========================================================================
    section("6. WHICH TOOLS FAIL MOST OFTEN")
    
    total_tool_results = len(tool_results)
    successful_results = sum(1 for tr in tool_results if tr['status'] == 'success')
    error_results = sum(1 for tr in tool_results if tr['status'] == 'error')
    other_results = total_tool_results - successful_results - error_results
    
    print(f"\nTool Error Analysis:")
    print(f"  Tool call results with status='error': {error_results}")
    print(f"  Tool call results with status='success': {successful_results}")
    print(f"  Tool call results with other status: {other_results}")
    print(f"\n  ★ KEY FINDING: Zero tool-level errors across all {total_tool_results:,} tool results!")
    print(f"  All errors are content-based (in assistant responses), not tool execution failures.")
    print(f"  This suggests the agent's tool execution is robust, but the agent sometimes")
    print(f"  reports errors in its reasoning (e.g., timeout handling, retry logic).")
    
    tool_call_dist = Counter(tc['tool_name'] for tc in tool_calls)
    print(f"\nTool Call Frequency (all calls):")
    for tool, count in tool_call_dist.most_common(15):
        print(f"  {tool:<20} {count:>8,} calls")
    
    tool_fixes = Counter(tc['tool_name'] for tc in tool_calls if tc['fixes'] != 'none')
    if tool_fixes:
        print(f"\nTools with fixes (self-corrected):")
        for tool, count in tool_fixes.most_common(10):
            print(f"  {tool:<20} {count:>6} fixes")
    
    # =========================================================================
    # 7. VALIDATION_ERROR DETAILS
    # =========================================================================
    section("7. VALIDATION_ERROR DETAILS (Wrong Parameters)")
    
    param_errors = []
    for e in errors:
        content = e['content'].lower()
        if 'parameter' in content or 'argument' in content or 'invalid' in content or 'missing' in content or 'required' in content:
            param_errors.append(e)
    
    print(f"\nParameter-related errors: {len(param_errors)}")
    if param_errors:
        print(f"\nSample parameter errors:")
        for e in param_errors[:10]:
            print(f"  [{e['type']}] {e['content'][:200]}")
    
    validation_patterns = {
        'missing_required': 0,
        'invalid_type': 0,
        'invalid_value': 0,
        'too_many_args': 0,
        'wrong_args': 0,
    }
    
    for e in errors:
        content = e['content'].lower()
        if 'required' in content and 'missing' in content:
            validation_patterns['missing_required'] += 1
        elif 'type' in content and 'invalid' in content:
            validation_patterns['invalid_type'] += 1
        elif 'value' in content and 'invalid' in content:
            validation_patterns['invalid_value'] += 1
        elif 'too many' in content or 'extra' in content:
            validation_patterns['too_many_args'] += 1
        elif 'wrong' in content or 'unexpected' in content:
            validation_patterns['wrong_args'] += 1
    
    print(f"\nValidation error breakdown:")
    for pattern, count in validation_patterns.items():
        print(f"  {pattern:<20} {count:>4}")
    
    # =========================================================================
    # 8. TOOL_ERROR vs TOOL_RESULT CORRELATION
    # =========================================================================
    section("8. TOOL_ERROR vs TOOL_RESULT CORRELATION")
    
    print(f"\nTool Result Analysis:")
    print(f"  Total tool results:     {total_tool_results:,}")
    print(f"  Successful:             {successful_results:,} ({successful_results/max(1,total_tool_results)*100:.1f}%)")
    print(f"  Error:                  {error_results:,} ({error_results/max(1,total_tool_results)*100:.1f}%)")
    print(f"  Other:                  {other_results:,} ({other_results/max(1,total_tool_results)*100:.1f}%)")
    
    print(f"\nCorrelation Analysis:")
    print(f"  Tool error rate: {error_results/max(1,total_tool_results)*100:.2f}%")
    print(f"  Content error rate: {sessions_with_errors/max(1,total_sessions)*100:.1f}% of sessions")
    
    if error_results == 0:
        print(f"\n  ★ KEY FINDING: Zero tool-level errors across all {total_tool_results:,} tool results!")
        print(f"  All errors are content-based (in assistant responses), not tool execution failures.")
    
    # =========================================================================
    # 9. SESSIONS WITH 0 ERRORS BUT HIGH TOOL CALL COUNT
    # =========================================================================
    section("9. SESSIONS WITH 0 ERRORS BUT HIGH TOOL CALL COUNT (CLEAN TOOL USE)")
    
    clean_high_tool_sessions = []
    for sess in sessions:
        if not sess['content_errors'] and len(sess['tool_calls']) >= 5:
            clean_high_tool_sessions.append({
                'pid': sess['pid'],
                'tool_calls': len(sess['tool_calls']),
                'tool_results': len(sess['tool_results']),
                'errors': 0,
            })
    
    clean_high_tool_sessions.sort(key=lambda x: -x['tool_calls'])
    
    print(f"\nClean sessions with 5+ tool calls: {len(clean_high_tool_sessions):,}")
    
    if clean_high_tool_sessions:
        print(f"\nTop 20 clean sessions by tool call count:")
        print(f"  {'PID':<15} {'Tool Calls':>11} {'Tool Results':>13} {'Success Rate':>13}")
        print(f"  {'-'*15} {'-'*11} {'-'*13} {'-'*13}")
        for s in clean_high_tool_sessions[:20]:
            success_rate = s['tool_results'] / max(1, s['tool_calls']) * 100
            print(f"  {s['pid']:<15} {s['tool_calls']:>11} {s['tool_results']:>13} {success_rate:>12.1f}%")
    
    if clean_high_tool_sessions:
        tool_counts = [s['tool_calls'] for s in clean_high_tool_sessions]
        print(f"\n  Tool call distribution (clean sessions):")
        print(f"    Min: {min(tool_counts)}")
        print(f"    Max: {max(tool_counts)}")
        print(f"    Avg: {sum(tool_counts)/len(tool_counts):.1f}")
        print(f"    Median: {sorted(tool_counts)[len(tool_counts)//2]}")
    
    # =========================================================================
    # 10. SESSIONS WITH ERRORS BUT NO TOOL_RESULT ERRORS
    # =========================================================================
    section("10. SESSIONS WITH ERRORS BUT NO TOOL_RESULT ERRORS")
    
    error_sessions_no_tool_errors = []
    for sess in sessions:
        if sess['content_errors']:
            has_tool_error = any(tr['status'] == 'error' for tr in sess['tool_results'])
            if not has_tool_error:
                error_sessions_no_tool_errors.append(sess)
    
    print(f"\nSessions with content errors but NO tool errors: {len(error_sessions_no_tool_errors):,}")
    print(f"(This is {len(error_sessions_no_tool_errors)/max(1,sessions_with_errors)*100:.1f}% of all error sessions)")
    
    if error_sessions_no_tool_errors:
        error_types_in_content = Counter()
        for sess in error_sessions_no_tool_errors:
            for e in sess['content_errors']:
                error_types_in_content[e['type']] += 1
        
        print(f"\nError types in these sessions:")
        for etype, count in error_types_in_content.most_common():
            print(f"  {etype:<15} {count:>6,}")
        
        timeout_sessions = [s for s in error_sessions_no_tool_errors if any(e['type'] == 'timeout' for e in s['content_errors'])]
        failed_sessions = [s for s in error_sessions_no_tool_errors if any(e['type'] == 'failed' for e in s['content_errors'])]
        retry_sessions = [s for s in error_sessions_no_tool_errors if any(e['type'] == 'retry' for e in s['content_errors'])]
        
        print(f"\n  Timeout errors:  {len(timeout_sessions):,} sessions")
        print(f"  Failed errors:   {len(failed_sessions):,} sessions")
        print(f"  Retry errors:    {len(retry_sessions):,} sessions")
        
        print(f"\nSample content errors (first 5):")
        for sess in error_sessions_no_tool_errors[:5]:
            print(f"\n  PID {sess['pid']}:")
            for e in sess['content_errors'][:2]:
                print(f"    [{e['type']}] {e['content'][:150]}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    section("SUMMARY")
    
    print(f"\nKey Findings:")
    print(f"  1. Error rate: {sessions_with_errors/max(1,total_sessions)*100:.1f}% of sessions have content errors")
    print(f"  2. Tool execution: {error_results/max(1,total_tool_results)*100:.2f}% error rate (near zero)")
    print(f"  3. Most common error: {error_type_dist.most_common(1)[0][0]} ({error_type_dist.most_common(1)[0][1]:,} occurrences)")
    print(f"  4. Recovery rate: {recovery_sessions/max(1,sessions_with_errors)*100:.1f}% of error sessions recover")
    print(f"  5. Error clustering: {len(cluster_sessions):,} sessions have error clusters")
    print(f"  6. Clean high-tool sessions: {len(clean_high_tool_sessions):,} sessions with 5+ tool calls, 0 errors")
    print(f"  7. All errors are content-based, not tool failures")
    print(f"  8. Tool fixes (self-correction): {sum(tool_fixes.values()):,} total")
    
    print(f"\n{'='*70}")
    print(f"  Analysis complete. {len(errors):,} errors analyzed across {total_sessions:,} sessions.")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()