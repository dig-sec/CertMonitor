from fetch_ssl import SSLCertificateFetcher
from elasticsearch_connector import ElasticsearchClient
from dotenv import load_dotenv
import os
import datetime
import time
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Retrieve environment variables
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "localhost")
ELASTICSEARCH_PORT = int(os.getenv("ELASTICSEARCH_PORT", 9200))
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", None)
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", None)
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "ssl_certificates")
ELASTICSEARCH_STATE = os.getenv("ELASTICSEARCH_STATE", "certmonitor_state")

def main():
    # Initialize Elasticsearch client
    elastic_client = ElasticsearchClient(
        host=ELASTICSEARCH_HOST,
        port=ELASTICSEARCH_PORT,
        data_index=ELASTICSEARCH_INDEX,
        state_index=ELASTICSEARCH_STATE
    )
    
    # Check for last fetch timestamp
    last_fetch_timestamp = elastic_client.get_last_fetch_timestamp()
    if not last_fetch_timestamp:
        # Default to fetching certificates from the last 5 minutes on the first run
        last_fetch_timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        logging.info("First run: Fetching certificates from the last 5 minutes.")
    else:
        logging.info(f"Resuming fetch from last timestamp: {last_fetch_timestamp}")

    # Fetch and store certificates in a loop
    fetcher = SSLCertificateFetcher()
    while True:
        logging.info("Fetching new SSL certificates...")
        # Fetch certificates
        new_certificates = fetcher.fetch_certificates(last_fetch_timestamp)
        logging.info(f"Fetched {len(new_certificates)} certificates.")

        # Store new certificates and update the last fetch timestamp
        if new_certificates:
            elastic_client.store_certificates(new_certificates)
            last_fetch_timestamp = datetime.datetime.utcnow()
            elastic_client.update_last_fetch_timestamp(last_fetch_timestamp)

        # Sleep for 5 minutes before the next fetch
        time.sleep(300)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
