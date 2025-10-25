from aiogram import Dispatcher, types

from ..utils.db_utils import get_or_create_user, get_balance
from ..utils.cleanup import schedule_cleanup
from ..keyboards.main_menu import (
    get_main_menu,
    BALANCE_BUTTON
)


async def balance_handler(message: types.Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    balance = await get_balance(user)
    await message.answer(
        f"💼 Твой текущий капитал: {balance:.2f} {user.currency} 💎",
        reply_markup=get_main_menu()
    )


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(balance_handler, lambda m: m.text == BALANCE_BUTTON, state="*")
