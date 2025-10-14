# utils/cleanup.py
from aiogram import Bot

async def clean_chat(bot: Bot, chat_id: int, message_id: int, count: int = 5):
    # Удаляем последние count сообщений (примерно)
    for i in range(message_id - count, message_id + 1):
        try:
            await bot.delete_message(chat_id, i)
        except:
            pass  # Если сообщение не найдено, игнор