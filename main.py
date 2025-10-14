import logging
from aiogram import Bot, Dispatcher, executor
from tortoise import Tortoise
from aiogram.contrib.fsm_storage.memory import MemoryStorage  # Или RedisStorage для production
from config import BOT_TOKEN, DB_URL
from data.utils.db_utils import get_or_create_user
from data.handlers import start, menu, expense, income, balance, summary, settings

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def on_startup(dp):
    await Tortoise.init(
        db_url=DB_URL,
        modules={'models': ['data.models.user', 'data.models.transaction', 'data.models.category']}
    )
    await Tortoise.generate_schemas()  
    logging.info("База данных инициализирована")

    start.register_handlers(dp)
    menu.register_handlers(dp)
    expense.register_handlers(dp)
    income.register_handlers(dp)
    summary.register_handlers(dp)
    settings.register_handlers(dp)

async def on_shutdown(dp):
    await Tortoise.close_connections()
    logging.info("Соединение с БД закрыто")

storage = MemoryStorage()  # Память для разработки
dp = Dispatcher(bot, storage=storage)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)