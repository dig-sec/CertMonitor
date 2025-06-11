import logging
import signal
from config import Config
from elastic import get_client, ensure_index_exists
from monitor import start_monitoring

# Setup logging
logging.basicConfig(level=logging.INFO)


def main():
    cfg = Config()
    client = get_client(cfg)
    if not client.ping():
        logging.error("Cannot reach Elasticsearch")
        return
    ensure_index_exists(client, cfg.elastic_index)

    stop_event, threads = start_monitoring(cfg, client)
    
    def _shutdown(sig, frame):
        logging.info("Shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()