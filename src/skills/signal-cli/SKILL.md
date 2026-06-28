---
name: signal-cli
description: Signal CLI and JSON-RPC API — send/receive messages, daemon setup, account management. Signal messenger, messaging, chat automation (also load: background)
category: integrations
keywords: signal, messenger, messaging, chat, send message, receive, JSON-RPC, daemon, automation
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

## CLI Examples
```bash
signal-cli -a +1234567890 send -m "Hello" +1987654321
signal-cli -a +1234567890 receive
signal-cli listAccounts
```

## Gotchas
- **Config locked**: When daemon runs, CLI commands fail with "Config file is in use"
- **Receive**: Use JSON-RPC POST, NOT HTTP GET
- **Multi-account**: Daemon starts in multi-account mode when multiple accounts configured

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
python3 skills/signal-cli/signal_rpc.py  # signal cli helper
```
## Related Skills
- `shell_scripting` — automate signal workflows
- `background` — run signal daemon in background
