#!/usr/bin/env python3
"""
Fix für das Session-Management-Problem.

Dieses Skript modifiziert die Worker-Klasse, um sicherzustellen, dass
alle Client-Sessions korrekt geschlossen werden.
"""

import re
import os
from pathlib import Path

def fix_session_management(filepath):
    """Behebt das Session-Management-Problem im Worker."""
    print(f"Fixing session management in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Prüfen, ob eine cleanup_sessions-Methode bereits existiert
    if 'async def cleanup_sessions' in content:
        print("cleanup_sessions-Methode existiert bereits, Überprüfe auf Vollständigkeit...")
        
        # Prüfen, ob die Methode vollständig ist
        cleanup_method_match = re.search(r'async def cleanup_sessions.*?def', content, re.DOTALL)
        if cleanup_method_match:
            cleanup_method = cleanup_method_match.group(0)[:-3].strip()  # Entferne das letzte 'def'
            
            # Prüfen, ob die Methode den Session-Cleanup durchführt
            if 'self.session' in cleanup_method and 'await self.session.close()' in cleanup_method:
                print("Session-Cleanup-Logik ist bereits vorhanden.")
            else:
                # Füge Session-Cleanup hinzu
                updated_method = re.sub(
                    r'async def cleanup_sessions\s*\(\s*self\s*\):\s*',
                    'async def cleanup_sessions(self):\n        if hasattr(self, "session") and self.session:\n            await self.session.close()\n        ',
                    cleanup_method
                )
                content = content.replace(cleanup_method, updated_method)
    else:
        # Füge die cleanup_sessions-Methode hinzu
        class_match = re.search(r'class\s+Worker.*?:', content)
        if class_match:
            # Füge die Methode nach der letzten Methode in der Klasse hinzu
            last_method_match = re.search(r'async def\s+\w+.*?return\s+.*?\n', content, re.DOTALL)
            if last_method_match:
                insert_pos = last_method_match.end()
                cleanup_method = '\n    async def cleanup_sessions(self):\n        if hasattr(self, "session") and self.session:\n            await self.session.close()\n'
                content = content[:insert_pos] + cleanup_method + content[insert_pos:]
    
    # Füge Aufrufe für cleanup_sessions ein
    
    # 1. Füge einen Aufruf in der stop-Methode hinzu
    stop_method_match = re.search(r'async def stop\s*\(\s*self.*?\):(.*?)(return|$)', content, re.DOTALL)
    if stop_method_match:
        stop_method_body = stop_method_match.group(1)
        
        # Füge den Aufruf hinzu, wenn er noch nicht existiert
        if 'await self.cleanup_sessions()' not in stop_method_body:
            updated_stop_body = stop_method_body.rstrip() + '\n        await self.cleanup_sessions()\n        '
            content = content.replace(stop_method_body, updated_stop_body)
    
    # 2. Füge einen Aufruf in der __del__-Methode hinzu, falls sie existiert
    del_method_match = re.search(r'def __del__\s*\(\s*self\s*\):(.*?)(def|\Z)', content, re.DOTALL)
    if del_method_match:
        del_method_body = del_method_match.group(1)
        
        # Füge den Aufruf hinzu, wenn er noch nicht existiert
        if 'cleanup_sessions' not in del_method_body:
            updated_del_body = del_method_body.rstrip() + '\n        import asyncio\n        try:\n            asyncio.run(self.cleanup_sessions())\n        except Exception:\n            pass\n        '
            content = content.replace(del_method_body, updated_del_body)
    else:
        # Füge eine __del__-Methode hinzu
        class_end = re.search(r'class\s+Worker.*?:(.*?)(\Z|class)', content, re.DOTALL)
        if class_end:
            insert_pos = class_end.end(1)
            del_method = '\n    def __del__(self):\n        import asyncio\n        try:\n            asyncio.run(self.cleanup_sessions())\n        except Exception:\n            pass\n'
            content = content[:insert_pos] + del_method + content[insert_pos:]
    
    # 3. Füge einen Aufruf in __aenter__/__aexit__ hinzu, falls das Worker-Objekt als Context Manager verwendet wird
    if 'async def __aenter__' in content:
        aexit_method_match = re.search(r'async def __aexit__\s*\(\s*self.*?\):(.*?)(return|$)', content, re.DOTALL)
        if aexit_method_match:
            aexit_method_body = aexit_method_match.group(1)
            
            # Füge den Aufruf hinzu, wenn er noch nicht existiert
            if 'await self.cleanup_sessions()' not in aexit_method_body:
                updated_aexit_body = aexit_method_body.rstrip() + '\n        await self.cleanup_sessions()\n        '
                content = content.replace(aexit_method_body, updated_aexit_body)
    
    # Schreibe die aktualisierte Datei zurück
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed session management in {filepath}")

if __name__ == "__main__":
    # Pfad zum Worker
    src_dir = Path(__file__).parent.parent.parent / 'src'
    worker_path = src_dir / 'workers' / 'worker.py'
    
    if worker_path.exists():
        fix_session_management(worker_path)
        print("\n✅ Session-Management wurde erfolgreich repariert!")
        print("🔄 Bitte starte die Services neu, um die Änderungen zu übernehmen:")
        print("   sudo systemctl restart aqea-master.service")
        print("   sudo systemctl restart 'aqea-worker@*.service'")
    else:
        print(f"❌ Worker nicht gefunden unter {worker_path}")
        print("Bitte überprüfe den Pfad und versuche es erneut.") 