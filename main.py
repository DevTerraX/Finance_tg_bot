import logging
import asyncio
from contextlib import suppress
from typing import Optional

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from tortoise import Tortoise

from config import BOT_TOKEN, DB_URL
from data.handlers import start, menu, expense, income, balance, summary, settings
from data.utils.reminders import reminder_loop
from data.utils.migrations import ensure_schema

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
reminder_task: Optional[asyncio.Task] = None

async def on_startup(dp):
    global reminder_task
    try:
        await Tortoise.init(db_url=DB_URL, modules={'models': ['data.models.user', 'data.models.transaction', 'data.models.category']})
        logging.info("База данных инициализирована с data/models/")
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    await Tortoise.generate_schemas()
    await ensure_schema()

    start.register_handlers(dp)
    menu.register_handlers(dp)
    expense.register_handlers(dp)
    income.register_handlers(dp)
    balance.register_handlers(dp)
    summary.register_handlers(dp)
    settings.register_handlers(dp)

    reminder_task = asyncio.create_task(reminder_loop(bot))
    logging.info("Задача напоминаний запущена.")

async def on_shutdown(dp):
    global reminder_task
    if reminder_task:
        reminder_task.cancel()
        with suppress(asyncio.CancelledError):
            await reminder_task

    await Tortoise.close_connections()
    logging.info("Соединение с БД закрыто")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
