# DVH Analyzer

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Standards:** QUANTEC, RTOG, ICRU 83, CAP / CLSI / ISO

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-10%20passing-brightgreen.svg)

</div>

---

## 📖 What It Does

**DVH Analyzer** is a radiation oncology Dose-Volume Histogram (DVH) analysis platform that evaluates treatment plans against QUANTEC/RTOG clinical constraints. It provides:

- **DVH Parsing:** Import tabular DVH data from CSV exports (Eclipse, RayStation, Monaco)
- **Dosimetric Metrics:** VxGy, Dy%, Dmean, Dmax, Homogeneity Index (ICRU 83), gEUD
- **QUANTEC Compliance:** Automated evaluation against standard organ-at-Risk constraints
- **SVG Visualization:** Publication-ready DVH plots with zero external dependencies
- **REST API:** FastAPI server with Prometheus telemetry endpoints
- **Audit Trail:** HMAC-SHA256 tamper-evident logging for all evaluations
- **PHI Guard:** Regex-based detection and blocking of outbound patient identifiers

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/dvh-analyzer.git
cd dvh-analyzer

# Install dependencies
pip install -e ".[dev]"
```

**Optional dependencies:**
```bash
# For REST API server
pip install fastapi uvicorn
```

---

## 💻 CLI Usage

### 1. Generate Sample Data
```bash
python -m dvh_analyzer.cli sample-csv --output sample.csv
```

### 2. Generate DVH Report (Metrics + QUANTEC Compliance)
```bash
python -m dvh_analyzer.cli report --input sample.csv --rx 60.0
```

### 3. Render DVH Plot (SVG)
```bash
python -m dvh_analyzer.cli plot --input sample.csv --output dvh_plot.svg --rx 60.0
```

### CLI Parameters

| Parameter | Command | Description |
|:----------|:--------|:------------|
| `-i, --input` | report, plot | Path to DVH CSV file |
| `-o, --output` | plot, sample-csv | Output file path |
| `--rx` | report, plot | Prescribed dose in Gy (default: 60.0) |
| `-t, --title` | plot | SVG plot title |

### Input CSV Format

The DVH CSV file should have a header row starting with `Dose_Gy` (or `Dose_cGy`), followed by structure names:

```csv
Dose_Gy,PTV_60Gy,Spinal_Cord,Total_Lungs,Heart,Esophagus
0.0,100.00,100.00,100.00,100.00,100.00
10.0,100.00,60.00,52.00,25.00,60.00
20.0,100.00,30.00,22.00,12.50,40.00
...
```

---

## 🌐 REST API Server

### Start the Server
```bash
# Using CLI
python cli.py serve --host 127.0.0.1 --port 8000

# Or with uvicorn directly
uvicorn agents.api:app --host 127.0.0.1 --port 8000
```

### Endpoints

| Method | Path | Description |
|:-------|:-----|:------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus-style metrics |
| POST | `/api/audit` | Submit task for evaluation |
| POST | `/api/chat` | Query supervisor chat |
| GET | `/api/audit/logs` | Retrieve audit trail |

### Security Configuration

Set the `AUDIT_SECRET_KEY` environment variable before running in production:

```bash
# Linux/macOS
export AUDIT_SECRET_KEY=$(openssl rand -hex 32)

# Windows PowerShell
$env:AUDIT_SECRET_KEY = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | % {[char]$_})
```

---

## 🐳 Docker Deployment

```bash
# Build and run
docker compose up --build

# Or manually
docker build -t dvh-analyzer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key dvh-analyzer
```

---

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run specific test files
pytest tests/test_dvh.py -v        # DVH core functionality
pytest tests/test_dvh_analyzer.py -v  # Agent system
pytest tests/test_enrichment.py -v    # Enrichment modules
```

**Current test results:** 10/10 tests passing

---

## 📁 Project Structure

```
dvh-analyzer/
├── dvh_analyzer/          # Core DVH analysis library
│   ├── models.py          # Data models & QUANTEC constraints
│   ├── parser.py          # CSV/DVH file parser
│   ├── metrics.py         # Dosimetric calculations
│   ├── evaluator.py       # QUANTEC compliance engine
│   ├── renderer_svg.py    # SVG visualization
│   └── cli.py             # Command-line interface
├── agents/                # Enterprise agent system
│   ├── api.py             # FastAPI server
│   ├── base.py            # Security, PHI guard, audit trail
│   ├── supervisor.py      # Orchestrator
│   ├── workers.py         # Evaluation workers
│   ├── models.py          # Pydantic schemas
│   └── metrics.py         # Prometheus metrics
├── tests/                 # Test suite
├── web/                   # Web operations console
├── cli.py                 # Agent system CLI
├── enrichment.py          # Enrichment modules
├── simulator.py           # Load testing simulator
└── Dockerfile             # Container configuration
```

---

## 🛡️ Security Features

- **PHI Outbound Guard:** Regex-based detection of SSNs, MRNs, phone numbers, emails, DOBs
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed audit logs
- **Input Validation:** File path validation, positive dose constraints
- **Zero External Dependencies:** Pure Python implementation for core calculations

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
