import logging
import asyncio
from aiogram import Bot
from keyboards import get_main_menu

async def delete_message_safe(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logging.error(f"Ошибка удаления сообщения {message_id} в чате {chat_id}: {e}")

async def send_reminder(bot: Bot, chat_id: int):
    try:
        sent = await bot.send_message(chat_id, "Не забудь внести расходы!", reply_markup=get_main_menu())
        await asyncio.sleep(3)
        await bot.delete_message(chat_id, sent.message_id)
        logging.info(f"Sent reminder to chat_id: {chat_id}")
    except Exception as e:
        logging.error(f"Failed to send reminder to chat_id {chat_id}: {e}")