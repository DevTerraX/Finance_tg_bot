# utils/validation.py
def validate_amount(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError("Сумма должна быть числом!")