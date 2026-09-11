from aiogram.fsm.state import State, StatesGroup


class CheckoutStates(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()
    waiting_zone = State()
    waiting_address = State()
    waiting_confirm = State()
