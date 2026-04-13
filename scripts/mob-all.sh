#!/usr/bin/env bash
# Launch every critter in its own Terminal.app tab.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANIMALS=(frog dog cat turtle slime)

for animal in "${ANIMALS[@]}"; do
  osascript <<EOF >/dev/null
tell application "Terminal"
  activate
  tell application "System Events" to keystroke "t" using command down
  delay 0.2
  do script "cd ${PROJECT_DIR} && uv run mob ${animal}" in front window
end tell
EOF
done
