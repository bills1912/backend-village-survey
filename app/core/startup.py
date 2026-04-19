# app/core/startup.py
# Auto-migrate dan seed saat pertama kali app dijalankan
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from .security import hash_password

USERS = [
    {"name": "Super Admin",  "email": "superadmin@desasukamakmur.id", "password": "admin123",   "roles": ["super_admin"]},
    {"name": "Admin Desa",   "email": "admin@desasukamakmur.id",      "password": "admin123",   "roles": ["admin"]},
    {"name": "Budi Santoso", "email": "budi@desasukamakmur.id",       "password": "petugas123", "roles": ["petugas"]},
    {"name": "Siti Rahayu",  "email": "siti@desasukamakmur.id",       "password": "petugas123", "roles": ["petugas"]},
    {"name": "Ahmad Fauzi",  "email": "ahmad@desasukamakmur.id",      "password": "petugas123", "roles": ["petugas"]},
]

SAMPLE_ANGGOTA = [
    [
        {"r_201": "Hendra Gunawan",    "r_202": "1271010101800001", "r_203": "1", "r_204": "1", "r_205": "1", "r_206": "Medan",          "r_207": "1980-01-15", "r_207_usia": 44, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "4", "r_300_pekerjaan": "2"},
        {"r_201": "Dewi Gunawan",      "r_202": "1271010101850001", "r_203": "2", "r_204": "1", "r_205": "2", "r_206": "Medan",          "r_207": "1985-06-20", "r_207_usia": 38, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "3", "r_300_pekerjaan": "3"},
        {"r_201": "Rian Gunawan",      "r_202": "1271010101050001", "r_203": "3", "r_204": "2", "r_205": "1", "r_206": "Medan",          "r_207": "2005-03-10", "r_207_usia": 19, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "4", "r_300_pekerjaan": "1"},
    ],
    [
        {"r_201": "Rusli Harahap",     "r_202": "1271020101750001", "r_203": "1", "r_204": "1", "r_205": "1", "r_206": "Tapanuli",       "r_207": "1975-08-22", "r_207_usia": 49, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": ["3"],    "r_212": "2", "r_300_pekerjaan": "2"},
        {"r_201": "Nurhayati Harahap", "r_202": "1271020101800002", "r_203": "2", "r_204": "1", "r_205": "2", "r_206": "Medan",          "r_207": "1980-12-05", "r_207_usia": 43, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "2", "r_300_pekerjaan": "3"},
        {"r_201": "Putri Harahap",     "r_202": "1271020101100001", "r_203": "3", "r_204": "2", "r_205": "2", "r_206": "Medan",          "r_207": "2010-04-14", "r_207_usia": 14, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "3", "r_300_pekerjaan": "1"},
        {"r_201": "Bagas Harahap",     "r_202": "1271020101130001", "r_203": "3", "r_204": "2", "r_205": "1", "r_206": "Medan",          "r_207": "2013-07-19", "r_207_usia": 10, "r_208": "Batak",              "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "2", "r_300_pekerjaan": "1"},
    ],
    [
        {"r_201": "Samino Widjaja",    "r_202": "1271030101500001", "r_203": "1", "r_204": "4", "r_205": "1", "r_206": "Tebing Tinggi",  "r_207": "1950-11-30", "r_207_usia": 73, "r_208": "Jawa",               "r_209": "1", "r_210": "1", "r_211": ["1","5"], "r_212": "1", "r_300_pekerjaan": "3"},
        {"r_201": "Rini Widjaja",      "r_202": "1271030101850002", "r_203": "3", "r_204": "1", "r_205": "2", "r_206": "Medan",          "r_207": "1985-02-28", "r_207_usia": 39, "r_208": "Jawa",               "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "5", "r_300_pekerjaan": "2"},
    ],
    [
        {"r_201": "Syahrul Nasution",  "r_202": "1271040101820001", "r_203": "1", "r_204": "1", "r_205": "1", "r_206": "Padang Sidimpuan","r_207": "1982-09-17","r_207_usia": 41, "r_208": "Batak Mandailing",  "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "6", "r_300_pekerjaan": "2"},
        {"r_201": "Fatimah Nasution",  "r_202": "1271040101870001", "r_203": "2", "r_204": "1", "r_205": "2", "r_206": "Medan",          "r_207": "1987-05-03", "r_207_usia": 37, "r_208": "Batak Mandailing",  "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "4", "r_300_pekerjaan": "3"},
        {"r_201": "Ilham Nasution",    "r_202": "1271040101120001", "r_203": "3", "r_204": "2", "r_205": "1", "r_206": "Medan",          "r_207": "2012-11-25", "r_207_usia": 11, "r_208": "Batak Mandailing",  "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "2", "r_300_pekerjaan": "1"},
    ],
    [
        {"r_201": "Lina Siregar",      "r_202": "1271050101900001", "r_203": "1", "r_204": "3", "r_205": "2", "r_206": "Sibolga",        "r_207": "1990-06-14", "r_207_usia": 33, "r_208": "Batak Toba",         "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "5", "r_300_pekerjaan": "2"},
        {"r_201": "Dinda Siregar",     "r_202": "1271050101170001", "r_203": "3", "r_204": "2", "r_205": "2", "r_206": "Medan",          "r_207": "2017-10-22", "r_207_usia": 6,  "r_208": "Batak Toba",         "r_209": "1", "r_210": "1", "r_211": [],       "r_212": "1", "r_300_pekerjaan": "1"},
    ],
]

QUESTIONNAIRE_META = [
    ("3371010101240001","1",0,"1",0), ("3371010101240002","1",0,"1",1),
    ("3371010101240003","2",1,"2",2), ("3371010101240004","2",1,"1",3),
    ("3371010101240005","3",2,"1",4), ("3371010101240006","3",2,"1",0),
    ("3371010101240007","4",2,"1",1), ("3371010101240008","4",2,"2",2),
    ("3371010101240009","5",2,"1",3), ("3371010101240010","6",2,"1",4),
]


async def run_migrate(db) -> list[str]:
    log = []
    try:
        await db["users"].create_index("email", unique=True)
        log.append("✓ Index email (users)")
    except Exception:
        log.append("⏭ Index email sudah ada")

    await db["users"].create_index("roles")
    await db["surveys"].create_index("created_at")
    await db["questionnaires"].create_index("survey_id")
    await db["questionnaires"].create_index("user_id")
    await db["questionnaires"].create_index("dusun")
    await db["questionnaires"].create_index("r_102")
    await db["questionnaires"].create_index("nama_petugas")
    await db["questionnaires"].create_index("created_at")
    await db["questionnaires"].create_index([("dusun", 1), ("created_at", -1)])
    await db["questionnaires"].create_index([("survey_id", 1), ("dusun", 1)])
    await db["token_blacklist"].create_index("expires_at", expireAfterSeconds=0)
    log.append("✓ Semua indexes selesai")
    return log


async def run_seed(db) -> list[str]:
    log = []
    now = datetime.now(timezone.utc)

    # ── Users ──────────────────────────────────────────────────────────────
    created_users = []
    for u in USERS:
        existing = await db["users"].find_one({"email": u["email"]})
        if existing:
            created_users.append(existing)
            continue
        doc = {
            "name": u["name"], "email": u["email"],
            "password": hash_password(u["password"]),
            "roles": u["roles"],
            "created_at": now, "updated_at": now,
        }
        res = await db["users"].insert_one(doc)
        doc["_id"] = res.inserted_id
        created_users.append(doc)
        log.append(f"✓ User: {u['email']}")

    if not log:
        log.append("⏭ Users sudah ada")

    # ── Survey ─────────────────────────────────────────────────────────────
    survey_doc = await db["surveys"].find_one({"nama_survey": "Sensus Penduduk 2024"})
    if survey_doc:
        survey_id = survey_doc["_id"]
        log.append("⏭ Survey sudah ada")
    else:
        res = await db["surveys"].insert_one({
            "nama_survey": "Sensus Penduduk 2024",
            "created_at": now, "updated_at": now,
        })
        survey_id = res.inserted_id
        log.append("✓ Survey dibuat")
        await db["surveys"].insert_one({
            "nama_survey": "Pendataan Ekonomi 2024",
            "created_at": now, "updated_at": now,
        })

    # ── Questionnaires ─────────────────────────────────────────────────────
    existing_q = await db["questionnaires"].count_documents({"survey_id": survey_id})
    if existing_q > 0:
        log.append(f"⏭ Kuesioner sudah ada ({existing_q} data)")
    else:
        petugas_users = [u for u in created_users if "petugas" in u.get("roles", [])]
        if not petugas_users:
            petugas_users = created_users
        inserted = 0
        for no_kk, dusun, p_idx, r103, a_idx in QUESTIONNAIRE_META:
            petugas = petugas_users[p_idx % len(petugas_users)]
            t = now - timedelta(days=inserted)
            await db["questionnaires"].insert_one({
                "survey_id": survey_id,
                "user_id": petugas["_id"],
                "nama_petugas": petugas["name"],
                "dusun": dusun, "r_102": no_kk, "r_103": r103,
                "r_104": None, "kelompok_dasa_wisma": f"KDW-{dusun}-{inserted+1:02d}",
                "lokasi_rumah": None,
                "waktu_pendataan": t.strftime("%Y-%m-%d %H:%M"),
                "r_200": SAMPLE_ANGGOTA[a_idx % len(SAMPLE_ANGGOTA)],
                "r_401": None, "created_at": t, "updated_at": t,
            })
            inserted += 1
        log.append(f"✓ {inserted} kuesioner contoh dibuat")

    return log


async def auto_setup(db) -> None:
    """Dipanggil saat app startup. Hanya jalankan jika db masih kosong."""
    user_count = await db["users"].count_documents({})
    if user_count > 0:
        print(f"⏭  Auto-setup skip: sudah ada {user_count} users")
        return

    print("🔧  Auto-setup: menjalankan migrate + seed...")
    try:
        migrate_log = await run_migrate(db)
        seed_log = await run_seed(db)
        for line in migrate_log + seed_log:
            print(f"   {line}")
        print("✅  Auto-setup selesai!")
    except Exception as e:
        print(f"❌  Auto-setup error: {e}")