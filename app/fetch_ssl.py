import requests
import datetime
import logging


class SSLCertificateFetcher:
    def __init__(self, base_url="https://crt.sh", query="%25"):
        self.base_url = base_url
        self.query = query

    def fetch_certificates(self, last_fetched):
        url = f"{self.base_url}/?q={self.query}&output=json"
        logging.info(f"Fetching certificates from {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            certificates = response.json()
            return self.filter_new_certificates(certificates, last_fetched)
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error while fetching SSL certificates: {e}")
        except ValueError:
            logging.error("Failed to parse JSON response from crt.sh.")
        return []

    def filter_new_certificates(self, certificates, last_fetched):
        new_certificates = []
        for cert in certificates:
            try:
                not_before = datetime.datetime.strptime(
                    cert["not_before"], "%Y-%m-%dT%H:%M:%S"
                )
                if not_before > last_fetched:
                    new_certificates.append(cert)
            except KeyError:
                logging.warning("Certificate missing 'not_before' field.")
            except ValueError:
                logging.warning("Invalid date format in 'not_before' field.")
        return new_certificates
