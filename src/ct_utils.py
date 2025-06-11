import time
import requests
import logging
from datetime import datetime, timezone
from typing import Optional


def make_request(url: str, session: requests.Session, timeout: int, max_retries: int = 3) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 60)
                logging.warning(f"429 Too Many Requests for {url}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request to {url} failed: {e}. Attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(min(2 ** attempt, 60))
            else:
                logging.error(f"Failed after {max_retries} attempts: {e}")
                return None

def load_log_list(url: str, timeout: int):
    session = requests.Session()
    try:
        resp = make_request(url, session, timeout)
        if not resp:
            raise Exception("Failed to fetch log list")
        data = resp.json()
    except Exception as e:
        logging.error(f"Could not load CT log list: {e}")
        return []
    logs = []
    log_entries = data.get("logs", data.get("operators", []))
    if "operators" in data:
        log_entries = []
        for operator in data["operators"]:
            log_entries.extend(operator.get("logs", []))
    now = datetime.now(timezone.utc)
    for log in log_entries:
        state = log.get("state", {})
        if "usable" not in state:
            continue
        interval = log.get("temporal_interval")
        if interval:
            try:
                start = datetime.fromisoformat(interval["start_inclusive"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(interval["end_exclusive"].replace("Z", "+00:00"))
                if now < start or now >= end:
                    continue
            except Exception as e:
                logging.warning(f"Cannot parse temporal_interval for {log.get('description')}: {e}")
        logs.append(log)
    logging.info(f"Loaded {len(logs)} CT logs to monitor.")
    return logs