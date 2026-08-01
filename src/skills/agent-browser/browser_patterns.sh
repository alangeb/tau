#!/bin/bash
# browser_patterns.sh — Browser automation pattern helpers for agent-browser CLI
# Usage: source this file or run directly: ./browser_patterns.sh <command>

set -euo pipefail

# Open URL, wait for network idle, take interactive snapshot
browser_init() {
    local url="${1:?Usage: browser_init <url>}"
    agent-browser open "$url"
    agent-browser wait --load networkidle
    agent-browser snapshot -i
}

# Click element by ref and re-snapshot
browser_click() {
    local ref="${1:?Usage: browser_click <ref>}"
    agent-browser click "@$ref"
    agent-browser snapshot -i
}

# Fill form field and press Enter, then snapshot
browser_fill_submit() {
    local ref="${1:?Usage: browser_fill_submit <ref> <text>}"
    local text="${2:?Text required}"
    agent-browser fill "@$ref" "$text"
    agent-browser press Enter
    agent-browser snapshot -i
}

# Extract text from elements matching CSS selector
browser_extract() {
    local selector="${1:?Usage: browser_extract <css_selector>}"
    agent-browser eval --stdin <<EVALEOF
JSON.stringify(Array.from(document.querySelectorAll('$selector')).map(el => el.textContent.trim()))
EVALEOF
}

# Wait for element to appear in DOM
browser_wait() {
    local ref="${1:?Usage: browser_wait <ref> [timeout_ms]}"
    local timeout="${2:-5000}"
    local elapsed=0
    local interval=500
    while (( elapsed < timeout )); do
        if agent-browser eval "document.querySelector('[data-ref=\"$ref\"]')" 2>/dev/null | grep -qv 'null'; then
            echo "Element '$ref' found after ${elapsed}ms"
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + interval))
    done
    echo "TIMEOUT: Element '$ref' not found after ${timeout}ms"
    return 1
}

# Extract text from a CSS selector (simpler version)
browser_extract_selector() {
    local selector="${1:?Usage: browser_extract_selector <css_selector>}"
    agent-browser eval --stdin <<EVALEOF
Array.from(document.querySelectorAll('$selector')).map(el => el.textContent.trim()).join('\n---\n')
EVALEOF
}

# Evaluate arbitrary JS expression and return JSON
browser_extract_json() {
    local expr="${1:?Usage: browser_extract_json <js_expression>}"
    agent-browser eval "JSON.stringify($expr)"
}

# Detect and dismiss common overlay modals (cookies, newsletter, etc.)
browser_handle_modal() {
    echo "Checking for modals..."
    # Try common accept buttons
    for text in "Accept All" "Accept" "Agree" "OK" "Dismiss" "Close" "X"; do
        local ref
        ref=$(agent-browser snapshot -i 2>/dev/null | grep -i "$text" | head -1 | grep -oP '@\w+' | head -1)
        if [[ -n "$ref" ]]; then
            echo "Found modal button: $text ($ref)"
            agent-browser click "$ref"
            sleep 1
            agent-browser snapshot -i
            return 0
        fi
    done
    # Try CSS selectors for common modal close buttons
    for sel in ".modal-close" ".close-btn" "[aria-label*='close']" ".cookie-accept"; do
        local count
        count=$(agent-browser eval "document.querySelectorAll('$sel').length" 2>/dev/null || echo "0")
        if [[ "$count" =~ ^[1-9] ]]; then
            echo "Found modal via $sel"
            agent-browser eval "document.querySelector('$sel').click()"
            sleep 1
            agent-browser snapshot -i
            return 0
        fi
    done
    echo "No modals detected"
    return 0
}

# Take screenshot to file
browser_screenshot() {
    local file="${1:?Usage: browser_screenshot <filename>}"
    agent-browser screenshot "$file" 2>/dev/null || \
        agent-browser snapshot > "$file" 2>/dev/null
    echo "Screenshot saved: $file"
}

# Close browser cleanly
browser_close() {
    agent-browser close 2>/dev/null && echo "Browser closed" || echo "No browser to close"
}

# Open URL and take snapshot (original simple version)
browser_open() {
    agent-browser open "${1:?Usage: browser_open <url>}"
    agent-browser snapshot -i
}

# Show usage
browser_help() {
    cat <<'EOF'
Browser Automation Helpers (requires agent-browser CLI)
Usage: source browser_patterns.sh  # then use functions
   or: ./browser_patterns.sh <command> [args]

Commands:
  init <url>              Open URL, wait for load, snapshot
  click <ref>             Click element, re-snapshot
  fill <ref> <text>       Fill field + Enter, snapshot
  extract <selector>      Extract text from CSS selector
  wait <ref> [timeout]    Wait for element to appear
  modal                   Detect and dismiss modals
  screenshot <file>       Save screenshot
  close                   Close browser
  help                    Show this help
EOF
}

# CLI entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cmd="${1:-help}"
    shift || true
    case "$cmd" in
        init)          browser_init "$@" ;;
        click)         browser_click "$@" ;;
        fill)          browser_fill_submit "$@" ;;
        extract)       browser_extract "$@" ;;
        wait)          browser_wait "$@" ;;
        modal)         browser_handle_modal "$@" ;;
        screenshot)    browser_screenshot "$@" ;;
        close)         browser_close "$@" ;;
        help|--help|-h) browser_help ;;
        *) echo "Unknown: $cmd. Run: $0 help" >&2; exit 1 ;;
    esac
fi
