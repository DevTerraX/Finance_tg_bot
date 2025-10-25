import asyncio
import logging
from contextlib import suppress
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates
from tortoise import Tortoise

from config import BOT_TOKEN, DB_URL
from data.handlers import start, menu, expense, income, balance, summary, settings, history
from data.utils.migrations import ensure_schema
from data.utils.reminders import reminder_loop

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
reminder_task: Optional[asyncio.Task] = None

async def on_startup(dp):
    global reminder_task
    try:
        await bot.delete_webhook(drop_pending_updates=True)
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
    history.register_handlers(dp)

    reminder_task = asyncio.create_task(reminder_loop(bot))
    logging.info("Задача напоминаний запущена.")

async def on_shutdown(dp):
    global reminder_task
    if reminder_task:
        reminder_task.cancel()
        with suppress(asyncio.CancelledError):
            await reminder_task
        reminder_task = None

    await Tortoise.close_connections()
    logging.info("Соединение с БД закрыто")


async def _start_polling():
    startup_completed = False
    try:
        await on_startup(dp)
        startup_completed = True
        await dp.start_polling(
            reset_webhook=False,
        )
    except TerminatedByOtherGetUpdates:
        logging.error(
            "Получен ответ Telegram \"Terminated by other getUpdates\". "
            "Похоже, бот уже запущен где-то ещё. Остановите другие экземпляры и попробуйте снова."
        )
    except Exception:
        logging.exception("Неожиданная ошибка во время polling.")
        raise
    finally:
        if startup_completed:
            await on_shutdown(dp)


if __name__ == '__main__':
    try:
        asyncio.run(_start_polling())
    except KeyboardInterrupt:
        logging.info("Выключаю бота по запросу пользователя.")
