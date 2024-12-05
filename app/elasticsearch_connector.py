from elasticsearch import Elasticsearch
import logging
from datetime import datetime
from elasticsearch.exceptions import ConnectionError, NotFoundError
import urllib3

# Suppress only the single InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticsearchClient:
    def __init__(self, host, port, data_index, state_index, username=None, password=None):
        self.data_index = data_index
        self.state_index = state_index
        logger.info(f"Connecting to Elasticsearch at {host}:{port}")
        es_config = {
            "hosts": [f"{host}:{port}"],
            "http_auth": (username, password) if username and password else None,
            "verify_certs": False
        }
        self.es = Elasticsearch(**es_config)
        self.setup_indices()

    def setup_indices(self):
        mappings = {
            self.data_index: {
                "properties": {
                    "id": {"type": "keyword"},
                    "name_value": {"type": "keyword"},
                    "not_before": {"type": "date"},
                    "not_after": {"type": "date"},
                    "issuer_name": {"type": "keyword"}
                }
            },
            self.state_index: {
                "properties": {
                    "timestamp": {"type": "date"}
                }
            }
        }
        for index, mapping in mappings.items():
            if not self.es.indices.exists(index=index):
                self.es.indices.create(index=index, body={"mappings": mapping})

    def get_last_fetch_timestamp(self):
        try:
            doc = self.es.get(index=self.state_index, id="last_fetch_timestamp")
            return datetime.fromisoformat(doc["_source"]["timestamp"])
        except NotFoundError:
            return None

    def update_last_fetch_timestamp(self, timestamp):
        self.es.index(index=self.state_index, id="last_fetch_timestamp", document={"timestamp": timestamp.isoformat()})

    def store_certificates(self, certificates):
        for cert in certificates:
            self.es.index(index=self.data_index, id=cert["id"], document=cert)