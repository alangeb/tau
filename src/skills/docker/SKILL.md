---
category: development
description: "Run container, docker compose, build image, exec into container, view logs, manage docker networks and volumes (also load: background, shell_scripting, dependency_management)"
keywords: docker, container, docker compose, build image, docker exec, docker logs, container management, docker run, deploy container
name: docker
---

# Docker Management

## When
"docker container", "docker-compose", "build image", "run container", "testbed", "SWE-bench environment"

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

## Helper
```bash
python3 skills/docker/docker_helper.py        # Status
python3 skills/docker/docker_helper.py up      # Start
python3 skills/docker/docker_helper.py down    # Stop
python3 skills/docker/docker_helper.py logs    # Tail logs
```

## Related Skills
- `background` — run containers in background
- `bug_investigation` — debug container issues
- `context_management` — delegate container tasks
- `dependency_management` — venv setup and pip installs
- `shell_scripting` — automate docker workflows
- `swe_bench` — SWE-bench workflow
