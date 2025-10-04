from aiogram.fsm.state import StatesGroup, State

class AddExpense(StatesGroup):
    amount = State()
    category = State()
    wallet = State()
    confirm = State()
    add_new_cat_exp = State()

class AddIncome(StatesGroup):
    amount = State()
    source = State()
    wallet = State()
    confirm = State()
    add_new_cat_inc = State()

class Settings(StatesGroup):
    wallet_add = State()
    wallet_delete = State()
    wallet_confirm_delete = State()
    category_add = State()
    category_delete = State()
    category_confirm_delete = State()
    reminder_set = State()
    pin_set = State()
    goal_set = State()

class PinCheck(StatesGroup):
    pin = State()