"""Background SLA monitor: checks every open incident on a fixed interval."""
import logging
import threading

from app.services.container import build_container

logger = logging.getLogger("iitsm.sla_monitor")


class SlaMonitor:
    def __init__(self, session_factory, clock, app_settings, interval_seconds: int = 60):
        self.session_factory = session_factory
        self.clock = clock
        self.app_settings = app_settings
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_run: dict | None = None
        self.runs = 0

    def run_once(self) -> dict:
        session = self.session_factory()
        try:
            container = build_container(session, self.clock, self.app_settings)
            summary = container.sla.run_check()
            self.last_run = summary
            self.runs += 1
            if summary["warnings"] or summary["breaches"] or summary["escalations"]:
                logger.info("SLA check: %s", summary)
            return summary
        finally:
            session.close()

    def _loop(self) -> None:
        logger.info("SLA monitor started (every %s s)", self.interval)
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 - the monitor must never die
                logger.exception("SLA monitor iteration failed")
            self._stop.wait(self.interval)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="sla-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
