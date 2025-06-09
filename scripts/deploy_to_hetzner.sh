#!/bin/bash
# Manuelles Deployment-Skript für AQEA Distributed Extractor auf Hetzner-Server

# Farben für bessere Lesbarkeit
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Konfiguration
MASTER_SERVER="157.180.67.142"      # aqea-master
WORKER1_SERVER="157.180.70.46"      # aqea-worker01
WORKER2_SERVER="37.27.0.192"        # aqea-worker02
WORKER3_SERVER="2a01:4f9:c013:c164::/64"  # aqea-worker03 (IPv6)
REPO_PATH="/opt/aqea-distributed-extractor"
BRANCH="feature/verbose-and-accumulation"

# Funktion zum Ausführen von SSH-Befehlen
run_ssh() {
    local server=$1
    local command=$2
    echo -e "${YELLOW}[SERVER $server]${NC} Führe aus: $command"
    ssh root@$server "$command"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SERVER $server]${NC} Befehl erfolgreich ausgeführt"
    else
        echo -e "${YELLOW}[SERVER $server]${NC} Befehl fehlgeschlagen mit Exit-Code $?"
    fi
}

# Deployment-Funktion
deploy_to_server() {
    local server=$1
    local is_master=$2

    echo -e "${GREEN}=== Deployment auf $server ===${NC}"
    
    # Aktualisiere Repository
    run_ssh $server "cd $REPO_PATH && git fetch && git checkout $BRANCH && git pull"
    
    # Virtuelle Umgebung aktualisieren
    run_ssh $server "cd $REPO_PATH && source aqea-venv/bin/activate && pip install -r requirements.txt"
    
    # Stelle sicher, dass Verzeichnisse existieren
    run_ssh $server "mkdir -p $REPO_PATH/logs $REPO_PATH/extracted_data $REPO_PATH/extracted_data/accumulated"
    
    # Stoppe laufende Prozesse
    run_ssh $server "pkill -f 'python -m src.main' || true"
    run_ssh $server "pkill -f 'python scripts/accumulating_worker.py' || true"
    
    # Starte Master oder Worker
    if [ "$is_master" = true ]; then
        echo -e "${GREEN}Starte Master auf $server${NC}"
        run_ssh $server "cd $REPO_PATH && source aqea-venv/bin/activate && nohup python -m src.main start-master --language de --workers 3 --source wiktionary --port 8080 --verbose > logs/master.log 2>&1 &"
    else
        local worker_id=$(echo $server | sed 's/\./-/g')
        echo -e "${GREEN}Starte akkumulierenden Worker auf $server${NC}"
        run_ssh $server "cd $REPO_PATH && source aqea-venv/bin/activate && nohup python scripts/accumulating_worker.py --worker-id worker-$worker_id --master-host $MASTER_SERVER --master-port 8080 --batch-size 500 --flush-interval 300 --verbose > logs/worker.log 2>&1 &"
    fi
    
    # Überprüfe, ob Prozesse laufen
    sleep 5
    run_ssh $server "ps aux | grep python"
    
    echo -e "${GREEN}=== Deployment auf $server abgeschlossen ===${NC}"
}

# Hauptteil
echo "AQEA Distributed Extractor - Manuelles Deployment auf Hetzner-Server"
echo "=============================================================="

# Frage nach Bestätigung
read -p "Möchten Sie das Deployment starten? (j/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Jj]$ ]]; then
    echo "Deployment abgebrochen."
    exit 1
fi

# Führe Deployment durch
deploy_to_server $MASTER_SERVER true
deploy_to_server $WORKER1_SERVER false
deploy_to_server $WORKER2_SERVER false

# IPv6 Server - nur wenn explizit gewählt
read -p "Möchten Sie auch auf dem IPv6-Server (worker03) deployen? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Jj]$ ]]; then
    deploy_to_server $WORKER3_SERVER false
fi

echo -e "${GREEN}Deployment abgeschlossen.${NC}"
echo "Prüfen Sie den Status mit: curl http://$MASTER_SERVER:8080/api/status" 