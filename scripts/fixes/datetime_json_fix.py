#!/usr/bin/env python3
"""
Fix für das Problem mit der datetime-JSON-Serialisierung.

Dieses Skript modifiziert die Dateien, die JSON-Serialisierung für Objekte durchführen,
um sicherzustellen, dass datetime-Objekte korrekt serialisiert werden.
"""

import re
import os
import datetime
from pathlib import Path

def create_datetime_encoder():
    return """
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)
"""

def update_file(filepath, import_fix=True, encoder_fix=True):
    """Aktualisiert eine Datei mit der datetime-JSON-Serialisierung."""
    print(f"Updating {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Füge datetime-Import hinzu, wenn nötig
    if import_fix and 'import datetime' not in content and 'from datetime import' not in content:
        content = 'import datetime\n' + content
    
    # Füge den DateTimeEncoder hinzu, wenn nötig
    if encoder_fix and 'class DateTimeEncoder' not in content:
        # Finde die Stelle nach den Imports
        import_section_end = re.search(r'(^import .*$|^from .* import .*$)', content, re.MULTILINE)
        if import_section_end:
            pos = content.rfind('\n', 0, import_section_end.end()) + 1
            content = content[:pos] + create_datetime_encoder() + content[pos:]
        else:
            # Füge es am Anfang ein, wenn keine Imports gefunden wurden
            content = create_datetime_encoder() + content
    
    # Ersetze web.json_response() Aufrufe
    if 'web.json_response' in content:
        content = re.sub(
            r'web\.json_response\((.*?)\)',
            r'web.json_response(\1, dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))',
            content
        )
    
    # Ersetze json.dumps() Aufrufe
    if 'json.dumps' in content and 'cls=DateTimeEncoder' not in content:
        content = re.sub(
            r'json\.dumps\((.*?)\)',
            r'json.dumps(\1, cls=DateTimeEncoder)',
            content
        )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {filepath}")

def find_and_fix_files(src_dir):
    """Findet alle relevanten Dateien und wendet die Fixes an."""
    src_path = Path(src_dir)
    
    # Finde alle Python-Dateien, die json verwenden
    for py_file in src_path.glob('**/*.py'):
        with open(py_file, 'r') as f:
            content = f.read()
        
        # Prüfe, ob die Datei json.dumps oder web.json_response verwendet
        if ('json.dumps' in content or 'web.json_response' in content) and 'import json' in content:
            update_file(py_file)

if __name__ == "__main__":
    # Pfad zur src-Directory
    src_dir = Path(__file__).parent.parent.parent / 'src'
    
    # Explizite Dateien aktualisieren
    update_file(src_dir / 'coordinator' / 'master.py')
    
    # Weitere Dateien finden und aktualisieren
    find_and_fix_files(src_dir)
    
    print("\n✅ Alle datetime-JSON-Serialisierungsprobleme wurden behoben!")
    print("🔄 Bitte starte die Services neu, um die Änderungen zu übernehmen:")
    print("   sudo systemctl restart aqea-master.service")
    print("   sudo systemctl restart 'aqea-worker@*.service'") 