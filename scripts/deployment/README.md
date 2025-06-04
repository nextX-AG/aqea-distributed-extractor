# AQEA Distributed Extractor - Deployment

Dieses Verzeichnis enthält Skripte und Konfigurationsdateien für das Deployment des AQEA Distributed Extractor auf Produktionsservern.

## Voraussetzungen

- Linux-Server mit systemd
- Python 3.11 oder höher
- Git
- SSH-Zugriff auf die Zielserver
- Benutzer mit sudo-Rechten auf den Zielservern
- jq (für Multi-Server-Deployment)

## Deployment-Optionen

### Option 1: Single-Server Deployment

Für eine einfache Deployment auf einem einzelnen Server:

```bash
# Deployment auf einem einzelnen Server
./deploy.sh [hostname] [user]

# Beispiel
./deploy.sh aqea-server.example.com aqea
```

### Option 2: Multi-Server Deployment

Für ein verteiltes Setup mit einem Master und mehreren Worker-Servern:

1. Passe die Konfigurationsdatei an:

```bash
# Kopiere die Beispiel-Konfiguration
cp deploy-config.json my-config.json

# Bearbeite die Konfiguration
nano my-config.json
```

2. Führe das Multi-Server-Deployment aus:

```bash
./deploy-multi.sh my-config.json
```

## Systemd Service-Dateien

Die Deployment-Skripte installieren automatisch die folgenden systemd Service-Dateien:

- `aqea-master.service`: Master-Koordinator-Service
- `aqea-worker@.service`: Worker-Service (Template für mehrere Instanzen)

### Manuelle Verwaltung der Services

```bash
# Master-Service starten
sudo systemctl start aqea-master.service

# Worker-Services starten (für 4 Worker-Instanzen)
for i in {1..4}; do sudo systemctl start aqea-worker@$i.service; done

# Status überprüfen
sudo systemctl status aqea-master.service
sudo systemctl status 'aqea-worker@*.service'

# Logs anzeigen
sudo journalctl -f -u aqea-master.service
sudo journalctl -f -u 'aqea-worker@*.service'
```

## Bekannte Probleme und Lösungen

Wenn du auf Probleme stößt, versuche die folgenden Fixes:

1. **Datetime JSON-Serialisierungsproblem**: Wende `scripts/fixes/datetime_json_fix.py` an
2. **NoneType-Fehler im AQEA-Converter**: Wende `scripts/fixes/aqea_converter_fix.py` an
3. **Session-Management-Probleme**: Wende `scripts/fixes/session_management_fix.py` an

Oder führe alle Fixes gleichzeitig aus:

```bash
cd ../fixes
./apply_all_fixes.sh
```

## Skalierung

Um die Anzahl der Worker zu ändern:

1. **Auf einem einzelnen Server**:
   - Bearbeite die Anzahl der Worker in der for-Schleife im deploy.sh-Skript
   - Oder starte/stoppe Worker manuell mit systemctl

2. **In einem Multi-Server-Setup**:
   - Bearbeite die "workers"-Anzahl in der Konfigurationsdatei
   - Führe das deploy-multi.sh-Skript erneut aus

## Monitoring

Die Deployment-Skripte richten automatisch systemd-Services ein, die Logs an journald senden.
Für ein umfassenderes Monitoring sind folgende Optionen vorgesehen:

- Master-Status-API: http://[master-host]:8080/api/status
- Journalctl für Logs: `sudo journalctl -f -u aqea-master.service`
- Integrationsmöglichkeit mit Prometheus und Grafana (siehe TODO.md) 