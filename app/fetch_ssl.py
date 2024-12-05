import requests
import datetime
import hashlib
import logging
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSLCertificateFetcher:
    def __init__(self, base_url="https://crt.sh", query="%25", timeout=10):
        self.base_url = base_url
        self.query = quote(query)
        self.timeout = timeout

    def fetch_certificates(self, last_fetched):
        url = f"{self.base_url}/?q={self.query}&output=json"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.headers.get("Content-Type") != "application/json":
                logger.error(f"Unexpected response content type: {response.headers.get('Content-Type')}")
                logger.error(f"Response text: {response.text}")
                return []
            response.raise_for_status()
            certificates = response.json()
            return self.filter_new_certificates(certificates, last_fetched)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching certificates: {e}")
            return []
        except ValueError as ve:
            logger.error(f"Error parsing JSON response: {ve}")
            logger.error(f"Response text: {response.text}")
            return []


    def filter_new_certificates(self, certificates, last_fetched):
        filtered = []
        for cert in certificates:
            try:
                not_before = datetime.datetime.strptime(cert.get("not_before", ""), "%Y-%m-%dT%H:%M:%S")
                if not_before > last_fetched:
                    cert["id"] = self.generate_id(cert)
                    filtered.append(cert)
            except Exception as e:
                logger.warning(f"Error parsing certificate: {cert}, {e}")
        return filtered

    def generate_id(self, cert):
        id_string = f"{cert.get('name_value', '')}-{cert.get('not_before', '')}-{cert.get('issuer_name', '')}"
        return hashlib.md5(id_string.encode()).hexdigest()