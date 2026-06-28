---
name: docker
description: Docker container management — build, run, compose, SWE-bench testbeds. Docker, container, docker-compose, build image, run container, testbed, SWE-bench environment (also load: background, bug_investigation)
category: development
keywords: docker, container, docker-compose, build image, run container, testbed, SWE-bench, environment, up, down, logs
---

# Docker Management

## When
"docker container", "docker-compose", "build image", "run container", "testbed", "SWE-bench environment", "docker build"

## Common Patterns

### Run Container
```bash
docker compose -f docker-compose.yaml up -d
docker compose -f docker-compose.yaml logs -f
docker compose -f docker-compose.yaml down
```

### Build Image
```bash
docker build -t image_name .
docker build --no-cache -t image_name .  # Force rebuild
```

### Interactive Access
```bash
docker exec -it <container> bash
docker logs <container>
```

## SWE-bench Patterns
- Container = isolated testbed with project code
- Mount tau agent: `./tau` folder inside container
- Run fix agent: `tau.py` inside container
- Eval: re-run project tests, compare patch

## Gotchas
- Container working dir ≠ host working dir
- Use absolute paths inside containers
- `docker compose down` before reconfiguring
- Port conflicts: check `docker ps` before starting
- Image caching: `--no-cache` for fresh builds

## Related Skills
- `swe_bench` — SWE-bench workflow
- `background` — run containers in background
- `shell_scripting` — automate docker workflows
- `bug_investigation` — debug container issues
- `context_management` — delegate container tasks

## Helper
```bash
python3 skills/docker/docker_helper.py        # Status
python3 skills/docker/docker_helper.py up      # Start
python3 skills/docker/docker_helper.py down    # Stop
python3 skills/docker/docker_helper.py logs    # Tail logs
```
