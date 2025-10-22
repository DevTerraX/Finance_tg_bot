from pathlib import Path
from typing import Dict

BASE_DIR = Path("users_data")


def ensure_user_dirs(user_id: int) -> Dict[str, Path]:
    """
    Создает структуру папок для пользователя и возвращает словарь путей.
    users_data/<user_id>/{checks,csv,charts}
    """
    user_dir = BASE_DIR / str(user_id)
    subdirs = {
        "root": user_dir,
        "checks": user_dir / "checks",
        "csv": user_dir / "csv",
        "charts": user_dir / "charts",
    }

    for path in subdirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return subdirs


def get_user_file_path(user_id: int, subfolder: str, filename: str) -> Path:
    """
    Возвращает путь к файлу конкретного пользователя в указанной подпапке.
    """
    dirs = ensure_user_dirs(user_id)
    return dirs[subfolder] / filename
