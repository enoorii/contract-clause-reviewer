# app/db/seed.py
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import setting
from app.core.enums import Role
from app.core.security import hash_password_async
from app.models.models import Users


async def seed_admin_user(db: AsyncSession) -> bool:
    """Seed the admin user if it doesn't exist.
    Returns True if seeded, False if already exists.
    """

    # Check if admin exists
    existing_admin = (
        await db.exec(select(Users).where(Users.username == setting.ADMIN_USERNAME))
    ).first()

    if existing_admin:
        # Don't update existing admin
        return False

    # Create admin
    admin = Users(
        username=setting.ADMIN_USERNAME,
        password_hash=await hash_password_async(setting.ADMIN_PASSWORD),
        role=Role.ADMIN,
        is_active=True,
        must_change_password=True,
    )

    db.add(admin)

    # Log the creation (important for security!)
    print(f"✅ Admin user created: {setting.ADMIN_USERNAME}")
    print("⚠️  Please change the default password immediately!")

    return True
