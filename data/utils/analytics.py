from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict

from ..models.transaction import Transaction
from ..models.user import User


async def get_top_categories(user: User, days: int = 30, limit: int = 5) -> List[Tuple[str, float]]:
    start = datetime.now() - timedelta(days=days)
    transactions = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=start
    ).all()

    totals: Dict[str, float] = defaultdict(float)
    for tx in transactions:
        name = tx.category_name or 'Без категории'
        totals[name] += tx.amount

    sorted_totals = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return sorted_totals[:limit]


async def get_average_daily_expense(user: User, days: int = 7) -> Optional[float]:
    start = datetime.now() - timedelta(days=days)
    transactions = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=start
    ).all()

    if not transactions:
        return None

    total = sum(tx.amount for tx in transactions)
    return round(total / days, 2)


async def get_income_expense_dynamics(user: User, days: int = 7) -> Dict[str, float]:
    now = datetime.now()
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    current_incomes = await Transaction.filter(
        user=user,
        type='income',
        date__gte=current_start,
        date__lte=now
    ).all()
    current_expenses = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=current_start,
        date__lte=now
    ).all()

    previous_incomes = await Transaction.filter(
        user=user,
        type='income',
        date__gte=previous_start,
        date__lt=current_start
    ).all()
    previous_expenses = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=previous_start,
        date__lt=current_start
    ).all()

    current_income_total = round(sum(tx.amount for tx in current_incomes), 2)
    current_expense_total = round(sum(tx.amount for tx in current_expenses), 2)
    previous_income_total = round(sum(tx.amount for tx in previous_incomes), 2)
    previous_expense_total = round(sum(tx.amount for tx in previous_expenses), 2)

    return {
        "current_income": current_income_total,
        "current_expense": current_expense_total,
        "income_change": round(current_income_total - previous_income_total, 2),
        "expense_change": round(current_expense_total - previous_expense_total, 2),
    }
