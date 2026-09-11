---
description: "Send and receive Signal messenger messages via CLI — configure daemon, JSON-RPC API, messaging automation (also load: background, dependency_management, dream, shell_scripting)"
keywords: signal-cli, Signal messaging, message automation, JSON-RPC API, signal daemon, message sending, signal configuration
name: signal-cli
category: communication
---

# signal-cli

## When
"send signal message", "signal CLI", "signal daemon", "receive signal", "signal JSON-RPC"

## Daemon Setup
```bash
signal-cli daemon --http --receive-mode=manual --send-read-receipts
```

## JSON-RPC API
- Endpoint: `POST http://localhost:8080/api/v1/rpc`
- Content-Type: `application/json`

### Send
```json
{"jsonrpc":"2.0","method":"send","params":{"message":"Hello","recipients":["+1234567890"]},"id":1}
```
Uses `recipients`, NOT `numbers`.

### Receive
```json
{"jsonrpc":"2.0","method":"receive","params":{},"id":1}
```
Returns array. Envelope types: `dataMessage`, `receiptMessage`, `expirationMessage`.

### Other Methods
- `version` — get version
- `listAccounts` — list registered accounts

## Gotchas
- **Config locked**: Daemon running → CLI fails with "Config file is in use"
- **Receive**: JSON-RPC POST, NOT HTTP GET
- **Multi-account**: Daemon starts multi-account mode with multiple accounts

## SQLite DB
Location: `~/.local/share/signal-cli/data/[ACCOUNT_ID]/account.db`

| Table | Purpose |
|-------|---------|
| `recipient` | Contacts (number, ACI, PNI, name, blocked/archived) |
| `session` | Protocol sessions per recipient/device |
| `identity` | Trusted identity keys |
| `pre_key` | Pre-signals keys |
| `message_send_log` | Outgoing message queue |

## Account Readiness
- Account in `accounts.json`, profile name set (profile_sharing=ENABLED)
- Session exists for target contact, identity trusted
- Pre-keys available: `SELECT COUNT(*) FROM pre_key`

## Helper
```bash
python3 skills/signal-cli/signal_rpc.py
```

## Related Skills
- `background` — run signal daemon in background
- `shell_scripting` — automate signal CLI commands
- `web-research` — JSON-RPC API patterns
