from aiogram import types
from ..utils.db_utils import get_or_create_user, get_balance
from ..keyboards.main_menu import get_main_menu

async def show_balance(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    balance = await get_balance(user)
    await message.answer(f"Ваш текущий баланс: {balance}", reply_markup=get_main_menu())