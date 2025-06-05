#!/usr/bin/env python3
"""
Test Script für AQEA Supabase Integration mit offiziellem Client

Testet die Supabase-Verbindung mit dem offiziellen Python-Client.
"""

import asyncio
import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection using the official client."""
    print("🔌 Testing Supabase connection with official client...")
    
    try:
        # Hole die Supabase-URL und den API-Key aus den Umgebungsvariablen
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ SUPABASE_URL oder SUPABASE_KEY nicht gefunden!")
            return False
        
        print(f"URL: {supabase_url}")
        print(f"Key: {supabase_key[:10]}...{supabase_key[-5:]}")
        
        # Erstelle den Supabase-Client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Teste die Verbindung durch einen einfachen Health-Check
        try:
            # Verwende einen einfachen SQL-Befehl, um die Verbindung zu testen
            response = supabase.table('aqea_entries').select("*").limit(1).execute()
            print(f"✅ Verbindung erfolgreich! Antwort: {response}")
            return True
        except Exception as e:
            print(f"❌ Fehler bei der Tabellenabfrage: {e}")
            # Versuche eine systemtabelle abzufragen, falls die aqea_entries Tabelle nicht existiert
            try:
                response = supabase.from_("pg_tables").select("*").limit(1).execute()
                print(f"✅ Verbindung zu Systemtabellen erfolgreich!")
                return True
            except Exception as e2:
                print(f"❌ Fehler bei der Systemtabellenabfrage: {e2}")
                return False
            
    except Exception as e:
        print(f"❌ Fehler bei der Supabase-Verbindung: {e}")
        return False

def test_database_url_connection():
    """Test connection using DATABASE_URL with asyncpg."""
    print("\n🔌 Testing connection with DATABASE_URL using asyncpg...")
    
    try:
        import asyncpg
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL nicht gefunden!")
            return False
        
        # Debug: Zeige die URL (ohne Passwort)
        db_parts = database_url.split(":")
        safe_url = f"{db_parts[0]}:{db_parts[1]}:***@{':'.join(db_parts[3:])}"
        print(f"Verbindung zu: {safe_url}")
        
        # Diese Funktion muss mit asyncio.run aufgerufen werden
        async def connect_test():
            try:
                # Stelle sicher, dass wir die korrekte Hostadresse verwenden
                # In DATABASE_URL sollte db.nljhcoqddnvscjulbiox.supabase.co stehen
                conn = await asyncpg.connect(database_url)
                result = await conn.fetchval("SELECT 1")
                await conn.close()
                
                if result == 1:
                    print("✅ Datenbankverbindung mit asyncpg erfolgreich!")
                    return True
                else:
                    print(f"❌ Unerwartetes Ergebnis: {result}")
                    return False
            except Exception as e:
                print(f"❌ Fehler bei der asyncpg-Verbindung: {e}")
                print("\nVersuche, die URL zu korrigieren...")
                
                # Versuche, die URL zu korrigieren, falls sie falsch formatiert ist
                try:
                    if "db." not in database_url and "nljhcoqddnvscjulbiox" in database_url:
                        # Füge "db." vor die Domain hinzu
                        fixed_url = database_url.replace("nljhcoqddnvscjulbiox", "db.nljhcoqddnvscjulbiox")
                        print(f"Versuche korrigierte URL: {fixed_url.split(':')[0]}:{fixed_url.split(':')[1]}:***@{':'.join(fixed_url.split(':')[3:])}")
                        
                        conn = await asyncpg.connect(fixed_url)
                        result = await conn.fetchval("SELECT 1")
                        await conn.close()
                        
                        if result == 1:
                            print("✅ Datenbankverbindung mit korrigierter URL erfolgreich!")
                            print("Bitte aktualisieren Sie Ihre .env Datei mit der korrigierten URL")
                            return True
                except Exception as e2:
                    print(f"❌ Fehler bei der Verbindung mit korrigierter URL: {e2}")
                
                return False
        
        return asyncio.run(connect_test())
    
    except Exception as e:
        print(f"❌ Fehler beim Test mit asyncpg: {e}")
        return False

if __name__ == "__main__":
    print("=== Supabase Connection Tests ===\n")
    
    # Teste mit offiziellem Client
    official_success = test_supabase_connection()
    
    # Teste mit DATABASE_URL und asyncpg
    url_success = test_database_url_connection()
    
    # Zusammenfassung
    print("\n=== Testergebnisse ===")
    print(f"Offizieller Supabase-Client: {'✅ Erfolgreich' if official_success else '❌ Fehlgeschlagen'}")
    print(f"DATABASE_URL mit asyncpg: {'✅ Erfolgreich' if url_success else '❌ Fehlgeschlagen'}")
    
    if not official_success and not url_success:
        print("\n❌ Beide Verbindungsmethoden sind fehlgeschlagen. Bitte überprüfen Sie die Verbindungsparameter.")
        print("\nBitte stellen Sie sicher, dass:")
        print("1. Die Supabase-URL korrekt ist (https://nljhcoqddnvscjulbiox.supabase.co)")
        print("2. Der API-Key gültig ist")
        print("3. Die DATABASE_URL den korrekten Hostnamen enthält (db.nljhcoqddnvscjulbiox.supabase.co)")
        print("4. Das Passwort korrekt URL-codiert ist (z.B. & als %26)")
        sys.exit(1)
    else:
        print("\n✅ Mindestens eine Verbindungsmethode war erfolgreich!")
        sys.exit(0) 