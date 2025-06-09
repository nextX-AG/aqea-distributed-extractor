#!/usr/bin/env python3
"""
AQEA Netzwerkprotokolle Vergleich

Dieses Skript simuliert die Übertragung von Text im AQEA-Format über verschiedene
Netzwerkprotokolle (TCP, MQTT, uRDP) und vergleicht die Effizienz.
Es demonstriert, wie der initiale Wörterbuchaustausch sich bei steigender Textmenge auszahlt.
"""

import random
import string
import json
import struct
import time
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple, Any

# Protokoll-Overhead-Simulationen
PROTOCOL_OVERHEADS = {
    "TCP": {
        "header_size": 40,  # IPv4 (20) + TCP (20) Bytes
        "ack_size": 40,     # ACK-Paket
        "max_packet": 1460, # Typische MSS (Maximum Segment Size)
        "reliability": 0.999, # Zuverlässigkeit
        "retransmit_percent": 0.001, # Prozentsatz der Neuübertragungen
        "handshake_overhead": 3 * 40, # 3-Way Handshake
        "connection_setup": 0.1, # Verbindungsaufbau in Sekunden
        "connection_teardown": 0.05, # Verbindungsabbau
    },
    "MQTT": {
        "header_size": 45,  # IPv4 (20) + TCP (20) + MQTT (~5) Bytes
        "ack_size": 45,     # MQTT QoS 1 ACK
        "max_packet": 10240, # Größere Pakete möglich
        "reliability": 0.998, # Zuverlässigkeit
        "retransmit_percent": 0.002, # Prozentsatz der Neuübertragungen
        "handshake_overhead": 3 * 40 + 20, # TCP + MQTT Connect
        "connection_setup": 0.15, # Verbindungsaufbau in Sekunden
        "connection_teardown": 0.05, # Verbindungsabbau
    },
    "uRDP": {
        "header_size": 28,  # IPv4 (20) + UDP (8) Bytes
        "ack_size": 28,     # Minimaler ACK
        "max_packet": 1472, # Typische UDP-Größe
        "reliability": 0.995, # Zuverlässigkeit (etwas geringer)
        "retransmit_percent": 0.01, # Höherer Prozentsatz der Neuübertragungen
        "handshake_overhead": 2 * 28, # Einfacherer Handshake
        "connection_setup": 0.05, # Schnellerer Verbindungsaufbau
        "connection_teardown": 0.01, # Schnellerer Verbindungsabbau
    }
}

# Netzwerk-Eigenschaften für die Simulation
NETWORK_PROFILES = {
    "LAN": {
        "bandwidth": 100 * 1024 * 1024,  # 100 Mbps
        "latency": 0.001,  # 1ms
        "packet_loss": 0.0001,
    },
    "WLAN": {
        "bandwidth": 20 * 1024 * 1024,  # 20 Mbps
        "latency": 0.005,  # 5ms
        "packet_loss": 0.001,
    },
    "4G": {
        "bandwidth": 5 * 1024 * 1024,  # 5 Mbps
        "latency": 0.050,  # 50ms
        "packet_loss": 0.005,
    },
    "3G": {
        "bandwidth": 1 * 1024 * 1024,  # 1 Mbps
        "latency": 0.100,  # 100ms
        "packet_loss": 0.01,
    }
}

class TextGenerator:
    """Klasse zum Generieren von deutschen Beispieltexten mit realistischen Eigenschaften."""
    
    def __init__(self, seed=42):
        random.seed(seed)
        self.german_words = self._load_german_common_words()
        self.word_frequency = {}
        for word in self.german_words:
            self.word_frequency[word] = random.randint(1, 1000)
            
    def _load_german_common_words(self):
        """Lädt eine Liste häufiger deutscher Wörter."""
        # Simulierte häufige deutsche Wörter
        common_words = [
            "der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich", 
            "des", "auf", "für", "ist", "im", "dem", "nicht", "ein", "eine", "als", 
            "auch", "es", "an", "werden", "aus", "er", "hat", "dass", "sie", "nach", 
            "bei", "um", "am", "sind", "noch", "wie", "einem", "über", "einen", "so", 
            "zum", "kann", "aber", "vor", "durch", "wenn", "nur", "war", "eines", "haben",
            "oder", "wird", "sein", "Zeit", "Jahr", "Mann", "Frau", "Kind", "Tag", "Haus",
            "Arbeit", "Welt", "Leben", "Hand", "Stadt", "Land", "Frage", "Fall", "Mensch", "Seite",
            "Weg", "Herr", "Teil", "Problem", "Ende", "Wasser", "Liebe", "Freund", "Geschichte", "Musik"
        ]
        
        # Erweitere die Liste mit zufälligen Wörtern für eine größere Vielfalt
        extended_words = common_words.copy()
        for _ in range(500):
            length = random.randint(3, 12)
            word = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
            if random.random() < 0.3:  # 30% der Wörter beginnen mit Großbuchstaben
                word = word.capitalize()
            extended_words.append(word)
        
        return extended_words
    
    def generate_text(self, num_words):
        """Generiert einen Text mit der angegebenen Anzahl von Wörtern."""
        # Zipf-Verteilung simulieren: Häufige Wörter werden öfter verwendet
        words = []
        for _ in range(num_words):
            if random.random() < 0.7:  # 70% häufige Wörter
                word = random.choice(self.german_words[:50])
            else:
                word = random.choice(self.german_words)
            words.append(word)
        
        # Konstruiere Sätze mit Punkten und Kommas
        text = ""
        current_sentence = []
        for word in words:
            current_sentence.append(word)
            if len(current_sentence) > random.randint(5, 15) and random.random() < 0.7:
                sentence = " ".join(current_sentence)
                if random.random() < 0.2:  # 20% der Sätze enden mit Komma
                    sentence += ", "
                else:
                    sentence += ". "
                    if random.random() < 0.3:  # 30% Chance für Absatz nach Punkt
                        sentence += "\n"
                text += sentence
                current_sentence = []
        
        if current_sentence:
            text += " ".join(current_sentence) + "."
        
        return text

class AQEAConverter:
    """Konvertiert Text in das AQEA-Format mit 4-Byte-Adressen."""
    
    def __init__(self):
        self.domain_byte = 0xA0  # Deutsch
        self.word_to_address = {}
        self.next_element_id = 0
    
    def convert_text(self, text):
        """Konvertiert einen Text in das AQEA-Format."""
        words = text.split()
        unique_words = list(set(words))
        
        # Erstelle Wörterbuch: Wort -> AQEA-Adresse
        for word in unique_words:
            if word not in self.word_to_address:
                self._assign_address(word)
        
        # Erstelle AQEA-Binärdaten
        dictionary_data = self._create_dictionary()
        text_data = self._encode_text(words)
        
        return {
            "dictionary": dictionary_data,
            "dictionary_size": len(dictionary_data),
            "text_data": text_data,
            "text_size": len(text_data),
            "total_size": len(dictionary_data) + len(text_data),
            "unique_words": len(unique_words),
            "total_words": len(words)
        }
    
    def _assign_address(self, word):
        """Weist einem Wort eine AQEA-Adresse zu."""
        # Bestimme Kategorie basierend auf erstem Buchstaben
        if word[0].isupper():
            category_byte = 0x01  # Nomen
        elif len(word) <= 3:
            category_byte = 0x03  # Artikelwörter, kurze Wörter
        else:
            category_byte = 0x02  # Andere Wörter
        
        # Bestimme Subkategorie basierend auf Wortlänge
        if len(word) < 4:
            subcategory_byte = 0x01
        elif len(word) < 8:
            subcategory_byte = 0x02
        else:
            subcategory_byte = 0x03
        
        # Element-ID
        element_id = self.next_element_id % 255
        self.next_element_id += 1
        
        # Speichere Adresse
        address = (self.domain_byte << 24) | (category_byte << 16) | (subcategory_byte << 8) | element_id
        self.word_to_address[word] = address
    
    def _create_dictionary(self):
        """Erstellt die Wörterbuch-Daten für die Übertragung."""
        dictionary_data = bytearray()
        
        # Anzahl der Einträge
        dictionary_data.extend(struct.pack(">I", len(self.word_to_address)))
        
        # Wörterbucheinträge
        for word, address in self.word_to_address.items():
            word_bytes = word.encode('utf-8')
            # Format: 4 Bytes für Adresse + 1 Byte für Wortlänge + n Bytes für Wort
            dictionary_data.extend(struct.pack(">IB", address, len(word_bytes)))
            dictionary_data.extend(word_bytes)
        
        return dictionary_data
    
    def _encode_text(self, words):
        """Kodiert einen Text als Folge von AQEA-Adressen."""
        text_data = bytearray()
        
        # Anzahl der Wörter
        text_data.extend(struct.pack(">I", len(words)))
        
        # Adressen für jedes Wort
        for word in words:
            address = self.word_to_address[word]
            text_data.extend(struct.pack(">I", address))
        
        return text_data

class NetworkSimulator:
    """Simuliert die Übertragung von Daten über verschiedene Netzwerkprotokolle."""
    
    def __init__(self, network_profile="WLAN"):
        self.network = NETWORK_PROFILES[network_profile]
    
    def simulate_transfer(self, data_size, protocol="TCP", initial_dictionary=None):
        """Simuliert die Übertragung einer bestimmten Datenmenge über das angegebene Protokoll."""
        protocol_params = PROTOCOL_OVERHEADS[protocol]
        
        # Berücksichtige Overhead von Protokollen bei der Berechnung der Gesamtdatenmenge
        total_overhead = 0
        total_packets = 0
        
        # Verbindungsaufbau
        setup_time = protocol_params["connection_setup"]
        total_overhead += protocol_params["handshake_overhead"]
        
        # Datenübertragung
        remaining_data = data_size
        if initial_dictionary:
            # Wenn ein Wörterbuch bereits übertragen wurde, muss nur der Text übertragen werden
            remaining_data = data_size - initial_dictionary
        
        while remaining_data > 0:
            packet_size = min(remaining_data, protocol_params["max_packet"])
            packet_with_header = packet_size + protocol_params["header_size"]
            total_overhead += protocol_params["header_size"]
            
            # Simuliere Paketneusendungen
            if random.random() < protocol_params["retransmit_percent"]:
                total_overhead += packet_with_header
            
            remaining_data -= packet_size
            total_packets += 1
        
        # ACKs für jedes Paket
        total_overhead += total_packets * protocol_params["ack_size"]
        
        # Verbindungsabbau
        teardown_time = protocol_params["connection_teardown"]
        
        # Berechnete Gesamtübertragungsgröße
        total_transfer_size = data_size + total_overhead
        
        # Berechnete Übertragungszeit
        transmission_time = (total_transfer_size / self.network["bandwidth"]) + \
                            (total_packets * self.network["latency"] * 2) + \
                            setup_time + teardown_time
        
        return {
            "protocol": protocol,
            "data_size": data_size,
            "overhead": total_overhead,
            "total_transfer_size": total_transfer_size,
            "overhead_percent": (total_overhead / data_size) * 100 if data_size > 0 else 0,
            "packets": total_packets,
            "transmission_time": transmission_time,
            "effective_bandwidth": (data_size / transmission_time) if transmission_time > 0 else 0
        }

class AQEANetworkAnalyzer:
    """Analysiert die Effizienz des AQEA-Formats bei der Netzwerkübertragung."""
    
    def __init__(self, network_profile="WLAN"):
        self.text_generator = TextGenerator()
        self.aqea_converter = AQEAConverter()
        self.network_simulator = NetworkSimulator(network_profile)
    
    def analyze_incremental_texts(self, text_sizes, protocols=None):
        """
        Analysiert die Effizienz bei inkrementeller Übertragung von Texten.
        Dies simuliert den Fall, dass ein initiales Wörterbuch einmal übertragen wird
        und dann nur noch die kompakte Adressreferenz für neue Texte.
        """
        if protocols is None:
            protocols = list(PROTOCOL_OVERHEADS.keys())
        
        results = {protocol: [] for protocol in protocols}
        
        # Simuliere die Übertragung für verschiedene Textgrößen
        # Das Wörterbuch wird einmal initial übertragen und dann wiederverwendet
        dictionary_size = None
        cumulative_raw_text_size = 0
        
        for size in text_sizes:
            # Generiere Text und konvertiere zu AQEA
            text = self.text_generator.generate_text(size)
            raw_text_size = len(text.encode('utf-8'))
            cumulative_raw_text_size += raw_text_size
            
            aqea_result = self.aqea_converter.convert_text(text)
            
            if dictionary_size is None:
                dictionary_size = aqea_result["dictionary_size"]
            
            # Simuliere Übertragung für jedes Protokoll
            for protocol in protocols:
                # 1. Fall: Initiale Übertragung (Wörterbuch + Text)
                initial_transfer = self.network_simulator.simulate_transfer(
                    aqea_result["total_size"], protocol)
                
                # 2. Fall: Inkrementelle Übertragung (nur neuer Text mit bestehendem Wörterbuch)
                incremental_transfer = self.network_simulator.simulate_transfer(
                    aqea_result["text_size"], protocol, dictionary_size)
                
                # 3. Fall: Rohtextübertragung zum Vergleich
                raw_text_transfer = self.network_simulator.simulate_transfer(
                    raw_text_size, protocol)
                
                # 4. Fall: Kumulierte Einsparung (Gesamter Rohtext vs. AQEA mit einmaligem Wörterbuch)
                cumulative_aqea_size = dictionary_size + aqea_result["text_size"]
                cumulative_savings = 100 * (1 - cumulative_aqea_size / cumulative_raw_text_size)
                
                results[protocol].append({
                    "words": size,
                    "raw_text_size": raw_text_size,
                    "aqea_dictionary_size": aqea_result["dictionary_size"],
                    "aqea_text_size": aqea_result["text_size"],
                    "aqea_total_size": aqea_result["total_size"],
                    "unique_words": aqea_result["unique_words"],
                    "initial_transfer": initial_transfer,
                    "incremental_transfer": incremental_transfer,
                    "raw_text_transfer": raw_text_transfer,
                    "size_ratio": aqea_result["total_size"] / raw_text_size,
                    "cumulative_raw_text": cumulative_raw_text_size,
                    "cumulative_aqea_size": cumulative_aqea_size,
                    "cumulative_savings": cumulative_savings
                })
        
        return results
    
    def print_analysis_results(self, results):
        """Gibt die Analyseergebnisse aus."""
        for protocol, protocol_results in results.items():
            print(f"\n=== Protokoll: {protocol} ===")
            print(f"{'Wörter':>10} | {'Rohtext (B)':>12} | {'AQEA (B)':>12} | {'Verhältnis':>10} | {'Übertr.-Zeit (s)':>15} | {'Kumul. Ersparnis':>15}")
            print("-" * 85)
            
            for result in protocol_results:
                print(f"{result['words']:>10} | "
                      f"{result['raw_text_size']:>12} | "
                      f"{result['aqea_total_size']:>12} | "
                      f"{result['size_ratio']:>10.2f} | "
                      f"{result['incremental_transfer']['transmission_time']:>15.4f} | "
                      f"{result['cumulative_savings']:>15.2f}%")
    
    def plot_results(self, results):
        """Erstellt Visualisierungen der Analyseergebnisse."""
        protocols = list(results.keys())
        text_sizes = [r["words"] for r in results[protocols[0]]]
        
        # Plot 1: Kumulative Einsparung über Text-Größe
        plt.figure(figsize=(12, 6))
        
        for protocol in protocols:
            savings = [r["cumulative_savings"] for r in results[protocol]]
            plt.plot(text_sizes, savings, label=f"{protocol}", marker='o')
        
        plt.xlabel('Anzahl Wörter (kumulativ)')
        plt.ylabel('Kumulative Einsparung (%)')
        plt.title('AQEA-Format: Kumulative Einsparung bei wachsender Textmenge')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.savefig('netzwerk_analyse/cumulative_savings.png')
        
        # Plot 2: Übertragungszeiten über verschiedene Protokolle
        plt.figure(figsize=(12, 6))
        
        for protocol in protocols:
            raw_times = [r["raw_text_transfer"]["transmission_time"] for r in results[protocol]]
            aqea_times = [r["incremental_transfer"]["transmission_time"] for r in results[protocol]]
            
            plt.plot(text_sizes, raw_times, label=f"{protocol} - Rohtext", linestyle='--')
            plt.plot(text_sizes, aqea_times, label=f"{protocol} - AQEA", linestyle='-')
        
        plt.xlabel('Anzahl Wörter')
        plt.ylabel('Übertragungszeit (s)')
        plt.title('Übertragungszeiten: Rohtext vs. AQEA (mit bestehendem Wörterbuch)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.savefig('netzwerk_analyse/transmission_times.png')
        
        # Plot 3: Verhältnis der Größen (AQEA/Rohtext)
        plt.figure(figsize=(12, 6))
        
        for protocol in protocols:
            ratios = [r["aqea_text_size"]/r["raw_text_size"] for r in results[protocol]]
            plt.plot(text_sizes, ratios, label=f"{protocol}", marker='o')
        
        plt.xlabel('Anzahl Wörter')
        plt.ylabel('Größenverhältnis (AQEA-Text/Rohtext)')
        plt.title('AQEA-Format: Größenverhältnis zum Rohtext (nur Textdaten)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.savefig('netzwerk_analyse/size_ratios.png')
        
        # Plot 4: Wörterbuchgröße und Textwachstum
        plt.figure(figsize=(12, 6))
        
        dict_sizes = [r["aqea_dictionary_size"] for r in results[protocols[0]]]
        cumulative_raw = [r["cumulative_raw_text"] for r in results[protocols[0]]]
        cumulative_aqea = [r["cumulative_aqea_size"] for r in results[protocols[0]]]
        
        plt.plot(text_sizes, dict_sizes, label="Wörterbuch", marker='s')
        plt.plot(text_sizes, cumulative_raw, label="Kumulativer Rohtext", marker='o')
        plt.plot(text_sizes, cumulative_aqea, label="Kumulativer AQEA-Text", marker='^')
        
        plt.xlabel('Anzahl Wörter (inkrementell)')
        plt.ylabel('Größe (Bytes)')
        plt.title('Wachstum: Wörterbuch vs. Gesamttext')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.savefig('netzwerk_analyse/dictionary_vs_text.png')

def main():
    """Hauptfunktion für die Analyse."""
    # Textgrößen für die Analyse (in Wörtern)
    text_sizes = [100, 500, 1000, 2000, 5000, 10000, 20000]
    
    # Verfügbare Protokolle
    protocols = ["TCP", "MQTT", "uRDP"]
    
    # Netzwerkprofil
    network_profile = "WLAN"
    
    print(f"\n=== AQEA Netzwerk-Analyse: {network_profile} ===")
    print(f"Analysiere Übertragungseffizienz des AQEA-Formats über {', '.join(protocols)}")
    print(f"Textgrößen: {text_sizes} Wörter")
    
    # Führe Analyse durch
    analyzer = AQEANetworkAnalyzer(network_profile)
    results = analyzer.analyze_incremental_texts(text_sizes, protocols)
    
    # Gib Ergebnisse aus
    analyzer.print_analysis_results(results)
    
    # Erstelle Visualisierungen
    analyzer.plot_results(results)
    
    print("\nAnalyse abgeschlossen. Visualisierungen wurden im Verzeichnis 'netzwerk_analyse/' gespeichert.")
    
    # Protokoll-Übersicht
    print("\n=== Protokoll-Eigenschaften ===")
    for protocol, params in PROTOCOL_OVERHEADS.items():
        print(f"\n{protocol}:")
        for key, value in params.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main() 