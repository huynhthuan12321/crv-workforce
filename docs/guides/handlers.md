# Handlers Guide

## Overview
Handlers are the entry point for Telegram updates. This project separates routers by domain (user, admin, webapp, errors) and wires them in `source/telegram/handlers/__init__.py`.

## Quick Links
- [Project Structure](../reference/project-structure.md)
- [Services](services.md)
- [Database](database.md)

## Router Layout

```
source/telegram/handlers/
├── admin/
├── user/
├── webapp/
└── errors/
```

Routers are registered in one place:

```python
# source/telegram/handlers/__init__.py
from aiogram import Dispatcher

from .admin import setup_admin_routers
from .errors import setup_errors_routers
from .user import setup_user_routers
from .webapp import setup_webapp_routers


def setup_routers(dp: Dispatcher) -> Dispatcher:
    dp.include_routers(
        setup_admin_routers(),
        setup_user_routers(),
        setup_webapp_routers(),
        setup_errors_routers(),
    )
    return dp
```

## Command Handlers

Commands live in `source/telegram/handlers/user/commands.py`:

```python
from aiogram.filters import Command
from aiogram.types import Message

@user_commands_router.message(Command("hello"))
async def hello_command(message: Message) -> None:
    await message.answer("Hello from aiogram")
```

## Callback Handlers

Callbacks filter by `data` and support DI:

```python
from aiogram import F
from aiogram.types import CallbackQuery
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService
from source.utils import I18n

@user_callbacks_router.callback_query(F.data == "language_ru")
@aiogram_inject
async def language_ru(
    callback: CallbackQuery,
    i18n: FromDishka[I18n],
    user_service: FromDishka[UserService],
) -> None:
    await callback.answer("")
    await user_service.update_user(callback.from_user.id, {"language_code": "ru"})
    i18n.invalidate_cache(callback.from_user.id)
```

## Message Handlers

Handle arbitrary text or media messages:

```python
from aiogram.types import Message

@user_messages_router.message()
async def any_message(message: Message) -> None:
    await message.answer("I received your message")
```

## FSM Handlers

Finite State Machines are defined in `source/telegram/states/`.

```python
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

@user_fsm_router.message(FormSG.name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(FormSG.age)
    await message.answer("Enter your age")
```

## Dialogs (aiogram-dialog)

Dialog flows are defined in `source/telegram/dialogs/`.

```python
from aiogram_dialog import DialogManager
from aiogram_dialog import StartMode

@user_commands_router.message(Command("dialog"))
async def dialog_command(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(DialogSG.first, mode=StartMode.RESET_STACK)
```

## WebApp Handlers

The WebApp can send data back to the bot via `web_app_data`:

```python
from aiogram import F
from aiogram.types import Message

@webapp_callbacks_router.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    await message.answer(f"Received: {message.web_app_data.data}")
```

## Dependency Injection

Dishka provides services and utilities in handlers:

```python
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService

@user_commands_router.message(Command("start"))
@aiogram_inject
async def start(message: Message, user_service: FromDishka[UserService]) -> None:
    await user_service.register_user(message.from_user.id)
    await message.answer("Welcome")
```

## Filters

Custom filters live in `source/telegram/filters/` and can be used directly:

```python
from source.telegram.filters import AdminFilter

@admin_commands_router.message(AdminFilter())
async def admin_only(message: Message) -> None:
    await message.answer("Admin panel")
```

## Middlewares

Middlewares are configured in `source/telegram/middlewares/` and typically handle:
- throttling
- access control
- error reporting

Example throttling middleware:

```python
from source.telegram.middlewares import ThrottlingMiddleware

# In dispatcher setup
# dp.message.middleware(ThrottlingMiddleware(time_limit=2))
```

## Common Issues

### Handler not firing
**Symptoms:** Bot ignores a command.
**Cause:** Router not included or filter mismatch.
**Solution:** Ensure the router is included in `setup_routers()` and filters are correct.

### Dependency not injected
**Symptoms:** DI returns `None` or errors.
**Cause:** Missing `@aiogram_inject` or provider not registered.
**Solution:** Add `@aiogram_inject` and register the provider in the container.

### FSM state stuck
**Symptoms:** Bot does not move to the next step.
**Cause:** State not updated or cleared.
**Solution:** Call `state.set_state()` and `state.clear()` appropriately.

## Best Practices

1. DO keep handlers thin and delegate logic to services.
2. DO group routers by domain (user/admin/webapp).
3. DO use filters for access control.
4. DO return early on errors to avoid hidden failures.
5. DO centralize router registration.

## Next Steps
- Build business logic in [Services](services.md)
- Store data with [Database](database.md)
- Add Mini App features in [mini-apps/adding-features.md](mini-apps/adding-features.md)
