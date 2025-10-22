from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from ..models.user import User
from ..models.category import Category
from ..models.transaction import Transaction
from config import DEFAULT_CATEGORIES_EXPENSE, DEFAULT_CATEGORIES_INCOME
from .storage import ensure_user_dirs


async def get_or_create_user(telegram_id: int, full_name: Optional[str] = None) -> User:
    """
    Возвращает пользователя, создавая запись и дефолтные категории при первом запуске.
    """
    defaults = {
        "name": full_name or "",
        "currency": "₽",
        "timezone": "Europe/Moscow",
        "date_format": "DD.MM.YYYY",
    }
    user, created = await User.get_or_create(id=telegram_id, defaults=defaults)

    if created:
        await _ensure_default_categories(user)

    ensure_user_dirs(user.id)

    return user


async def _ensure_default_categories(user: User) -> None:
    expense_categories = [
        Category(name=name, type='expense', user=user) for name in DEFAULT_CATEGORIES_EXPENSE
    ]
    income_categories = [
        Category(name=name, type='income', user=user) for name in DEFAULT_CATEGORIES_INCOME
    ]
    await Category.bulk_create(expense_categories + income_categories)


async def get_categories(user: User, type: str, include_deleted: bool = False) -> Iterable[Category]:
    query = Category.filter(user=user, type=type)
    if not include_deleted:
        query = query.filter(deleted=False)
    return await query.all()


async def create_category(user: User, name: str, type: str) -> Category:
    return await Category.create(name=name, type=type, user=user)


async def delete_category(category_id: int) -> None:
    category = await Category.get(id=category_id)
    category.deleted = True
    await category.save()

    transactions = await Transaction.filter(category=category).all()
    for tx in transactions:
        tx.category_name = f"(удаленная категория: {category.name})"
        tx.category = None
        await tx.save()


async def create_transaction(
    user: User,
    amount: float,
    category_id: int,
    type: str,
    check: Optional[str] = None,
    check_photo_path: Optional[str] = None
) -> Transaction:
    category = await Category.get(id=category_id)
    tx = await Transaction.create(
        amount=amount,
        category=category,
        category_name=category.name,
        type=type,
        check=check,
        check_photo_path=check_photo_path,
        user=user
    )

    if type == 'income':
        user.balance += amount
    else:
        user.balance -= amount
    await user.save()

    return tx


async def get_balance(user: User) -> float:
    return round(user.balance, 2)


async def get_summary(
    user: User,
    start: datetime = datetime.min,
    end: datetime = datetime.now()
) -> dict:
    incomes = await Transaction.filter(
        user=user,
        type='income',
        date__gte=start,
        date__lte=end
    ).all()
    expenses = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=start,
        date__lte=end
    ).all()

    total_income = round(sum(tx.amount for tx in incomes), 2)
    total_expense = round(sum(tx.amount for tx in expenses), 2)
    balance = round(total_income - total_expense, 2)

    return {
        'balance': balance,
        'income': total_income,
        'expense': total_expense,
        'incomes': incomes,
        'expenses': expenses
    }
