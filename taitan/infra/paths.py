# titan/infra/paths.py
from pathlib import Path
import sys


def is_exe() -> bool:
    """
    PyInstaller로 빌드된 exe인지 여부
    """
    return getattr(sys, "frozen", False)


def get_base_dir() -> Path:
    """
    - python main.py 실행 시: 프로젝트 루트
    - Titan.exe 실행 시: exe가 위치한 디렉토리
    """
    if is_exe():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def get_config_dir() -> Path:
    return get_base_dir() / "config"


def get_log_dir() -> Path:
    return get_base_dir() / "logs"
