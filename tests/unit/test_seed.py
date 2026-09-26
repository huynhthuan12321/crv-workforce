from sqlalchemy import func, select

from scripts.db_seed import seed_crv
from source.database.models import ConsentTextOrm, EmployeeOrm, ProductOrm
from source.enums import EmployeeRole


async def test_seed_crv_is_idempotent(session):
    await seed_crv(session)
    await seed_crv(session)

    assert await session.scalar(select(func.count()).select_from(ProductOrm)) == 7
    assert await session.scalar(select(func.count()).select_from(ConsentTextOrm).where(ConsentTextOrm.version == 1)) == 1
    assert await session.scalar(select(func.count()).select_from(EmployeeOrm).where(EmployeeOrm.code == "QL001", EmployeeOrm.role == EmployeeRole.manager)) == 1
    assert await session.scalar(select(func.count()).select_from(EmployeeOrm).where(EmployeeOrm.code == "GD001", EmployeeOrm.role == EmployeeRole.director)) == 1
