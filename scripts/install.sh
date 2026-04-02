#!/usr/bin/env bash
# Interactive setup script for the OpenClaw Swiggy Agent
set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/openclaw-swiggy-skill"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== OpenClaw Swiggy Agent Installer ==="
echo ""

# 1. Check prerequisites
echo "[1/4] Checking prerequisites..."

if ! command -v openclaw &>/dev/null; then
  echo "ERROR: OpenClaw is not installed."
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is not installed."
  exit 1
fi

if ! python3 -c 'import playwright' &>/dev/null; then
  echo "  Installing Python dependencies (playwright, websockets)..."
  pip3 install playwright websockets mcp requests || echo "Warning: pip install failed, you may need to run 'pip install playwright websockets mcp requests' manually."
  playwright install chromium || echo "Warning: playwright browser install failed."
fi

# 2. Copy skill files
echo ""
echo "[2/4] Installing skill to $SKILL_DIR..."
mkdir -p "$SKILL_DIR/scripts"
cp "$SCRIPT_DIR/skill/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$SCRIPT_DIR/skill/OAUTH_AUTOMATION_PLAYBOOK.md" "$SKILL_DIR/OAUTH_AUTOMATION_PLAYBOOK.md"
cp -r "$SCRIPT_DIR/skill/scripts/"* "$SKILL_DIR/scripts/"
echo "  Skill files copied."

# 3. MCP server config (via mcporter)
echo ""
echo "[3/4] Swiggy Unified MCP server configuration"

if ! command -v mcporter &>/dev/null; then
  echo "  mcporter not found. Installing..."
  npm install -g mcporter
fi

echo "  Removing old split Swiggy servers..."
mcporter config remove swiggy-instamart 2>/dev/null || true
mcporter config remove swiggy-food 2>/dev/null || true
mcporter config remove swiggy-dineout 2>/dev/null || true

echo "  Adding Unified Swiggy MCP server..."
mcporter config add swiggy --command "python3" --arg "$SKILL_DIR/scripts/swiggy_unified_mcp.py"
echo "  Done."

# 4. Instructions
echo ""
echo "[4/4] Authentication Instructions"
echo ""
echo "To authenticate, use one of the two options:"
echo "  Option 1 (Zero-Click, Preferred):"
echo "    1. Start URL generation: python3 $SKILL_DIR/scripts/swiggy_unified_mcp_login.py"
echo "    2. Start automation: python3 $SKILL_DIR/scripts/swiggy_playwright_auth.py --url <AUTH_URL> --phone <YOUR_PHONE_NUMBER>"
echo ""
echo "  Option 2 (Manual Fallback):"
echo "    1. Run: python3 $SKILL_DIR/scripts/swiggy_unified_mcp_login.py"
echo "    2. Open the printed URL, login, and copy the broken localhost callback URL."
echo "    3. Run: curl \"<PASTED_URL>\""
echo ""
echo "=== Setup complete! ==="

