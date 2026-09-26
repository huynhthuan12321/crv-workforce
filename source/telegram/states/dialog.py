from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class DialogSG(StatesGroup):
    first = State()
    second = State()
