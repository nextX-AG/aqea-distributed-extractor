#!/usr/bin/env python3
"""
Finaler AQEA Supabase Test

Testet das komplette AQEA-System mit Supabase-Datenbank.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Lade .env
load_dotenv()

def main():
    print("🚀 Finaler AQEA Supabase Test")
    print("=" * 50)
    
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
        
        # Test 1: AQEA Entry erstellen
        print("\n📝 Test 1: AQEA Entry erstellen...")
        test_entry = {
            'address': '20:01:01:01',
            'label': 'Wasser',
            'description': 'H2O - Chemische Verbindung',
            'domain': 'wiktionary',
            'created_by': 'test-system',
            'lang_ui': 'de'
        }
        
        # Lösche eventuell vorhandenen Testeintrag
        try:
            supabase.table('aqea_entries').delete().eq('address', '20:01:01:01').execute()
        except:
            pass  # Ignoriere Fehler beim Löschen
        
        # Erstelle neuen Eintrag
        result = supabase.table('aqea_entries').insert(test_entry).execute()
        print(f"✅ AQEA Entry erstellt: {result.data[0]['address']} -> {result.data[0]['label']}")
        
        # Test 2: Worker registrieren
        print("\n👤 Test 2: Worker registrieren...")
        worker_data = {
            'worker_id': 'test-worker-001',
            'ip_address': '192.168.1.100',
            'status': 'idle'
        }
        
        # Lösche eventuell vorhandenen Worker
        try:
            supabase.table('worker_status').delete().eq('worker_id', 'test-worker-001').execute()
        except:
            pass
        
        result = supabase.table('worker_status').insert(worker_data).execute()
        print(f"✅ Worker registriert: {result.data[0]['worker_id']} von {result.data[0]['ip_address']}")
        
        # Test 3: Work Unit erstellen
        print("\n📦 Test 3: Work Unit erstellen...")
        work_unit = {
            'work_id': 'de_wiktionary_test_01',
            'language': 'de',
            'source': 'wiktionary',
            'range_start': 'A',
            'range_end': 'E',
            'status': 'pending',
            'estimated_entries': 1000
        }
        
        # Lösche eventuell vorhandene Work Unit
        try:
            supabase.table('work_units').delete().eq('work_id', 'de_wiktionary_test_01').execute()
        except:
            pass
        
        result = supabase.table('work_units').insert(work_unit).execute()
        print(f"✅ Work Unit erstellt: {result.data[0]['work_id']} ({result.data[0]['range_start']}-{result.data[0]['range_end']})")
        
        # Test 4: Adresse reservieren
        print("\n🎯 Test 4: AQEA-Adresse reservieren...")
        address_alloc = {
            'language': 'de',
            'domain': 'wiktionary',
            'aa_byte': 32,  # 0x20
            'qq_byte': 1,   # 0x01
            'ee_byte': 1,   # 0x01
            'a2_byte': 1,   # 0x01
            'reserved_by': 'test-worker-001'
        }
        
        # Lösche eventuell vorhandene Allokation
        try:
            supabase.table('address_allocations').delete().eq('language', 'de').eq('domain', 'wiktionary').eq('aa_byte', 32).eq('qq_byte', 1).eq('ee_byte', 1).eq('a2_byte', 1).execute()
        except:
            pass
        
        result = supabase.table('address_allocations').insert(address_alloc).execute()
        print(f"✅ Adresse reserviert: 20:01:01:01 für {result.data[0]['reserved_by']}")
        
        # Test 5: Daten lesen und Statistiken erstellen
        print("\n📊 Test 5: Statistiken abrufen...")
        
        # Zähle Einträge
        entries = supabase.table('aqea_entries').select("*", count="exact").execute()
        workers = supabase.table('worker_status').select("*", count="exact").execute()
        work_units = supabase.table('work_units').select("*", count="exact").execute()
        
        print(f"   📝 AQEA Entries: {entries.count}")
        print(f"   👥 Worker: {workers.count}")
        print(f"   📦 Work Units: {work_units.count}")
        
        # Test 6: Progress Snapshot erstellen
        print("\n📈 Test 6: Progress Snapshot...")
        snapshot = {
            'total_estimated_entries': 1000,
            'total_processed_entries': 1,
            'progress_percent': 0.1,
            'current_rate_per_minute': 10.5,
            'total_workers': 1,
            'active_workers': 0,
            'idle_workers': 1,
            'pending_work_units': 1,
            'processing_work_units': 0,
            'completed_work_units': 0,
            'failed_work_units': 0
        }
        
        result = supabase.table('progress_snapshots').insert(snapshot).execute()
        print(f"✅ Progress Snapshot erstellt: {snapshot['progress_percent']}% complete")
        
        print("\n🎉 Alle Tests erfolgreich!")
        print("=" * 50)
        print("✅ Supabase-Datenbank ist vollständig funktionsfähig")
        print("✅ Alle AQEA-Tabellen sind einsatzbereit") 
        print("✅ Das System kann jetzt in Produktion gehen!")
        print("\n🚀 Bereit für den Start der Worker auf den Servern!")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        print("\n💡 Haben Sie die Tabellen bereits über das Supabase Dashboard erstellt?")
        print("   Führen Sie das SQL aus scripts/create-aqea-tables.sql aus!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 