#!/usr/bin/env python3
"""Final system check - Supabase integration and results"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def final_system_check():
    print("🎯 === FINAL SYSTEM CHECK: Deutsche Wörterbuch-Extraktion ===")
    
    # Create client
    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    
    # Check AQEA entries
    result = client.table('aqea_entries').select('*').execute()
    print(f"📊 AQEA Entries in Supabase: {len(result.data)}")
    
    if result.data:
        print("\n🔍 Alle Einträge in der Datenbank:")
        for i, entry in enumerate(result.data):
            print(f"{i+1}. {entry['address']} - {entry['label']} - {entry['description'][:100]}...")
            print(f"   Quelle: {entry.get('source', 'N/A')} | Erstellt: {entry.get('created_at', 'N/A')}")
        
        # Check for new entries from today's extraction
        recent_entries = [e for e in result.data if '2025-06-05' in str(e.get('created_at', ''))]
        print(f"\n🔥 Neue Einträge von heute: {len(recent_entries)}")
        
        if recent_entries:
            print("✅ ERFOLG: Supabase-Integration funktioniert! Neue Einträge wurden gespeichert!")
            for entry in recent_entries:
                print(f"   🆕 {entry['address']} - {entry['label']}")
        else:
            print("⚠️  Keine neuen Einträge von heute - möglicherweise HTTP-only mode")
    else:
        print("❌ Keine Einträge in der Datenbank gefunden!")
    
    # Check work units
    work_result = client.table('work_units').select('*').execute()
    print(f"\n📋 Work Units in Supabase: {len(work_result.data)}")
    
    if work_result.data:
        completed = len([wu for wu in work_result.data if wu.get('status') == 'completed'])
        print(f"✅ Completed Work Units: {completed}")
    
    print(f"\n🏁 FAZIT:")
    if len(result.data) > 3:  # More than our test entries
        print("🎉 VOLLSTÄNDIGER ERFOLG: System läuft mit Supabase-Integration!")
    else:
        print("⚠️  System läuft, aber möglicherweise ohne Supabase-Speicherung")

if __name__ == "__main__":
    final_system_check() 