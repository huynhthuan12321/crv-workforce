# Database Guide

## Overview
The project uses SQLAlchemy 2.x with async sessions, a repository layer, and a Unit of Work (UoW) to manage transactions. Migrations are handled by Alembic.

## Quick Links
- [Services](services.md)
- [Configuration](configuration.md)
- [Project Structure](../reference/project-structure.md)

## Models
Models live in `source/database/models/` and inherit from a shared base.

```python
# source/database/models/user.py
class UserOrm(Base, TableNameMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    language_code: Mapped[str | None] = mapped_column(String(2), default="en")
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
```

## Repositories
Repositories provide typed data access. Example:

```python
# source/database/repositories/user.py
class UserRepository(AbstractRepository[UserOrm, int]):
    model = UserOrm

    async def get_by_filters(self, **filters: Any) -> UserOrm | None:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

## Unit of Work
The UoW owns the session and transaction lifecycle:

```python
# source/database/tools/uow.py
class UnitOfWork(AbstractUnitOfWork):
    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._transaction = await self._session.begin()
        self.users = UserRepository(self._session)
        return self
```

Use it inside services:

```python
async def update_user(self, user_id: int, data: dict[str, Any]) -> UserOrm | None:
    async with self._uow:
        return await self._uow.users.update(user_id, data)
```

## Database Creation
In development, tables are created automatically on startup. In production, use migrations.

## Migrations

Create a new migration:

```bash
make migration MESSAGE="add bio field"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Rollback:

```bash
uv run alembic downgrade -1
```

## Seeding
A simple seeding script exists in `scripts/db_seed.py`:

```bash
make seed
```

## Common Issues

### Migration autogenerate fails
**Symptoms:** Alembic creates empty migrations.
**Cause:** Models not imported into Alembic env.
**Solution:** Check `migrations/env.py` imports.

### Connection refused
**Symptoms:** Bot fails to connect to Postgres.
**Cause:** DB not running or wrong credentials.
**Solution:** Verify `DB__*` values and container health.

### Duplicate user_id errors
**Symptoms:** IntegrityError on user creation.
**Cause:** `user_id` is unique.
**Solution:** Use `get_or_create_user` to avoid duplicates.

## Best Practices

1. DO use repositories for DB access.
2. DO wrap writes in a Unit of Work.
3. DO use Alembic for schema changes.
4. DO avoid raw SQL unless necessary.
5. DO keep migrations small and focused.

## Next Steps
- Build logic in [Services](services.md)
- Wire routes in [Handlers](handlers.md)
- Deploy with [Deployment](deployment.md)
