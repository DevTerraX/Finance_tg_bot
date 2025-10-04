from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.exceptions import DoesNotExist
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.functions import Sum
from config import DB_PATH
from bot import bot
from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

class Settings(Model):
    id = fields.IntField(pk=True)
    reminder_time = fields.CharField(max_length=5, null=True)
    chat_id = fields.BigIntField(null=True)
    pin = fields.CharField(max_length=4, null=True)

class Transaction(Model):
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=10)  # income or expense
    amount = fields.FloatField()
    category = fields.CharField(max_length=50)
    wallet = fields.CharField(max_length=50)
    note = fields.TextField(null=True)
    date = fields.DatetimeField(auto_now_add=True)

class Category(Model):
    name = fields.CharField(max_length=50, pk=True)
    emoji = fields.CharField(max_length=10, default='🆕')
    kind = fields.CharField(max_length=10)  # expense, income, both

class Wallet(Model):
    name = fields.CharField(max_length=50, pk=True)

class Goal(Model):
    id = fields.IntField(pk=True)
    description = fields.CharField(max_length=100)
    target = fields.FloatField()
    current = fields.FloatField(default=0.0)

async def init_db():
    await Tortoise.init(db_url=DB_PATH, modules={'models': ['database']})
    await Tortoise.generate_schemas()
    logging.info("Database initialized")

async def add_transaction(type_, amount, category, wallet):
    await Transaction.create(type=type_, amount=amount, category=category, wallet=wallet)
    logging.info(f"Added transaction: type={type_}, amount={amount}, category={category}, wallet={wallet}")

async def get_balance():
    incomes = await Transaction.filter(type='income').all().values_list('amount', flat=True)
    expenses = await Transaction.filter(type='expense').all().values_list('amount', flat=True)
    return sum(incomes or [0]) - sum(expenses or [0])

async def get_summary(period):
    now = datetime.now()
    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start = now - timedelta(days=now.weekday())
    elif period == 'month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime.min

    expenses = await Transaction.filter(type='expense', date__gte=start).group_by('category').annotate(total=Sum('amount')).values('category', 'total')
    incomes = await Transaction.filter(type='income', date__gte=start).group_by('category').annotate(total=Sum('amount')).values('category', 'total')
    
    expenses_list = [(item['category'], item['total']) for item in expenses]
    incomes_list = [(item['category'], item['total']) for item in incomes]
    
    return expenses_list, incomes_list

async def get_category_summary(category):
    data = await Transaction.filter(category=category).group_by('type').annotate(total=Sum('amount')).values('type', 'total')
    return [(item['type'], item['total']) for item in data]

async def get_wallet_summary(wallet):
    data = await Transaction.filter(wallet=wallet).group_by('type').annotate(total=Sum('amount')).values('type', 'total')
    return [(item['type'], item['total']) for item in data]

async def add_wallet(name):
    if await Wallet.filter(name=name).exists():
        return False
    if await Wallet.all().count() >= 50:
        return False
    await Wallet.create(name=name)
    logging.info(f"Added wallet: {name}")
    return True

async def delete_wallet(name):
    wallet = await Wallet.get_or_none(name=name)
    if wallet:
        await wallet.delete()
        logging.info(f"Deleted wallet: {name}")

async def add_category(name, emoji, kind):
    if kind not in ['expense', 'income', 'both']:
        raise ValueError("Invalid kind")
    if await Category.filter(name=name).exists():
        return False
    if await Category.all().count() >= 50:
        return False
    await Category.create(name=name, emoji=emoji, kind=kind)
    logging.info(f"Added category: {name}, kind={kind}")
    return True

async def delete_category(name):
    category = await Category.get_or_none(name=name)
    if category:
        await category.delete()
        logging.info(f"Deleted category: {name}")

async def set_reminder_time(time_, chat_id):
    settings = await Settings.get_or_none(id=1)
    if settings:
        settings.reminder_time = time_
        settings.chat_id = chat_id
        await settings.save()
    else:
        await Settings.create(id=1, reminder_time=time_, chat_id=chat_id)
    logging.info(f"Set reminder time: {time_}, chat_id={chat_id}")

async def set_pin(pin):
    settings = await Settings.get_or_none(id=1)
    if settings:
        settings.pin = pin
        await settings.save()
    else:
        await Settings.create(id=1, pin=pin)
    logging.info(f"Set pin: {'****' if pin else 'None'}")

async def get_pin():
    settings = await Settings.get_or_none(id=1)
    return settings.pin if settings else None

async def add_goal(description, target):
    await Goal.create(description=description, target=target)
    logging.info(f"Added goal: {description}, target={target}")

async def get_goals():
    return await Goal.all().values_list('id', 'description', 'target', 'current')

def setup_reminders():
    settings = Settings.get_or_none(id=1).run_sync()
    if settings and settings.reminder_time and settings.chat_id:
        try:
            hour, minute = map(int, settings.reminder_time.split(':'))
            if 0 <= hour < 24 and 0 <= minute < 60:
                from utils import send_reminder  # Перенесено в utils.py
                scheduler.add_job(
                    send_reminder,
                    'cron',
                    hour=hour,
                    minute=minute,
                    args=(bot, settings.chat_id),
                    id=f"reminder_{settings.chat_id}"
                )
                scheduler.start()
                logging.info(f"Scheduled reminder for {settings.reminder_time} to chat_id {settings.chat_id}")
            else:
                logging.error("Invalid reminder time format")
        except ValueError:
            logging.error("Invalid reminder time format")