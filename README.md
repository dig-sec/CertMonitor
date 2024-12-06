# CertMonitor

**CertMonitor** is a Python-based application designed to fetch newly registered SSL certificates from certificate transparency logs (e.g., CertStream) and store them in Elasticsearch. The application ensures consistency and scalability, supporting configurable logging and security options.

---

## Features

- Fetches newly issued SSL certificates via CertStream.
- Stores certificate details in an Elasticsearch index.
- Configurable logging level and options for suppressing TLS warnings.
- Dockerized for easy deployment.
- Highly customizable via environment variables.

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.
- Access to an Elasticsearch instance.

### Clone the Repository

```bash
git clone https://github.com/your-repo/certmonitor.git
cd certmonitor
```

---

## Configuration

The application uses environment variables to configure its behavior. Define these variables in a `.env` file located in the root directory.

### Environment Variables

| Variable                  | Description                                 | Default Value             |
|---------------------------|---------------------------------------------|---------------------------|
| `ELASTICSEARCH_HOST`      | Hostname or IP of the Elasticsearch server | `localhost`               |
| `ELASTICSEARCH_PORT`      | Port of the Elasticsearch server           | `9200`                    |
| `ELASTICSEARCH_INDEX`     | Index name for storing SSL certificates    | `ssl_certificates`        |
| `ELASTICSEARCH_USERNAME`  | Elasticsearch username (optional)          | `None`                    |
| `ELASTICSEARCH_PASSWORD`  | Elasticsearch password (optional)          | `None`                    |
| `ELASTICSEARCH_VERIFY_CERTS` | Verify SSL/TLS certificates when connecting to Elasticsearch (`True`/`False`) | `False`                  |
| `LOG_LEVEL`               | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO`                   |

### Suppressing TLS Warnings

By default, the application uses the `ELASTICSEARCH_VERIFY_CERTS` variable to decide whether to verify Elasticsearch SSL/TLS certificates. Set this to `False` to disable verification, and the application will suppress related warnings automatically.

---

## Usage

### Running Locally

1. **Install Dependencies**

   Create a virtual environment and install the required dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the Application**

   ```bash
   python main.py
   ```

### Running with Docker

1. **Build the Docker Image**

   ```bash
   docker-compose build
   ```

2. **Run the Application**

   ```bash
   docker-compose up -d
   ```

3. **Check Logs**

   ```bash
   docker-compose logs -f certmonitor
   ```

---

## How It Works

1. **Certificate Stream**:
   - Fetches real-time SSL certificate data from CertStream.
   - Processes the data and stores it in the Elasticsearch index.

2. **Batch Processing**:
   - Buffers certificates in batches of 100 before indexing in Elasticsearch.
   - Ensures efficient storage and reduces network overhead.

3. **Customizable Logging**:
   - Set the `LOG_LEVEL` to control the verbosity of application logs.

4. **Elasticsearch Integration**:
   - Stores detailed SSL certificate information in the configured index.
   - Optionally verifies SSL/TLS certificates using the `ELASTICSEARCH_VERIFY_CERTS` variable.

---

## Elasticsearch Indices

### `ssl_certificates`

Stores detailed SSL certificate data, including subject information, domains, validity periods, and extensions.

#### Example Document
```json
{
  "@timestamp": "2024-12-06T10:00:00Z",
  "message_type": "certificate_update",
  "subject": {
    "common_name": "example.com",
    "organization": "Example Org",
    "country": "US"
  },
  "domains": {
    "primary_domain": "example.com",
    "additional_domains": ["www.example.com", "mail.example.com"]
  },
  "certificate": {
    "not_before": "2024-12-01T00:00:00Z",
    "not_after": "2025-12-01T00:00:00Z",
    "serial_number": "123456789ABCDEF",
    "fingerprint": "SHA256:..."
  }
}
```

---

## Extending the Application

1. **Add New Data Sources**:
   - Modify the `parse_certificate_update` function to incorporate other certificate transparency sources.

2. **Enhance Elasticsearch Mappings**:
   - Define custom mappings for the `ssl_certificates` index to optimize search queries and improve performance.

3. **Integrate Alerting Mechanisms**:
   - Add webhook or email notifications to alert about specific certificate updates.

---

## Contributing

Contributions are welcome! Fork the repository and submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---
