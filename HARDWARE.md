# AQEA Distributed Extractor - Hardware Setup

## 🖥️ Hardwareanforderungen

### Master-Server
- **CPU**: 2-4 vCPUs
- **RAM**: 4-8 GB
- **Speicher**: 40 GB SSD
- **Betriebssystem**: Ubuntu 22.04 LTS
- **Netzwerk**: 1 Gbit/s
- **Empfohlener Hetzner-Typ**: CPX21 (2 vCPU, 4 GB RAM)

### Worker-Server
- **CPU**: 2-8 vCPUs (je nach Skalierungsbedarf)
- **RAM**: 4-16 GB (je nach Sprachvolumen)
- **Speicher**: 40 GB SSD
- **Betriebssystem**: Ubuntu 22.04 LTS
- **Netzwerk**: 1 Gbit/s
- **Empfohlener Hetzner-Typ**: 
  - Kleine Worker: CPX21 (2 vCPU, 4 GB RAM)
  - Mittlere Worker: CPX31 (4 vCPU, 8 GB RAM)
  - Große Worker: CPX41 (8 vCPU, 16 GB RAM)

## ☁️ Hetzner Cloud Setup

### 1. Einrichtung der Server

#### 1.1 Projekterstellung in Hetzner Cloud
1. Bei [Hetzner Cloud](https://console.hetzner.cloud/) anmelden
2. Neues Projekt "AQEA-Distributed-Extractor" erstellen
3. Auf "Add Server" klicken

#### 1.2 Master-Server erstellen
1. Serverstandort wählen (z.B. Nürnberg oder Helsinki)
2. Image: Ubuntu 22.04 LTS
3. Typ: CPX21 (2 vCPU, 4 GB RAM)
4. Netzwerk: Neues Netzwerk "aqea-network" erstellen (10.0.0.0/16)
5. Firewallregeln:
   - SSH: Port 22
   - HTTP: Port 8080 (Master API)
6. SSH-Schlüssel hinzufügen oder Passwort generieren
7. Servername: "aqea-master"
8. Auf "Create & Buy" klicken

#### 1.3 Worker-Server erstellen
1. Die gleichen Schritte wie für den Master-Server
2. Typ je nach Bedarf wählen (CPX21/CPX31/CPX41)
3. Gleiches Netzwerk "aqea-network" auswählen
4. Firewallregeln:
   - SSH: Port 22
5. Servernamen: "aqea-worker-01", "aqea-worker-02", usw.

### 2. Netzwerkkonfiguration

#### 2.1 Netzwerkübersicht
- **Master-Server**: 10.0.0.10/16
- **Worker-01**: 10.0.0.11/16
- **Worker-02**: 10.0.0.12/16
- **Worker-XX**: 10.0.0.XX/16

#### 2.2 Firewallkonfiguration
1. Firewallgruppe "aqea-firewall" erstellen
2. Regeln hinzufügen:
   - Eingehender Traffic auf Port 22 (SSH) von überall erlauben
   - Eingehender Traffic auf Port 8080 (Master API) vom internen Netzwerk erlauben
   - Interner Traffic zwischen allen Servern im 10.0.0.0/16 Netzwerk erlauben
   - Ausgehenden Traffic zu allen Zielen erlauben

### 3. Deployment

#### 3.1 Deployment-Skript anpassen
Die Konfigurationsdatei `scripts/deployment/deploy-config.json` anpassen:

```json
{
    "master": {
        "host": "10.0.0.10",
        "user": "root",
        "port": 8080
    },
    "workers": [
        {
            "host": "10.0.0.11",
            "user": "root",
            "workers": 4
        },
        {
            "host": "10.0.0.12",
            "user": "root", 
            "workers": 8
        }
    ]
}
```

#### 3.2 Multi-Server-Deployment ausführen
```bash
cd /path/to/aqea-distributed-extractor
./scripts/deployment/deploy-multi.sh scripts/deployment/deploy-config.json
```

## 📈 Skalierungsstrategie

### 4.1 Horizontale Skalierung
- **Kleine Sprachmodelle** (z.B. Deutsch, Englisch): 2-3 Worker-Server
- **Mittlere Sprachmodelle** (z.B. Französisch, Spanisch, Italienisch): 3-5 Worker-Server
- **Große Sprachmodelle** (z.B. Chinesisch, Russisch): 5-8 Worker-Server

### 4.2 Vertikale Skalierung
- **Speicherintensive Sprachen** (z.B. Chinesisch, Japanisch): Mehr RAM pro Worker (CPX41/CCX41)
- **CPU-intensive Verarbeitung**: Mehr vCPUs pro Worker (CPX41/CCX41)

### 4.3 Auto-Scaling (zukünftige Erweiterung)
- Hetzner Cloud API nutzen, um Worker-Server dynamisch zu starten/stoppen
- Load-Balancing zwischen Worker-Servern basierend auf CPU-Auslastung
- Kostenkontrolle durch automatisches Herunterfahren bei Inaktivität

## 💾 Backup-Strategie

### 5.1 Regelmäßige Snapshots
- Tägliche Snapshots des Master-Servers
- Wöchentliche Snapshots der Worker-Server

### 5.2 Datenbackup
- Regelmäßige Datenbank-Backups (falls Supabase verwendet wird)
- Backup der extrahierten AQEA-Daten auf S3-kompatiblen Speicher

## 📊 Monitoring

### 6.1 Server-Monitoring
- Hetzner Cloud Monitoring aktivieren
- Prometheus + Grafana für detaillierte Metriken

### 6.2 Anwendungs-Monitoring
- Worker-Metriken an Master senden
- Master-Dashboard zur Überwachung der Verarbeitungsraten und Fehler

## 🛡️ Sicherheit

### 7.1 Basis-Sicherheit
- Regelmäßige System-Updates
- Firewallkonfiguration wie oben beschrieben
- SSH nur mit Schlüsseln, kein Passwort-Login

### 7.2 Anwendungssicherheit
- API-Token für Worker-Master-Kommunikation
- HTTPS für API-Endpoints (in Zukunft)
- Rate-Limiting für API-Zugriffe

## 💰 Kostenschätzung

### 8.1 Monatliche Kosten
- Master-Server (CPX21): ~10,59 € / Monat
- Worker-Server (CPX21): ~10,59 € / Monat pro Server
- Worker-Server (CPX31): ~19,90 € / Monat pro Server
- Worker-Server (CPX41): ~34,90 € / Monat pro Server

### 8.2 Beispielkonfiguration
- 1x Master (CPX21)
- 3x Worker (CPX21)
- Geschätzte Gesamtkosten: ~42,36 € / Monat 