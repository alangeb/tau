#!/usr/bin/env python3
"""Docker helper — common docker-compose operations."""
import subprocess, sys, json

def run(cmd, capture=True):
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return r

def status():
    r = run("docker compose -f docker-compose.yaml ps --format json 2>/dev/null")
    if r.returncode == 0:
        try:
            containers = json.loads(r.stdout.strip())
            for c in containers:
                print(f"  {c.get('Name', '?')}: {c.get('State', '?')}")
        except:
            print(r.stdout)
    else:
        print("No docker-compose.yaml found or compose not available")

def quick_up():
    print("Starting containers...")
    r = run("docker compose -f docker-compose.yaml up -d")
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)

def quick_down():
    print("Stopping containers...")
    r = run("docker compose -f docker-compose.yaml down")
    print(r.stdout)

def main():
    if len(sys.argv) < 2:
        status()
        return 0
    
    cmd = sys.argv[1]
    if cmd == "up":
        quick_up()
    elif cmd == "down":
        quick_down()
    elif cmd == "logs":
        r = run("docker compose -f docker-compose.yaml logs --tail=50", capture=False)
    elif cmd == "ps":
        status()
    else:
        print(f"Unknown: {cmd}. Use: up, down, logs, ps")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
