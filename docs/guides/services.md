# Services Guide

## Overview
Services encapsulate business logic and coordinate database access through the Unit of Work (UoW). They are injected into handlers via Dishka.

## Quick Links
- [Handlers](handlers.md)
- [Database](database.md)
- [Python API Reference](../reference/api.md)

## Base Service
All services inherit from `BaseService`:

```python
# source/services/base.py
class BaseService(ABC, Generic[ModelType]):
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow: AbstractUnitOfWork = uow
```

## UserService Example

```python
# source/services/user_service.py
class UserService(BaseService[UserOrm]):
    async def get_or_create_user(self, telegram_id: int) -> UserOrm:
        async with self._uow:
            user = await self._uow.users.get(telegram_id)
            if user:
                return user
            return await self._uow.users.add({"user_id": telegram_id})
```

## Unit of Work Pattern
Use `async with` to scope a transaction:

```python
async def update_user(self, user_id: int, data: dict[str, Any]) -> UserOrm | None:
    async with self._uow:
        return await self._uow.users.update(user_id, data)
```

## Dependency Injection
Register services in the Dishka container:

```python
# source/factory/container.py
from dishka import provide, Scope
from source.database import AbstractUnitOfWork
from source.services import UserService

@provide(scope=Scope.REQUEST)
def provide_user_service(self, uow: AbstractUnitOfWork) -> UserService:
    return UserService(uow=uow)
```

## CacheService Example
Use `CacheService` for small, user-scoped values:

```python
# source/services/cache_service.py
lang = await cache_service.get_user_language(user_id)
await cache_service.set_user_language(user_id, "en", ttl=3600)
await cache_service.invalidate_user_language(user_id)
```

## Service Error Handling
`UserService` logs errors via `BaseService.log_error`.

```python
try:
    async with self._uow:
        return await self._uow.users.update(user_id, data)
except Exception as exc:
    self.log_error("update_user", exc, user_id=user_id)
    raise
```

## Common Issues

### Transaction not committed
**Symptoms:** Data not saved after service call.
**Cause:** Missing `async with self._uow` context.
**Solution:** Wrap writes in a Unit of Work block.

### Service not available in handler
**Symptoms:** Dependency injection fails.
**Cause:** Provider not registered in the container.
**Solution:** Add a provider in `source/factory/container.py`.

### Deadlocks or slow queries
**Symptoms:** Requests hang or time out.
**Cause:** Long-running operations in services.
**Solution:** Keep services focused on DB I/O and offload heavy jobs.

## Best Practices

1. DO keep services thin and composable.
2. DO keep database access inside the UoW.
3. DO log important state changes.
4. DO reuse services across bot and API layers.
5. DO avoid direct DB access in handlers.

## Next Steps
- Build handlers with [Handlers](handlers.md)
- Explore data models in [Database](database.md)
- See [Python API Reference](../reference/api.md)
