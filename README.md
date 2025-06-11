# Certificate Transparency Monitor

**CertMonitor** is a Python 3.11+ application that monitors Certificate Transparency (CT) logs for new X.509 and Precertificate entries and indexes them into Elasticsearch using the official Python client.

---

## Project Structure

```
CertMonitor/
├── src/
│   ├── config.py         # Loads environment variables and configuration
│   ├── ct_parser.py      # Parses CT entries into metadata
│   ├── ct_utils.py       # HTTP utility and CT log list loader
│   ├── elastic.py        # Elasticsearch client and index setup
│   ├── main.py           # Entrypoint
│   ├── monitor.py        # Monitoring and indexing logic
│   └── __pycache__/      # Compiled Python cache
├── .env_sample           # Sample env config
├── .gitignore
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Image definition
├── Makefile              # Optional automation commands
├── README.md             # This documentation
└── requirements.txt      # Python dependencies
```

---

## Features

* Monitors all usable logs from [Google's CT log list](https://www.gstatic.com/ct/log_list/v3/log_list.json)
* Handles both X.509 and Precertificate entries
* Caches seen certificates with TTL to avoid duplication
* Multi-threaded log ingestion
* Uses Elasticsearch Bulk API for high-efficiency indexing
* Resilient HTTP client with retry and backoff
* Graceful shutdown support via `SIGINT`/`SIGTERM`
* Docker and Compose compatible

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/dig-sec/CertMonitor.git
cd CertMonitor
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env_sample .env
# Edit .env with your Elasticsearch credentials and config
```

---

## Docker Setup

### Build and Run with Docker Compose

```bash
docker-compose up --build
```

This spins up the monitor container and runs it using settings from `.env`.

---

## Configuration

Edit the `.env` file or override using environment variables:

| Variable                 | Default                                                | Description                     |
| ------------------------ | ------------------------------------------------------ | ------------------------------- |
| `CT_LOG_LIST_URL`        | `https://www.gstatic.com/ct/log_list/v3/log_list.json` | Google’s CT log list            |
| `ELASTICSEARCH_HOSTS`    | `http://localhost:9200`                                | One or more Elasticsearch hosts |
| `ELASTICSEARCH_INDEX`    | `ssl_certificates`                                     | Index for storing parsed certs  |
| `ELASTICSEARCH_USERNAME` | `elastic`                                              | Auth username                   |
| `ELASTICSEARCH_PASSWORD` | `changeme`                                             | Auth password                   |
| `FETCH_INTERVAL`         | `60`                                                   | Polling interval (seconds)      |
| `BATCH_SIZE`             | `256`                                                  | Entry batch size                |
| `CACHE_MAXSIZE`          | `100000`                                               | Max cached fingerprints         |
| `CACHE_TTL`              | `3600`                                                 | Cache expiry (seconds)          |
| `REQUEST_TIMEOUT`        | `10`                                                   | Timeout for HTTP requests       |

---

## How It Works

1. Loads a list of usable CT logs.
2. Starts one monitoring thread per log.
3. Each thread polls the log, checks for new entries, and fetches them in batches.
4. Entries are parsed into structured metadata (issuer, domains, expiry, key usage, etc.).
5. Duplicate certificates (by fingerprint) are skipped using `cachetools.TTLCache`.
6. Parsed entries are bulk indexed into Elasticsearch via the official client.
7. Handles shutdown signals gracefully.

---

## Elasticsearch Index Mapping

An index template (`ct-monitor-template`) is auto-created for you, containing mappings for:

* `@timestamp`, `fingerprint`, `subject_cn`, `issuer_cn`
* Validity dates, public key info, key usages
* Source log name and entry metadata

No manual setup is required — the template is installed if it doesn't exist.

---

## Local Testing

```bash
python src/main.py
```

This will:

* Connect to Elasticsearch
* Load the CT logs
* Start fetching and indexing entries in real time

---

## Extending the Monitor

* Add webhook/email alerts for specific certs
* Integrate CertStream or other live feed sources
* Enrich parsed certs with WHOIS or threat intelligence
* Build Kibana dashboards for visualization

---