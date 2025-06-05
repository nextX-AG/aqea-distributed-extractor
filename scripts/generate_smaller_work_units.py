#!/usr/bin/env python3
"""
Generate smaller, more balanced work units for German Wiktionary extraction
"""

import asyncio
import sys
import os
import json
import logging
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("work_unit_generator")

# Feinere Aufteilung für Deutsch (basierend auf der Häufigkeitsverteilung)
DE_WORK_UNITS = [
    # Buchstabe, ungefähre Wörter
    ("A", "Ad", 25000),
    ("Ae", "Al", 25000),
    ("Am", "Ap", 15000),
    ("Aq", "Au", 20000),
    ("Av", "B", 20000),
    
    ("Ba", "Be", 25000),
    ("Bf", "Bl", 20000),
    ("Bm", "Br", 20000),
    ("Bs", "Bz", 15000),
    
    ("C", "Ch", 15000),
    ("Ci", "Cz", 10000),
    
    ("D", "De", 25000),
    ("Df", "Dp", 15000),
    ("Dq", "Dz", 15000),
    
    ("E", "Ei", 25000),
    ("Ej", "En", 20000),
    ("Eo", "Ez", 20000),
    
    ("F", "Fe", 20000),
    ("Ff", "Fr", 20000),
    ("Fs", "Fz", 15000),
    
    ("G", "Ge", 25000),
    ("Gf", "Gl", 15000),
    ("Gm", "Gr", 15000),
    ("Gs", "Gz", 10000),
    
    ("H", "He", 25000),
    ("Hf", "Hr", 20000),
    ("Hs", "Hz", 15000),
    
    ("I", "In", 20000),
    ("Io", "Iz", 15000),
    
    ("J", "K", 15000),
    
    ("Ka", "Ke", 20000),
    ("Kf", "Kn", 15000),
    ("Ko", "Kr", 15000),
    ("Ks", "Kz", 10000),
    
    ("L", "Le", 20000),
    ("Lf", "Lp", 15000),
    ("Lq", "Lz", 15000),
    
    ("M", "Me", 25000),
    ("Mf", "Mo", 20000),
    ("Mp", "Mz", 15000),
    
    ("N", "O", 25000),
    
    ("P", "Pe", 20000),
    ("Pf", "Pr", 20000),
    ("Ps", "Pz", 15000),
    
    ("Q", "R", 20000),
    
    ("Ra", "Re", 20000),
    ("Rf", "Ro", 15000),
    ("Rp", "Rz", 10000),
    
    ("S", "Sc", 25000),
    ("Sd", "Se", 20000),
    ("Sf", "Sm", 15000),
    ("Sn", "Sp", 15000),
    ("Sq", "St", 25000),
    ("Su", "Sz", 20000),
    
    ("T", "Te", 20000),
    ("Tf", "Tr", 15000),
    ("Ts", "Tz", 10000),
    
    ("U", "Un", 20000),
    ("Uo", "Uz", 15000),
    
    ("V", "Ve", 15000),
    ("Vf", "Vz", 10000),
    
    ("W", "We", 20000),
    ("Wf", "Wk", 15000),
    ("Wl", "Wz", 15000),
    
    ("X", "Z", 25000),
    
    ("Za", "Ze", 15000),
    ("Zf", "Zu", 15000),
    ("Zv", "Zz", 10000),
    
    # Umlaute und ß
    ("Ä", "Ö", 15000),
    ("Ü", "ß", 15000),
]

def generate_work_units(language="de", source="wiktionary"):
    """Generate balanced work units for extraction."""
    work_units = []
    
    for idx, (start, end, estimate) in enumerate(DE_WORK_UNITS):
        work_id = f"{language}_{source}_{idx+1:02d}"
        
        work_unit = {
            "work_id": work_id,
            "language": language,
            "source": source,
            "range_start": start,
            "range_end": end,
            "estimated_entries": estimate,
            "status": "pending",
            "assigned_worker": None,
            "entries_processed": 0
        }
        
        work_units.append(work_unit)
    
    logger.info(f"Generated {len(work_units)} work units for {language} {source}")
    return work_units

def save_work_units(work_units, output_file="config/work_units.json"):
    """Save work units to file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(work_units, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(work_units)} work units to {output_file}")

def main():
    """Generate and save work units."""
    work_units = generate_work_units()
    save_work_units(work_units)
    
    # Print summary
    total_estimate = sum(unit["estimated_entries"] for unit in work_units)
    logger.info(f"Total estimated entries: {total_estimate}")
    logger.info(f"Average entries per work unit: {total_estimate / len(work_units):.1f}")
    logger.info(f"Work units created: {len(work_units)}")
    
    print("\nExample work units:")
    for unit in work_units[:5]:
        print(f"  {unit['work_id']}: {unit['range_start']}-{unit['range_end']} ({unit['estimated_entries']} entries)")
    print(f"  ... and {len(work_units)-5} more")

if __name__ == "__main__":
    main() 