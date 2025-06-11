from elasticsearch import Elasticsearch, exceptions as es_exceptions
import logging

def get_client(cfg):
    try:
        client = Elasticsearch(
            hosts=[cfg.elasticsearch_hosts],
            basic_auth=(cfg.elastic_username, cfg.elastic_password),
            request_timeout=cfg.request_timeout,
        )
        return client
    except es_exceptions.ElasticsearchException as e:
        logging.error(f"Failed to create Elasticsearch client: {e}")
        raise

def ensure_index_exists(client: Elasticsearch, index_name: str):
    template_name = "ssl-certificates-template"
    template_body = {
        "index_patterns": [index_name],
        "template": {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "timestamp": {"type": "long"},
                    "type": {"type": "keyword"},
                    "update_type": {"type": "keyword"},
                    "fingerprint": {"type": "keyword"},
                    "version": {"type": "integer"},
                    "serial_number": {"type": "keyword"},
                    "signature_algorithm": {"type": "keyword"},
                    "issuer_cn": {"type": "keyword"},
                    "subject_cn": {"type": "keyword"},
                    "validity": {
                        "properties": {
                            "not_before": {
                                "type": "date",
                                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSXXX||yyyy-MM-dd'T'HH:mm:ss.SSSX||strict_date_optional_time||epoch_millis"
                            },
                            "not_after": {
                                "type": "date",
                                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSXXX||yyyy-MM-dd'T'HH:mm:ss.SSSX||strict_date_optional_time||epoch_millis"
                            },
                            "valid_days": {"type": "integer"}
                        }
                    },
                    "subject_public_key_info": {
                        "properties": {
                            "algorithm": {"type": "keyword"},
                            "key_size_bits": {"type": "integer"},
                            "curve_name": {"type": "keyword"}
                        }
                    },
                    "all_domains": {"type": "keyword"},
                    "ocsp_url": {"type": "keyword"},
                    "issuer_cert_url": {"type": "keyword"},
                    "crl_url": {"type": "keyword"},
                    "key_usage": {"type": "keyword"},
                    "extended_key_usage": {"type": "keyword"},
                    "cert_index": {"type": "integer"},
                    "cert_link": {"type": "keyword"},
                    "seen": {"type": "date"},
                    "source": {
                        "properties": {
                            "url": {"type": "keyword"},
                            "name": {"type": "keyword"}
                        }
                    },
                    "chain_summary": {
                        "type": "object",
                        "enabled": False
                    }
                }
            }
        },
        "priority": 500
    }
    
    try:
        # Check if template exists
        if not client.indices.exists_index_template(name=template_name):
            client.indices.put_index_template(name=template_name, body=template_body)
            logging.info("Created ct-monitor index template in Elasticsearch.")
        else:
            logging.info("ct-monitor index template already exists in Elasticsearch.")
    except es_exceptions.ElasticsearchException as e:
        logging.error(f"Error ensuring index template exists: {e}")

    # Now ensure the index exists
    try:
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name)
            logging.info(f"Created missing Elasticsearch index: {index_name}")
        else:
            logging.info(f"Elasticsearch index '{index_name}' already exists.")
    except es_exceptions.ElasticsearchException as e:
        logging.error(f"Error ensuring index exists: {e}")