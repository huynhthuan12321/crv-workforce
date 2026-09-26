"""Seed CRV Workforce reference data and invite links."""

import argparse
import asyncio
import secrets
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from source.config import settings
from source.database.models import (
    ConsentTextOrm,
    EmployeeOrm,
    InviteCodeOrm,
    OutputItemOrm,
    OutputLogOrm,
    PayBatchOrm,
    ProductOrm,
    RateHistoryOrm,
    WorkSessionOrm,
)
from source.enums import EmployeeRole
from source.utils.clock import Clock

PRODUCTS = [
    ("BOT", "Bột", Decimal("1.2"), 1),
    ("XUC_XICH", "Xúc xích", Decimal("1"), 2),
    ("PHO_MAI", "Phô mai", Decimal("1"), 3),
    ("CHA_BONG", "Chà bông", Decimal("1"), 4),
    ("SOT_CAM", "Sốt cam", Decimal("2"), 5),
    ("SOT_TRANG", "Sốt trắng", Decimal("2"), 6),
    ("BO", "Bơ", Decimal("2"), 7),
]

DEMO_EMPLOYEES = [
    ("NV001", "Nguyễn Văn A", 30_000),
    ("NV002", "Lê Thị B", 28_000),
    ("NV003", "Trần Văn C", 30_000),
    ("NV004", "Phạm Thị D", 28_000),
]


def invite_url(code: str) -> str:
    return f"https://t.me/{settings.tg.bot_username}/{settings.tg.miniapp_short_name}?startapp={code}"


async def upsert_products(session: AsyncSession) -> None:
    for code, name, kg, sort_order in PRODUCTS:
        row = await session.scalar(select(ProductOrm).where(ProductOrm.code == code))
        if row:
            row.name = name
            row.kg_per_bag = kg
            row.sort_order = sort_order
        else:
            session.add(ProductOrm(code=code, name=name, kg_per_bag=kg, sort_order=sort_order))


async def upsert_consent_v1(session: AsyncSession, now) -> None:
    content = Path("docs/consent_v1.md").read_text(encoding="utf-8")
    row = await session.get(ConsentTextOrm, 1)
    if row:
        row.content = content
    else:
        session.add(ConsentTextOrm(version=1, content=content, effective_at=now))


async def expire_unused_invites(session: AsyncSession, employee_id: int, now) -> None:
    rows = (await session.scalars(select(InviteCodeOrm).where(
        InviteCodeOrm.employee_id == employee_id,
        InviteCodeOrm.used_at.is_(None),
        InviteCodeOrm.expires_at > now,
    ).with_for_update())).all()
    for row in rows:
        row.expires_at = now


async def ensure_invite(session: AsyncSession, employee: EmployeeOrm, created_by: int | None, now) -> str | None:
    if employee.telegram_id:
        return None
    await expire_unused_invites(session, employee.id, now)
    code = secrets.token_urlsafe(32)
    session.add(InviteCodeOrm(
        employee_id=employee.id,
        code=code,
        created_by=created_by,
        expires_at=now + timedelta(days=settings.rules.invite_expire_days),
    ))
    return invite_url(code)


async def ensure_employee(
    session: AsyncSession,
    code: str,
    full_name: str,
    role: EmployeeRole,
    now,
    hourly_rate: int | None = None,
    created_by: int | None = None,
) -> tuple[EmployeeOrm, str | None]:
    employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.code == code))
    if employee:
        employee.full_name = full_name
        employee.role = role
        employee.is_active = True
    else:
        employee = EmployeeOrm(code=code, full_name=full_name, role=role, is_active=True)
        session.add(employee)
        await session.flush()
    if hourly_rate is not None:
        rate = await session.scalar(select(RateHistoryOrm).where(
            RateHistoryOrm.employee_id == employee.id,
            RateHistoryOrm.effective_from == now.date(),
        ))
        if rate:
            rate.hourly_rate = hourly_rate
        else:
            session.add(RateHistoryOrm(
                employee_id=employee.id,
                hourly_rate=hourly_rate,
                effective_from=now.date(),
                created_by=created_by,
            ))
    invite = await ensure_invite(session, employee, created_by, now)
    return employee, invite


async def reset_demo_data(session: AsyncSession) -> None:
    demo_ids = select(EmployeeOrm.id).where(EmployeeOrm.code.in_([code for code, _, _ in DEMO_EMPLOYEES]))
    session_ids = select(WorkSessionOrm.id).where(WorkSessionOrm.employee_id.in_(demo_ids))
    output_ids = select(OutputLogOrm.id).where(OutputLogOrm.work_session_id.in_(session_ids))
    await session.execute(delete(OutputItemOrm).where(OutputItemOrm.output_log_id.in_(output_ids)))
    await session.execute(delete(OutputLogOrm).where(OutputLogOrm.work_session_id.in_(session_ids)))
    await session.execute(delete(PayBatchOrm).where(PayBatchOrm.employee_id.in_(demo_ids)))
    await session.execute(delete(WorkSessionOrm).where(WorkSessionOrm.employee_id.in_(demo_ids)))
    await session.execute(delete(InviteCodeOrm).where(InviteCodeOrm.employee_id.in_(demo_ids)))
    await session.execute(delete(RateHistoryOrm).where(RateHistoryOrm.employee_id.in_(demo_ids)))
    await session.execute(delete(EmployeeOrm).where(EmployeeOrm.id.in_(demo_ids)))


async def seed_crv(session: AsyncSession, demo: bool = False, reset_demo: bool = False) -> list[str]:
    now = Clock().now()
    links: list[str] = []
    if reset_demo:
        if settings.app.env != "development":
            raise RuntimeError("--reset-demo is only allowed when APP__ENV=development")
        await reset_demo_data(session)
    await upsert_products(session)
    await upsert_consent_v1(session, now)
    manager, manager_invite = await ensure_employee(
        session,
        "QL001",
        settings.seed.manager_name,
        EmployeeRole.manager,
        now,
    )
    director, director_invite = await ensure_employee(
        session,
        "GD001",
        settings.seed.director_name,
        EmployeeRole.director,
        now,
        created_by=manager.id,
    )
    for label, link in [("QL001", manager_invite), ("GD001", director_invite)]:
        if link:
            links.append(f"{label}: {link}")
    if demo:
        for code, name, rate in DEMO_EMPLOYEES:
            _, link = await ensure_employee(
                session,
                code,
                name,
                EmployeeRole.employee,
                now,
                hourly_rate=rate,
                created_by=manager.id,
            )
            if link:
                links.append(f"{code}: {link}")
    return links


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Seed Appendix B demo employees")
    parser.add_argument("--reset-demo", action="store_true", help="Delete demo business data first; development only")
    args = parser.parse_args()
    engine = create_async_engine(settings.db.postgres_connection(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            links = await seed_crv(session, demo=args.demo, reset_demo=args.reset_demo)
        for link in links:
            print(link)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
