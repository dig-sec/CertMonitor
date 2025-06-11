import threading
from threading import Event, Thread, Lock
import logging
import json
import time
import requests
from typing import Optional, Tuple, List
from cachetools import TTLCache
from elasticsearch.helpers import bulk
from ct_parser import parse_ct_entry
from ct_utils import make_request, load_log_list

# Thread-safe lock for shared cert cache
seen_lock = Lock()

def monitor_log(log_info: dict, cfg, client, seen_cache: TTLCache, stop_event: Event) -> None:
    """Monitor a single CT log for new certificates."""
    session = requests.Session()

    desc = log_info.get("description", "CT Log")
    url = log_info.get("url", "")
    if not url.endswith("/"):
        url += "/"

    sth_url = url + "ct/v1/get-sth"
    entries_url = url + "ct/v1/get-entries"
    next_index = 0

    # Initialize monitoring position
    resp = make_request(sth_url, session, cfg.request_timeout)
    if resp:
        try:
            sth_data = resp.json()
            tree_size = int(sth_data.get("tree_size", 0))
            next_index = tree_size
            logging.info(f"Monitoring {desc}: starting at index {next_index}")
        except Exception as e:
            logging.error(f"Failed to initialize {desc}: {e}")
            return
    else:
        logging.error(f"Failed to fetch initial STH for {desc}")
        return

    while not stop_event.is_set():
        try:
            # Get current tree size
            resp = make_request(sth_url, session, cfg.request_timeout)
            if resp:
                try:
                    current_size = int(resp.json().get("tree_size", 0))
                except (ValueError, KeyError, TypeError) as e:
                    logging.error(f"{desc}: Invalid STH response: {e}")
                    current_size = next_index
            else:
                current_size = next_index

            # Handle tree size changes
            if current_size < next_index:
                logging.warning(f"{desc}: tree size decreased from {next_index} to {current_size}, resetting index.")
                next_index = current_size

            # Process new entries
            if current_size > next_index:
                start = next_index
                end = min(current_size - 1, start + cfg.batch_size - 1)

                while start <= end and not stop_event.is_set():
                    batch_url = f"{entries_url}?start={start}&end={end}"
                    resp_entries = make_request(batch_url, session, cfg.request_timeout)
                    if not resp_entries:
                        logging.warning(f"{desc}: Failed to fetch entries [{start}, {end}], skipping batch")
                        start = end + 1
                        continue

                    try:
                        data = resp_entries.json()
                    except Exception as e:
                        logging.error(f"Failed to parse entries for {desc}: {e}")
                        start = end + 1
                        continue

                    entries = data.get("entries", [])
                    if not entries:
                        logging.warning(f"{desc}: No entries in response for batch [{start}, {end}]")
                        start = end + 1
                        continue

                    # Process certificates
                    docs = []
                    for idx, entry in enumerate(entries, start=start):
                        try:
                            cert_meta = parse_ct_entry(entry, url, idx, seen_cache, seen_lock)
                            if cert_meta:
                                cert_meta["source"]["name"] = desc
                                docs.append(cert_meta)
                        except Exception as e:
                            logging.error(f"{desc}: Error parsing entry {idx}: {e}")
                            continue

                    # Index to Elasticsearch
                    if docs:
                        try:
                            actions = [
                                {
                                    "_index": cfg.elastic_index,
                                    "_source": doc
                                }
                                for doc in docs
                            ]
                            success, failed = bulk(client, actions, stats_only=True)
                            if failed:
                                logging.warning(f"{desc}: {failed} documents failed to index")
                            logging.info(f"{desc}: Successfully indexed {success} documents to Elasticsearch.")
                        except Exception as e:
                            logging.error(f"{desc}: Bulk indexing failed: {e}")

                    logging.info(f"Processed {len(docs)} certificates from {desc} in batch [{start}, {end}]")
                    start = end + 1
                    end = min(current_size - 1, start + cfg.batch_size - 1)
                    next_index = start

            # Wait before next check
            time.sleep(cfg.fetch_interval)
            
        except Exception as e:
            logging.exception(f"{desc}: Exception in monitor loop: {e}")
            time.sleep(cfg.fetch_interval)
        finally:
            # Ensure session is cleaned up on thread exit
            if 'session' in locals():
                session.close()


def start_monitoring(cfg, client) -> Optional[Tuple[Event, List[Thread]]]:
    """Start monitoring all configured CT logs."""
    logs = load_log_list(cfg.ct_log_list_url, cfg.request_timeout)
    if not logs:
        logging.error("No CT logs loaded. Monitoring will not start.")
        return None

    logging.info(f"Starting monitoring for {len(logs)} CT logs")
    
    seen_cache = TTLCache(maxsize=cfg.cache_maxsize, ttl=cfg.cache_ttl)
    stop_event = threading.Event()
    threads = []

    for log in logs:
        try:
            t = Thread(
                target=monitor_log,
                args=(log, cfg, client, seen_cache, stop_event),
                daemon=True,
                name=f"CTMonitor-{log.get('description', 'Unknown')}"
            )
            t.start()
            threads.append(t)
            logging.info(f"Started monitoring thread for {log.get('description', 'Unknown CT Log')}")
        except Exception as e:
            logging.error(f"Failed to start monitoring thread for {log.get('description', 'Unknown')}: {e}")

    if not threads:
        logging.error("No monitoring threads started successfully")
        return None

    return stop_event, threads
