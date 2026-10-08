#!/usr/bin/env bash
# One-time setup of the single Oracle VM kh-core (Ubuntu 24.04 arm64). PRD §24.
# Installs: base tools, 4G swap, Docker + compose, host firewall for 80/443, tmux, uv, Claude Code.
set -euo pipefail

sudo apt update && sudo apt -y upgrade
sudo timedatectl set-timezone Asia/Kolkata
sudo apt -y install git curl jq unzip htop tmux build-essential netfilter-persistent

# swap (safety net; the stacks fit in RAM)
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl --system
fi

# Docker Engine + compose plugin, with log rotation
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
echo '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' \
  | sudo tee /etc/docker/daemon.json && sudo systemctl restart docker

# host firewall: Oracle Ubuntu images reject inbound traffic by default; open web ports only
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80  -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# Python toolchain and Claude Code (terminal CLI, native installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash

# release checkout location for the hosted stack
sudo mkdir -p /opt/kharcha && sudo chown "$USER":"$USER" /opt/kharcha

echo "Done. Log out and back in (docker group), then run: claude --version"
