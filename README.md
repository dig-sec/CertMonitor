# Certificate Transparency Monitor

**CertMonitor** is a Python3 application that continuously monitors Certificate Transparency (CT) logs for newly issued X.509 and Precertificate entries and indexes them into Elasticsearch.

---

## Project Structure

```
CertMonitor/        # project root
├── app/
│   └── main.py      # entrypoint
├── Dockerfile       # container build instructions
├── docker-compose.yml
├── requirements.txt
├── .env_sample       # example environment file
├── README.md         # this documentation
└── Makefile          # helper commands (optional)
```

---

## Features

* Fetches and parses CT log entries from all usable logs listed in [Google's CT log list](https://www.gstatic.com/ct/log_list/v3/log_list.json).
* Supports both X.509 and Precertificate entry types.
* Deduplicates via in-memory caching (TTL-based) to avoid reprocessing certificates.
* Batch indexing into Elasticsearch using the Bulk API.
* Robust HTTP requests with retries, exponential backoff, and 429 handling.
* Configurable via environment variables or a `.env` file.
* Graceful shutdown on `SIGINT` and `SIGTERM`.
* (Optional) Dockerized for container-based deployment.

---

## Prerequisites

* Python 3.7+
* Elasticsearch 7.x or 8.x
* (Optional) Docker & Docker Compose for containerized deployment

---

## Installation

### Clone the repository

```bash
git clone https://github.com/dig-sec/CertMonitor.git
cd ct-monitor
```

### Python setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment variables

Copy the sample and edit values:

```bash
cp .env_sample .env
# then edit .env with your settings
```

---

## Docker Deployment

A `Dockerfile` and `docker-compose.yml` are provided for containerized runs.

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "app/main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  certmonitor:
    build:
      context: .
    container_name: certmonitor
    working_dir: /app
    env_file: .env
    volumes:
      - ./:/app
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Bring up the container:

```bash
docker-compose up -d
```

---

## Configuration

Configure via environment variables in `.env` (see `.env_sample`):

| Variable                 | Default                                                | Description                            |
| ------------------------ | ------------------------------------------------------ | -------------------------------------- |
| `CT_LOG_LIST_URL`        | `https://www.gstatic.com/ct/log_list/v3/log_list.json` | CT log list metadata URL               |
| `ELASTICSEARCH_HOSTS`    | `http://localhost:9200`                                | Elasticsearch host(s), comma-separated |
| `ELASTICSEARCH_INDEX`    | `ssl_certificates`                                     | Target index name                      |
| `ELASTICSEARCH_USERNAME` | `elastic`                                              | Elasticsearch username                 |
| `ELASTICSEARCH_PASSWORD` | `changeme`                                             | Elasticsearch password                 |
| `FETCH_INTERVAL`         | `60`                                                   | Seconds between batch polls            |
| `BATCH_SIZE`             | `256`                                                  | Entries per bulk request               |
| `CACHE_MAXSIZE`          | `100000`                                               | Max entries in cache                   |
| `CACHE_TTL`              | `3600`                                                 | Cache TTL (seconds)                    |
| `REQUEST_TIMEOUT`        | `10`                                                   | HTTP request timeout (seconds)         |

---

## Usage

### Local

```bash
python app/main.py
```

### Docker

```bash
docker-compose up -d
```

The monitor will:

1. Connect to Elasticsearch and create the index/template if missing.
2. Load all usable CT logs and spawn one thread per log.
3. Fetch new entries in batches, parse and dedupe.
4. Bulk index to Elasticsearch until interrupted.

---

## Elasticsearch Index Template

An example template to ensure correct mappings:

```http
PUT _index_template/ct-monitor-template
{
  "index_patterns": ["ct-monitor*"],
  "template": { "mappings": { /* see mappings below */ } },
  "priority": 500
}
```

Full mapping properties include date, keywords for fingerprints, issuer\_cn, subject\_cn, validity dates, public key info, URLs, key usages, and more.

---

## How It Works

1. **Log Discovery**: Load usable CT logs from Google's JSON list.
2. **Threaded Monitoring**: Spawn a thread per log, polling tree size every `FETCH_INTERVAL` seconds.
3. **Batch Fetching**: Download new entries in batches of size `BATCH_SIZE`.
4. **Parsing**: Decode DER certificates, extract metadata (fingerprint, domains, validity, key usage, extensions).
5. **Deduplication**: Use `cachetools.TTLCache` to skip already seen fingerprints.
6. **Indexing**: Bulk index parsed documents to Elasticsearch.
7. **Shutdown**: Handle `SIGINT`/`SIGTERM` for graceful exit.

---

## Extending

* **Add Data Sources**: Integrate additional CT feed sources (e.g., CertStream).
* **Alerting**: Hook into webhooks/emails for real-time alerts on specific certificates.
* **Custom Mappings**: Tailor Elasticsearch mappings for performance and query patterns.

---

## Contributing

1. Fork and clone.
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m "Add feature"`
4. Push and open a PR.

Please include tests and documentation for new functionality.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
