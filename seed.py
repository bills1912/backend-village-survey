#!/usr/bin/env python3
"""
seed.py – Isi database dengan data awal (users, roles, surveys, contoh kuesioner)
Jalankan: python seed.py
         python seed.py --reset   (hapus semua data dulu)
"""
import asyncio
import sys
import os
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_password

# ─── Data Roles ───────────────────────────────────────────────────────────────
ROLES = ["super_admin", "admin", "petugas"]

# ─── Data Users ───────────────────────────────────────────────────────────────
USERS = [
    {
        "name": "Super Admin",
        "email": "superadmin@desasukamakmur.id",
        "password": "admin123",
        "roles": ["super_admin"],
        "description": "Akses penuh ke semua fitur",
    },
    {
        "name": "Admin Desa",
        "email": "admin@desasukamakmur.id",
        "password": "admin123",
        "roles": ["admin"],
        "description": "Manajemen data dan laporan",
    },
    {
        "name": "Budi Santoso",
        "email": "budi@desasukamakmur.id",
        "password": "petugas123",
        "roles": ["petugas"],
        "description": "Petugas Dusun I-A dan I-B",
    },
    {
        "name": "Siti Rahayu",
        "email": "siti@desasukamakmur.id",
        "password": "petugas123",
        "roles": ["petugas"],
        "description": "Petugas Dusun II Timur dan II Barat",
    },
    {
        "name": "Ahmad Fauzi",
        "email": "ahmad@desasukamakmur.id",
        "password": "petugas123",
        "roles": ["petugas"],
        "description": "Petugas Dusun III dan IV",
    },
]

# ─── Data Dusun ───────────────────────────────────────────────────────────────
DUSUN = {
    "1": "Dusun I-A",
    "2": "Dusun I-B",
    "3": "Dusun II Timur",
    "4": "Dusun II Barat",
    "5": "Dusun III",
    "6": "Dusun IV",
}

# ─── Sample Anggota Keluarga ──────────────────────────────────────────────────
SAMPLE_ANGGOTA = [
    # KK 1
    [
        {
            "r_201": "Hendra Gunawan", "r_202": "1271010101800001",
            "r_203": "1", "r_204": "1", "r_205": "1",
            "r_206": "Medan", "r_207": "1980-01-15", "r_207_usia": 44,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "4", "r_300_pekerjaan": "2",
        },
        {
            "r_201": "Dewi Gunawan", "r_202": "1271010101850001",
            "r_203": "2", "r_204": "1", "r_205": "2",
            "r_206": "Medan", "r_207": "1985-06-20", "r_207_usia": 38,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "3", "r_300_pekerjaan": "3",
        },
        {
            "r_201": "Rian Gunawan", "r_202": "1271010101050001",
            "r_203": "3", "r_204": "2", "r_205": "1",
            "r_206": "Medan", "r_207": "2005-03-10", "r_207_usia": 19,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "4", "r_300_pekerjaan": "1",
        },
    ],
    # KK 2
    [
        {
            "r_201": "Rusli Harahap", "r_202": "1271020101750001",
            "r_203": "1", "r_204": "1", "r_205": "1",
            "r_206": "Tapanuli", "r_207": "1975-08-22", "r_207_usia": 49,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": ["3"], "r_212": "2", "r_300_pekerjaan": "2",
        },
        {
            "r_201": "Nurhayati Harahap", "r_202": "1271020101800002",
            "r_203": "2", "r_204": "1", "r_205": "2",
            "r_206": "Medan", "r_207": "1980-12-05", "r_207_usia": 43,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "2", "r_300_pekerjaan": "3",
        },
        {
            "r_201": "Putri Harahap", "r_202": "1271020101100001",
            "r_203": "3", "r_204": "2", "r_205": "2",
            "r_206": "Medan", "r_207": "2010-04-14", "r_207_usia": 14,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "3", "r_300_pekerjaan": "1",
        },
        {
            "r_201": "Bagas Harahap", "r_202": "1271020101130001",
            "r_203": "3", "r_204": "2", "r_205": "1",
            "r_206": "Medan", "r_207": "2013-07-19", "r_207_usia": 10,
            "r_208": "Batak", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "2", "r_300_pekerjaan": "1",
        },
    ],
    # KK 3 – lansia
    [
        {
            "r_201": "Samino Widjaja", "r_202": "1271030101500001",
            "r_203": "1", "r_204": "4", "r_205": "1",
            "r_206": "Tebing Tinggi", "r_207": "1950-11-30", "r_207_usia": 73,
            "r_208": "Jawa", "r_209": "1", "r_210": "1",
            "r_211": ["1", "5"], "r_212": "1", "r_300_pekerjaan": "3",
        },
        {
            "r_201": "Rini Widjaja", "r_202": "1271030101850002",
            "r_203": "3", "r_204": "1", "r_205": "2",
            "r_206": "Medan", "r_207": "1985-02-28", "r_207_usia": 39,
            "r_208": "Jawa", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "5", "r_300_pekerjaan": "2",
        },
    ],
    # KK 4
    [
        {
            "r_201": "Syahrul Nasution", "r_202": "1271040101820001",
            "r_203": "1", "r_204": "1", "r_205": "1",
            "r_206": "Padang Sidimpuan", "r_207": "1982-09-17", "r_207_usia": 41,
            "r_208": "Batak Mandailing", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "6", "r_300_pekerjaan": "2",
        },
        {
            "r_201": "Fatimah Nasution", "r_202": "1271040101870001",
            "r_203": "2", "r_204": "1", "r_205": "2",
            "r_206": "Medan", "r_207": "1987-05-03", "r_207_usia": 37,
            "r_208": "Batak Mandailing", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "4", "r_300_pekerjaan": "3",
        },
        {
            "r_201": "Ilham Nasution", "r_202": "1271040101120001",
            "r_203": "3", "r_204": "2", "r_205": "1",
            "r_206": "Medan", "r_207": "2012-11-25", "r_207_usia": 11,
            "r_208": "Batak Mandailing", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "2", "r_300_pekerjaan": "1",
        },
        {
            "r_201": "Zahra Nasution", "r_202": "1271040101150001",
            "r_203": "3", "r_204": "2", "r_205": "2",
            "r_206": "Medan", "r_207": "2015-08-09", "r_207_usia": 8,
            "r_208": "Batak Mandailing", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "2", "r_300_pekerjaan": "1",
        },
        {
            "r_201": "Yusuf Nasution", "r_202": "1271040101180001",
            "r_203": "3", "r_204": "2", "r_205": "1",
            "r_206": "Medan", "r_207": "2018-03-15", "r_207_usia": 6,
            "r_208": "Batak Mandailing", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "2", "r_300_pekerjaan": "1",
        },
    ],
    # KK 5
    [
        {
            "r_201": "Lina Siregar", "r_202": "1271050101900001",
            "r_203": "1", "r_204": "3", "r_205": "2",
            "r_206": "Sibolga", "r_207": "1990-06-14", "r_207_usia": 33,
            "r_208": "Batak Toba", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "5", "r_300_pekerjaan": "2",
        },
        {
            "r_201": "Dinda Siregar", "r_202": "1271050101170001",
            "r_203": "3", "r_204": "2", "r_205": "2",
            "r_206": "Medan", "r_207": "2017-10-22", "r_207_usia": 6,
            "r_208": "Batak Toba", "r_209": "1", "r_210": "1",
            "r_211": [], "r_212": "1", "r_300_pekerjaan": "1",
        },
    ],
    # KK 6 – pindah
    [
        {
            "r_201": "Bambang Susilo", "r_202": "1271060101700001",
            "r_203": "1", "r_204": "1", "r_205": "1",
            "r_206": "Solo", "r_207": "1970-04-01", "r_207_usia": 54,
            "r_208": "Jawa", "r_209": "1", "r_210": "2",
            "r_211": [], "r_212": "3", "r_300_pekerjaan": "3",
        },
    ],
]

# Pasangan (No KK, dusun, petugas_idx, r_103, anggota_idx)
QUESTIONNAIRE_META = [
    ("3371010101240001", "1", 0, "1", 0),
    ("3371010101240002", "1", 0, "1", 1),
    ("3371010101240003", "2", 0, "2", 2),
    ("3371010101240004", "2", 1, "1", 3),
    ("3371010101240005", "3", 1, "1", 4),
    ("3371010101240006", "3", 2, "1", 5),
    ("3371010101240007", "4", 2, "1", 0),
    ("3371010101240008", "4", 2, "2", 1),
    ("3371010101240009", "5", 2, "1", 2),
    ("3371010101240010", "6", 2, "1", 3),
]


async def run_seed(reset: bool = False):
    print("=" * 60)
    print(f"  Seeder: {settings.DB_NAME}")
    print("=" * 60)

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DB_NAME]
    await client.admin.command("ping")
    print("✅  Koneksi berhasil\n")

    if reset:
        print("⚠️   Mode RESET – Menghapus semua data...")
        for col in ["users", "surveys", "questionnaires", "token_blacklist"]:
            await db[col].delete_many({})
            print(f"    ✓ Kosongkan collection '{col}'")
        print()

    # ── Seed Users ────────────────────────────────────────────────────────
    print("👥  Seeding Users...")
    user_ids: list[ObjectId] = []
    created_users = []

    for u in USERS:
        existing = await db["users"].find_one({"email": u["email"]})
        if existing:
            print(f"    ⏭  Skip (sudah ada): {u['email']}")
            user_ids.append(existing["_id"])
            created_users.append(existing)
            continue

        doc = {
            "name": u["name"],
            "email": u["email"],
            "password": hash_password(u["password"]),
            "roles": u["roles"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        res = await db["users"].insert_one(doc)
        user_ids.append(res.inserted_id)
        doc["_id"] = res.inserted_id
        created_users.append(doc)
        print(f"    ✓ Buat user: {u['email']}  [{', '.join(u['roles'])}]  pwd: {u['password']}")

    # ── Seed Surveys ──────────────────────────────────────────────────────
    print("\n📋  Seeding Surveys...")
    survey_doc = await db["surveys"].find_one({"nama_survey": "Sensus Penduduk 2024"})
    if survey_doc:
        print("    ⏭  Skip: Survey sudah ada")
        survey_id = survey_doc["_id"]
    else:
        survey_res = await db["surveys"].insert_one({
            "nama_survey": "Sensus Penduduk 2024",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        survey_id = survey_res.inserted_id
        print(f"    ✓ Survey 'Sensus Penduduk 2024' dibuat (id: {survey_id})")

    # Tambah satu survey lagi
    survey2 = await db["surveys"].find_one({"nama_survey": "Pendataan Ekonomi 2024"})
    if not survey2:
        await db["surveys"].insert_one({
            "nama_survey": "Pendataan Ekonomi 2024",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        print(f"    ✓ Survey 'Pendataan Ekonomi 2024' dibuat")

    # ── Seed Questionnaires ───────────────────────────────────────────────
    print("\n📝  Seeding Questionnaires (contoh data)...")
    petugas_users = [u for u in created_users if "petugas" in u.get("roles", [])]
    if not petugas_users:
        petugas_users = created_users[:1]

    existing_count = await db["questionnaires"].count_documents({"survey_id": survey_id})
    if existing_count > 0:
        print(f"    ⏭  Skip: Sudah ada {existing_count} kuesioner")
    else:
        inserted = 0
        for no_kk, dusun, petugas_idx, r103, anggota_idx in QUESTIONNAIRE_META:
            petugas = petugas_users[petugas_idx % len(petugas_users)]
            anggota = SAMPLE_ANGGOTA[anggota_idx % len(SAMPLE_ANGGOTA)]

            now = datetime.now(timezone.utc) - timedelta(days=inserted)
            doc = {
                "survey_id": survey_id,
                "user_id": petugas["_id"],
                "nama_petugas": petugas["name"],
                "dusun": dusun,
                "r_102": no_kk,
                "r_103": r103,
                "r_104": None,
                "kelompok_dasa_wisma": f"KDW-{dusun}-{inserted+1:02d}",
                "lokasi_rumah": None,
                "waktu_pendataan": now.strftime("%Y-%m-%d %H:%M"),
                "r_200": anggota,
                "r_401": None,
                "created_at": now,
                "updated_at": now,
            }
            await db["questionnaires"].insert_one(doc)
            inserted += 1

        print(f"    ✓ {inserted} kuesioner contoh berhasil dibuat")

    # ── Summary ───────────────────────────────────────────────────────────
    total_users = await db["users"].count_documents({})
    total_surveys = await db["surveys"].count_documents({})
    total_q = await db["questionnaires"].count_documents({})

    print("\n" + "=" * 60)
    print("✅  Seeding selesai!")
    print(f"    Users        : {total_users}")
    print(f"    Surveys      : {total_surveys}")
    print(f"    Questionnaires: {total_q}")
    print("=" * 60)
    print("\n📌  Akun login yang tersedia:")
    print(f"{'Email':<40}  {'Password':<15}  {'Role'}")
    print("-" * 70)
    for u in USERS:
        print(f"  {u['email']:<38}  {u['password']:<15}  {', '.join(u['roles'])}")
    print()

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database Desa Suka Makmur")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Hapus semua data sebelum seeding ulang",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(reset=args.reset))
