# utils/db_utils.py
# ...existing code...
from datetime import datetime, timedelta
from tortoise.exceptions import DoesNotExist
from ..models.user import User
from ..models.category import Category
from ..models.transaction import Transaction
from config import DEFAULT_CATEGORIES_EXPENSE, DEFAULT_CATEGORIES_INCOME

async def get_or_create_user(telegram_id: int) -> User:
    try:
        user = await User.get(id=telegram_id)
    except DoesNotExist:
        user = await User.create(id=telegram_id)
        # Добавляем дефолтные категории
        for name in DEFAULT_CATEGORIES_EXPENSE:
            await Category.create(name=name, type='expense', user=user)
        for name in DEFAULT_CATEGORIES_INCOME:
            await Category.create(name=name, type='income', user=user)
    return user

async def get_categories(user: User, type: str, include_deleted=False) -> list:
    query = Category.filter(user=user, type=type)
    if not include_deleted:
        query = query.filter(deleted=False)
    return await query.all()

async def create_category(user: User, name: str, type: str) -> Category:
    return await Category.create(name=name, type=type, user=user)

async def delete_category(category_id: int):
    category = await Category.get(id=category_id)
    category.deleted = True
    await category.save()
    # Пометить транзакции
    transactions = await Transaction.filter(category=category)
    for tx in transactions:
        tx.category_name = f"(удаленная категория: {category.name})"
        tx.category = None
        await tx.save()

async def create_transaction(user: User, amount: float, category_id: int, type: str, check: str = None):
    category = await Category.get(id=category_id)
    tx = await Transaction.create(
        amount=amount,
        category=category,
        category_name=category.name,
        type=type,
        check=check,
        user=user
    )
    # Обновить баланс
    if type == 'income':
        user.balance += amount
    else:
        user.balance -= amount
    await user.save()
    return tx

async def get_balance(user: User) -> float:
    return user.balance  # Или пересчитать: sum(incomes) - sum(expenses), но для скорости храним

async def get_summary(user: User, period: str = 'all') -> dict:
    now = datetime.now()
    if period == 'day':
        start = now - timedelta(days=1)
    elif period == 'week':
        start = now - timedelta(weeks=1)
    elif period == 'month':
        start = now - timedelta(days=30)
    else:
        start = datetime.min
    
    incomes = await Transaction.filter(user=user, type='income', date__gte=start).all()
    expenses = await Transaction.filter(user=user, type='expense', date__gte=start).all()
    
    total_income = sum(tx.amount for tx in incomes)
    total_expense = sum(tx.amount for tx in expenses)
    balance = total_income - total_expense
    
    return {
        'balance': balance,
        'income': total_income,
        'expense': total_expense,
        'incomes': incomes,
        'expenses': expenses
    }

# Другие функции: для периодов, фильтров по ТЗ