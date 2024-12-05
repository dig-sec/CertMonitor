import os
import time
import datetime
import logging
from fetch_ssl import SSLCertificateFetcher
from elasticsearch_connector import ElasticsearchClient
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("ssl_monitor.log")]
)
logger = logging.getLogger(__name__)

load_dotenv()

def get_config():
    return {
        'host': os.getenv('ELASTICSEARCH_HOST'),
        'port': int(os.getenv('ELASTICSEARCH_PORT')),
        'username': os.getenv('ELASTICSEARCH_USERNAME'),
        'password': os.getenv('ELASTICSEARCH_PASSWORD'),
        'data_index': os.getenv('ELASTICSEARCH_INDEX'),
        'state_index': os.getenv('ELASTICSEARCH_STATE'),
        'fetch_interval': int(os.getenv('FETCH_INTERVAL'))
    }

def main():
    config = get_config()
    elastic_client = ElasticsearchClient(
        host=config['host'],
        port=config['port'],
        data_index=config['data_index'],
        state_index=config['state_index'],
        username=config['username'],
        password=config['password']
    )
    fetcher = SSLCertificateFetcher()
    last_fetch_timestamp = elastic_client.get_last_fetch_timestamp() or datetime.datetime.utcnow() - datetime.timedelta(minutes=5)

    while True:
        try:
            new_certificates = fetcher.fetch_certificates(last_fetch_timestamp)
            if new_certificates:
                elastic_client.store_certificates(new_certificates)
                elastic_client.update_last_fetch_timestamp(datetime.datetime.utcnow())
            time.sleep(config['fetch_interval'])
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()