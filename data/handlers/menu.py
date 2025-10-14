from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from ..keyboards.main_menu import get_main_menu, get_back_keyboard
from ..states.expense_states import ExpenseStates
from ..states.income_states import IncomeStates
from ..states.settings_states import SettingsStates

async def menu_handler(message: types.Message, state: FSMContext):
    text = message.text
    if text == "Баланс":
        from .balance import show_balance
        await show_balance(message)  # Изменить на message вместо query
    elif text == "Добавить расход":
        await ExpenseStates.sum.set()
        await message.answer("Введите сумму расхода:", reply_markup=get_back_keyboard())
    elif text == "Добавить доход":
        await IncomeStates.sum.set()
        await message.answer("Введите сумму дохода:", reply_markup=get_back_keyboard())
    elif text == "Итоги":
        from .summary import show_summary_menu
        await show_summary_menu(message)  # Адаптировать под message
    elif text == "Настройки":
        await SettingsStates.categories_menu.set()
        await message.answer("Настройки: Выберите раздел.", reply_markup=get_back_keyboard())
    elif text == "Назад":
        await state.finish()
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(menu_handler, lambda m: m.text in ["Баланс", "Добавить расход", "Добавить доход", "Итоги", "Настройки", "Назад"])