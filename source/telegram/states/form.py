from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class FormSG(StatesGroup):
    name = State()
    age = State()
