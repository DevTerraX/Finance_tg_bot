def validate_amount(text: str) -> float:
    """
    Валидирует сумму: заменяет запятую на точку, проверяет что число >= 0.
    """
    normalized = text.replace(',', '.').strip()
    try:
        amount = float(normalized)
    except ValueError as exc:
        raise ValueError("Сумма должна быть числом!") from exc

    if amount < 0:
        raise ValueError("Сумма должна быть неотрицательной!")

    return round(amount, 2)
