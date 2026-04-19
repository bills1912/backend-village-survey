# app/core/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Verify connection
    await _client.admin.command("ping")
    print(f"✅  Terhubung ke MongoDB – database: {settings.DB_NAME}")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        print("❌  Koneksi MongoDB ditutup")


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database belum terhubung. Panggil connect_db() dulu.")
    return _client[settings.DB_NAME]
