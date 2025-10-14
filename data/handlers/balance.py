# handlers/balance.py
from aiogram import types
from ..utils.db_utils import get_or_create_user, get_balance
from keyboards.main_menu import get_main_menu

async def show_balance(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user.id)
    balance = await get_balance(user)
    await query.message.edit_text(f"Ваш текущий баланс: {balance}", reply_markup=get_main_menu())  # Или отдельная клавиатура с назад

# В menu.py уже зарегистрировано через callback