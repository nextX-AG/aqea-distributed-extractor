# AQEA Distributed Extractor - Fixes

Dieses Verzeichnis enthält Skripte zur Behebung bekannter Probleme im AQEA Distributed Extractor.

## Verfügbare Fixes

### 1. Datetime JSON-Serialisierung

**Problem**: `TypeError: Object of type datetime is not JSON serializable`

Dieses Problem tritt auf, wenn datetime-Objekte in den API-Antworten serialisiert werden. Der Fix fügt einen benutzerdefinierten JSON-Encoder hinzu, der datetime-Objekte korrekt serialisiert.

```bash
python3 datetime_json_fix.py
```

### 2. AQEA Converter NoneType-Fehler

**Problem**: `'NoneType' object has no attribute 'lower'`

Dieses Problem tritt auf, wenn der AQEA Converter versucht, Methoden auf None-Objekte anzuwenden. Der Fix fügt NULL-Checks zu allen String-Operationen hinzu.

```bash
python3 aqea_converter_fix.py
```

### 3. Session Management

**Problem**: `Unclosed client session` und `Unclosed connector` Warnungen

Dieses Problem führt zu Memory-Leaks bei längeren Läufen. Der Fix fügt eine cleanup_sessions-Methode hinzu und ruft diese an den entsprechenden Stellen auf.

```bash
python3 session_management_fix.py
```

## Alle Fixes anwenden

Um alle Fixes gleichzeitig anzuwenden, führe das folgende Skript aus:

```bash
./apply_all_fixes.sh
```

## Nach dem Anwenden der Fixes

Nach dem Anwenden der Fixes müssen die Services neu gestartet werden, damit die Änderungen wirksam werden:

```bash
sudo systemctl restart aqea-master.service
sudo systemctl restart 'aqea-worker@*.service'
```

## Wichtige Hinweise

1. **Vor dem Anwenden der Fixes**:
   - Erstelle Backups wichtiger Dateien
   - Teste die Fixes in einer Entwicklungsumgebung, bevor du sie in der Produktion anwendest

2. **Bei Multi-Server-Deployments**:
   - Wende die Fixes auf allen Servern an oder
   - Pushe die Änderungen ins Git-Repository und aktualisiere alle Server

3. **Bekannte Einschränkungen**:
   - Die Skripte verwenden reguläre Ausdrücke zur Codemanipulation und könnten bei stark angepasstem Code fehlschlagen
   - Bei Fehlern prüfe die entsprechenden Dateien manuell und nimm die notwendigen Änderungen vor 