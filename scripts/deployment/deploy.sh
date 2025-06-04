#!/bin/bash
# AQEA Distributed Extractor - Deployment Script
# 
# Dieses Skript installiert den AQEA Distributed Extractor auf einem neuen Server
# Nutzung: ./deploy.sh [hostname] [user]

set -e  # Exit on any error

# Default values
HOST=${1:-"aqea-server"}
USER=${2:-"aqea"}
INSTALL_DIR="/opt/aqea-distributed-extractor"
REPO_URL="https://github.com/nextX-AG/aqea-distributed-extractor.git"
BRANCH="main"

echo "🚀 Deploying AQEA Distributed Extractor to $HOST as $USER"

# Create deployment directory structure
echo "📁 Creating directory structure..."
ssh $USER@$HOST "sudo mkdir -p $INSTALL_DIR && sudo chown $USER:$USER $INSTALL_DIR"

# Clone or update repository
echo "📥 Cloning repository..."
ssh $USER@$HOST "if [ -d $INSTALL_DIR/.git ]; then 
  cd $INSTALL_DIR && git pull origin $BRANCH; 
else 
  git clone -b $BRANCH $REPO_URL $INSTALL_DIR; 
fi"

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
ssh $USER@$HOST "cd $INSTALL_DIR && python3.11 -m venv aqea-venv && 
  source aqea-venv/bin/activate && 
  pip install --upgrade pip && 
  pip install -r requirements.txt"

# Install systemd service files
echo "⚙️ Installing systemd service files..."
scp scripts/deployment/aqea-master.service $USER@$HOST:/tmp/
scp scripts/deployment/aqea-worker@.service $USER@$HOST:/tmp/
ssh $USER@$HOST "sudo mv /tmp/aqea-master.service /etc/systemd/system/ && 
  sudo mv /tmp/aqea-worker@.service /etc/systemd/system/ && 
  sudo systemctl daemon-reload"

# Start services
echo "▶️ Starting services..."
ssh $USER@$HOST "sudo systemctl enable aqea-master.service &&
  sudo systemctl start aqea-master.service &&
  sleep 5 &&  # Give master time to start up
  for i in {1..4}; do
    sudo systemctl enable aqea-worker@\$i.service
    sudo systemctl start aqea-worker@\$i.service
  done"

# Check status
echo "🔍 Checking service status..."
ssh $USER@$HOST "sudo systemctl status aqea-master.service"
ssh $USER@$HOST "for i in {1..4}; do sudo systemctl status aqea-worker@\$i.service; done"

echo "✅ Deployment completed successfully!"
echo "🌐 Master dashboard available at: http://$HOST:8080/api/status"
echo "📊 To monitor logs: ssh $USER@$HOST 'sudo journalctl -f -u aqea-master.service'" 