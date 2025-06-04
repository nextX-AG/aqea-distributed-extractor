# 🗄️ Supabase Setup für AQEA Distributed Extractor

Diese Anleitung zeigt, wie Sie Supabase als zentrale Datenbank für das AQEA Distributed Extractor System einrichten.

## 🎯 **Warum Supabase?**

**Zentrale Datenbank für alle Worker:**
- ✅ **Ein Datenbank** statt N lokale Datenbanken 
- ✅ **Keine Duplikate** durch zentrale AQEA-Adressvergabe
- ✅ **Real-time Monitoring** aller Worker gleichzeitig
- ✅ **Multi-Cloud Ready** - Worker aus verschiedenen Providern
- ✅ **Kosteneffizient** - €0-25/Monat statt €100+ für eigene DB-Server

## 📋 **Schritt-für-Schritt Setup**

### 1. Supabase Projekt erstellen

```bash
# 1. Gehe zu https://supabase.com
# 2. Klicke "Start your project" 
# 3. Erstelle ein neues Projekt:
#    - Name: aqea-distributed-extractor
#    - Region: Europe (Central) für deutsche Extraktion
#    - Passwort: [Starkes Passwort generieren]
```

### 2. Datenbank-Schema einrichten

```bash
# 1. Gehe zu deinem Supabase Projekt Dashboard
# 2. Klicke "SQL Editor" im Seitenmenü
# 3. Kopiere den kompletten Inhalt von scripts/init-supabase.sql
# 4. Füge ihn in den SQL Editor ein und klicke "RUN"
```

Das Schema erstellt automatisch:
- 📊 **AQEA Entries** - Haupttabelle für alle Spracheinträge
- 📦 **Work Units** - Verteilte Arbeitseinheiten für Worker
- 👥 **Worker Status** - Live-Tracking aller Worker
- 🏷️ **Address Allocations** - Verhindert AQEA-Adress-Kollisionen
- 📈 **Statistics** - Performance-Monitoring und Dashboard-Daten

### 3. Environment Variables konfigurieren

```bash
# Kopiere .env.example zu .env
cp .env.example .env

# Editiere .env mit deinen Supabase-Details:
nano .env
```

**Erforderliche Variablen:**
```bash
# Supabase Connection (aus Project Settings > Database)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres?sslmode=require

# Oder einzelne Komponenten:
DB_HOST=db.YOUR_PROJECT.supabase.co
DB_PASSWORD=YOUR_PASSWORD
DB_DATABASE=postgres
DB_USERNAME=postgres
```

### 4. Verbindung testen

```bash
# Test der Supabase-Integration
python scripts/test-supabase.py
```

**Erwartete Ausgabe:**
```
🚀 AQEA Supabase Integration Test Suite
🔌 Testing Supabase database connection...
✅ Database connection successful!

👥 Testing worker registration...
✅ Worker registration successful!
✅ Worker heartbeat update successful!

📦 Testing work unit management...
✅ Retrieved work unit: de_wiktionary_01
   Range: A-E
   Estimated entries: 160,000
✅ Work progress update successful!
✅ Work unit completion successful!

🎉 Supabase integration test suite completed!
```

## 🚀 **System mit Supabase starten**

### Lokaler Test (Single Worker)

```bash
# Terminal 1: Master starten
python -m src.main start-master --language de --workers 2 --source wiktionary

# Terminal 2: Worker starten  
python -m src.main start-worker --worker-id worker-001 --master-host localhost --master-port 8080

# Terminal 3: Status prüfen
python -m src.main status --master-host localhost --master-port 8080
```

### Multi-Cloud Deployment

```bash
# 1. Erstelle .env-Dateien für jeden Cloud-Provider
# 2. Deploy Worker auf verschiedenen Providern:

# Hetzner (Deutschland)
export DATABASE_URL="postgresql://postgres:..."
python -m src.main start-worker --worker-id hetzner-worker-001 --master-host MASTER_IP

# DigitalOcean (Frankfurt) 
export DATABASE_URL="postgresql://postgres:..."
python -m src.main start-worker --worker-id do-worker-001 --master-host MASTER_IP

# Alle schreiben in dieselbe Supabase-Datenbank! 🎉
```

## 📊 **Live-Monitoring über Supabase**

### Dashboard-Queries

**Aktueller Fortschritt:**
```sql
SELECT 
    SUM(estimated_entries) as total_estimated,
    SUM(entries_processed) as total_processed,
    ROUND(SUM(entries_processed)::float / SUM(estimated_entries) * 100, 2) as progress_percent
FROM work_units;
```

**Worker-Status:**
```sql
SELECT 
    worker_id,
    status,
    current_work_id,
    total_processed,
    last_heartbeat
FROM worker_status 
ORDER BY last_heartbeat DESC;
```

**AQEA-Einträge pro Sprache:**
```sql
SELECT 
    lang_ui,
    COUNT(*) as entries_count,
    COUNT(DISTINCT substring(address from 1 for 7)) as categories_used
FROM aqea_entries 
GROUP BY lang_ui 
ORDER BY entries_count DESC;
```

### Real-time Updates mit Supabase Realtime

```typescript
// Für Web-Dashboard (optional)
const { data, error } = await supabase
  .from('work_units')
  .select('*')
  .on('UPDATE', payload => {
    console.log('Work unit updated:', payload)
    updateDashboard(payload.new)
  })
  .subscribe()
```

## 🔧 **Erweiterte Konfiguration**

### Connection Pooling für High Performance

```yaml
# config/cloud-database.yml
database:
  provider: "supabase"
  pool_size: 50        # Für viele Worker
  max_overflow: 100
  pool_timeout: 30
  pool_recycle: 3600
```

### Automatische Backups

```sql
-- Supabase erstellt automatisch täglich Backups
-- Zusätzliche Sicherung der AQEA-Einträge:
pg_dump -h db.YOUR_PROJECT.supabase.co -U postgres -t aqea_entries > aqea_backup.sql
```

### Skalierung & Performance

**Für große Extraktionen (> 1M Einträge):**

1. **Upgrade Supabase Plan:**
   - Free: Bis 500MB (ca. 100k Einträge)
   - Pro ($25/Monat): Bis 8GB (ca. 2M Einträge)  
   - Team ($599/Monat): Bis 100GB (ca. 25M Einträge)

2. **Database Optimierung:**
   ```sql
   -- Zusätzliche Indizes für große Datasets
   CREATE INDEX CONCURRENTLY idx_aqea_entries_created_hour 
   ON aqea_entries (date_trunc('hour', created_at));
   
   CREATE INDEX CONCURRENTLY idx_work_units_processing_rate 
   ON work_units (processing_rate) WHERE status = 'processing';
   ```

3. **Worker-Konfiguration:**
   ```yaml
   # Für High-Throughput
   performance:
     db_batch_size: 200      # Größere Batches
     commit_frequency: 100   # Häufigere Commits
   ```

## 🎯 **Produktions-Deployment Checklist**

- [ ] ✅ Supabase Projekt mit Backup-Policy erstellt
- [ ] ✅ `scripts/init-supabase.sql` erfolgreich ausgeführt  
- [ ] ✅ DATABASE_URL in allen Worker-Umgebungen gesetzt
- [ ] ✅ `scripts/test-supabase.py` erfolgreich durchgelaufen
- [ ] ✅ Row Level Security (RLS) Policies konfiguriert
- [ ] ✅ Monitoring Dashboard eingerichtet
- [ ] ✅ Worker auf verschiedenen Cloud-Providern deployed
- [ ] ✅ AQEA-Adressen werden korrekt alloziert (keine Duplikate)

## 🚨 **Troubleshooting**

### Häufige Fehler

**1. Connection refused:**
```bash
# Prüfe DATABASE_URL Format
echo $DATABASE_URL
# Sollte sein: postgresql://postgres:password@db.project.supabase.co:5432/postgres?sslmode=require
```

**2. SSL-Probleme:**
```bash
# Supabase erfordert SSL
# Füge ?sslmode=require zum Ende der DATABASE_URL hinzu
```

**3. Worker können keine Work Units bekommen:**
```sql
-- Prüfe Work Units Status
SELECT work_id, status, assigned_worker FROM work_units;

-- Reset falls nötig
UPDATE work_units SET status = 'pending', assigned_worker = NULL WHERE status = 'assigned';
```

**4. AQEA-Adressen-Kollisionen:**
```sql
-- Prüfe Adress-Allokationen
SELECT category_key, COUNT(*) as allocated_count 
FROM address_allocations 
GROUP BY category_key 
ORDER BY allocated_count DESC;
```

## 🎉 **Nächste Schritte**

Nach erfolgreichem Supabase-Setup:

1. **Multi-Cloud Workers starten:** [README-CLOUD.md](README-CLOUD.md)
2. **Performance Monitoring:** [monitoring/dashboard.md](monitoring/dashboard.md)  
3. **Cost Optimization:** [docs/cost-analysis.md](docs/cost-analysis.md)

**🚀 Ihr AQEA System ist bereit für die großskalige verteilte Extraktion!** 