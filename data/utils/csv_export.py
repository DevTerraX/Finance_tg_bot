# utils/csv_export.py
import pandas as pd
import os

def export_to_csv(transactions: list, filename: str) -> str:
    data = [{
        'Сумма': tx.amount,
        'Категория': tx.category_name or 'Без категории',
        'Тип': tx.type,
        'Дата': tx.date,
        'Чек': tx.check or ''
    } for tx in transactions]
    
    df = pd.DataFrame(data)
    path = f"data/{filename}.csv"
    os.makedirs('data', exist_ok=True)
    df.to_csv(path, index=False)
    return path