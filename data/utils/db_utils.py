from __future__ import annotations

from datetime import datetime
from pathlib import Path
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
        "cleanup_mode": "standard",
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


async def get_user_category(user: User, category_id: int, include_deleted: bool = False) -> Optional[Category]:
    query = Category.filter(id=category_id, user=user)
    if not include_deleted:
        query = query.filter(deleted=False)
    return await query.first()


async def create_category(user: User, name: str, type: str) -> Category:
    return await Category.create(name=name, type=type, user=user)


async def delete_category(user: User, category_id: int) -> None:
    category = await get_user_category(user, category_id, include_deleted=False)
    if not category:
        raise ValueError("Категория не найдена или недоступна.")
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
    category = await get_user_category(user, category_id, include_deleted=False)
    if not category:
        raise ValueError("Категория недоступна.")
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


async def get_recent_transactions(user: User, limit: int = 10) -> Iterable[Transaction]:
    return await Transaction.filter(user=user).order_by("-date").limit(limit)


async def get_transaction_by_id(user: User, tx_id: int) -> Optional[Transaction]:
    return await Transaction.filter(id=tx_id, user=user).first()


async def update_transaction(
    transaction: Transaction,
    *,
    amount: Optional[float] = None,
    category_id: Optional[int] = None,
) -> Transaction:
    await transaction.fetch_related("user")
    user = transaction.user
    updated = False

    if amount is not None and amount != transaction.amount:
        delta = amount - transaction.amount
        if transaction.type == "income":
            user.balance += delta
        else:
            user.balance -= delta
        transaction.amount = amount
        updated = True

    if category_id is not None:
        current_category_id = transaction.category.id if transaction.category else None
        if current_category_id != category_id:
            category = await get_user_category(user, category_id, include_deleted=False)
            if not category:
                raise ValueError("Категория недоступна.")
            transaction.category = category
            transaction.category_name = category.name
            updated = True

    if updated:
        await user.save()
        await transaction.save()

    return transaction


async def delete_transaction(transaction: Transaction) -> None:
    await transaction.fetch_related("user")
    user = transaction.user

    if transaction.type == "income":
        user.balance -= transaction.amount
    else:
        user.balance += transaction.amount
    await user.save()

    if transaction.check_photo_path:
        path = Path(transaction.check_photo_path)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    await transaction.delete()


async def get_balance(user: User) -> float:
    return round(user.balance, 2)


async def get_summary(
    user: User,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> dict:
    start_dt = start or datetime.min
    end_dt = end or datetime.now()
    incomes = await Transaction.filter(
        user=user,
        type='income',
        date__gte=start_dt,
        date__lte=end_dt
    ).all()
    expenses = await Transaction.filter(
        user=user,
        type='expense',
        date__gte=start_dt,
        date__lte=end_dt
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
