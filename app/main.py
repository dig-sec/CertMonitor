import logging
import datetime
from datetime import timezone
import certstream
from elasticsearch import Elasticsearch, helpers
import os
from dotenv import load_dotenv

import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    format='[%(levelname)s:%(name)s] %(asctime)s - %(message)s',
    level=logging.WARNING  # Change level to WARNING
)

# Elasticsearch configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "localhost")
ELASTICSEARCH_VERIFY_CERTS = os.getenv("ELASTICSEARCH_VERIFY_CERTS", "False").lower() in ("true", "1", "yes")
ELASTICSEARCH_PORT = int(os.getenv("ELASTICSEARCH_PORT", 9200))
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "ssl_certificates")

# Initialize Elasticsearch client
try:
    es = Elasticsearch(
        hosts=[{
            "host": ELASTICSEARCH_HOST,
            "port": ELASTICSEARCH_PORT,
            "scheme": "https"
        }],
        basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD),
        verify_certs=ELASTICSEARCH_VERIFY_CERTS
    )
except Exception as e:
    logging.critical(f"Failed to initialize Elasticsearch client: {e}")
    exit(1)

batch = []
BATCH_SIZE = 100

def parse_certificate_update(message):
    """Parses the certificate update and structures the output for Elasticsearch."""
    current_timestamp = datetime.datetime.now(timezone.utc)
    cert_data = message['data']
    leaf_cert = cert_data.get('leaf_cert', {})
    subject = leaf_cert.get('subject', {})
    extensions = leaf_cert.get('extensions', {})
    all_domains = leaf_cert.get('all_domains', [])

    parsed_domains = {
        'primary_domain': all_domains[0] if all_domains else None,
        'additional_domains': all_domains[1:] if len(all_domains) > 1 else []
    }

    cert_info = {
        "_index": ELASTICSEARCH_INDEX,
        "_source": {
            "@timestamp": current_timestamp,
            "message_type": message['message_type'],
            
            "subject_country": subject.get('C'),
            "subject_state": subject.get('ST'),
            "subject_locality": subject.get('L'),
            "subject_organization": subject.get('O'),
            "subject_organizational_unit": subject.get('OU'),
            "subject_common_name": subject.get('CN'),
            "subject_full": subject.get('aggregated', ''),
            
            "domains": parsed_domains,
            
            "certificate": {
                "not_before": datetime.datetime.fromtimestamp(leaf_cert.get('not_before'), timezone.utc) if leaf_cert.get('not_before') else None,
                "not_after": datetime.datetime.fromtimestamp(leaf_cert.get('not_after'), timezone.utc) if leaf_cert.get('not_after') else None,
                "serial_number": leaf_cert.get('serial_number'),
                "fingerprint": leaf_cert.get('fingerprint'),
            },
            
            "extensions": {
                "key_usage": extensions.get('keyUsage'),
                "extended_key_usage": extensions.get('extendedKeyUsage'),
                "basic_constraints": extensions.get('basicConstraints'),
                "subject_key_identifier": extensions.get('subjectKeyIdentifier'),
                "authority_key_identifier": extensions.get('authorityKeyIdentifier'),
                "subject_alt_name": extensions.get('subjectAltName'),
            },
            
            "source": {
                "update_type": cert_data.get('update_type'),
                "seen": cert_data.get('seen'),
                "original_source": cert_data.get('source', {})
            }
        }
    }

    return cert_info

def print_callback(message, context):
    global batch
    if message['message_type'] != "certificate_update":
        return

    parsed_data = parse_certificate_update(message)
    batch.append(parsed_data)

    if len(batch) >= BATCH_SIZE:
        insert_to_elasticsearch()

def insert_to_elasticsearch():
    global batch
    if not batch:
        return

    try:
        helpers.bulk(es, batch)
        logging.info(f"Inserted {len(batch)} documents into Elasticsearch.")
        batch = []
    except Exception as e:
        logging.error(f"Error inserting documents: {e}")
        batch = []

def on_open():
    logging.info("Connection successfully established!")

def on_error(instance, exception=None):
    logging.error(f"Exception in CertStreamClient! -> {exception}")

def main():
    try:
        certstream.listen_for_events(print_callback, on_open=on_open, on_error=on_error, url='wss://certstream.calidog.io/')
    except Exception as e:
        logging.critical(f"Critical error in main execution: {e}")
    finally:
        insert_to_elasticsearch()

if __name__ == "__main__":
    main()