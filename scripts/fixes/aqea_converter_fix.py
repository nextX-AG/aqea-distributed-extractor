#!/usr/bin/env python3
"""
Fix für das NoneType-Problem im AQEA Converter.

Dieses Skript modifiziert den AQEA Converter, um sicherzustellen, dass
alle String-Operationen NULL-Checks durchführen.
"""

import re
import os
from pathlib import Path

def add_none_checks(content):
    """Fügt NULL-Checks zu allen String-Methoden hinzu."""
    
    # Pattern für String-Methoden wie .lower(), .upper(), .strip() usw.
    string_method_pattern = r'(\w+)\.(lower|upper|strip|split|replace|startswith|endswith|find|rfind|index|rindex|count|format)\('
    
    # Finde alle String-Methoden-Aufrufe
    matches = list(re.finditer(string_method_pattern, content))
    
    # Füge NULL-Checks hinzu (von hinten nach vorne, um die Indizes zu erhalten)
    for match in reversed(matches):
        var_name = match.group(1)
        method = match.group(2)
        
        # Prüfe, ob die Variable bereits einen NULL-Check hat
        if not re.search(rf'if\s+{var_name}\s+is\s+not\s+None', content[:match.start()]):
            # Ersetze den Aufruf durch einen NULL-Check
            replacement = f'({var_name} or "").{method}('
            content = content[:match.start()] + replacement + content[match.end():]
    
    return content

def fix_aqea_converter(filepath):
    """Behebt das NoneType-Problem im AQEA Converter."""
    print(f"Fixing AQEA Converter at {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Füge NULL-Checks zu allen String-Methoden hinzu
    modified_content = add_none_checks(content)
    
    # Füge spezifische Null-Checks für bekannte Probleme hinzu
    if "Error generating address: 'NoneType' object has no attribute 'lower'" in content:
        # Finde die generate_address-Methode
        generate_address_match = re.search(r'def\s+generate_address\s*\((.*?)\):(.*?)def', content, re.DOTALL)
        if generate_address_match:
            method_body = generate_address_match.group(2)
            
            # Füge einen NULL-Check für die Hauptoperationen hinzu
            modified_method_body = method_body.replace(
                'term.lower()', 
                '(term or "").lower()'
            )
            
            # Ersetze die Methode im Content
            modified_content = modified_content.replace(method_body, modified_method_body)
    
    # Schreibe die geänderte Datei zurück
    with open(filepath, 'w') as f:
        f.write(modified_content)
    
    print(f"✅ Fixed AQEA Converter at {filepath}")

if __name__ == "__main__":
    # Pfad zum AQEA Converter
    src_dir = Path(__file__).parent.parent.parent / 'src'
    aqea_converter_path = src_dir / 'aqea' / 'converter.py'
    
    if aqea_converter_path.exists():
        fix_aqea_converter(aqea_converter_path)
        print("\n✅ AQEA Converter wurde erfolgreich repariert!")
        print("🔄 Bitte starte die Services neu, um die Änderungen zu übernehmen:")
        print("   sudo systemctl restart aqea-master.service")
        print("   sudo systemctl restart 'aqea-worker@*.service'")
    else:
        print(f"❌ AQEA Converter nicht gefunden unter {aqea_converter_path}")
        print("Bitte überprüfe den Pfad und versuche es erneut.") 