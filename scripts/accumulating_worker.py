#!/usr/bin/env python
"""
Akkumulierender Worker für AQEA Distributed Extractor

Dieser Worker akkumuliert extrahierte Einträge bis zu einem bestimmten Schwellenwert
oder Zeitlimit und speichert sie dann in einer einzigen Datei.
Dies verhindert die Erzeugung zu vieler kleiner Dateien.
"""

import asyncio
import logging
import os
import sys
import json
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import der AQEA-Module
from src.workers.worker import ExtractionWorker
from src.utils.config import Config
from src.utils.logger import setup_logging

# Konfiguriere Logger
logger = logging.getLogger("accumulating_worker")

class AccumulatingWorker(ExtractionWorker):
    """Worker, der Einträge akkumuliert und in Batches speichert."""
    
    def __init__(self, config, worker_id, master_host, master_port, 
                 batch_size=500, flush_interval=300):
        """
        Initialisiert den akkumulierenden Worker.
        
        Args:
            config: Konfigurationsobjekt
            worker_id: ID des Workers
            master_host: Host des Master-Koordinators
            master_port: Port des Master-Koordinators
            batch_size: Anzahl der Einträge, nach denen ein Flush ausgeführt wird
            flush_interval: Zeitintervall in Sekunden, nach dem ein Flush erzwungen wird
        """
        super().__init__(config, worker_id, master_host, master_port)
        
        # Akkumulierungs-Parameter
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Akkumulierte Daten
        self.accumulated_entries = []
        self.accumulated_aqea_entries = []
        self.last_flush_time = datetime.now()
        
        # Statistiken
        self.total_accumulated = 0
        self.total_flushed = 0
        self.total_flushes = 0
        
        # Stelle sicher, dass Ausgabeverzeichnisse existieren
        Path("extracted_data/accumulated").mkdir(exist_ok=True, parents=True)
        
        logger.info(f"Akkumulierender Worker initialisiert: batch_size={batch_size}, "
                    f"flush_interval={flush_interval}s")
    
    async def run(self):
        """Führt den Worker-Prozess aus."""
        try:
            logger.info(f"Starte akkumulierenden Worker {self.worker_id}")
            logger.info(f"Verbinde zu Master: {self.master_url}")
            
            # Starte Tasks
            await asyncio.gather(
                self.work_loop(),
                self.heartbeat_loop(),
                self.accumulation_monitor_loop()
            )
        except Exception as e:
            logger.error(f"Fehler beim Ausführen des Workers: {e}", exc_info=True)
        finally:
            # Flush alle verbleibenden Daten beim Beenden
            await self.flush_accumulated_data()
            
            if self.session:
                await self.session.close()
                
            logger.info(f"Worker {self.worker_id} beendet")
    
    async def accumulation_monitor_loop(self):
        """Überwacht die Akkumulierung und führt periodische Flushes durch."""
        while True:
            try:
                # Prüfe, ob Zeitlimit erreicht ist
                time_since_last_flush = datetime.now() - self.last_flush_time
                if time_since_last_flush.total_seconds() >= self.flush_interval and self.accumulated_entries:
                    logger.info(f"Zeitlimit von {self.flush_interval}s erreicht, führe Flush durch")
                    await self.flush_accumulated_data()
                
                # Ausgabe des aktuellen Status
                if self.accumulated_entries:
                    logger.debug(f"Akkumulierte Einträge: {len(self.accumulated_entries)}/{self.batch_size}, "
                                f"Zeit seit letztem Flush: {time_since_last_flush.total_seconds():.1f}s")
                
                await asyncio.sleep(10)  # Kurze Pause, um CPU-Last zu reduzieren
                
            except Exception as e:
                logger.error(f"Fehler im Akkumulierungs-Monitor: {e}", exc_info=True)
                await asyncio.sleep(30)  # Längere Pause bei Fehlern
    
    async def process_entries(self, entries):
        """
        Verarbeitet extrahierte Einträge und akkumuliert sie.
        
        Args:
            entries: Liste von extrahierten Einträgen
        """
        if not entries:
            return
        
        # Akkumuliere Roheinträge
        self.accumulated_entries.extend(entries)
        self.total_accumulated += len(entries)
        
        # Konvertiere zu AQEA
        for entry in entries:
            try:
                aqea_entry = await self.converter.convert(entry)
                if aqea_entry:
                    self.accumulated_aqea_entries.append(aqea_entry.to_dict())
            except Exception as e:
                logger.error(f"Fehler bei Konvertierung von {entry.get('word')}: {e}")
        
        # Prüfe, ob Batch-Größe erreicht ist
        if len(self.accumulated_entries) >= self.batch_size:
            logger.info(f"Batch-Größe von {self.batch_size} erreicht, führe Flush durch")
            await self.flush_accumulated_data()
    
    async def flush_accumulated_data(self):
        """Speichert akkumulierte Daten in Dateien und leert die Akkumulationen."""
        if not self.accumulated_entries:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Speichere Roheinträge
            raw_path = f"extracted_data/accumulated/raw_entries_{self.worker_id}_{timestamp}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(self.accumulated_entries, f, ensure_ascii=False, indent=2)
            
            # Speichere AQEA-Einträge
            aqea_path = f"extracted_data/accumulated/aqea_entries_{self.worker_id}_{timestamp}.json"
            with open(aqea_path, "w", encoding="utf-8") as f:
                json.dump(self.accumulated_aqea_entries, f, ensure_ascii=False, indent=2)
            
            # Berechne Erfolgsrate
            success_rate = len(self.accumulated_aqea_entries) / len(self.accumulated_entries) * 100
            
            # Logge Informationen
            logger.info(f"✅ Daten erfolgreich gespeichert:")
            logger.info(f"   - {len(self.accumulated_entries)} Roheinträge in {raw_path}")
            logger.info(f"   - {len(self.accumulated_aqea_entries)} AQEA-Einträge in {aqea_path}")
            logger.info(f"   - Erfolgsrate: {success_rate:.2f}%")
            
            # Aktualisiere Statistiken
            self.total_flushed += len(self.accumulated_entries)
            self.total_flushes += 1
            
            # Leere Akkumulationen
            entries_count = len(self.accumulated_entries)
            aqea_count = len(self.accumulated_aqea_entries)
            self.accumulated_entries = []
            self.accumulated_aqea_entries = []
            self.last_flush_time = datetime.now()
            
            # Melde Fortschritt an Master
            await self.report_progress(entries_processed=entries_count, aqea_generated=aqea_count)
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern akkumulierter Daten: {e}", exc_info=True)
    
    async def report_status(self):
        """Berichtet detaillierten Status an den Master."""
        # Erweitere den Status mit Akkumulierungs-Informationen
        status = await super().report_status()
        
        # Füge Akkumulierungs-Statistiken hinzu
        status.update({
            "accumulation": {
                "currently_accumulated": len(self.accumulated_entries),
                "batch_size": self.batch_size,
                "flush_interval_seconds": self.flush_interval,
                "time_since_last_flush": (datetime.now() - self.last_flush_time).total_seconds(),
                "total_accumulated": self.total_accumulated,
                "total_flushed": self.total_flushed,
                "total_flushes": self.total_flushes
            }
        })
        
        return status


def parse_args():
    """Kommandozeilenargumente parsen."""
    parser = argparse.ArgumentParser(description="Akkumulierender Worker für AQEA Distributed Extractor")
    
    parser.add_argument("--worker-id", "-i", required=True, help="Eindeutige Worker-ID")
    parser.add_argument("--master-host", "-m", default="localhost", help="Master-Host")
    parser.add_argument("--master-port", "-p", type=int, default=8080, help="Master-Port")
    parser.add_argument("--batch-size", "-b", type=int, default=500, 
                        help="Anzahl der Einträge, nach denen ein Flush ausgeführt wird")
    parser.add_argument("--flush-interval", "-f", type=int, default=300, 
                        help="Zeitintervall in Sekunden, nach dem ein Flush erzwungen wird")
    parser.add_argument("--config", "-c", default="config/default.yml", help="Konfigurationsdatei")
    parser.add_argument("--verbose", "-v", action="store_true", help="Ausführliche Logging-Ausgabe")
    
    return parser.parse_args()


async def main():
    """Hauptfunktion."""
    args = parse_args()
    
    # Konfiguriere Logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    # Lade Konfiguration
    config = Config.load(args.config)
    
    # Erstelle und starte Worker
    worker = AccumulatingWorker(
        config=config,
        worker_id=args.worker_id,
        master_host=args.master_host,
        master_port=args.master_port,
        batch_size=args.batch_size,
        flush_interval=args.flush_interval
    )
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker durch Benutzer beendet")
    finally:
        logger.info("Führe abschließenden Flush durch...")
        await worker.flush_accumulated_data()


if __name__ == "__main__":
    print("🧩 Starte Akkumulierenden AQEA Worker")
    asyncio.run(main()) 