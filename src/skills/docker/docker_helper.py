#!/usr/bin/env python3
"""Docker helper — common docker-compose operations with status, logs, and health checks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

COMPOSE_FILE = "docker-compose.yaml"


def run(cmd: str, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, shell=True, capture_output=capture, text=True)


def status() -> list[dict]:
    """Get container status from docker-compose.
    
    Returns list of {name, state, service} dicts.
    """
    r = run(f"docker compose -f {COMPOSE_FILE} ps --format json 2>/dev/null")
    if r.returncode == 0 and r.stdout.strip():
        try:
            containers = json.loads(r.stdout.strip())
            result = []
            for c in containers:
                result.append({
                    "name": c.get("Name", "?"),
                    "state": c.get("State", "?"),
                    "service": c.get("Service", "?"),
                })
                print(f"  {c.get('Name', '?')}: {c.get('State', '?')}")
            return result
        except json.JSONDecodeError:
            print(r.stdout)
            return []
    else:
        print("No docker-compose.yaml found or compose not available")
        return []


def quick_up() -> bool:
    """Start containers via docker-compose up -d. Returns True on success."""
    print("Starting containers...")
    r = run(f"docker compose -f {COMPOSE_FILE} up -d")
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)
    return r.returncode == 0


def quick_down() -> bool:
    """Stop containers via docker-compose down. Returns True on success."""
    print("Stopping containers...")
    r = run(f"docker compose -f {COMPOSE_FILE} down")
    print(r.stdout)
    return r.returncode == 0


def tail_logs(service: str = "", lines: int = 50) -> None:
    """Tail logs from docker-compose containers.
    
    Args:
        service: Service name (empty = all services)
        lines: Number of lines to show
    """
    svc = f" {service}" if service else ""
    run(f"docker compose -f {COMPOSE_FILE} logs --tail={lines}{svc}", capture=False)


def health_check() -> dict:
    """Check health of all containers.
    
    Returns dict with total, healthy, unhealthy, and unknown counts.
    """
    containers = status()
    health = {"total": len(containers), "healthy": 0, "unhealthy": 0, "unknown": 0}
    for c in containers:
        state = c.get("state", "").lower()
        if "running" in state:
            health["healthy"] += 1
        elif "exited" in state or "dead" in state:
            health["unhealthy"] += 1
        else:
            health["unknown"] += 1
    return health


def main() -> int:
    if len(sys.argv) < 2:
        status()
        return 0
    
    cmd = sys.argv[1]
    if cmd == "up":
        return 0 if quick_up() else 1
    elif cmd == "down":
        return 0 if quick_down() else 1
    elif cmd == "logs":
        service = sys.argv[2] if len(sys.argv) > 2 else ""
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        tail_logs(service, lines)
        return 0
    elif cmd == "ps":
        status()
        return 0
    elif cmd == "health":
        h = health_check()
        print(json.dumps(h, indent=2))
        return 0
    else:
        print(f"Unknown: {cmd}. Use: up, down, logs, ps, health")
        return 1


if __name__ == "__main__":
    sys.exit(main())
