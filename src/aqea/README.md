# Universal Semantic Hierarchy (USH) für AQEA

## Überblick

Die **Universal Semantic Hierarchy (USH)** ist eine Erweiterung des AQEA-Adressierungsformats, die eine sprachübergreifende semantische Adressierung ermöglicht. Sie basiert auf linguistischen Universalien statt sprachspezifischen Eigenschaften und ist optimal für Graph- und Vector-Datenbanken optimiert.

### Format: `AA:QQ:EE:A2`

- **AA** = Sprachdomäne (z.B. 0x20 für Deutsch, 0x21 für Englisch)
- **QQ** = Universelle semantische Kategorie (z.B. 0x08 für Naturphänomene)
- **EE** = Hierarchisches Clustering (z.B. 0x10 für häufige Wörter)
- **A2** = Vector-optimierte Element-ID

## Kernkomponenten

### USHAdapter (`ush_adapter.py`)

Der `USHAdapter` dient als Brücke zwischen dem alten AQEA-Format und dem neuen USH-Format:

```python
# Adapter erstellen
adapter = USHAdapter(config, 'de')  # Für Deutsch

# Kategorie bestimmen
category_name, qq_value = adapter.determine_semantic_category(entry)

# Hierarchisches Cluster bestimmen
cluster_name, ee_value = adapter.determine_hierarchical_cluster(entry)

# USH-Adresse generieren
address, metadata = adapter.generate_ush_address(entry)

# Cross-linguistische Mappings
adapter.register_cross_linguistic_mapping(address, 'en', 'water')
english_equivalent = adapter.find_cross_linguistic_equivalent(address, 'en')
```

### USH-Konverter (`ush_converter.py`)

Der `USHConverter` ist eine USH-erweiterte Version des AQEA-Konverters:

```python
# Konverter erstellen
converter = USHConverter(config, 'de', database)

# Eintrag konvertieren
aqea_entry = await converter.convert(entry)

# Legacy-Eintrag migrieren
migrated_entry = await converter.migrate_entry(legacy_entry)
```

### USH-Kategorien (`ush_categories.py`)

Dieser Modul definiert die offiziellen USH-Kategorien:

- `LANGUAGE_DOMAINS`: Sprachdomänen (AA-Byte)
- `UNIVERSAL_CATEGORIES`: Universelle semantische Kategorien (QQ-Byte)
- `HIERARCHICAL_CLUSTERS`: Hierarchische Cluster (EE-Byte)
- `SEMANTIC_ROLES`: Semantische Rollen (A2-Byte, spezielle Werte)

## Vorteile des USH-Formats

1. **Sprachübergreifende Konsistenz**: Gleiche Konzepte haben gleiche QQ:EE:A2-Muster über Sprachgrenzen hinweg
2. **ML-Ready**: Optimiert für Vector-Datenbanken und Embedding-basierte Suche
3. **Skalierbarkeit**: Unterstützt mehr Kategorien und feinere Unterteilungen
4. **Interoperabilität**: Verbesserte semantische Verlinkung zwischen Sprachen

## Verwendungsbeispiel

```python
# Konfiguration
config = {
    'aqea': {
        'use_legacy_mode': False,
        'enable_cross_linguistic': True
    }
}

# Konverter für Deutsch erstellen
de_converter = USHConverter(config, 'de')

# Eintrag konvertieren
entry = {
    'word': 'Wasser',
    'pos': 'noun',
    'definitions': ['H₂O, drinking liquid'],
    'labels': ['nature', 'fluid'],
    'translations': {'en': ['water']}
}

# AQEA-Eintrag mit USH-Adressierung erstellen
aqea_entry = await de_converter.convert(entry)

# Adresse analysieren
address = aqea_entry.address  # z.B. 0x20:08:10:42
```

## Migrationsunterstützung

Die USH-Integration bietet Rückwärtskompatibilität und Migrationstools:

```python
# Legacy-Modus aktivieren (für Abwärtskompatibilität)
config['aqea']['use_legacy_mode'] = True
legacy_converter = USHConverter(config, 'de')

# Prüfen, ob eine Adresse migriert werden muss
needs_migration = adapter.needs_migration(address)

# Alte Adresse migrieren
migrated_entry = await converter.migrate_entry(legacy_entry)
```

## Tests und Beispiele

- **Unit Tests**: `tests/test_ush_integration.py`
- **Demo-Skript**: `examples/ush_demo.py`

## Integration

Die USH-Integration ist vollständig in das AQEA-System integriert und kann durch Konfigurationsparameter aktiviert werden:

```python
from src.aqea import USHConverter

# In master.py oder worker.py
config = {
    'aqea': {
        'use_legacy_mode': False,  # USH aktivieren
        'enable_cross_linguistic': True  # Cross-linguistische Mappings aktivieren
    }
}

# Bisherigen AQEAConverter ersetzen
# converter = AQEAConverter(config, language, database)
converter = USHConverter(config, language, database)
``` 