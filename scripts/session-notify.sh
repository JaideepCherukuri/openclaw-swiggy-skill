#!/usr/bin/env bash
set -euo pipefail
# Check OpenClaw logs for Swiggy session expiry and send a desktop notification.
# Add to crontab:
#   0 * * * * /path/to/swiggy-agent/scripts/session-notify.sh
#
# Supports macOS (osascript), Linux (notify-send), or falls back to stderr.

LOG_DIR="$HOME/.openclaw/logs"
LOG_FILE="$LOG_DIR/gateway.log"

# Only check log entries from the last 2 hours
HOUR_AGO=$(date -u -v-2H +%Y-%m-%dT%H 2>/dev/null || date -u -d '2 hours ago' +%Y-%m-%dT%H 2>/dev/null || "")
NOW_HOUR=$(date -u +%Y-%m-%dT%H 2>/dev/null || "")

if [ ! -f "$LOG_FILE" ]; then
  exit 0
fi

# Match recent entries by hour prefix, then check for auth errors
RECENT_ERRORS=""
if [ -n "$HOUR_AGO" ] && [ -n "$NOW_HOUR" ]; then
  RECENT_ERRORS=$(grep -E "($HOUR_AGO|$NOW_HOUR)" "$LOG_FILE" 2>/dev/null | grep -i "session expired\|auth.*expired\|unauthorized\|unauthenticated" || true)
else
  # Fallback: check last 100 lines if date parsing failed
  RECENT_ERRORS=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -i "session expired\|auth.*expired\|unauthorized\|unauthenticated" || true)
fi

if [ -n "$RECENT_ERRORS" ]; then
  MSG="Swiggy session expired. Re-authenticate in OpenClaw using mcporter."
  if command -v osascript &>/dev/null; then
    osascript -e "display notification \"$MSG\" with title \"Swiggy Agent\" sound name \"Basso\""
  elif command -v notify-send &>/dev/null; then
    notify-send "Swiggy Agent" "$MSG"
  else
    echo "[swiggy-agent] $(date): $MSG" >&2
  fi
fi
