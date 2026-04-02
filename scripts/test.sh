#!/usr/bin/env bash
# Manual test for swiggy-agent skill
set -euo pipefail

echo "=== Swiggy Agent Test ==="
echo ""

# Check gateway
if ! openclaw gateway status 2>/dev/null | grep -q "Runtime: running"; then
  echo "FAIL: OpenClaw gateway is not running."
  echo "Start it: openclaw gateway start"
  exit 1
fi
echo "[OK] Gateway is running"

# Check skill is installed
SKILL_DIR="$HOME/.openclaw/skills/openclaw-swiggy-skill"
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
  echo "FAIL: Skill not installed at $SKILL_DIR"
  echo "Run: ./scripts/install.sh"
  exit 1
fi
echo "[OK] Skill is installed"

# Check mcporter
if ! command -v mcporter &>/dev/null; then
  echo "FAIL: mcporter not installed. Run: npm install -g mcporter"
  exit 1
fi

echo "[OK] mcporter is installed"
echo ""
echo "Note: You must run the unified Python auth script (e.g., 'python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_unified_mcp_login.py') first."
echo "Running the Swiggy Agent in a dry-run test mode..."
echo "---"
RESULT=$(openclaw agent --agent omi -m "Run the Swiggy Agent skill to search for pizzas. Do NOT place an order. Tell me what you found." 2>&1)
echo "$RESULT"
echo "---"

echo "[INFO] Test execution finished. Check output to see if it correctly retrieved food items."
