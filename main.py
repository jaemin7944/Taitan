# main.py
from pathlib import Path

from taitan.infra.paths import (
    is_exe,
    get_base_dir,
    get_config_dir,
    get_log_dir,
)


def prepare_runtime_dirs():
    """
    실행에 필요한 디렉토리 생성
    (exe / py 공용)
    """
    config_dir = get_config_dir()
    log_dir = get_log_dir()

    config_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)

    return config_dir, log_dir


def main():
    base_dir = get_base_dir()
    config_dir, log_dir = prepare_runtime_dirs()

    # 실행 환경 로그 (디버깅용)
    print("=" * 50)
    print("Titan starting...")
    print(f"Mode        : {'EXE' if is_exe() else 'PYTHON'}")
    print(f"Base dir    : {base_dir}")
    print(f"Config dir  : {config_dir}")
    print(f"Log dir     : {log_dir}")
    print("=" * 50)

    # 실제 앱 실행은 app 계층에 위임
    from titan.app.app import run
    run(
        base_dir=base_dir,
        config_dir=config_dir,
        log_dir=log_dir,
        exe_mode=is_exe(),
    )


if __name__ == "__main__":
    main()
