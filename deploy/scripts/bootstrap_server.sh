#!/usr/bin/env bash
# One-time setup of kh-core (Ubuntu 24.04 arm64). Safe on a VM that already runs Docker,
# host nginx and other containers (e.g. Apache Guacamole): it never removes or restarts them
# unless noted, and never overwrites an existing /etc/docker/daemon.json.
set -euo pipefail

sudo apt update
sudo apt -y install git curl jq unzip htop tmux build-essential netfilter-persistent

# Docker: keep an existing install (Ubuntu docker.io or docker-ce); only add what is missing
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
if ! docker compose version >/dev/null 2>&1; then
  sudo apt -y install docker-compose-v2
fi
if ! docker buildx version >/dev/null 2>&1; then
  sudo apt -y install docker-buildx
fi
sudo usermod -aG docker "$USER"
if [ ! -s /etc/docker/daemon.json ]; then
  echo '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' \
    | sudo tee /etc/docker/daemon.json
  echo "NOTE: run 'sudo systemctl restart docker' when a restart of running containers is acceptable."
else
  echo "Keeping existing /etc/docker/daemon.json"
fi

# swap (safety net)
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl --system
fi

# host firewall for 80/443 only if not already allowed (Oracle Ubuntu images block by default)
for port in 80 443; do
  if ! sudo iptables -C INPUT -m state --state NEW -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT
  fi
done
sudo netfilter-persistent save

# certbot for the existing host nginx (used at first deploy)
sudo apt -y install certbot python3-certbot-nginx

# Python toolchain and Claude Code (terminal CLI, native installer)
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash

sudo mkdir -p /opt/kharcha && sudo chown "$USER":"$USER" /opt/kharcha
echo "Done. Log out and back in (docker group, PATH), then run: claude --version"
