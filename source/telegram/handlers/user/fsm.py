from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.telegram.filters import AgeValidator
from source.telegram.states import FormSG
from source.utils import I18n

user_fsm_router = Router(name=__name__)


@user_fsm_router.message(FormSG.name)
@aiogram_inject
async def process_name(
    message: Message, state: FSMContext, i18n: FromDishka[I18n]
) -> None:
    await state.update_data(name=message.text)
    await state.set_state(FormSG.age)
    await message.answer(await i18n(message.from_user.id, "fsm-enter-age"))


@user_fsm_router.message(FormSG.age, AgeValidator())
@aiogram_inject
async def process_age(
    message: Message, state: FSMContext, i18n: FromDishka[I18n]
) -> None:
    data = await state.get_data()
    await message.answer(
        await i18n(
            message.from_user.id,
            "fsm-result",
            name=data["name"],
            age=message.text,
        ),
    )
    await state.clear()


@user_fsm_router.message(FormSG.age)
@aiogram_inject
async def invalid_age(message: Message, i18n: FromDishka[I18n]) -> None:
    await message.answer(await i18n(message.from_user.id, "invalid-age"))
