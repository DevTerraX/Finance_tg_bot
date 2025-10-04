import asyncio
from aiogram import Dispatcher
from database import init_db
from handlers import register_handlers
from bot import bot

dp = Dispatcher()

async def main():
    init_db()
    register_handlers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())