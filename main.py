import asyncio
import logging
from bot import dp, bot
from database import init_db, setup_reminders
from middlewares import ErrorMiddleware
from handlers.common import register_common_handlers
from handlers.expense import register_expense_handlers
from handlers.income import register_income_handlers
from handlers.settings import register_settings_handlers
from handlers.quick import register_quick_handlers

logging.basicConfig(level=logging.INFO, filename='bot.log', format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    await init_db()
    dp.middleware.setup(ErrorMiddleware())
    register_common_handlers(dp)
    register_expense_handlers(dp)
    register_income_handlers(dp)
    register_settings_handlers(dp)
    register_quick_handlers(dp)
    setup_reminders()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())