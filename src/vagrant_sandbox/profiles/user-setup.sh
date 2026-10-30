#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/workspace"
if ! grep -Fq "alias ll=" "$HOME/.bashrc"; then
  cat >> "$HOME/.bashrc" <<'EOF'

# --- dev sandbox ---
alias ll='ls -alF'
alias gs='git status'
cd ~/workspace 2>/dev/null || true
EOF
fi
git config --global init.defaultBranch main

