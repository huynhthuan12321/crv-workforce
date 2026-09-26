# Tutorial: Building Your First Bot

## Overview
This tutorial walks you through creating a simple command and integrating a service call.

## Quick Links
- [Getting Started](../getting-started.md)
- [Handlers Guide](../guides/handlers.md)

## Step 1: Run the Bot

```bash
make venv
make install
make run
```

## Step 2: Add a Command

Edit `source/telegram/handlers/user/commands.py`:

```python
from aiogram.filters import Command
from aiogram.types import Message

@user_commands_router.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("pong")
```

## Step 3: Test in Telegram

Open your bot and send `/ping`. You should receive `pong`.

## Step 4: Use a Service

```python
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService

@user_commands_router.message(Command("whoami"))
@aiogram_inject
async def whoami(message: Message, user_service: FromDishka[UserService]) -> None:
    user = await user_service.get_or_create_user(message.from_user.id)
    await message.answer(f"Your internal id is {user.id}")
```

## Common Issues

### Command does not work
**Symptoms:** No response.
**Cause:** Router not included or handler not registered.
**Solution:** Ensure `setup_user_routers()` is included in `setup_routers()`.

### Service injection error
**Symptoms:** Dependency injection fails.
**Cause:** Missing provider in container.
**Solution:** Register the service in `source/factory/container.py`.

## Best Practices

1. DO keep command handlers small.
2. DO move logic into services.
3. DO use DI for database access.

## Next Steps
- Learn about [Services](../guides/services.md)
- Add Mini App features in [tutorials/adding-mini-app.md](adding-mini-app.md)
