---
description: "Check server health and status — circuit breaker state, API latency, error rates, failure counts, dashboard (also load: info, tau_audit, background)"
keywords: circuit breaker state, API response latency, failure rate percentage, consecutive failure count, service availability dashboard
name: health
category: monitoring
---

# Health — Server Health Monitoring

## When
"check server health", "API status", "latency check", "error rates", "health dashboard", "circuit state"

## Helper
```bash
python3 skills/health/health_check.py status   # Dashboard view
python3 skills/health/health_check.py check    # Connection test
python3 skills/health/health_check.py metrics  # Raw metrics
```

## Circuit States
| State | Meaning |
|-------|---------|
| CLOSED | Normal, accepting requests |
| HALF_OPEN | Testing recovery, limited requests |
| OPEN | Failing, requests blocked |

## Interpreting Metrics
- **Normal**: Circuit CLOSED, failure rate < 5%, consecutive failures: 0
- **Degraded**: Circuit HALF_OPEN, failure rate 5-20%, elevated latency
- **Failing**: Circuit OPEN, failure rate > 20%, high consecutive failures

## Related Skills
- `background` — run health checks in background
- `performance` — performance profiling and optimization
- `bug_investigation` — diagnose server issues
- `tau_audit` — comprehensive system audit
