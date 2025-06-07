"""
Universal Semantic Hierarchy (USH) Categories

Based on UNIVERSAL_LANGUAGE_DOMAIN_PLAN.md
This module defines the official Universal Semantic Hierarchy categories for AQEA addressing.
"""

# Language domain mappings (AA-Byte)
LANGUAGE_DOMAINS = {
    # GERMANISCHE SPRACHEN (0x20-0x2F)
    'de': 0x20,  # Deutsch (Standarddeutsch)
    'en': 0x21,  # Englisch (Standard American/British)
    'nl': 0x22,  # Niederländisch
    'sv': 0x23,  # Schwedisch
    'no': 0x24,  # Norwegisch
    'da': 0x25,  # Dänisch
    'is': 0x26,  # Isländisch
    'af': 0x27,  # Afrikaans
    'yi': 0x28,  # Jiddisch
    
    # ROMANISCHE SPRACHEN (0x30-0x3F)
    'fr': 0x30,  # Französisch
    'es': 0x31,  # Spanisch
    'it': 0x32,  # Italienisch
    'pt': 0x33,  # Portugiesisch
    'ro': 0x34,  # Rumänisch
    'ca': 0x35,  # Katalanisch
    'gl': 0x36,  # Galicisch
    'la': 0x37,  # Lateinisch
    
    # SLAWISCHE SPRACHEN (0x40-0x4F)
    'ru': 0x40,  # Russisch
    'pl': 0x41,  # Polnisch
    'cs': 0x42,  # Tschechisch
    'sk': 0x43,  # Slowakisch
    'uk': 0x44,  # Ukrainisch
    'sr': 0x45,  # Serbisch
    'hr': 0x46,  # Kroatisch
    'bg': 0x47,  # Bulgarisch
    'sl': 0x48,  # Slowenisch
    
    # SINO-TIBETISCHE SPRACHEN (0x50-0x5F)
    'zh': 0x50,  # Mandarin-Chinesisch (Simplified)
    'zh_Hant': 0x51,  # Mandarin-Chinesisch (Traditional)
    'yue': 0x52,  # Kantonesisch
    'wuu': 0x53,  # Wu-Chinesisch
    'min': 0x54,  # Min-Chinesisch
    'bo': 0x55,  # Tibetisch
    'my': 0x56,  # Birmanisch
    
    # AFROASIATISCHE SPRACHEN (0x60-0x6F)
    'ar': 0x60,  # Arabisch (Standard)
    'he': 0x61,  # Hebräisch
    'am': 0x62,  # Amharisch
    'ti': 0x63,  # Tigrinya
    'om': 0x64,  # Oromo
    'so': 0x65,  # Somali
    'ha': 0x66,  # Hausa
    
    # JAPANO-KOREANISCHE SPRACHEN (0x90-0x9F)
    'ja': 0x90,  # Japanisch (Hiragana/Katakana)
    'ja_Kanji': 0x91,  # Japanisch (Kanji-dominant)
    'ko': 0x92,  # Koreanisch
    
    # INDOEUROPÄISCHE (ANDERE) (0xA0-0xAF)
    'hi': 0xA0,  # Hindi
    'bn': 0xA1,  # Bengali
    'ur': 0xA2,  # Urdu
    'pa': 0xA3,  # Punjabi
    'gu': 0xA4,  # Gujarati
    'mr': 0xA5,  # Marathi
    'ta': 0xA6,  # Tamil
    'te': 0xA7,  # Telugu
    'fa': 0xA8,  # Farsi/Persisch
    'el': 0xA9,  # Griechisch
    'hy': 0xAA,  # Armenisch
    
    # SPEZIELLE DOMÄNEN (0xF0-0xFF)
    'eo': 0xF0,  # Esperanto
    'code': 0xF1,  # Programmiersprachen
    'math': 0xF2,  # Mathematische Notation
    'chem': 0xF3,  # Chemische Formeln
    'music': 0xF4,  # Musikalische Notation
    'logic': 0xF5,  # Logische Systeme
    'mixed': 0xFF,  # Unklassifizierte/Mixed Sprachen
}

# Universal Semantic Categories (QQ-Byte)
UNIVERSAL_CATEGORIES = {
    # SUBSTANTIVE - CONCRETE CONCEPTS (0x01-0x0F)
    'physical_object': 0x01,  # Physische Objekte (Stein, Buch, Auto)
    'living_entity': 0x02,  # Lebewesen (Mensch, Tier, Pflanze)
    'abstract_concept': 0x03,  # Abstrakta (Liebe, Zeit, Idee, Freiheit)
    'collective': 0x04,  # Kollektiva (Familie, Gruppe, Armee)
    'proper_name': 0x05,  # Eigennamen (Personen, Städte, Marken)
    'body_part': 0x06,  # Körperteile (Hand, Auge, Herz) [UNIVERSAL]
    'kinship': 0x07,  # Verwandtschaft (Mutter, Vater, Kind) [UNIVERSAL]
    'natural_phenomenon': 0x08,  # Naturphänomene (Wasser, Feuer, Wind, Sonne)
    'tool_artifact': 0x09,  # Werkzeuge & Artefakte (Messer, Rad, Buch)
    'food_substance': 0x0A,  # Nahrung & Substanzen (Brot, Milch, Salz)
    'place_space': 0x0B,  # Orte & Räume (Haus, Berg, Fluss)
    'event': 0x0C,  # Ereignisse (Hochzeit, Krieg, Geburt)
    'state': 0x0D,  # Zustände (Gesundheit, Krankheit, Schlaf)
    'quantity_measure': 0x0E,  # Mengen & Maße (Größe, Gewicht, Entfernung)
    'meta_linguistic': 0x0F,  # Meta-sprachliche Begriffe (Wort, Sprache, Name)
    
    # PRÄDIKATE - ACTION CONCEPTS (0x10-0x1F)
    'motion_verb': 0x10,  # Bewegungsverben (gehen, kommen, fliegen)
    'action_verb': 0x11,  # Handlungsverben (machen, nehmen, geben)
    'communication_verb': 0x12,  # Kommunikation (sprechen, hören, sehen)
    'cognition_verb': 0x13,  # Kognition (denken, wissen, verstehen)
    'emotion_verb': 0x14,  # Emotion (lieben, hassen, fürchten)
    'physiological_verb': 0x15,  # Physiologische Prozesse (essen, trinken, schlafen)
    'state_verb': 0x16,  # Zustandsverben (sein, werden, bleiben)
    'possession_verb': 0x17,  # Possession (haben, gehören, besitzen)
    'causation_verb': 0x18,  # Causation (verursachen, bewirken, zerstören)
    'aspect_verb': 0x19,  # Aspekt (beginnen, beenden, fortsetzen)
    'modal_verb': 0x1A,  # Modalität (können, müssen, wollen)
    'technical_verb': 0x1B,  # Fachverben (operieren, programmieren, etc.)
    'metaphorical_verb': 0x1C,  # Metaphorische Verben (erblühen, erleuchten)
    'event_verb': 0x1D,  # Ereignisverben (geschehen, passieren)
    'interaction_verb': 0x1E,  # Interaktion (treffen, helfen, kämpfen)
    'reflexive_verb': 0x1F,  # Reflexivität (sich waschen, sich erinnern)
    
    # MODIFIKATOREN - PROPERTY CONCEPTS (0x20-0x2F)
    'dimension_adj': 0x20,  # Dimension (groß, klein, lang, kurz)
    'sensory_adj': 0x21,  # Sensorik (rot, laut, süß, weich)
    'evaluative_adj': 0x22,  # Bewertung (gut, schlecht, schön, hässlich)
    'temporal_adj': 0x23,  # Temporalität (alt, neu, schnell, langsam)
    'quantity_adj': 0x24,  # Quantität (viel, wenig, alle, keine)
    'physical_adj': 0x25,  # Physikalische Eigenschaften (hart, heiß, schwer)
    'emotional_adj': 0x26,  # Emotionale Eigenschaften (glücklich, traurig)
    'social_adj': 0x27,  # Soziale Eigenschaften (freundlich, höflich)
    'cognitive_adj': 0x28,  # Kognitive Eigenschaften (klug, dumm, weise)
    'ethical_adj': 0x29,  # Ethische Eigenschaften (richtig, falsch, gut)
    'aesthetic_adj': 0x2A,  # Ästhetische Eigenschaften (schön, elegant)
    'relational_adj': 0x2B,  # Relationale Eigenschaften (ähnlich, gleich)
    'probability_adj': 0x2C,  # Probabilität (möglich, sicher, wahrscheinlich)
    'functional_adj': 0x2D,  # Funktionalität (nützlich, kaputt, brauchbar)
    'complex_adj': 0x2E,  # Komplexe Eigenschaften (intelligent, kreativ)
    'meta_adj': 0x2F,  # Meta-Eigenschaften (typisch, normal, seltsam)
    
    # FUNKTIONSWÖRTER - GRAMMATICAL CONCEPTS (0x30-0x3F)
    'spatial_relation': 0x30,  # Spatial Relations (in, auf, unter, neben)
    'temporal_relation': 0x31,  # Temporal Relations (vor, nach, während, seit)
    'logical_connector': 0x32,  # Logical Connectors (und, oder, aber, wenn)
    'causal_relation': 0x33,  # Causal Relations (weil, damit, trotz, obwohl)
    'pronoun': 0x34,  # Pronouns (ich, du, er/sie/es, wir, ihr, sie)
    'quantifier': 0x35,  # Quantifiers (alle, einige, keine, viele)
    'deixis': 0x36,  # Deixis (hier, dort, jetzt, dann, dies, das)
    'article': 0x37,  # Articles & Determiners (der/die/das, ein/eine)
    'interrogative': 0x38,  # Interrogatives (wer, was, wann, wo, wie, warum)
    'negation': 0x39,  # Negation (nicht, nein, nie, kein, nichts)
    'comparison': 0x3A,  # Comparison (mehr, weniger, als, wie, am meisten)
    'aspect_marker': 0x3B,  # Aspect Markers (schon, noch, bereits, gerade)
    'modal_marker': 0x3C,  # Modal Markers (vielleicht, bestimmt, sicher)
    'focus_marker': 0x3D,  # Focus/Topic Markers (sogar, nur, besonders)
    'discourse_marker': 0x3E,  # Discourse Markers (also, jedoch, außerdem)
    'function_word': 0x3F,  # Other Function Words (zu, um, für, von, mit)
    
    # ZAHLEN & MENGEN (0x40-0x4F)
    'cardinal_number': 0x40,  # Grundzahlen (null, eins, zwei, drei, ...)
    'ordinal_number': 0x41,  # Ordnungszahlen (erste, zweite, dritte, ...)
    'fractional_number': 0x42,  # Bruchzahlen (halb, drittel, viertel, ...)
    'collective_number': 0x43,  # Kollektivzahlen (beide, alle drei, dutzend)
    'approximation': 0x44,  # Approximation (etwa, ungefähr, circa)
    'math_operator': 0x45,  # Mathematische Operatoren (+, -, ×, ÷, =)
    'unit_measure': 0x46,  # Maßeinheiten (Meter, Kilogramm, Liter)
    'currency': 0x47,  # Währungen (Euro, Dollar, Yen, Pfund)
    'time_unit': 0x48,  # Zeiteinheiten (Sekunde, Minute, Stunde, Tag)
    'frequency': 0x49,  # Häufigkeit (oft, selten, immer, nie)
    'quantity_unit': 0x4A,  # Mengenangaben (Stück, Paar, Gruppe)
    
    # SPEZIAL-KATEGORIEN (0xF0-0xFF)
    'interjection': 0xF0,  # Interjektionen (oh, ah, wow, ouch)
    'onomatopoeia': 0xF1,  # Onomatopoetika (boom, klick, miau)
    'particle': 0xF2,  # Partikeln & Füllwörter (äh, nun, halt)
    'loanword': 0xF3,  # Lehnwörter (Computer, Internet, Sushi)
    'neologism': 0xF4,  # Neologismen (googeln, liken, posten)
    'archaism': 0xF5,  # Archaismen (thou, ye, verily)
    'dialect': 0xF6,  # Dialekte & Varianten (bayerisch, berlinisch)
    'slang': 0xF7,  # Slang & Jargon (cool, krass, geil)
    'technical_term': 0xF8,  # Fachterminologie (interdisziplinär)
    'abbreviation': 0xF9,  # Abkürzungen & Akronyme (USA, NATO, etc.)
    'symbol': 0xFA,  # Symbole & Zeichen (@, #, €, ©)
    'multi_word': 0xFB,  # Mehrwort-Ausdrücke (ins Bett gehen)
    'nlp_specific': 0xFC,  # Computerlinguistik-spezifisch
    'ml_optimized': 0xFD,  # Machine-Learning-optimiert
    'vector_optimized': 0xFE,  # Vector-Database-optimiert
    'unclassified': 0xFF,  # Unklassifizierbar
}

# Hierarchical Cluster Categories (EE-Byte)
HIERARCHICAL_CLUSTERS = {
    # ABSTRAKTIONSGRAD (0x01-0x0F)
    'ultra_concrete': 0x01,  # Ultra-konkret (physisch greifbare Objekte)
    'concrete': 0x02,  # Konkret (sichtbare, definierte Entitäten)
    'semi_concrete': 0x03,  # Semi-konkret (zählbare abstrakte Konzepte)
    'semi_abstract': 0x04,  # Semi-abstrakt (Emotionen, mentale Zustände)
    'abstract': 0x05,  # Abstrakt (philosophische Konzepte, Ideen)
    'ultra_abstract': 0x06,  # Ultra-abstrakt (Meta-Konzepte, Kategorien)
    
    # HÄUFIGKEITS-CLUSTER (0x10-0x1F)
    'ultra_frequent': 0x10,  # Ultra-häufig (Top 1.000 Wörter global)
    'very_frequent': 0x11,  # Sehr häufig (Top 10.000 Wörter)
    'frequent': 0x12,  # Häufig (Top 100.000 Wörter)
    'medium_frequent': 0x13,  # Mittel-häufig (Top 1.000.000 Wörter)
    'rare': 0x14,  # Selten (Seltene, aber bekannte Wörter)
    'ultra_rare': 0x15,  # Ultra-selten (Extrem seltene Begriffe)
    'archaic': 0x16,  # Archaisch (Veraltete, historische Begriffe)
    'neologistic': 0x17,  # Neologistisch (Neue, moderne Begriffe)
    
    # KOGNITIVE PRIORITÄT (0x20-0x2F)
    'core_vocabulary': 0x20,  # Grundwortschatz (Erste 1.000 Lernwörter)
    'basic_vocabulary': 0x21,  # Aufbauwortschatz (Erweiterte Basis)
    'educated_vocabulary': 0x22,  # Bildungswortschatz (Gehobener Wortschatz)
    'specialized_vocabulary': 0x23,  # Fachvokabular (Spezialisierte Begriffe)
    'expert_vocabulary': 0x24,  # Expertenwissen (Hochspezialisiert)
    'research_vocabulary': 0x25,  # Forschungsebene (Cutting-edge Begriffe)
    
    # KULTURELLE UNIVERSALITÄT (0x30-0x3F)
    'universal': 0x30,  # Universell (In allen Kulturen vorhanden)
    'near_universal': 0x31,  # Fast-universal (In 90%+ der Kulturen)
    'widespread': 0x32,  # Weit verbreitet (In 70%+ der Kulturen)
    'regional': 0x33,  # Regional (Kulturkreis-spezifisch)
    'local': 0x34,  # Lokal (Sehr kulturspezifisch)
    'subcultural': 0x35,  # Subkulturell (Nur in Subgruppen)
    
    # VECTOR-EMBEDDING OPTIMIERUNG (0x40-0x4F)
    'high_vector_distance': 0x40,  # Hohe Vector-Distanz (Einzigartige Konzepte)
    'medium_vector_distance': 0x41,  # Mittlere Vector-Distanz (Verwandte Konzepte)
    'low_vector_distance': 0x42,  # Niedrige Vector-Distanz (Quasi-Synonyme)
    'synonym_cluster': 0x43,  # Synonym-Cluster (Echte Synonyme)
    'antonym_cluster': 0x44,  # Antonym-Cluster (Gegensätze)
    'hyperonym_cluster': 0x45,  # Hyperonym-Cluster (Übergeordnet)
    'hyponym_cluster': 0x46,  # Hyponym-Cluster (Untergeordnet)
    'meronym_cluster': 0x47,  # Meronym-Cluster (Teil-von-Beziehung)
    
    # GRAPH-KONNEKTIVITÄT (0x50-0x5F)
    'hub_node': 0x50,  # Hub-Knoten (>100 Verbindungen)
    'super_connector': 0x51,  # Super-Connectors (>50 Verbindungen)
    'connector': 0x52,  # Connectors (10-50 Verbindungen)
    'normal_node': 0x53,  # Normal-Knoten (3-10 Verbindungen)
    'low_connector': 0x54,  # Low-Connectors (1-3 Verbindungen)
    'leaf_node': 0x55,  # Blatt-Knoten (1 Verbindung)
    'isolated_node': 0x56,  # Isolierte Knoten (0 Verbindungen)
    
    # EMOTIONALE VALENZ (0x60-0x6F)
    'strong_positive': 0x60,  # Stark positiv (Freude, Liebe, Erfolg)
    'positive': 0x61,  # Positiv (gut, schön, angenehm)
    'slight_positive': 0x62,  # Leicht positiv (okay, nett, brauchbar)
    'neutral': 0x63,  # Neutral (Tisch, gehen, Zahl)
    'slight_negative': 0x64,  # Leicht negativ (schlecht, langweilig)
    'negative': 0x65,  # Negativ (Trauer, Verlust, Schmerz)
    'strong_negative': 0x66,  # Stark negativ (Hass, Tod, Katastrophe)
    
    # MACHINE LEARNING CLUSTER (0xF0-0xFF)
    'ml_cluster_a': 0xF0,  # ML-Cluster-A (Dynamisch basierend auf Embeddings)
    'ml_cluster_b': 0xF1,  # ML-Cluster-B (K-Means-Cluster)
    'ml_cluster_c': 0xF2,  # ML-Cluster-C (Hierarchical Clustering)
    'bert_cluster': 0xF3,  # BERT-Cluster (BERT-optimierte Gruppierung)
    'gpt_cluster': 0xF4,  # GPT-Cluster (GPT-optimierte Gruppierung)
    'domain_adapter': 0xF5,  # Domain-Adapter (Transfer Learning)
    'cross_lingual': 0xF6,  # Cross-Lingual-Cluster (Multilingual Models)
    'dynamic': 0xFF,  # Dynamisch zugewiesen (Auto-Clustering)
}

# Semantic Role Indicators (A2-Byte 0x00-0x0F, special values)
SEMANTIC_ROLES = {
    'undefined': 0x00,  # [RESERVED - Null/Undefined]
    'prototype': 0x01,  # Prototyp (Das zentrale Beispiel des Konzepts)
    'common_variant': 0x02,  # Häufigste Variante (Most common instance)
    'hyperonym': 0x03,  # Hyperonym (Übergeordneter Begriff)
    'hyponym': 0x04,  # Hyponym (Untergeordneter Begriff)
    'meronym': 0x05,  # Meronym (Teil des Ganzen)
    'holonym': 0x06,  # Holonym (Das Ganze, von dem etwas Teil ist)
    'synonym': 0x07,  # Synonym (Bedeutungsgleich)
    'antonym': 0x08,  # Antonym (Bedeutungsgegensatz)
    'co_hyponym': 0x09,  # Co-Hyponym (Geschwisterbegriff)
    'metaphoric': 0x0A,  # Metaphorische Verwendung
    'metonymic': 0x0B,  # Metonymische Verwendung
    'symbolic': 0x0C,  # Symbolische Verwendung
    'idiomatic': 0x0D,  # Idiomatische Verwendung
    'archaic': 0x0E,  # Archaische Variante
    'modern': 0x0F,  # Moderne/Neue Variante
}

# POS to QQ-Category mapping (for backwards compatibility)
POS_TO_UNIVERSAL_CATEGORY = {
    'noun': 'physical_object',  # Default für Substantive
    'verb': 'action_verb',  # Default für Verben
    'adjective': 'dimension_adj',  # Default für Adjektive
    'adverb': 'function_word',  # Default für Adverbien
    'pronoun': 'pronoun',
    'preposition': 'spatial_relation',
    'conjunction': 'logical_connector',
    'interjection': 'interjection',
    'article': 'article',
    'numeral': 'cardinal_number',
    'unknown': 'unclassified',
}

# Semantic category keywords for text-based classification
CATEGORY_KEYWORDS = {
    'natural_phenomenon': ['water', 'fire', 'air', 'nature', 'natural', 'environment', 'wasser', 'feuer', 'luft', 'natur', 'umwelt'],
    'living_entity': ['animal', 'plant', 'person', 'organism', 'living', 'tier', 'pflanze', 'lebewesen'],
    'body_part': ['body', 'head', 'arm', 'leg', 'eye', 'hand', 'körper', 'kopf', 'auge', 'hand', 'fuß'],
    'kinship': ['family', 'mother', 'father', 'child', 'parent', 'familie', 'mutter', 'vater', 'kind', 'eltern'],
    'food_substance': ['food', 'drink', 'meal', 'eat', 'taste', 'essen', 'trinken', 'mahlzeit', 'geschmack'],
    'motion_verb': ['go', 'come', 'walk', 'run', 'move', 'gehen', 'kommen', 'laufen', 'bewegen'],
    'emotion_verb': ['feel', 'love', 'hate', 'fear', 'fühlen', 'lieben', 'hassen', 'fürchten'],
    'communication_verb': ['say', 'speak', 'tell', 'ask', 'sagen', 'sprechen', 'erzählen', 'fragen'],
    'dimension_adj': ['big', 'small', 'long', 'short', 'groß', 'klein', 'lang', 'kurz'],
    'sensory_adj': ['red', 'blue', 'loud', 'quiet', 'rot', 'blau', 'laut', 'leise'],
    'temporal_relation': ['before', 'after', 'during', 'while', 'vor', 'nach', 'während'],
    'spatial_relation': ['in', 'on', 'under', 'above', 'below', 'auf', 'unter', 'über'],
}

# EE-Byte frequency-based clusters for common words
FREQUENCY_RANK_TO_CLUSTER = {
    # Ultra-häufig
    (0, 999): 'ultra_frequent',  # Top 1.000 Wörter
    # Sehr häufig
    (1000, 9999): 'very_frequent',  # Top 10.000 Wörter
    # Häufig
    (10000, 99999): 'frequent',  # Top 100.000 Wörter
    # Mittel-häufig
    (100000, 999999): 'medium_frequent',  # Top 1.000.000 Wörter
    # Selten
    (1000000, float('inf')): 'rare',  # Alle anderen Wörter
} 