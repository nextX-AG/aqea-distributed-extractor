# AQEA Distributed Extractor - Cloud Config Setup

Diese Anleitung beschreibt, wie du die automatische Server-Einrichtung mit Hetzner Cloud und der mitgelieferten Cloud-Config-Datei durchführst.

## Voraussetzungen

- Ein Hetzner Cloud Konto
- SSH Public Key für den Server-Zugriff
- Git-Repository des AQEA Distributed Extractor

## Einrichtungsschritte

### 1. SSH Public Key vorbereiten

Füge deinen SSH Public Key in die `cloud-config.yml` Datei ein:

```yaml
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc... # Dein SSH Public Key hier
```

### 2. Cloud-Config bei Hetzner verwenden

#### Option A: Über die Hetzner Cloud Console

1. Melde dich bei der [Hetzner Cloud Console](https://console.hetzner.cloud/) an
2. Erstelle einen neuen Server
3. Wähle den Servertyp (CPX21 für Master, CPX21/31/41 für Worker)
4. Wähle als Betriebssystem Ubuntu 22.04
5. Scrolle nach unten zu "User data" und kopiere den Inhalt der `cloud-config.yml` Datei hinein
6. Erstelle den Server

#### Option B: Über die Hetzner CLI

```bash
hcloud server create --name aqea-master \
  --type cpx21 \
  --image ubuntu-22.04 \
  --ssh-key dein-ssh-key-name \
  --user-data-from-file cloud-config.yml
```

### 3. Master-Server konfigurieren

Nach der automatischen Einrichtung (ca. 5-10 Minuten) verbinde dich mit dem Server:

```bash
ssh aqea@<server-ip>
```

Prüfe den Status der AQEA-Services:

```bash
sudo systemctl status aqea-master
```

Falls nötig, starte den Master-Service:

```bash
sudo systemctl enable --now aqea-master
```

### 4. Worker-Server konfigurieren

Wiederhole die Schritte 1-2 für jeden Worker-Server.

Nach der automatischen Einrichtung, verbinde dich mit dem Worker:

```bash
ssh aqea@<worker-ip>
```

Starte die Worker-Instanzen (Anzahl je nach Serverkapazität):

```bash
# Starte 4 Worker-Instanzen auf diesem Server
sudo systemctl enable --now aqea-worker@{1..4}
```

## Besonderheiten für verschiedene Servertypen

### Master-Server

Die Cloud-Config richtet automatisch den Port 8080 für die Master-API ein.

### Worker-Server

Worker-Server benötigen keinen speziellen Port, sie verbinden sich zum Master.
Die `--master-host` Option in der Systemd-Service-Datei muss vor dem Start angepasst werden:

```bash
sudo sed -i 's/localhost/<master-server-ip>/g' /etc/systemd/system/aqea-worker@.service
sudo systemctl daemon-reload
```

## Fehlersuche

### Logs überprüfen

```bash
# Master-Logs
sudo journalctl -u aqea-master -f

# Worker-Logs
sudo journalctl -u aqea-worker@1 -f
```

### Firewall-Status prüfen

```bash
sudo ufw status
```

### Netzwerkverbindung zum Master testen

```bash
curl http://<master-ip>:8080/api/health
```

## Multi-Server-Setup mit Private Network

Für größere Deployments empfiehlt sich ein privates Netzwerk bei Hetzner:

1. Erstelle ein privates Netzwerk in der Hetzner Cloud Console
2. Füge alle Server diesem Netzwerk hinzu
3. Verwende die privaten IP-Adressen für die Kommunikation zwischen Master und Workers

### Anpassung der Worker-Config für privates Netzwerk

```bash
sudo sed -i 's/--master-host localhost/--master-host 10.0.0.10/g' /etc/systemd/system/aqea-worker@.service
sudo systemctl daemon-reload
``` 