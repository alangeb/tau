"""A2A (Agent-to-Agent) interface for inter-agent communication via Unix domain sockets.

Agents communicate through ``/tmp/taua2a-{PID}.sock`` using JSON messages.

Protocol:
- Agent card request (sync): ``{"type": "agent_card"}`` → agent metadata
- Status request (sync): ``{"type": "status"}`` → running/idle info
- Query request (async): ``{"type": "query", "id": <uuid>, "query": <prompt>}``
  → ``{"type": "queued", "id": <request_id>}`` → ``{"type": "response", "id": <request_id>, "response": <result>}``

Key components:
- A2AServer: Handles incoming connections (agent_card, status, query) in a daemon thread
- connect_to_agent, get_agent_card, query_agent, list_agents: Client utilities
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

from agent_console import (
    a2a_cli_error,
    agent_a2a_response,
    agent_card_json,
    agent_status_message,
    agents_json,
    agents_table_header,
    agents_table_row,
)
from agent_context_utils import read_context_metadata_for_a2a
from agent_models import InputMessage

__all__ = [
    "A2AServer",
    "Supervisor",
    "connect_to_agent",
    "get_agent_card",
    "list_agents",
    "query_agent",
    "a2a_cli_mode",
]

# ── Constants ──────────────────────────────────────────────────────────────

DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_ACK_TIMEOUT = 5
DEFAULT_POLL_INTERVAL = 0.1
SOCKET_BUFFER = 4096

# Heartbeat protocol: server sends periodic heartbeats while processing.
# Client considers connection alive as long as heartbeats arrive within
# HEARTBEAT_IDLE_TIMEOUT seconds. No wall-clock timeout — slow agents are fine.
HEARTBEAT_INTERVAL = 5.0          # Server sends heartbeat every N seconds
HEARTBEAT_IDLE_TIMEOUT = 30.0     # Client gives up if no heartbeat for N seconds

# Supervision protocol: supervisor maintains persistent connection to child.
SUPERVISE_CONNECT_TIMEOUT = 10.0  # Timeout for supervisor connect
SUPERVISE_ACK_TIMEOUT = 10.0      # Timeout for command acknowledgment


# ── Client utilities ──────────────────────────────────────────────────────


def _verify_socket(sock_path: str) -> bool:
    """Check if a socket file exists and accepts connections."""
    if not Path(sock_path).exists():
        return False
    try:
        test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        test_sock.settimeout(1)
        test_sock.connect(sock_path)
        test_sock.close()
        return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


def _make_connection(sock_path: str, timeout: float) -> socket.socket:
    """Create and connect a Unix domain socket with the given timeout."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    client.connect(sock_path)
    return client


def connect_to_agent(pid: int, timeout: float = DEFAULT_CONNECT_TIMEOUT) -> socket.socket:
    """Connect to an agent by PID via its Unix socket."""
    sock_path = f"/tmp/taua2a-{pid}.sock"

    if not Path(sock_path).exists():
        raise FileNotFoundError(f"Socket not found: {sock_path}")

    if not _verify_socket(sock_path):
        raise ConnectionError(f"Agent {pid} not responding (socket may be stale)")

    return _make_connection(sock_path, timeout)


def _decode_json_stream(client: socket.socket, timeout: float, initial_buffer: str = ""):
    """Decode one JSON object from a socket stream.

    Reads until a complete JSON object is available, then returns
    ``(obj, remainder_buffer)``.
    """
    client.settimeout(timeout)
    decoder = json.JSONDecoder()
    buffer = initial_buffer

    while True:
        try:
            chunk = client.recv(SOCKET_BUFFER).decode()
            if not chunk:
                break
            buffer += chunk
            while buffer:
                try:
                    obj, idx = decoder.raw_decode(buffer)
                    return obj, buffer[idx:]
                except json.JSONDecodeError:
                    break
        except TimeoutError as exc:
            raise TimeoutError("Response timed out") from exc
    return None, buffer


def _read_json_response(client: socket.socket, timeout: float = DEFAULT_ACK_TIMEOUT):
    """Read a complete JSON object from a socket, returning (obj, remainder_buffer)."""
    return _decode_json_stream(client, timeout)


def get_agent_card(client: socket.socket) -> dict:
    """Fetch the agent card from a connected socket (synchronous)."""
    client.send(json.dumps({"type": "agent_card"}).encode())
    data, _ = _read_json_response(client, DEFAULT_ACK_TIMEOUT)

    if data.get("type") == "agent_card":
        return data
    raise RuntimeError(f"Unexpected response: {data}")


def _wait_for_response(
    client: socket.socket,
    request_id: str,
    initial_buffer: str = "",
    idle_timeout: float = HEARTBEAT_IDLE_TIMEOUT,
) -> dict:
    """Wait for a response matching *request_id*, accepting heartbeats.

    Times out only if no data (response or heartbeat) arrives for *idle_timeout*
    seconds. As long as heartbeats keep flowing, the connection stays alive
    indefinitely — no wall-clock timeout.
    """
    decoder = json.JSONDecoder()
    last_activity = time.time()
    buffer = initial_buffer

    while True:
        try:
            client.settimeout(1.0)
            chunk = client.recv(SOCKET_BUFFER).decode()
            if not chunk:
                continue
            buffer += chunk
            last_activity = time.time()  # Any data resets idle timer
            while buffer:
                start_idx = buffer.find("{")
                if start_idx == -1:
                    break
                try:
                    obj, end_idx = decoder.raw_decode(buffer[start_idx:])
                    buffer = buffer[start_idx + end_idx :]

                    if obj.get("id") == request_id and obj.get("type") == "response":
                        return obj
                    # Heartbeats are accepted but not returned — they just keep us alive
                except json.JSONDecodeError:
                    break
        except TimeoutError:
            if time.time() - last_activity >= idle_timeout:
                raise TimeoutError(
                    f"Agent stopped responding (no heartbeat for {idle_timeout}s)"
                ) from None
            continue

    raise TimeoutError(f"Agent did not respond within {idle_timeout}s")


def query_agent(client: socket.socket, prompt: str, idle_timeout: float = HEARTBEAT_IDLE_TIMEOUT) -> dict:
    """Send a query to an agent and wait for the result (async protocol).

    No wall-clock timeout — waits indefinitely as long as the server sends
    heartbeats. Times out only if no heartbeat arrives for *idle_timeout* seconds.
    """
    request_id = str(uuid.uuid4())

    client.send(
        json.dumps(
            {
                "type": "query",
                "id": request_id,
                "query": prompt,
            }
        ).encode()
    )

    ack, ack_remainder = _read_json_response(client, DEFAULT_ACK_TIMEOUT)

    if ack.get("type") != "queued":
        raise RuntimeError(f"Unexpected acknowledgment: {ack}")

    return _wait_for_response(client, request_id, ack_remainder, idle_timeout)


def _get_agent_status(sock_path: str) -> dict | None:
    """Probe a socket and return an agent info dict (or None if PID unparseable)."""
    pid_match = Path(sock_path).stem.split("-")
    try:
        pid = int(pid_match[1])
    except (ValueError, IndexError):
        return None

    if not Path(sock_path).exists():
        return {"pid": pid, "sock_path": sock_path, "status": "stale"}

    if not _verify_socket(sock_path):
        return {"pid": pid, "sock_path": sock_path, "status": "unreachable"}

    try:
        client = _make_connection(sock_path, 2)
        card = get_agent_card(client)
        client.close()
    except (FileNotFoundError, ConnectionError, TimeoutError, RuntimeError, OSError):
        return {"pid": pid, "sock_path": sock_path, "status": "unreachable"}

    return {
        "pid": pid,
        "sock_path": sock_path,
        "name": card.get("name", "Unknown"),
        "tools_count": len(card.get("tools", [])),
        "working_dir": card.get("working_dir", "Unknown"),
        "model": card.get("model", "Unknown"),
        "file": card.get("file", "Unknown"),
        "status": "active",
    }


def list_agents() -> list:
    """Scan /tmp for active agent sockets and return their info dicts."""
    return [
        info
        for sock_file in Path("/tmp").glob("taua2a-*.sock")
        if (info := _get_agent_status(str(sock_file)))
    ]


def _socket_path_for_pid(pid: int) -> str:
    """Return the Unix socket path for a given agent PID."""
    return f"/tmp/taua2a-{pid}.sock"



def _is_sanity_session(log_dir: Path, agent_name: str | None = None) -> bool:
    """Return True for sessions that belong to sanity-test runs.

    A session is considered a sanity session when:
    - Its log directory path contains ``logtest`` (sanity.sh sets
      ``TAU_LOG_DIR`` to ``...logtest``), or
    - Its agent name follows the ``a2aname-`` pattern used by sanity.sh.
    """
    if "logtest" in str(log_dir).lower():
        return True
    if agent_name and agent_name.startswith("a2aname-"):
        return True
    return False


def _probe_session_socket(pid: int) -> tuple[str, dict | None]:
    """Probe the A2A socket for *pid*.

    Returns ``(status, agent_card_or_none)`` where *status* is one of
    ``active``, ``stale``, or ``unreachable``.
    """
    sock_path = _socket_path_for_pid(pid)

    if not Path(sock_path).exists():
        return "stale", None

    if not _verify_socket(sock_path):
        return "unreachable", None

    try:
        client = _make_connection(sock_path, DEFAULT_CONNECT_TIMEOUT)
        card = get_agent_card(client)
        client.close()
        return "active", card
    except (FileNotFoundError, ConnectionError, TimeoutError, RuntimeError, OSError):
        return "unreachable", None


# Regex matching the context-file naming convention: {ppid}_{YYYYMMDDHHMMSS}_{N}
_CONTEXT_FILE_RE = re.compile(r"^(\d+)_\d+_\d+\.context$")


def _build_session_info(
    prefix: str,
    pid: int,
    context_file: Path,
    log_dir: Path,
) -> dict:
    """Build a single session-metadata dict from a context file.

    The agent card (when reachable) takes priority over context-file
    metadata for shared fields; non-reachable sessions fall back to the
    metadata block written by TAU_005, or to ``None`` defaults.
    """
    metadata, message_count = read_context_metadata_for_a2a(context_file)
    status, card = _probe_session_socket(pid)

    # Agent card fields take priority; fall back to context metadata.
    source = card or metadata

    agent_name = source.get("name") or source.get("agent_name")
    model = source.get("model")
    working_dir = source.get("working_dir")
    start_time = source.get("start_time")
    parent_pid = source.get("parent_pid")
    llm_group = source.get("llm_group")
    max_context_tokens = card.get("max_context_tokens") if card else None

    uptime = None
    if start_time is not None:
        try:
            uptime = int(time.time() - float(start_time))
        except (TypeError, ValueError):
            uptime = None

    socket_path = _socket_path_for_pid(pid)

    return {
        "id": prefix,
        "pid": pid,
        "status": status,
        "agent_name": agent_name,
        "model": model,
        "working_dir": working_dir,
        "context_length": message_count,
        "message_count": message_count,
        "start_time": start_time,
        "uptime": uptime,
        "parent_pid": parent_pid,
        "llm_group": llm_group,
        "max_context_tokens": max_context_tokens,
        "socket_path": socket_path,
        "context_file": str(context_file),
        "audit_file": str(log_dir / f"{prefix}.audit"),
        "is_sanity": _is_sanity_session(log_dir, agent_name),
    }


def _scan_sessions(log_dir: Path) -> list[dict]:
    """Scan *log_dir* for context files and return session-metadata dicts.

    Only files whose name matches ``^\\d+_\\d+_\\d+\\.context$`` are
    considered (the ``{ppid}_{timestamp}_{counter}`` convention).
    """
    sessions: list[dict] = []
    if not log_dir.exists():
        return sessions

    for ctx_file in sorted(log_dir.glob("*.context")):
        match = _CONTEXT_FILE_RE.match(ctx_file.name)
        if not match:
            continue
        pid = int(match.group(1))
        sessions.append(_build_session_info(ctx_file.stem, pid, ctx_file, log_dir))

    return sessions


def _list_sessions_json() -> None:
    """Print all sessions in LOG_DIR as JSON, then exit.

    Short-circuits in :func:`a2a_cli_mode` like ``--list`` / ``--listjson``.
    """
    # Lazy import to avoid circular dependency at module load time.
    from agent_session import LOG_DIR

    sessions = _scan_sessions(LOG_DIR)
    print(json.dumps({"sessions": sessions}, indent=2))
    sys.exit(0)


# ── Server ─────────────────────────────────────────────────────────────────


class A2AServer:
    """Unix socket server for inter-agent communication.

    Runs in a daemon thread; handles ``agent_card`` (sync), ``status`` (sync),
    and ``query`` (async) requests from other agents.
    """

    def __init__(self, agent, sock_path: str = None):
        """Initialize server for *agent*; defaults socket to ``/tmp/taua2a-{PID}.sock``."""
        self.agent = agent
        self.sock_path = sock_path or f"/tmp/taua2a-{os.getpid()}.sock"
        self.sock = None
        self.running = False
        self.thread = None
        self._ready = threading.Event()

    def start(self):
        """Start the server in a daemon thread; blocks until ready or 5s timeout."""
        self.running = True
        self._ready.clear()
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("A2A server failed to start within 5s")

    def stop(self):
        """Stop the server and clean up the socket file (idempotent)."""
        self.running = False

        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

        if hasattr(self, "sock_path") and Path(self.sock_path).exists():
            try:
                Path(self.sock_path).unlink(missing_ok=True)
            except OSError:
                pass

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _accept_loop(self):
        """Bind socket, listen, and spawn a daemon thread per connection."""
        try:
            Path(self.sock_path).unlink(missing_ok=True)
        except OSError:
            pass

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.sock_path)
        self.sock.listen(5)
        self._ready.set()
        self.sock.settimeout(1.0)

        while self.running:
            try:
                client_sock, _ = self.sock.accept()
                threading.Thread(
                    target=self._handle_client, args=(client_sock,), daemon=True
                ).start()
            except TimeoutError:
                continue
            except OSError:
                if self.running:
                    continue

    def _recv_request(self, client_sock: socket.socket) -> bytes:
        """Receive the full request from a client socket."""
        data = b""
        while True:
            chunk = client_sock.recv(SOCKET_BUFFER)
            if not chunk:
                break
            data += chunk
            if len(chunk) < SOCKET_BUFFER:
                break
        return data

    def _handle_client(self, client_sock: socket.socket):
        """Read a JSON request and dispatch to handler."""
        request_type = "query"  # Default for finally block
        try:
            data = self._recv_request(client_sock)
            if not data:
                return

            request = json.loads(data.decode("utf-8"))
            request_type = request.get("type", "query")

            if request_type == "agent_card":
                self._send_agent_card(client_sock)
            elif request_type == "status":
                self._handle_status(client_sock)
            elif request_type == "supervise":
                self._handle_supervise(client_sock, request.get("id", ""))
            else:
                request_id = request.get("id", str(uuid.uuid4()))
                query_content = request.get("query", "")
                self._handle_query(client_sock, request_id, query_content)
        except (OSError, RuntimeError, json.JSONDecodeError) as e:
            try:
                client_sock.send(
                    json.dumps({"type": "error", "message": str(e)}).encode() + b"\n"
                )
            except OSError:
                pass
        finally:
            if request_type not in ("supervise",):
                client_sock.close()

    def _build_agent_card(self) -> dict:
        """Build the agent card dict.

        Includes the A2A extension-004 session metadata fields
        (``original_task``, ``start_time``, ``parent_pid``, ``llm_group``,
        ``max_context_tokens``, ``session_id``). All new fields are optional and
        use ``getattr`` defaults so minimal duck-typed agents (and old clients)
        keep working.
        """
        session = getattr(self.agent, "_session", None)
        return {
            "type": "agent_card",
            "name": self.agent.agent_name,
            "model": self.agent.model_name,
            "tools": sorted(self.agent.available_tool_names),
            "working_dir": str(self.agent.original_cwd),
            "context_length": len(self.agent.context),
            "uptime": (
                int(time.time() - self.agent._start_time)  # pylint: disable=W0212
                if hasattr(self.agent, "_start_time")
                else 0
            ),
            "sock_path": self.sock_path,
            "file": os.path.basename(sys.argv[0]) if sys.argv else "tau.py",
            "original_task": getattr(self.agent, "original_task", None),
            "start_time": getattr(self.agent, "_start_time", None),
            "parent_pid": os.getppid(),
            "llm_group": getattr(self.agent, "current_group_name", None),
            "max_context_tokens": getattr(self.agent, "max_context_tokens", None),
            "session_id": getattr(session, "prefix", None),
            "turn_active": getattr(self.agent, "_turn_active", False),
        }

    def _send_agent_card(self, client_sock: socket.socket):
        """Send agent metadata as JSON to *client_sock*."""
        try:
            client_sock.send(json.dumps(self._build_agent_card()).encode() + b"\n")
        except OSError:
            pass

    def _handle_status(self, client_sock: socket.socket):
        """Handle a lightweight status request — return running/idle info.

        Returns a JSON object with ``status_response`` type containing
        ``pid``, ``turn_active``, ``context_length``, ``uptime``,
        ``nesting_count``, and ``last_audit_mtime``.
        """
        audit_file = getattr(self.agent, "audit_file", None)
        last_audit_mtime = None
        if audit_file:
            try:
                last_audit_mtime = os.path.getmtime(str(audit_file))
            except OSError:
                pass

        status = {
            "type": "status_response",
            "pid": os.getpid(),
            "turn_active": getattr(self.agent, "_turn_active", False),
            "context_length": len(self.agent.context),
            "uptime": (
                int(time.time() - self.agent._start_time)  # pylint: disable=W0212
                if hasattr(self.agent, "_start_time")
                else 0
            ),
            "nesting_count": getattr(self.agent, "nesting_count", 0),
            "last_audit_mtime": last_audit_mtime,
        }
        try:
            client_sock.send(json.dumps(status).encode() + b"\n")
        except OSError:
            pass

    def _poll_for_response(self, client_sock: socket.socket, request_id: str) -> bool:
        """Poll for the response to *request_id* and send it to *client_sock*.

        Sends periodic heartbeats so the client knows the server is still alive.
        Polls indefinitely until response is available or client disconnects.
        Also sends streaming chunks (tool_call, tool_result, assistant) as they arrive.

        Returns True if response was sent, False if client disconnected.
        """
        last_heartbeat = time.time()
        while True:
            try:
                # Atomically snapshot and clear pending chunks (thread-safe: pop + list()
                # avoids race with main thread appending to the list).
                chunks_snapshot = list(
                    self.agent._pending_a2a_chunks.pop(request_id, [])  # pylint: disable=W0212
                )
                if chunks_snapshot:
                    for chunk in chunks_snapshot:
                        envelope = {
                            "protocol_version": "1.0",
                            "type": "stream_chunk",
                            "id": request_id,
                            "chunk": chunk,
                        }
                        client_sock.send(json.dumps(envelope).encode() + b"\n")

                if (
                    hasattr(self.agent, "_pending_a2a_responses")
                    and request_id in self.agent._pending_a2a_responses
                ):  # pylint: disable=W0212
                    result = self.agent._pending_a2a_responses.pop(
                        request_id
                    )  # pylint: disable=W0212
                    client_sock.send(json.dumps(result).encode() + b"\n")
                    return True

                # Send heartbeat if enough time has passed
                if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    heartbeat = {"type": "heartbeat", "id": request_id}
                    client_sock.send(json.dumps(heartbeat).encode() + b"\n")
                    last_heartbeat = time.time()
            except OSError:
                return False
            time.sleep(DEFAULT_POLL_INTERVAL)
        return False

    def _handle_query(
        self, client_sock: socket.socket, request_id: str, query_content: str
    ):
        """Send ack, queue the query, then poll for the response with heartbeats."""
        ack = {"type": "queued", "id": request_id}
        try:
            client_sock.send(json.dumps(ack).encode() + b"\n")
        except OSError:
            return

        message = InputMessage.from_a2a(query_content, request_id)
        self.agent.input_queue.put(message)
        self._poll_for_response(client_sock, request_id)

    def _handle_supervise(self, client_sock: socket.socket, session_id: str):
        """Handle persistent supervision connection.

        Reads commands from the supervisor and forwards them to the agent's
        control queue. The connection stays open for the duration of supervision.
        """
        # Send supervising acknowledgment
        ack = {"type": "supervising", "id": session_id}
        try:
            client_sock.send(json.dumps(ack).encode() + b"\n")
        except OSError:
            return

        # Process commands from supervisor
        while True:
            try:
                data = self._recv_request(client_sock)
                if not data:
                    break

                cmd = json.loads(data.decode("utf-8"))
                cmd_type = cmd.get("type", "")

                if cmd_type in ("inject", "terminate", "redirect", "status"):
                    # Forward command to agent's control queue
                    self.agent._control_queue.put(data.decode("utf-8"))  # pylint: disable=W0212
                    # Send acknowledgment
                    cmd_id = cmd.get("id", "")
                    client_sock.send(
                        json.dumps({"type": "ack", "id": cmd_id}).encode() + b"\n"
                    )
                elif cmd_type == "close":
                    break
                else:
                    # Unknown command type
                    cmd_id = cmd.get("id", "")
                    client_sock.send(
                        json.dumps({"type": "error", "id": cmd_id, "message": f"Unknown command: {cmd_type}"}).encode() + b"\n"
                    )
            except (OSError, json.JSONDecodeError):
                break

        client_sock.close()


# ── Supervisor class ──────────────────────────────────────────────────────


class Supervisor:
    """Spawn and supervise a child Tau process.

    Connects to a child agent's A2A socket and sends control commands
    (inject, terminate, redirect, status). Can tail the child's audit log
    and detect repeated tool call patterns (loops).
    """

    def __init__(self, task: str, child_pid: int, sock_path: str, audit_file: Path):
        """Initialize supervisor for a child process.

        Args:
            task: Description of the task being supervised.
            child_pid: PID of the child process.
            sock_path: Path to the child's A2A Unix socket.
            audit_file: Path to the child's audit log file.
        """
        self.task = task
        self.child_pid = child_pid
        self.sock_path = sock_path
        self.audit_file = audit_file
        self._sock: socket.socket | None = None
        self._cmd_id = 0
        self._last_audit_pos = 0

    def connect(self) -> None:
        """Open persistent supervision connection to child."""
        self._sock = _make_connection(self.sock_path, SUPERVISE_CONNECT_TIMEOUT)
        request = {"type": "supervise", "id": f"sup-{self._cmd_id}"}
        self._sock.send(json.dumps(request).encode() + b"\n")
        data = self._recv_response()
        if data.get("type") != "supervising":
            raise RuntimeError(f"Supervision failed: {data}")

    def inject(self, role: str, content: str) -> None:
        """Inject a message into the child's context.

        Args:
            role: Message role (informational, always creates user message).
            content: Message content to inject.
        """
        self._cmd_id += 1
        cmd = {"type": "inject", "role": role, "content": content, "id": f"cmd-{self._cmd_id}"}
        self._sock.send(json.dumps(cmd).encode() + b"\n")
        self._wait_for_ack()

    def terminate(self, graceful: bool = True, force_kill: bool = False) -> None:
        """Request child termination.

        Args:
            graceful: If True, child finishes current turn. If False, exits immediately.
            force_kill: If True, sends SIGKILL to child (immediate, no cleanup).
        """
        self._cmd_id += 1
        cmd = {"type": "terminate", "graceful": graceful, "force_kill": force_kill, "id": f"cmd-{self._cmd_id}"}
        self._sock.send(json.dumps(cmd).encode() + b"\n")
        self._wait_for_ack()

    def redirect(self, new_task: str) -> None:
        """Redirect child to a new task, clearing context.

        Args:
            new_task: New task description.
        """
        self._cmd_id += 1
        cmd = {"type": "redirect", "task": new_task, "id": f"cmd-{self._cmd_id}"}
        self._sock.send(json.dumps(cmd).encode() + b"\n")
        self._wait_for_ack()

    def get_new_audit_lines(self) -> str:
        """Return new lines from child's audit log since last check.

        Returns:
            New audit log content as string, empty if no changes or file missing.
        """
        try:
            with open(self.audit_file, "r") as f:
                f.seek(self._last_audit_pos)
                new_lines = f.read()
                self._last_audit_pos = f.tell()
                return new_lines
        except FileNotFoundError:
            return ""

    def detect_loop(self, window: int = 5) -> bool | None:
        """Detect repeated tool call patterns in recent audit lines.

        Parses recent audit lines for tool_call records and returns True if
        the same tool+args pattern repeats N times within the window.

        Args:
            window: Number of consecutive identical calls to detect.

        Returns:
            True if loop detected, False if no loop, None if insufficient data.
        """
        new_lines = self.get_new_audit_lines()
        if not new_lines:
            return None

        # Parse tool_call records from audit lines
        tool_calls: list[tuple[str, str]] = []
        for line in new_lines.split("\n"):
            if '"tool_call"' in line or '"tool_calls"' in line:
                try:
                    record = json.loads(line)
                    calls = record.get("tool_calls", [])
                    if not calls and "tool_call" in record:
                        calls = [record["tool_call"]]
                    for call in calls:
                        name = call.get("name", call.get("function", {}).get("name", ""))
                        args = json.dumps(call.get("args", call.get("arguments", "")))
                        tool_calls.append((name, args))
                except (json.JSONDecodeError, TypeError):
                    continue

        if len(tool_calls) < window:
            return None

        # Check for repeated pattern
        for i in range(len(tool_calls) - window + 1):
            pattern = tool_calls[i]
            if all(tool_calls[i + j] == pattern for j in range(1, window)):
                return True

        return False

    def close(self) -> None:
        """Close the supervision connection."""
        if self._sock:
            try:
                self._sock.send(json.dumps({"type": "close"}).encode() + b"\n")
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _recv_response(self) -> dict:
        """Receive a JSON response from the child."""
        buf = b""
        self._sock.settimeout(SUPERVISE_ACK_TIMEOUT)
        while True:
            try:
                chunk = self._sock.recv(SOCKET_BUFFER)
                if not chunk:
                    raise ConnectionError("Connection closed by child")
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        return json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
            except socket.timeout:
                raise TimeoutError("Timeout waiting for child response")

    def _wait_for_ack(self) -> None:
        """Wait for acknowledgment from child."""
        data = self._recv_response()
        if data.get("type") == "error":
            raise RuntimeError(f"Child error: {data.get('message', 'unknown')}")


# ── CLI helpers ────────────────────────────────────────────────────────────


def _filter_active_agents(agents: list) -> list:
    """Return only agents with status 'active'."""
    return [a for a in agents if a.get("status") == "active"]


def _empty_agents_message(include_all: bool) -> str:
    """Return the appropriate empty-agents message."""
    return "No agents found." if include_all else "No active agents found."


def _print_agents_table(agents: list, include_all: bool = False):
    """Display agents in a formatted table (active only unless *include_all*)."""
    if not include_all:
        agents = _filter_active_agents(agents)

    if not agents:
        agent_status_message(_empty_agents_message(include_all))
        return

    agents_table_header()
    for agent in agents:
        agents_table_row(agent)


def _print_agents_json(agents: list, include_all: bool = False):
    """Display agents as JSON."""
    if not include_all:
        agents = _filter_active_agents(agents)
    if not agents:
        agent_status_message(_empty_agents_message(include_all))
        return
    agents_json(json.dumps(agents, indent=2))


_A2A_CLI_ERRORS = (
    FileNotFoundError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
)


def _cli_connect_and_execute(pid: int, action):
    """Connect to agent, run action(client), close, handle errors."""
    try:
        client = connect_to_agent(pid)
        action(client)
        client.close()
    except _A2A_CLI_ERRORS as e:
        a2a_cli_error(f"Error: {e}")
    sys.exit(0)


def _action_card(c):
    """Fetch and display the agent card."""
    agent_card_json(json.dumps(get_agent_card(c), indent=2))


def _handle_cli_card(pid: int):
    """Fetch and display the agent card for the specified PID, then exit."""
    _cli_connect_and_execute(pid, _action_card)


def _action_query(c, query: str, idle_timeout: float):
    """Send a query and display the response."""
    agent_a2a_response(query_agent(c, query, idle_timeout)["response"])


def _handle_cli_query(pid: int, query: str, idle_timeout: float):
    """Send a query to the specified agent, display the response, then exit."""
    _cli_connect_and_execute(pid, lambda c: _action_query(c, query, idle_timeout))


# ── List flag configurations ─────────────────────────────────────────────

_A2A_LIST_FLAGS = [
    ("list", False, False),
    ("list_all", False, True),
    ("listjson", True, False),
    ("listjson_all", True, True),
]


def a2a_cli_mode(args) -> None:
    """Handle A2A CLI mode: list agents, show card, or send query. Exits after."""
    # List mode (table or JSON, active or all)
    for list_flag, json_flag, include_all in _A2A_LIST_FLAGS:
        if getattr(args, list_flag):
            agents = list_agents()
            printer = _print_agents_json if json_flag else _print_agents_table
            printer(agents, include_all=include_all)
            sys.exit(0)

    # Session metadata mode (--list-sessions): scan LOG_DIR for all sessions.
    if getattr(args, "list_sessions", False):
        _list_sessions_json()

    # Resolve target PID (by --pid or --name)
    target_pid = args.pid
    if args.name and not args.pid:
        agents = list_agents()
        found = next((a for a in agents if a.get("name") == args.name), None)
        if not found:
            a2a_cli_error(f"Error: Agent with name '{args.name}' not found.")
            sys.exit(1)
        target_pid = found["pid"]

    # Card requires a target (resolved from --pid or --name)
    if args.card and not target_pid:
        a2a_cli_error("Error: --card requires --pid or --name")
        sys.exit(1)

    # Execute card or query
    if target_pid:
        query_value = args.inputs[0] if args.inputs else None

        if args.card:
            _handle_cli_card(target_pid)

        if query_value is not None:
            _handle_cli_query(target_pid, query_value, args.timeout)
