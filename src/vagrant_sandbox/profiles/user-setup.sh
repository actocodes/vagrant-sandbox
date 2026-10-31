#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/workspace"
if ! grep -Fq "alias ll=" "$HOME/.bashrc"; then
  printf "\n# --- dev sandbox ---\nalias ll='ls -alF'\nalias gs='git status'\ncd ~/workspace 2>/dev/null || true\n" >> "$HOME/.bashrc"
fi
git config --global init.defaultBranch main
