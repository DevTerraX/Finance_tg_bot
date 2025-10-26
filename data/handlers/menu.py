from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import get_or_create_user
from ..keyboards.main_menu import (
    get_main_menu,
    BACK_BUTTON
)


async def back_to_main_menu(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await state.finish()
    await message.answer("🔁 Возвращаю тебя в главное меню. Готов продолжать путешествие по финансам?", reply_markup=get_main_menu())


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(back_to_main_menu, lambda m: m.text == BACK_BUTTON, state=None)
    dp.register_message_handler(back_to_main_menu, commands=['menu'], state='*')
