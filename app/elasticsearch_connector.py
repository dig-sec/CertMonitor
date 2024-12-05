import datetime
from elasticsearch import Elasticsearch
import logging

class ElasticsearchClient:
    def __init__(self, host="localhost", port=9200, data_index="ssl_certificates", state_index="certmonitor_state"):
        self.es = Elasticsearch([{"host": host, "port": port}])
        self.data_index = data_index
        self.state_index = state_index
        self.timestamp_doc_id = "last_fetch_timestamp"
        self.setup_indices()

    def setup_indices(self):
        """
        Create the data and state indices if they do not exist.
        """
        if not self.es.indices.exists(index=self.data_index):
            self.es.indices.create(index=self.data_index)
            logging.info(f"Created data index: {self.data_index}")

        if not self.es.indices.exists(index=self.state_index):
            self.es.indices.create(index=self.state_index)
            logging.info(f"Created state index: {self.state_index}")

    def get_last_fetch_timestamp(self):
        """
        Retrieve the last fetch timestamp from the state index.
        Returns the timestamp or None if not set.
        """
        try:
            result = self.es.get(index=self.state_index, id=self.timestamp_doc_id)
            return datetime.datetime.fromisoformat(result["_source"]["timestamp"])
        except Exception as e:
            logging.warning(f"Failed to fetch last timestamp: {e}")
            return None

    def update_last_fetch_timestamp(self, timestamp):
        """
        Update the last fetch timestamp in the state index.
        """
        try:
            self.es.index(
                index=self.state_index,
                id=self.timestamp_doc_id,
                document={"timestamp": timestamp.isoformat()}
            )
            logging.info(f"Updated last fetch timestamp to: {timestamp}")
        except Exception as e:
            logging.error(f"Failed to update last fetch timestamp: {e}")

    def store_certificates(self, certificates):
        """
        Store a list of SSL certificates in the Elasticsearch data index.
        """
        for cert in certificates:
            cert_id = cert.get("id")  # Replace with actual unique identifier field
            if not self.certificate_exists(cert_id):
                self.es.index(index=self.data_index, id=cert_id, document=cert)
                self.mark_certificate_as_processed(cert_id)
            else:
                logging.info(f"Certificate {cert_id} already exists in the state index.")

    def certificate_exists(self, cert_id):
        """
        Check if a certificate ID exists in the state index.
        """
        return self.es.exists(index=self.state_index, id=cert_id)

    def mark_certificate_as_processed(self, cert_id):
        """
        Add a certificate ID to the state index to mark it as processed.
        """
        self.es.index(index=self.state_index, id=cert_id, document={"processed": True})
