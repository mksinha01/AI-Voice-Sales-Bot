#!/usr/bin/env bash
# ==============================================================================
# deploy/setup-vultr.sh
# Production Bootstrap Script for AI Voice Sales Bot on Vultr Cloud Compute
# Supported OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
# ==============================================================================
set -e

echo "=========================================================="
echo " Provisioning AI Voice Sales Bot on Vultr Cloud Compute   "
echo "=========================================================="

# 1. Ensure script is run with sudo / root
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root or with sudo: sudo ./deploy/setup-vultr.sh"
  exit 1
fi

echo "[1/7] Updating system packages..."
apt-get update -y
apt-get install -y --no-install-recommends curl git ufw ca-certificates

# Auto-configure swapfile if server RAM is under 2GB (prevents Docker build OOM crashes)
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM_MB" -lt 2000 ] && [ $(swapon --show | wc -l) -le 1 ]; then
    echo "[+] RAM is ${TOTAL_RAM_MB}MB (<2GB). Setting up 2GB swap space for stability..."
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# 2. Install Docker & Docker Compose plugin if missing
if ! command -v docker &> /dev/null; then
    echo "[2/7] Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
    systemctl enable docker
    systemctl start docker
else
    echo "[2/7] Docker is already installed: $(docker --version)"
fi

# 3. Configure UFW Host Firewall (Allow 22/SSH, 80/HTTP, 443/HTTPS)
echo "[3/7] Configuring UFW host firewall rules..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP (Let Encrypt Auth)'
ufw allow 443/tcp comment 'HTTPS (WebRTC Web Client)'
ufw --force enable

# 4. Ensure data directories exist with proper permissions
echo "[4/7] Setting up persistent storage..."
mkdir -p data/recordings
chmod 755 data data/recordings

# 5. Check environment configuration
echo "[5/7] Checking environment configuration..."
if [ ! -f .env ]; then
    if [ -f .env.production.example ]; then
        cp .env.production.example .env
        echo "=========================================================="
        echo " [!] Created .env from .env.production.example template. "
        echo " [!] Please edit .env with your credentials and domain:   "
        echo "     nano .env                                           "
        echo "     Then re-run: docker compose up -d --build           "
        echo "=========================================================="
        exit 0
    else
        echo "[-] ERROR: .env file not found. Please create .env before deploying."
        exit 1
    fi
fi

# 6. Build and launch Docker Compose stack
echo "[6/7] Building and starting production containers..."
docker compose pull caddy
docker compose up -d --build

echo "[7/7] Verifying container status..."

echo ""
echo "=========================================================="
echo " Deployment Successfully Started!                         "
echo "=========================================================="
docker compose ps
echo ""
echo "Helpful commands:"
echo " - View live logs:     docker compose logs -f"
echo " - Restart stack:      docker compose restart"
echo " - Check health:       curl -k https://localhost/api/health"
echo "=========================================================="
