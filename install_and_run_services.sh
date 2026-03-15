#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="${PROJECT_DIR}/services"
SERVICE_FILES=("my-google-adk.service" "telegram.service")
SYSTEMD_DIR="/etc/systemd/system"
ENV_SYMLINK="/etc/default/local-adk-agent"

echo "🚀 Installing systemd services for Local ADK Agent Bot..."

# 1. Create Symlink for Environment File
echo "🔗 Linking .env to ${ENV_SYMLINK}..."
sudo ln -sf "${PROJECT_DIR}/.env" "${ENV_SYMLINK}"

# 2. Copy and Register Service Files
for service in "${SERVICE_FILES[@]}"; do
    echo "📋 Copying ${service} to ${SYSTEMD_DIR}..."
    sudo cp "${SERVICE_DIR}/${service}" "${SYSTEMD_DIR}/"
done

# 3. Reload Daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# 4. Enable and Restart Services
for service in "${SERVICE_FILES[@]}"; do
    echo "⚡ Enabling and restarting ${service}..."
    sudo systemctl enable "${service}"
    sudo systemctl restart "${service}"
done

echo "✅ Services installed and started successfully!"
echo "📈 Use 'journalctl -u my-google-adk.service -f' to view logs."
