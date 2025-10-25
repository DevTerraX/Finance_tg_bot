from aiogram.dispatcher.filters.state import State, StatesGroup

class SummaryStates(StatesGroup):
    period_mode = State()
    period_input = State()
    checks_period_mode = State()
    checks_period_input = State()
