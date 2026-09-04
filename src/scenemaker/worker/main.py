"""Worker loop: pop job ids from the queue and process them until stopped."""

import logging
import signal
import threading

from scenemaker.services import Services, build_services
from scenemaker.worker.tasks import process_job

log = logging.getLogger(__name__)


def run_worker(services: Services | None = None, *, poll_seconds: float = 5.0) -> None:
    services = services or build_services()
    stop = threading.Event()

    def _handle_signal(signum, _frame):  # noqa: ANN001
        log.info("received signal %s, finishing current job", signum)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    log.info("worker started, queue backend=%s", services.settings.queue_backend)
    while not stop.is_set():
        job_id = services.queue.pop(poll_seconds)
        if job_id is None:
            continue
        process_job(services, job_id)
    log.info("worker stopped")
