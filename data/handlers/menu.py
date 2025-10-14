# handlers/menu.py
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram import Dispatcher, types
from ..keyboards.main_menu import get_main_menu
from ..states.expense_states import ExpenseStates
from ..states.income_states import IncomeStates
from ..states.settings_states import SettingsStates
# Импорт других handlers для переходов (будем добавлять)

async def menu_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data == 'balance':
        from .balance import show_balance  # Импорт внутри, чтобы избежать циклов
        await show_balance(query)
    elif data == 'add_expense':
        await ExpenseStates.sum.set()
        await query.message.edit_text("Введите сумму расхода:")
    elif data == 'add_income':
        await IncomeStates.sum.set()
        await query.message.edit_text("Введите сумму дохода:")
    elif data == 'summary':
        from .summary import show_summary_menu
        await show_summary_menu(query)
    elif data == 'settings':
        await SettingsStates.categories_menu.set()
        await query.message.edit_text("Настройки: Выберите раздел.")
        # Добавить клавиатуру для настроек

    # Общая кнопка назад в меню
    if data == 'back_to_menu':
        await query.message.edit_text("Главное меню", reply_markup=get_main_menu())
        await state.finish()

def register_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(menu_callback, lambda q: q.data in ['balance', 'add_expense', 'add_income', 'summary', 'settings', 'back_to_menu'])