#!/usr/bin/env python3
"""
AQEA Distributed Extractor - Cloud Config Generator

Dieses Skript generiert angepasste Cloud-Config-Dateien für Hetzner Cloud
basierend auf Templates und benutzerdefinierten Einstellungen.
"""

import os
import sys
import argparse
import yaml
import json
from pathlib import Path

def load_template(template_type):
    """Lädt ein Cloud-Config-Template aus einer Datei."""
    template_path = Path(__file__).parent / f"cloud-config-{template_type}.yml"
    
    if not template_path.exists():
        print(f"Fehler: Template-Datei {template_path} nicht gefunden!")
        sys.exit(1)
    
    with open(template_path, 'r') as f:
        return f.read()

def add_ssh_key(config_str, ssh_key):
    """Fügt den SSH-Schlüssel in die Cloud-Config ein."""
    # Hier wird ein einfacher String-Ersatz durchgeführt
    return config_str.replace("# HIER DEINEN SSH PUBLIC KEY EINFÜGEN", ssh_key.strip())

def update_master_config(config_str, **kwargs):
    """Aktualisiert die Master-Konfiguration mit benutzerdefinierten Werten."""
    # Hier könnten weitere Anpassungen vorgenommen werden
    return config_str

def update_worker_config(config_str, master_host, master_port, workers_per_server):
    """Aktualisiert die Worker-Konfiguration mit benutzerdefinierten Werten."""
    # Ersetze die Standardwerte im Environment-Block
    lines = config_str.split('\n')
    for i, line in enumerate(lines):
        if "MASTER_HOST=" in line:
            lines[i] = f"      MASTER_HOST={master_host}"
        elif "MASTER_PORT=" in line:
            lines[i] = f"      MASTER_PORT={master_port}"
        elif "WORKERS_PER_SERVER=" in line:
            lines[i] = f"      WORKERS_PER_SERVER={workers_per_server}"
    
    return '\n'.join(lines)

def generate_configs(args):
    """Generiert Cloud-Config-Dateien basierend auf den Eingabeparametern."""
    # Master-Config generieren
    if args.generate_master or args.generate_all:
        master_template = load_template("master")
        master_config = add_ssh_key(master_template, args.ssh_key)
        master_config = update_master_config(master_config)
        
        master_output = Path(args.output_dir) / f"cloud-config-master-{args.project}.yml"
        with open(master_output, 'w') as f:
            f.write(master_config)
        print(f"Master-Config generiert: {master_output}")
    
    # Worker-Configs generieren
    if args.generate_workers or args.generate_all:
        worker_template = load_template("worker")
        
        for i, worker in enumerate(args.workers):
            worker_config = add_ssh_key(worker_template, args.ssh_key)
            worker_config = update_worker_config(
                worker_config,
                master_host=args.master_host,
                master_port=args.master_port,
                workers_per_server=worker.get('workers_per_server', 4)
            )
            
            worker_output = Path(args.output_dir) / f"cloud-config-worker-{i+1}-{args.project}.yml"
            with open(worker_output, 'w') as f:
                f.write(worker_config)
            print(f"Worker-Config {i+1} generiert: {worker_output}")

def parse_workers_json(workers_json):
    """Parst die JSON-Konfiguration für Worker-Server."""
    try:
        if workers_json.startswith('@'):
            # Lade aus Datei
            file_path = Path(workers_json[1:])
            if not file_path.exists():
                print(f"Fehler: Worker-Konfigurationsdatei {file_path} nicht gefunden!")
                sys.exit(1)
            
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            # Direktes JSON parsen
            return json.loads(workers_json)
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der Worker-Konfiguration: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="AQEA Cloud Config Generator")
    parser.add_argument("--ssh-key", required=True, help="SSH Public Key oder Pfad zur Datei mit dem Key (mit '@' als Präfix)")
    parser.add_argument("--project", default="aqea", help="Projektname für die Dateibenennung")
    parser.add_argument("--output-dir", default=".", help="Ausgabeverzeichnis für die generierten Dateien")
    parser.add_argument("--master-host", default="10.0.0.10", help="IP-Adresse oder Hostname des Master-Servers")
    parser.add_argument("--master-port", default="8080", help="Port des Master-Servers")
    parser.add_argument("--generate-master", action="store_true", help="Generiere Master-Config")
    parser.add_argument("--generate-workers", action="store_true", help="Generiere Worker-Configs")
    parser.add_argument("--generate-all", action="store_true", help="Generiere Master- und Worker-Configs")
    parser.add_argument("--workers", default="[{\"workers_per_server\": 4}]", 
                        help="JSON-Array mit Worker-Konfigurationen oder Pfad zur JSON-Datei (mit '@' als Präfix)")
    
    args = parser.parse_args()
    
    # SSH-Schlüssel laden
    if args.ssh_key.startswith('@'):
        key_path = Path(args.ssh_key[1:])
        if not key_path.exists():
            print(f"Fehler: SSH-Key-Datei {key_path} nicht gefunden!")
            sys.exit(1)
        
        with open(key_path, 'r') as f:
            args.ssh_key = f.read().strip()
    
    # Worker-Konfiguration parsen
    args.workers = parse_workers_json(args.workers)
    
    # Ausgabeverzeichnis erstellen
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Konfigurationen generieren
    generate_configs(args)

if __name__ == "__main__":
    main() 