from elasticsearch import Elasticsearch
from elastic_transport import ApiError
import logging

def get_client(cfg):
    try:
        client = Elasticsearch(
            hosts=[cfg.elasticsearch_hosts],
            basic_auth=(cfg.elastic_username, cfg.elastic_password),
            request_timeout=cfg.request_timeout,
        )
        return client
    except ApiError as e:
        logging.error(f"Failed to create Elasticsearch client: {e}")
        raise

def ensure_index_exists(client: Elasticsearch, base_index_name: str):
    index_name = f"{base_index_name}-000001"
    alias_name = base_index_name
    template_name = f"{base_index_name}-template"
    policy_name = f"{base_index_name}_policy"

    template_body = {
        "index_patterns": [f"{base_index_name}-*"],
        "template": {
            "settings": {
                "index.lifecycle.name": policy_name,  # assumes policy already exists
                "index.lifecycle.rollover_alias": alias_name,
                "number_of_replicas": 1,
                "refresh_interval": "1s",
                "routing.allocation.include._tier_preference": "data_content"
            },
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
        if not client.indices.exists_index_template(name=template_name):
            client.indices.put_index_template(name=template_name, body=template_body)
            logging.info("Created index template.")
        else:
            logging.info("Index template already exists.")
    except ApiError as e:
        logging.error(f"Error ensuring index template exists: {e}")

    try:
        if not client.indices.exists(index=index_name):
            client.indices.create(
                index=index_name,
                body={
                    "aliases": {
                        alias_name: {
                            "is_write_index": True
                        }
                    }
                }
            )
            logging.info(f"Created index {index_name} with alias {alias_name}.")
        else:
            logging.info(f"Index '{index_name}' already exists.")
    except ApiError as e:
        logging.error(f"Error ensuring index exists: {e}")
