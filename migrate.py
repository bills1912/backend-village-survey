#!/usr/bin/env python3
"""
migrate.py – Buat indexes, validasi collections, dan setup awal MongoDB
Jalankan: python migrate.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def run_migration():
    print("=" * 60)
    print(f"  Migrasi Database: {settings.DB_NAME}")
    print("=" * 60)

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DB_NAME]

    # ── Ping ──────────────────────────────────────────────────────────────
    await client.admin.command("ping")
    print("✅  Koneksi MongoDB berhasil\n")

    # ── Collection: users ─────────────────────────────────────────────────
    print("📁  Collection: users")
    await db["users"].create_index("email", unique=True)
    print("    ✓ Index unik pada 'email'")
    await db["users"].create_index("roles")
    print("    ✓ Index pada 'roles'")
    await db["users"].create_index("created_at")
    print("    ✓ Index pada 'created_at'")

    # ── Collection: surveys ───────────────────────────────────────────────
    print("\n📁  Collection: surveys")
    await db["surveys"].create_index("created_at")
    print("    ✓ Index pada 'created_at'")
    await db["surveys"].create_index("nama_survey")
    print("    ✓ Index pada 'nama_survey'")

    # ── Collection: questionnaires ────────────────────────────────────────
    print("\n📁  Collection: questionnaires")
    await db["questionnaires"].create_index("survey_id")
    print("    ✓ Index pada 'survey_id'")
    await db["questionnaires"].create_index("user_id")
    print("    ✓ Index pada 'user_id'")
    await db["questionnaires"].create_index("dusun")
    print("    ✓ Index pada 'dusun'")
    await db["questionnaires"].create_index("r_102")
    print("    ✓ Index pada 'r_102' (No. KK)")
    await db["questionnaires"].create_index("nama_petugas")
    print("    ✓ Index pada 'nama_petugas'")
    await db["questionnaires"].create_index("created_at")
    print("    ✓ Index pada 'created_at'")
    # Compound index yang sering dipakai
    await db["questionnaires"].create_index([("dusun", 1), ("created_at", -1)])
    print("    ✓ Compound index (dusun, created_at)")
    await db["questionnaires"].create_index([("survey_id", 1), ("dusun", 1)])
    print("    ✓ Compound index (survey_id, dusun)")

    # ── Collection: tokens (blacklist logout — opsional) ──────────────────
    print("\n📁  Collection: token_blacklist")
    await db["token_blacklist"].create_index(
        "expires_at", expireAfterSeconds=0
    )
    print("    ✓ TTL index pada 'expires_at' (auto-hapus token expired)")

    print("\n" + "=" * 60)
    print("✅  Migrasi selesai!")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
