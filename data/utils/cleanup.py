import asyncio

from aiogram import Bot


async def clean_chat(bot: Bot, chat_id: int, last_message_id: int, *, limit: int = 200, delay: float = 4.0) -> None:
    await asyncio.sleep(delay)
    for message_id in range(last_message_id, max(last_message_id - limit, 0), -1):
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            continue
