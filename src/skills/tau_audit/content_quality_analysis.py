#!/usr/bin/env python3
"""
Comprehensive content quality and time analysis across all tau audit files.

Outputs:
1. Content quality statistics (baseline from batch_analyze.py)
2. Uncertainty indicator analysis
3. Confidence indicator analysis
4. Self-correction frequency analysis
5. Response length distributions
6. Time patterns (session duration, entry gaps)
7. High uncertainty + low success rate sessions
8. High confidence + high success rate sessions
9. Response length vs quality correlation
10. Unusually long/short response sessions
11. Cache warning patterns and session quality
"""

import sys
import os
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_audit import analyze_audit

AUDIT_DIR = "~/.local/tau/log"
UNCERTAINTY_WORDS = ['probably', 'maybe', 'i think', 'i\'m not sure', 'possibly', 'likely']
CONFIDENCE_WORDS = ['confirmed', 'verified', 'tested', 'works', 'definitely', 'certain']
SELF_CORRECTION_WORDS = ['actually', 'wait', 'no,', 'correction', 'oops']


def find_all_audit_files(directory):
    return sorted(Path(directory).glob('*.audit'))


def analyze_all_files(files, batch_size=500):
    """Process files in batches, collecting aggregated statistics."""
    all_results = []
    total = len(files)
    
    for i in range(0, total, batch_size):
        batch = files[i:i+batch_size]
        for fpath in batch:
            try:
                data = analyze_audit(str(fpath))
                data['_filepath'] = str(fpath)
                data['_basename'] = fpath.name
                all_results.append(data)
            except Exception as e:
                pass
    
    print(f"Processed {len(all_results)}/{total} files", file=sys.stderr)
    return all_results


def percentile(data, pct):
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def generate_report(results):
    """Generate comprehensive analysis report."""
    if not results:
        print("No results to analyze.")
        return
    
    n = len(results)
    lines = []
    lines.append("=" * 80)
    lines.append("TAU AUDIT: COMPREHENSIVE CONTENT QUALITY & TIME ANALYSIS")
    lines.append("=" * 80)
    lines.append(f"\nTotal sessions analyzed: {n:,}")
    
    # ===== 1. BASELINE CONTENT QUALITY STATISTICS =====
    lines.append("\n" + "=" * 80)
    lines.append("1. BASELINE CONTENT QUALITY STATISTICS")
    lines.append("=" * 80)
    
    uncertainty_counts = [r['content_quality']['uncertainty_count'] for r in results]
    confidence_counts = [r['content_quality']['confidence_count'] for r in results]
    self_correction_counts = [r['content_quality']['self_correction_count'] for r in results]
    long_resp_counts = [r['content_quality']['long_responses_count'] for r in results]
    short_resp_counts = [r['content_quality']['short_responses_count'] for r in results]
    
    lines.append(f"\n  Uncertainty indicators (total):")
    lines.append(f"    Sum: {sum(uncertainty_counts):,}")
    lines.append(f"    Mean: {statistics.mean(uncertainty_counts):.2f}")
    lines.append(f"    Median: {statistics.median(uncertainty_counts):.2f}")
    lines.append(f"    Std Dev: {statistics.stdev(uncertainty_counts) if len(uncertainty_counts) > 1 else 0:.2f}")
    lines.append(f"    Sessions with >0: {sum(1 for x in uncertainty_counts if x > 0):,} ({sum(1 for x in uncertainty_counts if x > 0)/n*100:.1f}%)")
    
    lines.append(f"\n  Confidence indicators (total):")
    lines.append(f"    Sum: {sum(confidence_counts):,}")
    lines.append(f"    Mean: {statistics.mean(confidence_counts):.2f}")
    lines.append(f"    Median: {statistics.median(confidence_counts):.2f}")
    lines.append(f"    Std Dev: {statistics.stdev(confidence_counts) if len(confidence_counts) > 1 else 0:.2f}")
    lines.append(f"    Sessions with >0: {sum(1 for x in confidence_counts if x > 0):,} ({sum(1 for x in confidence_counts if x > 0)/n*100:.1f}%)")
    
    lines.append(f"\n  Self-corrections (total):")
    lines.append(f"    Sum: {sum(self_correction_counts):,}")
    lines.append(f"    Mean: {statistics.mean(self_correction_counts):.2f}")
    lines.append(f"    Median: {statistics.median(self_correction_counts):.2f}")
    lines.append(f"    Std Dev: {statistics.stdev(self_correction_counts) if len(self_correction_counts) > 1 else 0:.2f}")
    lines.append(f"    Sessions with >0: {sum(1 for x in self_correction_counts if x > 0):,} ({sum(1 for x in self_correction_counts if x > 0)/n*100:.1f}%)")
    
    lines.append(f"\n  Long responses (>1KB) (total):")
    lines.append(f"    Sum: {sum(long_resp_counts):,}")
    lines.append(f"    Mean: {statistics.mean(long_resp_counts):.2f}")
    lines.append(f"    Sessions with >0: {sum(1 for x in long_resp_counts if x > 0):,} ({sum(1 for x in long_resp_counts if x > 0)/n*100:.1f}%)")
    
    lines.append(f"\n  Short responses (<30 chars) (total):")
    lines.append(f"    Sum: {sum(short_resp_counts):,}")
    lines.append(f"    Mean: {statistics.mean(short_resp_counts):.2f}")
    lines.append(f"    Sessions with >0: {sum(1 for x in short_resp_counts if x > 0):,} ({sum(1 for x in short_resp_counts if x > 0)/n*100:.1f}%)")
    
    # ===== 2. UNCERTAINTY INDICATOR ANALYSIS =====
    lines.append("\n" + "=" * 80)
    lines.append("2. UNCERTAINTY INDICATOR ANALYSIS")
    lines.append("=" * 80)
    
    # Distribution
    unc_dist = Counter()
    for x in uncertainty_counts:
        if x == 0:
            unc_dist['0'] += 1
        elif x <= 2:
            unc_dist['1-2'] += 1
        elif x <= 5:
            unc_dist['3-5'] += 1
        elif x <= 10:
            unc_dist['6-10'] += 1
        elif x <= 20:
            unc_dist['11-20'] += 1
        else:
            unc_dist['21+'] += 1
    
    lines.append(f"\n  Distribution of uncertainty counts per session:")
    for bucket, count in sorted(unc_dist.items()):
        bar = '#' * int(count / (n / 100))
        lines.append(f"    {bucket:>6}: {count:>6,} ({count/n*100:5.1f}%) {bar}")
    
    # Top uncertainty sessions
    top_unc = sorted(results, key=lambda r: r['content_quality']['uncertainty_count'], reverse=True)[:10]
    lines.append(f"\n  Top 10 sessions by uncertainty count:")
    lines.append(f"    {'File':<45} {'Uncertainty':>10} {'Confidence':>10} {'Health':<10}")
    lines.append(f"    {'-'*45} {'-'*10} {'-'*10} {'-'*10}")
    for r in top_unc:
        bn = r['_basename']
        if len(bn) > 44:
            bn = '...' + bn[-41:]
        cq = r['content_quality']
        lines.append(f"    {bn:<45} {cq['uncertainty_count']:>10} {cq['confidence_count']:>10} {r['summary']['health']:<10}")
    
    # Uncertainty ratio (uncertainty / (uncertainty + confidence))
    unc_ratios = []
    for r in results:
        u = r['content_quality']['uncertainty_count']
        c = r['content_quality']['confidence_count']
        if u + c > 0:
            unc_ratios.append(u / (u + c))
    
    lines.append(f"\n  Uncertainty ratio (uncertainty / (uncertainty + confidence)):")
    if unc_ratios:
        lines.append(f"    Mean: {statistics.mean(unc_ratios):.3f}")
        lines.append(f"    Median: {statistics.median(unc_ratios):.3f}")
        lines.append(f"    Std Dev: {statistics.stdev(unc_ratios) if len(unc_ratios) > 1 else 0:.3f}")
        lines.append(f"    Sessions with ratio > 0.7: {sum(1 for x in unc_ratios if x > 0.7):,} ({sum(1 for x in unc_ratios if x > 0.7)/len(unc_ratios)*100:.1f}%)")
        lines.append(f"    Sessions with ratio < 0.1: {sum(1 for x in unc_ratios if x < 0.1):,} ({sum(1 for x in unc_ratios if x < 0.1)/len(unc_ratios)*100:.1f}%)")
    
    # ===== 3. CONFIDENCE INDICATOR ANALYSIS =====
    lines.append("\n" + "=" * 80)
    lines.append("3. CONFIDENCE INDICATOR ANALYSIS")
    lines.append("=" * 80)
    
    conf_dist = Counter()
    for x in confidence_counts:
        if x == 0:
            conf_dist['0'] += 1
        elif x <= 2:
            conf_dist['1-2'] += 1
        elif x <= 5:
            conf_dist['3-5'] += 1
        elif x <= 10:
            conf_dist['6-10'] += 1
        elif x <= 20:
            conf_dist['11-20'] += 1
        else:
            conf_dist['21+'] += 1
    
    lines.append(f"\n  Distribution of confidence counts per session:")
    for bucket, count in sorted(conf_dist.items()):
        bar = '#' * int(count / (n / 100))
        lines.append(f"    {bucket:>6}: {count:>6,} ({count/n*100:5.1f}%) {bar}")
    
    top_conf = sorted(results, key=lambda r: r['content_quality']['confidence_count'], reverse=True)[:10]
    lines.append(f"\n  Top 10 sessions by confidence count:")
    lines.append(f"    {'File':<45} {'Confidence':>10} {'Uncertainty':>12} {'Health':<10}")
    lines.append(f"    {'-'*45} {'-'*10} {'-'*12} {'-'*10}")
    for r in top_conf:
        bn = r['_basename']
        if len(bn) > 44:
            bn = '...' + bn[-41:]
        cq = r['content_quality']
        lines.append(f"    {bn:<45} {cq['confidence_count']:>10} {cq['uncertainty_count']:>12} {r['summary']['health']:<10}")
    
    # ===== 4. SELF-CORRECTION FREQUENCY ANALYSIS =====
    lines.append("\n" + "=" * 80)
    lines.append("4. SELF-CORRECTION FREQUENCY ANALYSIS")
    lines.append("=" * 80)
    
    sc_dist = Counter()
    for x in self_correction_counts:
        if x == 0:
            sc_dist['0'] += 1
        elif x <= 2:
            sc_dist['1-2'] += 1
        elif x <= 5:
            sc_dist['3-5'] += 1
        elif x <= 10:
            sc_dist['6-10'] += 1
        else:
            sc_dist['11+'] += 1
    
    lines.append(f"\n  Distribution of self-correction counts per session:")
    for bucket, count in sorted(sc_dist.items()):
        bar = '#' * int(count / (n / 100))
        lines.append(f"    {bucket:>6}: {count:>6,} ({count/n*100:5.1f}%) {bar}")
    
    # Self-correction per assistant turn
    sc_per_turn = []
    for r in results:
        turns = r['conversation']['assistant_turns']
        sc = r['content_quality']['self_correction_count']
        if turns > 0:
            sc_per_turn.append(sc / turns)
    
    lines.append(f"\n  Self-corrections per assistant turn:")
    if sc_per_turn:
        lines.append(f"    Mean: {statistics.mean(sc_per_turn):.3f}")
        lines.append(f"    Median: {statistics.median(sc_per_turn):.3f}")
    
    # Sessions with high self-correction rate
    high_sc = sorted(results, key=lambda r: r['content_quality']['self_correction_count'], reverse=True)[:10]
    lines.append(f"\n  Top 10 sessions by self-correction count:")
    lines.append(f"    {'File':<45} {'Self-Corr':>9} {'Assist Turns':>12} {'Rate':>8}")
    lines.append(f"    {'-'*45} {'-'*9} {'-'*12} {'-'*8}")
    for r in high_sc:
        bn = r['_basename']
        if len(bn) > 44:
            bn = '...' + bn[-41:]
        cq = r['content_quality']
        turns = r['conversation']['assistant_turns']
        rate = cq['self_correction_count'] / turns if turns > 0 else 0
        lines.append(f"    {bn:<45} {cq['self_correction_count']:>9} {turns:>12} {rate:>8.3f}")
    
    # ===== 5. RESPONSE LENGTH DISTRIBUTIONS =====
    lines.append("\n" + "=" * 80)
    lines.append("5. RESPONSE LENGTH DISTRIBUTIONS")
    lines.append("=" * 80)
    
    avg_lengths = [r['conversation']['avg_assistant_length'] for r in results]
    max_lengths = [r['conversation']['max_assistant_length'] for r in results]
    min_lengths = [r['conversation']['min_assistant_length'] for r in results]
    
    lines.append(f"\n  Average assistant response length (chars):")
    lines.append(f"    Mean: {statistics.mean(avg_lengths):.0f}")
    lines.append(f"    Median: {statistics.median(avg_lengths):.0f}")
    lines.append(f"    Std Dev: {statistics.stdev(avg_lengths) if len(avg_lengths) > 1 else 0:.0f}")
    lines.append(f"    Min: {min(avg_lengths):.0f}")
    lines.append(f"    Max: {max(avg_lengths):.0f}")
    lines.append(f"    P5: {percentile(avg_lengths, 5):.0f}")
    lines.append(f"    P25: {percentile(avg_lengths, 25):.0f}")
    lines.append(f"    P75: {percentile(avg_lengths, 75):.0f}")
    lines.append(f"    P95: {percentile(avg_lengths, 95):.0f}")
    lines.append(f"    P99: {percentile(avg_lengths, 99):.0f}")
    
    lines.append(f"\n  Max assistant response length (chars):")
    lines.append(f"    Mean: {statistics.mean(max_lengths):.0f}")
    lines.append(f"    Median: {statistics.median(max_lengths):.0f}")
    lines.append(f"    Max: {max(max_lengths):.0f}")
    lines.append(f"    P99: {percentile(max_lengths, 99):.0f}")
    
    # Length distribution buckets
    length_buckets = Counter()
    for x in avg_lengths:
        if x < 100:
            length_buckets['<100'] += 1
        elif x < 500:
            length_buckets['100-500'] += 1
        elif x < 1000:
            length_buckets['500-1K'] += 1
        elif x < 2000:
            length_buckets['1K-2K'] += 1
        elif x < 5000:
            length_buckets['2K-5K'] += 1
        elif x < 10000:
            length_buckets['5K-10K'] += 1
        else:
            length_buckets['10K+'] += 1
    
    lines.append(f"\n  Average response length distribution:")
    for bucket, count in sorted(length_buckets.items()):
        bar = '#' * int(count / (n / 100))
        lines.append(f"    {bucket:>8}: {count:>6,} ({count/n*100:5.1f}%) {bar}")
    
    # ===== 6. TIME PATTERNS =====
    lines.append("\n" + "=" * 80)
    lines.append("6. TIME PATTERNS (SESSION DURATION & ENTRY GAPS)")
    lines.append("=" * 80)
    
    durations = [r['time']['session_duration_seconds'] for r in results if r['time']['session_duration_seconds'] is not None]
    avg_gaps = [r['time']['avg_entry_gap_seconds'] for r in results]
    max_gaps = [r['time']['max_entry_gap_seconds'] for r in results]
    
    lines.append(f"\n  Session duration (seconds):")
    if durations:
        lines.append(f"    Count: {len(durations):,}")
        lines.append(f"    Mean: {statistics.mean(durations):.1f}s ({statistics.mean(durations)/60:.1f}min)")
        lines.append(f"    Median: {statistics.median(durations):.1f}s ({statistics.median(durations)/60:.1f}min)")
        lines.append(f"    Std Dev: {statistics.stdev(durations):.1f}s")
        lines.append(f"    Min: {min(durations):.1f}s")
        lines.append(f"    Max: {max(durations):.1f}s ({max(durations)/3600:.1f}h)")
        lines.append(f"    P5: {percentile(durations, 5):.1f}s")
        lines.append(f"    P25: {percentile(durations, 25):.1f}s")
        lines.append(f"    P75: {percentile(durations, 75):.1f}s")
        lines.append(f"    P95: {percentile(durations, 95):.1f}s")
        lines.append(f"    P99: {percentile(durations, 99):.1f}s")
    
    # Duration distribution
    dur_buckets = Counter()
    for x in durations:
        if x < 10:
            dur_buckets['<10s'] += 1
        elif x < 30:
            dur_buckets['10-30s'] += 1
        elif x < 60:
            dur_buckets['30-60s'] += 1
        elif x < 300:
            dur_buckets['1-5min'] += 1
        elif x < 600:
            dur_buckets['5-10min'] += 1
        elif x < 1800:
            dur_buckets['10-30min'] += 1
        elif x < 3600:
            dur_buckets['30-60min'] += 1
        else:
            dur_buckets['60min+'] += 1
    
    lines.append(f"\n  Session duration distribution:")
    for bucket, count in sorted(dur_buckets.items()):
        bar = '#' * int(count / (n / 100))
        lines.append(f"    {bucket:>10}: {count:>6,} ({count/n*100:5.1f}%) {bar}")
    
    lines.append(f"\n  Average entry gap (seconds):")
    if avg_gaps:
        lines.append(f"    Mean: {statistics.mean(avg_gaps):.1f}s")
        lines.append(f"    Median: {statistics.median(avg_gaps):.1f}s")
        lines.append(f"    Max: {max(avg_gaps):.1f}s")
    
    lines.append(f"\n  Max entry gap (seconds):")
    if max_gaps:
        lines.append(f"    Mean: {statistics.mean(max_gaps):.1f}s")
        lines.append(f"    Median: {statistics.median(max_gaps):.1f}s")
        lines.append(f"    Max: {max(max_gaps):.1f}s ({max(max_gaps)/3600:.1f}h)")
    
    # ===== 7. HIGH UNCERTAINTY + LOW SUCCESS RATE =====
    lines.append("\n" + "=" * 80)
    lines.append("7. HIGH UNCERTAINTY + LOW SUCCESS RATE SESSIONS")
    lines.append("=" * 80)
    
    # Define: high uncertainty = top quartile, low success = below median tool success rate
    unc_q1 = percentile(uncertainty_counts, 25)
    tool_success_rates = [r['summary']['tool_success_rate'] for r in results]
    median_success = statistics.median(tool_success_rates) if tool_success_rates else 50
    
    high_unc_low_success = [
        r for r in results
        if r['content_quality']['uncertainty_count'] > unc_q1
        and r['summary']['tool_success_rate'] < median_success
        and r['conversation']['assistant_turns'] > 0
    ]
    high_unc_low_success.sort(key=lambda r: r['content_quality']['uncertainty_count'], reverse=True)
    
    lines.append(f"\n  Criteria: Uncertainty > {unc_q1:.0f} (Q1) AND Tool success < {median_success:.1f}% (median)")
    lines.append(f"  Matching sessions: {len(high_unc_low_success):,}")
    
    if high_unc_low_success:
        lines.append(f"\n  Top 15 by uncertainty count:")
        lines.append(f"    {'File':<45} {'Uncertainty':>10} {'Success%':>8} {'Health':<10} {'Errors':>6}")
        lines.append(f"    {'-'*45} {'-'*10} {'-'*8} {'-'*10} {'-'*6}")
        for r in high_unc_low_success[:15]:
            bn = r['_basename']
            if len(bn) > 44:
                bn = '...' + bn[-41:]
            cq = r['content_quality']
            lines.append(f"    {bn:<45} {cq['uncertainty_count']:>10} {r['summary']['tool_success_rate']:>7.1f}% {r['summary']['health']:<10} {r['errors']['total_count']:>6}")
    
    # ===== 8. HIGH CONFIDENCE + HIGH SUCCESS RATE =====
    lines.append("\n" + "=" * 80)
    lines.append("8. HIGH CONFIDENCE + HIGH SUCCESS RATE SESSIONS")
    lines.append("=" * 80)
    
    conf_q3 = percentile(confidence_counts, 75)
    
    high_conf_high_success = [
        r for r in results
        if r['content_quality']['confidence_count'] > conf_q3
        and r['summary']['tool_success_rate'] > 80
        and r['conversation']['assistant_turns'] > 0
    ]
    high_conf_high_success.sort(key=lambda r: r['content_quality']['confidence_count'], reverse=True)
    
    lines.append(f"\n  Criteria: Confidence > {conf_q3:.0f} (Q3) AND Tool success > 80%")
    lines.append(f"  Matching sessions: {len(high_conf_high_success):,}")
    
    if high_conf_high_success:
        lines.append(f"\n  Top 15 by confidence count:")
        lines.append(f"    {'File':<45} {'Confidence':>10} {'Success%':>8} {'Health':<10} {'Errors':>6}")
        lines.append(f"    {'-'*45} {'-'*10} {'-'*8} {'-'*10} {'-'*6}")
        for r in high_conf_high_success[:15]:
            bn = r['_basename']
            if len(bn) > 44:
                bn = '...' + bn[-41:]
            cq = r['content_quality']
            lines.append(f"    {bn:<45} {cq['confidence_count']:>10} {r['summary']['tool_success_rate']:>7.1f}% {r['summary']['health']:<10} {r['errors']['total_count']:>6}")
    
    # ===== 9. RESPONSE LENGTH vs QUALITY CORRELATION =====
    lines.append("\n" + "=" * 80)
    lines.append("9. RESPONSE LENGTH vs QUALITY CORRELATION")
    lines.append("=" * 80)
    
    # Correlate avg response length with:
    # - error count
    # - uncertainty count
    # - confidence count
    # - health
    
    error_counts = [r['errors']['total_count'] for r in results]
    
    def pearson_corr(x, y):
        if len(x) < 2:
            return 0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5
        if std_x == 0 or std_y == 0:
            return 0
        return cov / (std_x * std_y)
    
    corr_length_errors = pearson_corr(avg_lengths, error_counts)
    corr_length_uncertainty = pearson_corr(avg_lengths, uncertainty_counts)
    corr_length_confidence = pearson_corr(avg_lengths, confidence_counts)
    corr_length_selfcorr = pearson_corr(avg_lengths, self_correction_counts)
    
    # Health as numeric: healthy=2, degraded=1, unhealthy=0
    health_numeric = {'healthy': 2, 'degraded': 1, 'unhealthy': 0}
    health_vals = [health_numeric.get(r['summary']['health'], 1) for r in results]
    corr_length_health = pearson_corr(avg_lengths, health_vals)
    
    lines.append(f"\n  Pearson correlation coefficients:")
    lines.append(f"    Response length vs Error count:      {corr_length_errors:+.4f}")
    lines.append(f"    Response length vs Uncertainty count:  {corr_length_uncertainty:+.4f}")
    lines.append(f"    Response length vs Confidence count:   {corr_length_confidence:+.4f}")
    lines.append(f"    Response length vs Self-correction:    {corr_length_selfcorr:+.4f}")
    lines.append(f"    Response length vs Health (0-2):       {corr_length_health:+.4f}")
    
    # Group by length buckets and show avg quality metrics
    lines.append(f"\n  Quality metrics by response length bucket:")
    lines.append(f"    {'Bucket':<12} {'Sessions':>8} {'Avg Errors':>10} {'Avg Uncert':>10} {'Avg Confid':>10} {'Health%':>8}")
    lines.append(f"    {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    
    length_groups = defaultdict(list)
    for r in results:
        avg_len = r['conversation']['avg_assistant_length']
        if avg_len < 100:
            bucket = '<100'
        elif avg_len < 500:
            bucket = '100-500'
        elif avg_len < 1000:
            bucket = '500-1K'
        elif avg_len < 2000:
            bucket = '1K-2K'
        elif avg_len < 5000:
            bucket = '2K-5K'
        elif avg_len < 10000:
            bucket = '5K-10K'
        else:
            bucket = '10K+'
        length_groups[bucket].append(r)
    
    for bucket in sorted(length_groups.keys()):
        group = length_groups[bucket]
        gn = len(group)
        avg_err = statistics.mean([r['errors']['total_count'] for r in group])
        avg_unc = statistics.mean([r['content_quality']['uncertainty_count'] for r in group])
        avg_conf = statistics.mean([r['content_quality']['confidence_count'] for r in group])
        health_pct = sum(1 for r in group if r['summary']['health'] == 'healthy') / gn * 100
        lines.append(f"    {bucket:<12} {gn:>8,} {avg_err:>10.2f} {avg_unc:>10.2f} {avg_conf:>10.2f} {health_pct:>7.1f}%")
    
    # ===== 10. UNUSUALLY LONG/SHORT RESPONSE SESSIONS =====
    lines.append("\n" + "=" * 80)
    lines.append("10. UNUSUALLY LONG/SHORT RESPONSE SESSIONS (OUTLIERS)")
    lines.append("=" * 80)
    
    # Outliers: beyond 1.5 * IQR
    q1_len = percentile(avg_lengths, 25)
    q3_len = percentile(avg_lengths, 75)
    iqr_len = q3_len - q1_len
    lower_outlier = q1_len - 1.5 * iqr_len
    upper_outlier = q3_len + 1.5 * iqr_len
    
    lines.append(f"\n  IQR analysis for avg response length:")
    lines.append(f"    Q1: {q1_len:.0f}  Q3: {q3_len:.0f}  IQR: {iqr_len:.0f}")
    lines.append(f"    Lower fence: {lower_outlier:.0f}  Upper fence: {upper_outlier:.0f}")
    
    short_outliers = [r for r in results if avg_lengths[results.index(r)] < lower_outlier and r['conversation']['assistant_turns'] > 0]
    long_outliers = [r for r in results if avg_lengths[results.index(r)] > upper_outlier and r['conversation']['assistant_turns'] > 0]
    
    lines.append(f"\n  Short outliers ({len(short_outliers):,} sessions, avg < {lower_outlier:.0f} chars):")
    if short_outliers:
        # Show by avg length ascending
        short_outliers.sort(key=lambda r: r['conversation']['avg_assistant_length'])
        lines.append(f"    {'File':<45} {'AvgLen':>8} {'MaxLen':>8} {'Assist':>6} {'Health':<10}")
        lines.append(f"    {'-'*45} {'-'*8} {'-'*8} {'-'*6} {'-'*10}")
        for r in short_outliers[:20]:
            bn = r['_basename']
            if len(bn) > 44:
                bn = '...' + bn[-41:]
            conv = r['conversation']
            lines.append(f"    {bn:<45} {conv['avg_assistant_length']:>8.0f} {conv['max_assistant_length']:>8.0f} {conv['assistant_turns']:>6} {r['summary']['health']:<10}")
    
    lines.append(f"\n  Long outliers ({len(long_outliers):,} sessions, avg > {upper_outlier:.0f} chars):")
    if long_outliers:
        long_outliers.sort(key=lambda r: r['conversation']['avg_assistant_length'], reverse=True)
        lines.append(f"    {'File':<45} {'AvgLen':>8} {'MaxLen':>8} {'Assist':>6} {'Health':<10}")
        lines.append(f"    {'-'*45} {'-'*8} {'-'*8} {'-'*6} {'-'*10}")
        for r in long_outliers[:20]:
            bn = r['_basename']
            if len(bn) > 44:
                bn = '...' + bn[-41:]
            conv = r['conversation']
            lines.append(f"    {bn:<45} {conv['avg_assistant_length']:>8.0f} {conv['max_assistant_length']:>8.0f} {conv['assistant_turns']:>6} {r['summary']['health']:<10}")
    
    # ===== 11. CACHE WARNING PATTERNS =====
    lines.append("\n" + "=" * 80)
    lines.append("11. CACHE WARNING PATTERNS & SESSION QUALITY")
    lines.append("=" * 80)
    
    # Console warnings (cache warnings)
    warning_counts = [r['console_warnings']['count'] for r in results]
    sessions_with_warnings = [r for r in results if r['console_warnings']['count'] > 0]
    
    lines.append(f"\n  Console warnings overview:")
    lines.append(f"    Total warnings across all sessions: {sum(warning_counts):,}")
    lines.append(f"    Sessions with warnings: {len(sessions_with_warnings):,} ({len(sessions_with_warnings)/n*100:.1f}%)")
    lines.append(f"    Mean warnings per session (all): {statistics.mean(warning_counts):.2f}")
    lines.append(f"    Mean warnings per session (with warnings): {statistics.mean([w for w in warning_counts if w > 0]):.2f}")
    
    # Compare sessions with vs without warnings
    with_warn = [r for r in results if r['console_warnings']['count'] > 0]
    without_warn = [r for r in results if r['console_warnings']['count'] == 0]
    
    lines.append(f"\n  Sessions WITH warnings ({len(with_warn):,}) vs WITHOUT ({len(without_warn):,}):")
    
    if with_warn:
        avg_err_warn = statistics.mean([r['errors']['total_count'] for r in with_warn])
        avg_err_nowarn = statistics.mean([r['errors']['total_count'] for r in without_warn]) if without_warn else 0
        avg_unc_warn = statistics.mean([r['content_quality']['uncertainty_count'] for r in with_warn])
        avg_unc_nowarn = statistics.mean([r['content_quality']['uncertainty_count'] for r in without_warn]) if without_warn else 0
        avg_conf_warn = statistics.mean([r['content_quality']['confidence_count'] for r in with_warn])
        avg_conf_nowarn = statistics.mean([r['content_quality']['confidence_count'] for r in without_warn]) if without_warn else 0
        avg_len_warn = statistics.mean([r['conversation']['avg_assistant_length'] for r in with_warn])
        avg_len_nowarn = statistics.mean([r['conversation']['avg_assistant_length'] for r in without_warn]) if without_warn else 0
        avg_dur_warn = statistics.mean([r['time']['session_duration_seconds'] for r in with_warn if r['time']['session_duration_seconds']]) if with_warn else 0
        avg_dur_nowarn = statistics.mean([r['time']['session_duration_seconds'] for r in without_warn if r['time']['session_duration_seconds']]) if without_warn else 0
        
        health_warn = sum(1 for r in with_warn if r['summary']['health'] == 'healthy') / len(with_warn) * 100
        health_nowarn = sum(1 for r in without_warn if r['summary']['health'] == 'healthy') / len(without_warn) * 100 if without_warn else 0
        
        lines.append(f"    {'Metric':<30} {'With Warnings':>14} {'Without Warnings':>16} {'Diff':>10}")
        lines.append(f"    {'-'*30} {'-'*14} {'-'*16} {'-'*10}")
        lines.append(f"    {'Avg Errors':<30} {avg_err_warn:>14.2f} {avg_err_nowarn:>16.2f} {avg_err_warn-avg_err_nowarn:>+10.2f}")
        lines.append(f"    {'Avg Uncertainty':<30} {avg_unc_warn:>14.2f} {avg_unc_nowarn:>16.2f} {avg_unc_warn-avg_unc_nowarn:>+10.2f}")
        lines.append(f"    {'Avg Confidence':<30} {avg_conf_warn:>14.2f} {avg_conf_nowarn:>16.2f} {avg_conf_warn-avg_conf_nowarn:>+10.2f}")
        lines.append(f"    {'Avg Response Length':<30} {avg_len_warn:>14.0f} {avg_len_nowarn:>16.0f} {avg_len_warn-avg_len_nowarn:>+10.0f}")
        lines.append(f"    {'Avg Duration (s)':<30} {avg_dur_warn:>14.1f} {avg_dur_nowarn:>16.1f} {avg_dur_warn-avg_dur_nowarn:>+10.1f}")
        lines.append(f"    {'Healthy Rate':<30} {health_warn:>13.1f}% {health_nowarn:>15.1f}% {health_warn-health_nowarn:>+9.1f}%")
    
    # Top warning sessions
    top_warn = sorted(results, key=lambda r: r['console_warnings']['count'], reverse=True)[:15]
    lines.append(f"\n  Top 15 sessions by console warning count:")
    lines.append(f"    {'File':<45} {'Warnings':>8} {'Errors':>6} {'Health':<10} {'Duration':>10}")
    lines.append(f"    {'-'*45} {'-'*8} {'-'*6} {'-'*10} {'-'*10}")
    for r in top_warn:
        bn = r['_basename']
        if len(bn) > 44:
            bn = '...' + bn[-41:]
        cw = r['console_warnings']
        dur = r['time']['session_duration_seconds']
        dur_str = f"{dur/60:.1f}m" if dur and dur > 60 else f"{dur:.0f}s" if dur else "N/A"
        lines.append(f"    {bn:<45} {cw['count']:>8} {r['errors']['total_count']:>6} {r['summary']['health']:<10} {dur_str:>10}")
    
    # ===== SUMMARY =====
    lines.append("\n" + "=" * 80)
    lines.append("SUMMARY & KEY INSIGHTS")
    lines.append("=" * 80)
    
    # Health distribution
    health_dist = Counter(r['summary']['health'] for r in results)
    lines.append(f"\n  Health distribution:")
    for h, c in health_dist.most_common():
        lines.append(f"    {h:<12}: {c:>6,} ({c/n*100:.1f}%)")
    
    # Efficiency distribution
    eff_dist = Counter(r['summary']['efficiency'] for r in results)
    lines.append(f"\n  Efficiency distribution:")
    for e, c in eff_dist.most_common():
        lines.append(f"    {e:<12}: {c:>6,} ({c/n*100:.1f}%)")
    
    # Key findings
    lines.append(f"\n  KEY FINDINGS:")
    lines.append(f"    1. {n:,} sessions analyzed across all tau audit files")
    lines.append(f"    2. Uncertainty indicators: {sum(uncertainty_counts):,} total ({statistics.mean(uncertainty_counts):.2f} per session avg)")
    lines.append(f"    3. Confidence indicators: {sum(confidence_counts):,} total ({statistics.mean(confidence_counts):.2f} per session avg)")
    lines.append(f"    4. Self-corrections: {sum(self_correction_counts):,} total ({statistics.mean(self_correction_counts):.2f} per session avg)")
    lines.append(f"    5. Average response length: {statistics.mean(avg_lengths):.0f} chars (median: {statistics.median(avg_lengths):.0f})")
    lines.append(f"    6. Session duration: {statistics.median(durations):.1f}s median, {max(durations)/3600:.1f}h max")
    lines.append(f"    7. High uncertainty + low success: {len(high_unc_low_success):,} sessions")
    lines.append(f"    8. High confidence + high success: {len(high_conf_high_success):,} sessions")
    lines.append(f"    9. Response length-health correlation: {corr_length_health:+.4f}")
    lines.append(f"    10. Response outliers: {len(short_outliers):,} short, {len(long_outliers):,} long")
    lines.append(f"    11. Cache warnings: {sum(warning_counts):,} total in {len(sessions_with_warnings):,} sessions")
    
    # Edge cases
    lines.append(f"\n  EDGE CASES:")
    neg_dur = sum(1 for r in results if r['edge_cases']['negative_duration'])
    ghost = sum(1 for r in results if r['edge_cases']['ghost_session'])
    llm_before = sum(1 for r in results if r['edge_cases']['llm_before_session_start'])
    incomplete = sum(1 for r in results if r['edge_cases']['incomplete_operations'])
    lines.append(f"    Negative duration: {neg_dur:,}")
    lines.append(f"    Ghost sessions: {ghost:,}")
    lines.append(f"    LLM before session start: {llm_before:,}")
    lines.append(f"    Incomplete operations: {incomplete:,}")
    
    lines.append("\n" + "=" * 80)
    
    return '\n'.join(lines)


def main():
    print("Finding audit files...", file=sys.stderr)
    files = find_all_audit_files(AUDIT_DIR)
    print(f"Found {len(files):,} audit files", file=sys.stderr)
    
    print("Analyzing all files (this may take a few minutes)...", file=sys.stderr)
    results = analyze_all_files(files, batch_size=500)
    
    print("Generating comprehensive report...", file=sys.stderr)
    report = generate_report(results)
    
    # Output report
    print(report)
    
    # Save to file
    output_path = "$HOME/tau-dev1/content_quality_analysis.txt"
    with open(output_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
