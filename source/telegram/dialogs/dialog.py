
from aiogram_dialog import Dialog
from aiogram_dialog import DialogManager
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.kbd import Next
from aiogram_dialog.widgets.text import Format
from dishka import AsyncContainer
from typing import Any

from source.telegram.states import DialogSG
from source.utils import I18n


async def _get_container(dialog_manager: DialogManager) -> AsyncContainer:
    md = dialog_manager.middleware_data
    for key in ("container", "di", "dishka_container"):
        if key in md:
            return md[key]
    raise RuntimeError(
        "DI container not found in DialogManager.middleware_data. "
        "Ensure Dishka middleware provides one of: 'container' | 'di' | 'dishka_container'.",
    )


async def get_texts(*args: Any, **kwargs: Any) -> dict[str, str]:
    dialog_manager: DialogManager | None = kwargs.get("dialog_manager")

    if dialog_manager is None and args:
        if isinstance(args[0], DialogManager):
            dialog_manager = args[0]
    if dialog_manager is None:
        raise RuntimeError("DialogManager not provided to getter")

    container = await _get_container(dialog_manager)
    i18n: I18n = await container.get(I18n)

    user_id = dialog_manager.event.from_user.id
    return {
        "welcome": await i18n(user_id, "dialog-welcome"),
        "next": await i18n(user_id, "dialog-next"),
        "second": await i18n(user_id, "dialog-second"),
        "close": await i18n(user_id, "dialog-close"),
    }


dialog = Dialog(
    Window(
        Format("{welcome}"),
        Next(text=Format("{next}")),
        state=DialogSG.first,
        getter=get_texts,
    ),
    Window(
        Format("{second}"),
        Cancel(text=Format("{close}")),
        state=DialogSG.second,
        getter=get_texts,
    ),
)
