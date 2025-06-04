# AQEA Distributed Extractor

**Distributed data extraction system for AQEA (Universal Knowledge Database)**

Automatically extracts and processes language data from multiple sources (Wiktionary, PanLex, Wikidata) using a distributed cloud architecture.

## 🎯 **Features**

- **Multi-Source Support**: Wiktionary, PanLex, Wikidata Lexemes, MusicBrainz
- **Distributed Processing**: Horizontal scaling across multiple cloud servers  
- **API-Limit Friendly**: Different IPs to avoid rate limiting
- **Real-Time Monitoring**: Progress tracking and performance metrics
- **AQEA Integration**: Direct output to AQEA 4-byte address format
- **Cloud-Ready**: Docker containers with one-click deployment

## 📊 **Performance**

| Language | Estimated Entries | Single Server Time | 5 Servers Time | Cost (5 servers) |
|----------|-------------------|-------------------|-----------------|------------------|
| German   | 800,000          | 4.6 days          | 22 hours        | ~12 CHF          |
| English  | 6,000,000        | 34.7 days         | 6.9 days        | ~90 CHF          |
| French   | 4,000,000        | 23.1 days         | 4.6 days        | ~60 CHF          |
| Spanish  | 1,000,000        | 5.8 days          | 28 hours        | ~15 CHF          |

## 🏗️ **Architecture**

```
Master Coordinator  ←→  Worker 1 (A-E entries)
        ↕               Worker 2 (F-J entries)  
PostgreSQL DB       ←→  Worker 3 (K-O entries)
        ↕               Worker 4 (P-T entries)
Web Dashboard       ←→  Worker 5 (U-Z entries)
```

## 🚀 **Quick Start**

### Local Development
```bash
# Clone repository
git clone https://github.com/your-username/aqea-distributed-extractor.git
cd aqea-distributed-extractor

# Start local cluster
docker-compose up -d

# Monitor progress
curl http://localhost:8080/api/status
```

### Cloud Deployment (Hetzner)
```bash
# Deploy 5 servers for German extraction
./scripts/deploy.sh hetzner 5 de

# Monitor distributed progress
./scripts/status.sh
```

## 📁 **Project Structure**

```
aqea-distributed-extractor/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── src/
│   ├── coordinator/          # Master coordination logic
│   ├── workers/             # Worker extraction processes
│   ├── data_sources/        # Wiktionary, PanLex, etc. integrations
│   ├── monitoring/          # Progress tracking and metrics
│   ├── aqea/               # AQEA format conversion
│   └── utils/              # Shared utilities
├── config/
│   ├── languages.yml       # Language-specific configurations
│   ├── sources.yml         # Data source configurations  
│   └── deployment.yml      # Cloud deployment settings
├── scripts/
│   ├── deploy.sh           # Automated cloud deployment
│   ├── status.sh           # Status monitoring
│   └── cleanup.sh          # Resource cleanup
├── tests/
└── docs/
    ├── API.md              # API documentation
    ├── DEPLOYMENT.md       # Deployment guide
    └── CONTRIBUTING.md     # Development guide
```

## 🛠️ **Installation**

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- PostgreSQL (for local development)

### Dependencies
```bash
pip install -r requirements.txt
```

Main dependencies:
- `aiohttp` - Async HTTP client/server
- `asyncpg` - PostgreSQL async driver  
- `psycopg2-binary` - PostgreSQL sync driver
- `requests` - HTTP requests for APIs
- `beautifulsoup4` - HTML parsing
- `click` - CLI framework

## 📝 **Usage Examples**

### Start German Extraction (Local)
```bash
python -m src.main --language de --workers 3 --source wiktionary
```

### Cloud Deployment
```bash
# Deploy to Hetzner Cloud (5 servers)
./scripts/deploy.sh hetzner 5 de

# Check status
./scripts/status.sh hetzner

# Cleanup when done
./scripts/cleanup.sh hetzner
```

### API Usage
```bash
# Get extraction status
GET http://your-master-ip:8080/api/status

# Start new extraction
POST http://your-master-ip:8080/api/extract
{
  "language": "de",
  "source": "wiktionary",
  "workers": 5
}
```

## 🌐 **Supported Data Sources**

| Source | Format | Entries | License | API Limits |
|--------|--------|---------|---------|------------|
| **Wiktionary** | MediaWiki API | 8.4M+ | CC-BY-SA | 5000/hour/IP |
| **PanLex** | Bulk Download | 80GB | CC0 | None (bulk) |
| **Wikidata Lexemes** | SPARQL/Dumps | 3GB | CC0 | 5000/min |
| **MusicBrainz** | REST API | 40GB | CC0-PD | 1/sec |

## 📈 **Monitoring & Metrics**

Real-time dashboard shows:
- **Progress**: Percentage completed per language
- **Performance**: Entries processed per minute per worker
- **Health**: Worker status and error rates  
- **Costs**: Current cloud spending
- **ETA**: Estimated completion time

## ⚙️ **Configuration**

### Language Configuration (`config/languages.yml`)
```yaml
languages:
  de:
    name: "German"
    estimated_entries: 800000
    alphabet_ranges:
      - { start: "A", end: "E", weight: 0.2 }
      - { start: "F", end: "J", weight: 0.15 }
      # ...
  en:
    name: "English"  
    estimated_entries: 6000000
    # ...
```

### Cloud Provider Configuration (`config/deployment.yml`)
```yaml
providers:
  hetzner:
    master_type: "cx21"    # 2 vCPU, 4GB RAM
    worker_type: "cx11"    # 1 vCPU, 2GB RAM  
    cost_per_hour: 0.015   # EUR
    regions: ["nbg1", "fsn1"]
```

## 🔧 **Development**

### Run Tests
```bash
pytest tests/
```

### Add New Data Source
1. Create `src/data_sources/your_source.py`
2. Implement `DataSourceInterface`
3. Add configuration to `config/sources.yml`
4. Update tests

### Local Development Setup
```bash
# Start PostgreSQL
docker run -d --name postgres -e POSTGRES_PASSWORD=aqea -p 5432:5432 postgres:15

# Install dependencies
pip install -r requirements.txt

# Run coordinator locally
python -m src.coordinator.main --mode development
```

## 📊 **Cost Analysis**

**Hetzner Cloud (5 servers for German):**
- 1x CX21 Master: €0.031/hour × 24h = €0.74
- 5x CX11 Workers: €0.015/hour × 24h × 5 = €1.80
- **Total: €2.54/day** for 800K German entries

**vs. Local Processing:**
- Laptop blocked for 4.6 days
- Opportunity cost: ~€100-200
- **ROI: 40-80x better with cloud**

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **AQEA Framework** - Universal knowledge database format
- **Wikimedia Foundation** - Wiktionary and Wikidata
- **PanLex Project** - Multilingual lexical database
- **Cloud Providers** - Hetzner, DigitalOcean for affordable compute

## 📞 **Support**

- 📧 Email: your-email@domain.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/aqea-distributed-extractor/issues)
- 💬 Discord: [AQEA Community](https://discord.gg/aqea)

---

**Ready to extract millions of language entries? Let's go! 🚀** 