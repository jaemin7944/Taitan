# taitan/app/app.py

from pathlib import Path
import sys
import signal
from taitan.core.scheduler import Scheduler
from taitan.infra.config import load_config
from taitan.infra.logger import init_logger
import time
from taitan.core.engine import Engine

def run(
    base_dir: Path,
    config_dir: Path,
    log_dir: Path,
    exe_mode: bool = False,
):
    """
    타이탄 애플리케이션 진입점
    - main.py에서 호출됨
    - 전체 초기화 및 실행 흐름을 담당
    """

    # ------------------------------------------------------------------
    # 1. 설정 로딩
    # ------------------------------------------------------------------
    config = load_config(config_dir)

    # ------------------------------------------------------------------
    # 2. logger 초기화 (config 연동)
    # ------------------------------------------------------------------
    logger = init_logger(
        log_dir=log_dir,
        level=config["log"]["level"],
    )

    logger.info("Titan app starting")
    logger.info("exe_mode = %s", exe_mode)
    logger.info("base_dir = %s", base_dir)
    logger.info("config_dir = %s", config_dir)
    logger.info("log_dir = %s", log_dir)

    logger.info("Config loaded successfully")
    logger.info(
        "Scheduler interval = %ss",
        config["scheduler"]["interval_sec"],
    )

    # ------------------------------------------------------------------
    # 3. 종료 시그널 핸들링 (Ctrl+C / exe 종료 대비)
    # ------------------------------------------------------------------
    setup_signal_handler(logger)

    # ------------------------------------------------------------------
    # 4. 메인 실행 루프 (지금은 더미)
    # ------------------------------------------------------------------
    logger.info("Entering main loop")

    try:
        main_loop(logger, config)
    except Exception:
        logger.exception("Unhandled exception occurred")
        raise
    finally:
        logger.info("Titan app shutdown complete")


# ======================================================================
# 내부 함수들
# ======================================================================

def setup_signal_handler(logger):
    """
    종료 시그널 처리
    """

    def _handler(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main_loop(logger, config):
    import time
    from taitan.core.scheduler import Scheduler

    interval = config["scheduler"]["interval_sec"]

    engine = Engine(config=config, logger=logger)

    scheduler = Scheduler(
        interval_sec=interval,
        task=engine.run_once,
        logger=logger,
    )

    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    finally:
        scheduler.stop()


