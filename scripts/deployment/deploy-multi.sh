#!/bin/bash
# AQEA Distributed Extractor - Multi-Server Deployment Script
# 
# Dieses Skript installiert den AQEA Distributed Extractor auf mehreren Servern
# mit einem Master und mehreren Worker-Servern.
# Nutzung: ./deploy-multi.sh config.json

set -e  # Exit on any error

CONFIG_FILE=${1:-"deploy-config.json"}

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Konfigurationsdatei $CONFIG_FILE nicht gefunden!"
    echo "Bitte erstelle eine Konfigurationsdatei im folgenden Format:"
    echo '{
        "master": {
            "host": "aqea-master.example.com",
            "user": "aqea",
            "port": 8080
        },
        "workers": [
            {
                "host": "aqea-worker1.example.com",
                "user": "aqea",
                "workers": 4
            },
            {
                "host": "aqea-worker2.example.com",
                "user": "aqea",
                "workers": 8
            }
        ]
    }'
    exit 1
fi

# Lade Konfiguration
echo "📋 Lade Konfiguration aus $CONFIG_FILE..."
MASTER_HOST=$(jq -r '.master.host' $CONFIG_FILE)
MASTER_USER=$(jq -r '.master.user' $CONFIG_FILE)
MASTER_PORT=$(jq -r '.master.port' $CONFIG_FILE)
WORKER_COUNT=$(jq -r '.workers | length' $CONFIG_FILE)

INSTALL_DIR="/opt/aqea-distributed-extractor"
REPO_URL="https://github.com/nextX-AG/aqea-distributed-extractor.git"
BRANCH="main"

# Funktion zum Installieren des Basis-Systems
install_base() {
    local HOST=$1
    local USER=$2
    
    echo "📁 Erstelle Verzeichnisstruktur auf $HOST..."
    ssh $USER@$HOST "sudo mkdir -p $INSTALL_DIR && sudo chown $USER:$USER $INSTALL_DIR"
    
    echo "📥 Klone Repository auf $HOST..."
    ssh $USER@$HOST "if [ -d $INSTALL_DIR/.git ]; then 
      cd $INSTALL_DIR && git pull origin $BRANCH; 
    else 
      git clone -b $BRANCH $REPO_URL $INSTALL_DIR; 
    fi"
    
    echo "🐍 Richte Python-Umgebung auf $HOST ein..."
    ssh $USER@$HOST "cd $INSTALL_DIR && python3.11 -m venv aqea-venv && 
      source aqea-venv/bin/activate && 
      pip install --upgrade pip && 
      pip install -r requirements.txt"
}

# Installiere Master
echo "🚀 Installiere Master auf $MASTER_HOST..."
install_base $MASTER_HOST $MASTER_USER

echo "⚙️ Installiere Master-Service-Datei..."
scp scripts/deployment/aqea-master.service $MASTER_USER@$MASTER_HOST:/tmp/
ssh $MASTER_USER@$MASTER_HOST "sudo mv /tmp/aqea-master.service /etc/systemd/system/ && 
  sudo systemctl daemon-reload && 
  sudo systemctl enable aqea-master.service && 
  sudo systemctl start aqea-master.service"

echo "✅ Master-Installation abgeschlossen"

# Warte kurz, damit der Master starten kann
sleep 5

# Installiere Worker auf verschiedenen Servern
for (( i=0; i<$WORKER_COUNT; i++ )); do
    WORKER_HOST=$(jq -r ".workers[$i].host" $CONFIG_FILE)
    WORKER_USER=$(jq -r ".workers[$i].user" $CONFIG_FILE)
    WORKER_INSTANCES=$(jq -r ".workers[$i].workers" $CONFIG_FILE)
    
    echo "🚀 Installiere Worker auf $WORKER_HOST ($WORKER_INSTANCES Instanzen)..."
    install_base $WORKER_HOST $WORKER_USER
    
    # Generiere angepasste Worker-Service-Datei für diesen Host
    cat > /tmp/aqea-worker@.service << EOF
[Unit]
Description=AQEA Distributed Extractor - Worker %i
After=network.target

[Service]
Type=simple
User=$WORKER_USER
Group=$WORKER_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/aqea-venv/bin/python -m src.main start-worker --worker-id $WORKER_HOST-%i --master-host $MASTER_HOST --master-port $MASTER_PORT
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aqea-worker-%i
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1

[Install]
WantedBy=multi-user.target
EOF

    echo "⚙️ Installiere Worker-Service-Dateien auf $WORKER_HOST..."
    scp /tmp/aqea-worker@.service $WORKER_USER@$WORKER_HOST:/tmp/
    ssh $WORKER_USER@$WORKER_HOST "sudo mv /tmp/aqea-worker@.service /etc/systemd/system/ && 
      sudo systemctl daemon-reload"
    
    echo "▶️ Starte Worker-Instanzen auf $WORKER_HOST..."
    ssh $WORKER_USER@$WORKER_HOST "for j in \$(seq 1 $WORKER_INSTANCES); do
      sudo systemctl enable aqea-worker@\$j.service
      sudo systemctl start aqea-worker@\$j.service
    done"
    
    echo "✅ Worker-Installation auf $WORKER_HOST abgeschlossen"
done

echo "
🎉 Deployment auf allen Servern abgeschlossen!

📊 System-Übersicht:
- Master: http://$MASTER_HOST:$MASTER_PORT/api/status
- Master Logs: ssh $MASTER_USER@$MASTER_HOST 'sudo journalctl -f -u aqea-master.service'

💡 Worker-Logs auf einem bestimmten Server abrufen:
ssh [worker-user]@[worker-host] 'sudo journalctl -f -u \"aqea-worker@*.service\"'
" 