from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from ..models.transaction import Transaction
from ..models.user import User
from .storage import get_user_file_path, ensure_user_dirs


async def export_transactions_to_csv(user: User, period: timedelta) -> Optional[str]:
    """
    Экспортирует операции пользователя за указанный период в CSV.
    Возвращает путь к файлу или None, если операций нет.
    """
    ensure_user_dirs(user.id)
    since = datetime.now() - period
    transactions = await Transaction.filter(user=user, date__gte=since).order_by('-date').all()

    if not transactions:
        return None

    date_format = _to_strftime(user.date_format)

    data = [{
        'Дата': tx.date.strftime(date_format),
        'Сумма': f"{tx.amount:.2f}",
        'Категория': tx.category_name or 'Без категории',
        'Тип операции': 'Доход' if tx.type == 'income' else 'Расход',
        'Комментарий': tx.check or '',
        'Фото чека': tx.check_photo_path or ''
    } for tx in transactions]

    df = pd.DataFrame(data)
    filename = f"operations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = get_user_file_path(user.id, "csv", filename)
    df.to_csv(path, index=False, encoding='utf-8')
    return str(path)


def _to_strftime(pattern: str) -> str:
    """
    Преобразует пользовательский шаблон даты (DD.MM.YYYY) в формат strftime.
    """
    mapping = {
        'DD': '%d',
        'MM': '%m',
        'YYYY': '%Y'
    }
    result = pattern
    for key, value in mapping.items():
        result = result.replace(key, value)
    return result
