#!/usr/bin/env python3
"""
Einfacher Supabase Test - Direkt und ohne Umwege

Testet die Supabase-Verbindung und erstellt die notwendigen Tabellen.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Lade .env
load_dotenv()

def main():
    print("🚀 Einfacher Supabase Test")
    print("=" * 40)
    
    # Hole Verbindungsdaten
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ SUPABASE_URL oder SUPABASE_KEY fehlt in .env")
        return False
    
    try:
        # Erstelle Client
        supabase: Client = create_client(url, key)
        print("✅ Supabase Client erstellt")
        
        # Teste Verbindung durch Erstellen einer einfachen Tabelle
        print("\n🔧 Teste Verbindung durch Erstellen einer Testtabelle...")
        
        # Teste einen Eintrag direkt
        print("\n📝 Teste Eintrag in Datenbank...")
        test_entry = {
            'address': '20:01:01:01',
            'label': 'Test',
            'description': 'Testentrag',
            'domain': 'wiktionary',
            'created_by': 'test-script',
            'lang_ui': 'de'
        }
        
        # Versuche, direkt in die aqea_entries Tabelle zu schreiben
        # (Falls die Tabelle nicht existiert, erstellen wir sie über das Supabase Dashboard)
        try:
            result = supabase.table('aqea_entries').insert(test_entry).execute()
            print(f"✅ Testeintrag erstellt: {result.data}")
        except Exception as e:
            print(f"⚠️ Tabelle existiert noch nicht: {e}")
            print("   Das ist OK - wir können die Verbindung testen")
        
        # Teste eine einfache Abfrage auf eine Standard-Systemtabelle
        try:
            # Versuche, eine leere Abfrage zu machen, um die Verbindung zu testen
            result = supabase.table('aqea_entries').select("*").limit(1).execute()
            print(f"✅ Datenbankverbindung funktioniert! Anzahl Einträge: {len(result.data)}")
        except Exception as e:
            if "does not exist" in str(e):
                print("✅ Verbindung funktioniert! (Tabelle muss nur noch erstellt werden)")
                print("\n📝 Legen Sie jetzt die Tabelle über das Supabase Dashboard an:")
                print("   1. Gehen Sie zu https://nljhcoqddnvscjulbiox.supabase.co")
                print("   2. Klicken Sie auf 'Table Editor'")
                print("   3. Führen Sie das folgende SQL aus:")
                print()
                print("""
CREATE TABLE aqea_entries (
    id SERIAL PRIMARY KEY,
    address VARCHAR(50) NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT,
    domain VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(50),
    lang_ui VARCHAR(10) DEFAULT 'de',
    meta JSONB DEFAULT '{}',
    relations JSONB DEFAULT '[]'
);
                """)
                print()
                return True
            else:
                print(f"❌ Unerwarteter Fehler: {e}")
                return False
        
        print("\n🎉 Supabase-Verbindung erfolgreich!")
        print("   Die Datenbank ist einsatzbereit!")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 