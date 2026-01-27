# taitan/core/scheduler.py

import time
import threading
from typing import Callable


class Scheduler:
    """
    주기 실행 스케줄러
    """

    def __init__(
        self,
        interval_sec: int,
        task: Callable,
        logger,
    ):
        self.interval_sec = interval_sec
        self.task = task
        self.logger = logger

        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )

    def start(self):
        self.logger.info(
            "Scheduler starting (interval=%ss)",
            self.interval_sec,
        )
        self._thread.start()

    def stop(self):
        self.logger.info("Scheduler stopping...")
        self._stop_event.set()
        self._thread.join()
        self.logger.info("Scheduler stopped")

    def _run(self):
        """
        내부 실행 루프
        """
        next_run = time.time()

        while not self._stop_event.is_set():
            now = time.time()

            if now >= next_run:
                try:
                    self.logger.debug("Scheduler tick")
                    self.task()
                except Exception:
                    self.logger.exception("Error during scheduled task")

                next_run = now + self.interval_sec

            time.sleep(0.1)
