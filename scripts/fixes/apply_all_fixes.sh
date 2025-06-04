#!/bin/bash
# AQEA Distributed Extractor - Apply All Fixes
# 
# Dieses Skript wendet alle Fixes für bekannte Probleme an.

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Wende alle Fixes für den AQEA Distributed Extractor an..."

# 1. Datetime JSON Serialization Fix
echo -e "\n📅 Behebe das datetime-JSON-Serialisierungsproblem..."
python3 datetime_json_fix.py

# 2. AQEA Converter NoneType Fix
echo -e "\n🔤 Behebe das NoneType-Problem im AQEA Converter..."
python3 aqea_converter_fix.py

# 3. Session Management Fix
echo -e "\n🔄 Behebe das Session-Management-Problem..."
python3 session_management_fix.py

echo -e "\n✅ Alle Fixes wurden erfolgreich angewendet!"
echo "🔄 Bitte starte die Services neu, um alle Änderungen zu übernehmen:"
echo "   sudo systemctl restart aqea-master.service"
echo "   sudo systemctl restart 'aqea-worker@*.service'"

echo -e "\n💡 Hinweis: Diese Fixes wurden lokal angewendet. Wenn du auf mehreren Servern arbeitest,"
echo "   musst du das Repository pushen und auf allen Servern aktualisieren, oder"
echo "   dieses Skript auf jedem Server ausführen." 