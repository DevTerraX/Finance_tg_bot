from aiogram import types
from aiogram import BaseMiddleware
import logging

class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Update, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            logging.error(f"Error: {e}")
            if isinstance(event, types.Message):
                await event.answer("Произошла ошибка. Попробуйте позже.")
            return None