# Python API Reference

## Overview
This reference describes the main service and repository APIs available for internal use in handlers and other services.

## UserService

Available methods:

```python
user = await user_service.register_user(telegram_id)
user = await user_service.get_user(telegram_id)
user = await user_service.update_user(telegram_id, {"language_code": "en"})
user = await user_service.get_or_create_user(telegram_id, language_code="en")
user = await user_service.update_bio(telegram_id, "Hello")
```

## CacheService

```python
lang = await cache_service.get_user_language(user_id)
await cache_service.set_user_language(user_id, "en", ttl=3600)
await cache_service.invalidate_user_language(user_id)
```

## UserRepository

```python
user = await uow.users.get_by_filters(user_id=user_id)
users = await uow.users.list_by_filters(language_code="en")
updated = await uow.users.update(user_id, {"bio": "Hi"})
```

## UnitOfWork

```python
async with uow:
    user = await uow.users.get(user_id)
```

## Common Issues

### AttributeError on repository
**Symptoms:** `uow.users` is missing.
**Cause:** UoW not entered via `async with`.
**Solution:** Always use `async with uow:`.

### None returned on update
**Symptoms:** `update_user` returns `None`.
**Cause:** User not found.
**Solution:** Ensure the user exists or call `get_or_create_user` first.

## Best Practices

1. DO use services for business logic.
2. DO keep repository usage inside a UoW.
3. DO handle `None` returns from repositories.

## Next Steps
- Read [Services Guide](../guides/services.md)
- Explore [Database Guide](../guides/database.md)
