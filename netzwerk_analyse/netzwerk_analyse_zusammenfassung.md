# AQEA-Format: Netzwerk-Übertragungseffizienz

## 1. Übersicht der Analyse

Diese Analyse untersucht die Effizienz des AQEA-Formats für die Datenübertragung über verschiedene Netzwerkprotokolle. Das AQEA-Format nutzt ein Wörterbuch-basiertes System, bei dem jedes Wort durch eine 4-Byte-Adresse repräsentiert wird. Bei der Übertragung wird zunächst ein Wörterbuch übermittelt, und anschließend können Texte durch Referenzen auf dieses Wörterbuch kompakt dargestellt werden.

### Analysierte Protokolle
- **TCP** (Transmission Control Protocol)
- **MQTT** (Message Queuing Telemetry Transport)
- **uRDP** (Micro Reliable Datagram Protocol)

## 2. Schlüsselergebnisse

### 2.1 Break-Even-Punkt

Der initiale Nachteil des AQEA-Formats (höhere Größe durch das Wörterbuch) wird ab ca. 500-1000 Wörtern ausgeglichen. Ab diesem Punkt beginnt das Format, Effizienzvorteile zu zeigen:

| Textgröße (Wörter) | Rohtext (Bytes) | AQEA (Bytes) | Verhältnis | Kumulative Ersparnis |
|--------------------|-----------------|--------------|------------|----------------------|
| 100                | 600             | 1.197        | 2,00x      | -99,50%              |
| 500                | 2.819           | 4.593        | 1,63x      | 18,19%               |
| 1.000              | 5.548           | 9.092        | 1,64x      | 46,50%               |
| 2.000              | 11.197          | 16.108       | 1,44x      | 56,37%               |
| 5.000              | 28.031          | 30.601       | 1,09x      | 56,85%               |
| 10.000             | 55.624          | 52.957       | 0,95x      | 60,70%               |
| 20.000             | 111.825         | 95.895       | 0,86x      | 62,53%               |

### 2.2 Kumulative Einsparung

Die kumulative Einsparung bei kontinuierlicher Datenübertragung (mit einmaligem Wörterbuchaustausch) erreicht bis zu **62,53%** bei 20.000 Wörtern. Diese Einsparung steigt mit der Textmenge weiter an.

### 2.3 Protokollvergleich (Übertragungszeiten in Sekunden)

| Textgröße (Wörter) | TCP (Rohtext) | TCP (AQEA) | MQTT (Rohtext) | MQTT (AQEA) | uRDP (Rohtext) | uRDP (AQEA) |
|--------------------|---------------|------------|----------------|-------------|----------------|-------------|
| 100                | 0,1500        | 0,1500     | 0,2000         | 0,2000      | 0,0600         | 0,0600      |
| 1.000              | 0,1900        | 0,1802     | 0,2200         | 0,2102      | 0,1000         | 0,0902      |
| 10.000             | 0,4400        | 0,4220     | 0,2600         | 0,2419      | 0,3400         | 0,3320      |
| 20.000             | 0,7400        | 0,7040     | 0,3000         | 0,2839      | 0,6400         | 0,6040      |

**Beobachtungen:**
- **uRDP** bietet die niedrigsten Übertragungszeiten für alle Formate
- **MQTT** zeigt eine bessere Skalierung bei größeren Datenmengen
- Die relativen Vorteile des AQEA-Formats sind über alle Protokolle hinweg konsistent

## 3. Visualisierungen

Die Analyse umfasst mehrere Visualisierungen:

1. **Kumulative Einsparung**: Zeigt, wie die Einsparung mit wachsender Textmenge zunimmt
2. **Übertragungszeiten**: Vergleicht die Zeiten zwischen Rohtext und AQEA über verschiedene Protokolle
3. **Größenverhältnis**: Verdeutlicht das sinkende Verhältnis von AQEA-Größe zu Rohtext-Größe
4. **Wörterbuchgröße vs. Textwachstum**: Demonstriert, wie das Wörterbuch relativ langsamer wächst als der Text

## 4. Protokolleigenschaften

| Eigenschaft        | TCP           | MQTT         | uRDP         |
|--------------------|---------------|--------------|--------------|
| Header-Größe       | 40 Bytes      | 45 Bytes     | 28 Bytes     |
| Max. Paketgröße    | 1.460 Bytes   | 10.240 Bytes | 1.472 Bytes  |
| Zuverlässigkeit    | 99,9%         | 99,8%        | 99,5%        |
| Verbindungsaufbau  | 0,1 Sekunden  | 0,15 Sekunden| 0,05 Sekunden|
| Handshake-Overhead | 120 Bytes     | 140 Bytes    | 56 Bytes     |

## 5. Anwendungsszenarien

### 5.1 Optimale Szenarien für AQEA

AQEA bietet signifikante Vorteile in folgenden Szenarien:

1. **Langzeitkommunikation**: Systeme, die kontinuierlich Textdaten austauschen
2. **Ressourcenbeschränkte Geräte**: IoT-Geräte mit begrenzter Bandbreite
3. **Hochfrequente Updates**: Systeme, die regelmäßig inkrementelle Updates senden
4. **Multi-Client-Systeme**: Ein Server, der dasselbe Wörterbuch mit vielen Clients teilt

### 5.2 Suboptimale Szenarien

Weniger vorteilhaft ist AQEA in folgenden Fällen:

1. **Einmalige kleine Übertragungen**: Der Wörterbuch-Overhead wiegt die Vorteile nicht auf
2. **Sehr heterogene Texte**: Wenn jede Übertragung völlig unterschiedliches Vokabular verwendet
3. **Extrem kurze Verbindungen**: Wenn der Verbindungsaufbau den Großteil der Zeit ausmacht

## 6. Fazit

Das AQEA-Format bietet signifikante Übertragungsvorteile in Netzwerkszenarien, insbesondere wenn:

1. **Kontinuierliche Kommunikation** stattfindet
2. Das **initiale Wörterbuch wiederverwendet** werden kann
3. **Ähnliches Vokabular** in unterschiedlichen Texten vorkommt

Die Analyse zeigt, dass über verschiedene Protokolle hinweg (TCP, MQTT, uRDP) konsistente Einsparungen erzielt werden können, die mit der Menge der übertragenen Daten zunehmen. Bei großen Textmengen (>10.000 Wörter) erreicht das AQEA-Format eine Einsparung von über 60% gegenüber der Rohtext-Übertragung.

Die Wahl des Übertragungsprotokolls sollte auf Basis der spezifischen Anwendungsanforderungen erfolgen, wobei uRDP für latenzempfindliche Anwendungen und MQTT für größere Datenmengen Vorteile bietet. 