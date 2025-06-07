# AQEA Domain Plan - Sprachoptimierung

**Problem:** Deutsche Sprache hat ~800.000 Einträge, aber nur 655.360 mögliche Adressen pro Domain-Byte (0x20).

**Lösung:** Bessere Nutzung der 256 verfügbaren QQ-Bytes (Kategorien) statt mehrerer AA-Bytes pro Sprache.

---

## Konzept 1: Frequenz-basierte QQ-Aufteilung

### Grundidee
Teile Wortarten nach Häufigkeit auf und nutze mehrere QQ-Bytes für häufige Wortarten.

### QQ-Byte-Verteilung (0x01-0xFF)

```
NOMEN (häufigste Wortart - ~40% aller Wörter)
├── 0x01-0x1F: Nomen Basis (31 Kategorien × 256 × 256 = 2.015.744 Adressen)
│   ├── 0x01: Nomen A-D
│   ├── 0x02: Nomen E-H  
│   ├── 0x03: Nomen I-L
│   ├── 0x04: Nomen M-P
│   ├── 0x05: Nomen Q-T
│   ├── 0x06: Nomen U-Z
│   ├── 0x07: Eigennamen A-D
│   ├── 0x08: Eigennamen E-H
│   ├── 0x09: Eigennamen I-L
│   ├── 0x0A: Eigennamen M-P
│   ├── 0x0B: Eigennamen Q-T
│   ├── 0x0C: Eigennamen U-Z
│   ├── 0x0D: Fachbegriffe Medizin
│   ├── 0x0E: Fachbegriffe Technik
│   ├── 0x0F: Fachbegriffe Wissenschaft
│   ├── 0x10: Zusammengesetzte Nomen A-F
│   ├── 0x11: Zusammengesetzte Nomen G-L
│   ├── 0x12: Zusammengesetzte Nomen M-R
│   ├── 0x13: Zusammengesetzte Nomen S-Z
│   ├── 0x14: Fremdwörter A-F
│   ├── 0x15: Fremdwörter G-L
│   ├── 0x16: Fremdwörter M-R
│   ├── 0x17: Fremdwörter S-Z
│   ├── 0x18: Archaische Nomen
│   ├── 0x19: Neologismen
│   ├── 0x1A: Umgangssprache
│   └── 0x1B-0x1F: Reserve

VERBEN (~25% aller Wörter)
├── 0x20-0x2F: Verben (16 Kategorien × 256 × 256 = 1.048.576 Adressen)
│   ├── 0x20: Starke Verben A-F
│   ├── 0x21: Starke Verben G-L
│   ├── 0x22: Starke Verben M-R
│   ├── 0x23: Starke Verben S-Z
│   ├── 0x24: Schwache Verben A-F
│   ├── 0x25: Schwache Verben G-L
│   ├── 0x26: Schwache Verben M-R
│   ├── 0x27: Schwache Verben S-Z
│   ├── 0x28: Modalverben & Hilfsverben
│   ├── 0x29: Reflexive Verben
│   ├── 0x2A: Trennbare Verben A-L
│   ├── 0x2B: Trennbare Verben M-Z
│   ├── 0x2C: Fremdwort-Verben
│   ├── 0x2D: Fachsprache-Verben
│   ├── 0x2E: Umgangssprache-Verben
│   └── 0x2F: Archaische Verben

ADJEKTIVE (~20% aller Wörter)
├── 0x30-0x3A: Adjektive (11 Kategorien × 256 × 256 = 720.896 Adressen)
│   ├── 0x30: Adjektive A-E
│   ├── 0x31: Adjektive F-J
│   ├── 0x32: Adjektive K-O
│   ├── 0x33: Adjektive P-T
│   ├── 0x34: Adjektive U-Z
│   ├── 0x35: Farbadjektive
│   ├── 0x36: Größenadjektive
│   ├── 0x37: Bewertungsadjektive
│   ├── 0x38: Zusammengesetzte Adjektive
│   ├── 0x39: Fremdwort-Adjektive
│   └── 0x3A: Fachsprache-Adjektive

RESTLICHE WORTARTEN (~15% aller Wörter)
├── 0x40: Adverbien
├── 0x41: Pronomen
├── 0x42: Präpositionen
├── 0x43: Konjunktionen
├── 0x44: Interjektionen
├── 0x45: Artikel
├── 0x46: Numeralia
├── 0x47: Partikeln
├── 0x48-0xFE: Reserve für Erweiterungen
└── 0xFF: Unbekannte Wortarten
```

### Kapazität
- **Gesamt:** 4.194.304 deutsche Wörter pro Domain
- **Nomen:** 2.015.744 Adressen (für ~320.000 erwartete Nomen)
- **Verben:** 1.048.576 Adressen (für ~200.000 erwartete Verben)
- **Adjektive:** 720.896 Adressen (für ~160.000 erwartete Adjektive)

---

## Konzept 2: Alphabetisch-Semantische Hybridaufteilung

### Grundidee
Kombiniere Wortart mit alphabetischen und semantischen Unterteilungen.

### QQ-Byte-Verteilung

```
NOMEN MIT ALPHABETISCHER UNTERTEILUNG
├── 0x01-0x1A: Nomen nach Anfangsbuchstaben (26 Kategorien)
│   ├── 0x01: Nomen A (ca. 30.000 Wörter)
│   ├── 0x02: Nomen B (ca. 25.000 Wörter)
│   ├── 0x03: Nomen C (ca. 15.000 Wörter)
│   ├── ... (jeweils 256 × 256 = 65.536 Adressen)
│   └── 0x1A: Nomen Z (ca. 5.000 Wörter)

VERBEN MIT EIGENSCHAFTEN
├── 0x20-0x2F: Verben nach Eigenschaften (16 Kategorien)
│   ├── 0x20: Verben A-E regulär
│   ├── 0x21: Verben F-J regulär
│   ├── 0x22: Verben K-O regulär
│   ├── 0x23: Verben P-T regulär
│   ├── 0x24: Verben U-Z regulär
│   ├── 0x25: Starke/Unregelmäßige Verben A-L
│   ├── 0x26: Starke/Unregelmäßige Verben M-Z
│   ├── 0x27: Modalverben & Hilfsverben
│   ├── 0x28: Reflexive Verben
│   ├── 0x29: Trennbare Verben
│   ├── 0x2A: Nicht-trennbare Verben
│   └── 0x2B-0x2F: Reserve

ADJEKTIVE MIT SEMANTIK
├── 0x30-0x3F: Adjektive nach Bedeutungsfeldern (16 Kategorien)
│   ├── 0x30: Farben & Aussehen
│   ├── 0x31: Größe & Dimension
│   ├── 0x32: Gefühle & Emotionen
│   ├── 0x33: Bewertung & Qualität
│   ├── 0x34: Zeit & Zustand
│   ├── 0x35: Physische Eigenschaften
│   ├── 0x36: Charaktereigenschaften
│   ├── 0x37: Fachbegriffe
│   └── 0x38-0x3F: Weitere semantische Felder
```

### Vorteile
- **Intuitive Suche:** Alphabetische Sortierung
- **Semantische Gruppierung:** Ähnliche Konzepte beieinander
- **Flexibilität:** Einfache Erweiterung pro Wortart

---

## Konzept 3: Dynamische Häufigkeits-Allocation

### Grundidee
Teile QQ-Bytes basierend auf tatsächlicher Worthäufigkeit aus dem deutschen Wiktionary auf.

### Datenanalyse-basierte Verteilung

```
HÄUFIGKEITSBASIERTE ZUTEILUNG (aus realen Daten)

SUPER-HÄUFIGE WÖRTER (Top 0.1% = ~800 Wörter)
├── 0x01: Die häufigsten 256 deutschen Wörter
├── 0x02: Häufige Wörter 257-512
├── 0x03: Häufige Wörter 513-768
└── (EE/A2 für feine Graduierungen der Häufigkeit)

HÄUFIGE NOMEN (nach Frequenz-Clustern)
├── 0x10: Nomen Häufigkeitsrang 1-65.536
├── 0x11: Nomen Häufigkeitsrang 65.537-131.072
├── 0x12: Nomen Häufigkeitsrang 131.073-196.608
├── 0x13: Nomen Häufigkeitsrang 196.609-262.144
└── 0x14: Seltene Nomen (ab Rang 262.145)

HÄUFIGE VERBEN
├── 0x20: Verben Top 65.536
├── 0x21: Verben Rang 65.537-131.072
├── 0x22: Verben Rang 131.073-196.608
└── 0x23: Seltene Verben

HÄUFIGE ADJEKTIVE
├── 0x30: Adjektive Top 65.536
├── 0x31: Adjektive Rang 65.537-131.072
└── 0x32: Seltene Adjektive

SPEZIELLE KATEGORIEN
├── 0x40: Eigennamen (häufige)
├── 0x41: Eigennamen (seltene)
├── 0x42: Fachbegriffe Medizin
├── 0x43: Fachbegriffe Technik
├── 0x44: Fachbegriffe Recht
├── 0x45: Fachbegriffe Wissenschaft
├── 0x46: Fremdwörter (integriert)
├── 0x47: Fremdwörter (wenig integriert)
├── 0x48: Umgangssprache
├── 0x49: Jugendsprache
├── 0x4A: Regionalismen
├── 0x4B: Archaismen
├── 0x4C: Neologismen
└── 0x4D-0xFE: Dynamische Erweiterung basierend auf Corpus-Analyse
```

### Implementierung
```python
# Häufigkeitsbasierte QQ-Zuteilung
def get_qq_byte_by_frequency(word: str, pos: str, frequency_rank: int) -> int:
    if frequency_rank <= 256:
        return 0x01  # Super-häufig
    elif frequency_rank <= 512:
        return 0x02  # Sehr häufig
    elif frequency_rank <= 768:
        return 0x03  # Häufig
    elif pos == "noun":
        return 0x10 + (frequency_rank // 65536)  # Nomen-Cluster
    elif pos == "verb":
        return 0x20 + (frequency_rank // 65536)  # Verb-Cluster
    elif pos == "adjective":
        return 0x30 + (frequency_rank // 65536)  # Adjektiv-Cluster
    else:
        return get_special_category_qq(word, pos)
```

---

## Empfehlung: Hybrid-Konzept

### Beste Lösung für Deutsche Sprache

```
OPTIMALE QQ-VERTEILUNG:
├── 0x01-0x03: Häufigste 768 Wörter (sprachübergreifend wichtig)
├── 0x10-0x1F: Nomen (16 Kategorien = 1.048.576 Adressen)
│   └── Alphabetisch + Semantic: A-E, F-J, K-O, P-T, U-Z, 
│       Eigennamen, Fachbegriffe, Komposita, etc.
├── 0x20-0x2A: Verben (11 Kategorien = 720.896 Adressen)
│   └── A-E, F-J, K-O, P-T, U-Z, Modal/Hilfs, Stark/Schwach, etc.
├── 0x30-0x37: Adjektive (8 Kategorien = 524.288 Adressen)
│   └── A-E, F-J, K-O, P-T, U-Z, Farben, Größen, Bewertungen
├── 0x40-0x4F: Sonstige Wortarten & Spezialitäten
└── 0x50-0xFF: Reserve für zukünftige Erweiterungen
```

### Kapazität Gesamt
- **Häufige Wörter:** 196.608 Adressen
- **Nomen:** 1.048.576 Adressen  
- **Verben:** 720.896 Adressen
- **Adjektive:** 524.288 Adressen
- **Sonstiges:** 1.048.576 Adressen
- **Reserve:** 1.703.936 Adressen

**TOTAL: 5.242.880 mögliche deutsche Wörter** - mehr als genug für alle absehbaren Anforderungen!

---

## Implementierungsschritte

1. **Analyse der aktuellen Datenbank:** Häufigkeitsverteilung bestimmen
2. **QQ-Mapping aktualisieren:** `src/aqea/converter.py` erweitern
3. **Migration bestehender Adressen:** Alte Adressen auf neues Schema mappen
4. **Validierung:** Sicherstellen, dass keine Duplikate entstehen
5. **Dokumentation:** AQEA-Standard um erweiterte QQ-Codes ergänzen 