from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import get_or_create_user
from ..utils.cleanup import clean_chat
from ..keyboards.main_menu import (
    get_main_menu,
    BACK_BUTTON
)


async def back_to_main_menu(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await state.finish()
    reply = await message.answer("🔁 Возвращаю тебя в главное меню. Готов продолжать путешествие по финансам?", reply_markup=get_main_menu())
    if user.clean_chat:
        await clean_chat(message.bot, message.chat.id, reply.message_id)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(back_to_main_menu, lambda m: m.text == BACK_BUTTON, state=None)
