from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

@dataclass
class Config:
    elasticsearch_hosts: str = os.getenv("ELASTICSEARCH_HOSTS", "http://localhost:9200")
    elastic_username: str = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
    elastic_password: str = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
    elastic_index: str = os.getenv("ELASTICSEARCH_INDEX", "ssl_certificates")
    fetch_interval: int = int(os.getenv("FETCH_INTERVAL", "60"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "256"))
    cache_maxsize: int = int(os.getenv("CACHE_MAXSIZE", "100000"))
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "10"))
    ct_log_list_url: str = os.getenv(
        "CT_LOG_LIST_URL",
        "https://www.gstatic.com/ct/log_list/v3/log_list.json",
    )