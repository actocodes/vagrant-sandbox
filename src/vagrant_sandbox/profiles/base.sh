#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get upgrade -y
apt-get install -y build-essential git curl wget unzip jq vim tmux htop tree ripgrep ca-certificates gnupg ufw
timedatectl set-timezone UTC

