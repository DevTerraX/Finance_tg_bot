from aiogram.dispatcher.filters.state import State, StatesGroup

class SummaryStates(StatesGroup):
    period_mode = State()
    period_input = State()
