#!/usr/bin/env bash
# Interactive setup script for the OpenClaw Swiggy Agent
set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/swiggy-agent"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== OpenClaw Swiggy Agent Installer ==="
echo ""

# 1. Check prerequisites
echo "[1/4] Checking prerequisites..."

if ! command -v openclaw &>/dev/null; then
  echo "ERROR: OpenClaw is not installed."
  exit 1
fi
echo "  OpenClaw: $(openclaw --version)"

# 2. Copy skill files
echo ""
echo "[2/4] Installing skill to $SKILL_DIR..."
mkdir -p "$SKILL_DIR"
cp "$SCRIPT_DIR/skill/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$SCRIPT_DIR/skill/config.json" "$SKILL_DIR/config.json"
echo "  Skill files copied."

# 3. MCP server config (via mcporter)
echo ""
echo "[3/4] Swiggy MCP server configuration"

if ! command -v mcporter &>/dev/null; then
  echo "  mcporter not found. Installing..."
  npm install -g mcporter
fi

echo "  Adding Swiggy MCP servers via mcporter..."
mcporter config add swiggy-instamart --url https://mcp.swiggy.com/im --scope home 2>/dev/null || true
mcporter config add swiggy-food --url https://mcp.swiggy.com/food --scope home 2>/dev/null || true
mcporter config add swiggy-dineout --url https://mcp.swiggy.com/dineout --scope home 2>/dev/null || true
echo "  Done."

# 4. Instructions
echo ""
echo "[4/4] Authentication Instructions"
echo ""
echo "You must manually authenticate each domain you wish to use:"
echo "  mcporter auth swiggy-instamart"
echo "  mcporter auth swiggy-food"
echo "  mcporter auth swiggy-dineout"
echo ""
echo "=== Setup complete! ==="
