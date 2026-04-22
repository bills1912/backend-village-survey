# app/core/startup.py
# Auto-migrate dan seed saat pertama kali app dijalankan
from datetime import datetime, timezone, timedelta
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
        {"r_201": "Hendra Gunawan",    "r_202": "1271010101800001", "r_203": "1", "r_204": "1", "r_205": "1",
         "r_206": "Medan", "r_207": "1980-01-15", "r_207_usia": 44, "r_208": "Batak",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "4", "r_300_pekerjaan": "2"},
        {"r_201": "Dewi Gunawan",      "r_202": "1271010101850001", "r_203": "2", "r_204": "1", "r_205": "2",
         "r_206": "Medan", "r_207": "1985-06-20", "r_207_usia": 38, "r_208": "Batak",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "3", "r_300_pekerjaan": "3"},
    ],
    [
        {"r_201": "Rusli Harahap",     "r_202": "1271020101750001", "r_203": "1", "r_204": "1", "r_205": "1",
         "r_206": "Tapanuli", "r_207": "1975-08-22", "r_207_usia": 49, "r_208": "Batak",
         "r_209": "1", "r_210": "1", "r_211": ["3"], "r_212": "2", "r_300_pekerjaan": "2"},
        {"r_201": "Nurhayati Harahap", "r_202": "1271020101800002", "r_203": "2", "r_204": "1", "r_205": "2",
         "r_206": "Medan", "r_207": "1980-12-05", "r_207_usia": 43, "r_208": "Batak",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "2", "r_300_pekerjaan": "3"},
    ],
    [
        {"r_201": "Samino Widjaja",    "r_202": "1271030101500001", "r_203": "1", "r_204": "4", "r_205": "1",
         "r_206": "Tebing Tinggi", "r_207": "1950-11-30", "r_207_usia": 73, "r_208": "Jawa",
         "r_209": "1", "r_210": "1", "r_211": ["1", "5"], "r_212": "1", "r_300_pekerjaan": "3"},
        {"r_201": "Rini Widjaja",      "r_202": "1271030101850002", "r_203": "3", "r_204": "1", "r_205": "2",
         "r_206": "Medan", "r_207": "1985-02-28", "r_207_usia": 39, "r_208": "Jawa",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "5", "r_300_pekerjaan": "2"},
    ],
    [
        {"r_201": "Syahrul Nasution",  "r_202": "1271040101820001", "r_203": "1", "r_204": "1", "r_205": "1",
         "r_206": "Padang Sidimpuan", "r_207": "1982-09-17", "r_207_usia": 41, "r_208": "Batak Mandailing",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "6", "r_300_pekerjaan": "2"},
        {"r_201": "Fatimah Nasution",  "r_202": "1271040101870001", "r_203": "2", "r_204": "1", "r_205": "2",
         "r_206": "Medan", "r_207": "1987-05-03", "r_207_usia": 37, "r_208": "Batak Mandailing",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "4", "r_300_pekerjaan": "3"},
    ],
    [
        {"r_201": "Lina Siregar",      "r_202": "1271050101900001", "r_203": "1", "r_204": "3", "r_205": "2",
         "r_206": "Sibolga", "r_207": "1990-06-14", "r_207_usia": 33, "r_208": "Batak Toba",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "5", "r_300_pekerjaan": "2"},
        {"r_201": "Dinda Siregar",     "r_202": "1271050101170001", "r_203": "3", "r_204": "2", "r_205": "2",
         "r_206": "Medan", "r_207": "2017-10-22", "r_207_usia": 6, "r_208": "Batak Toba",
         "r_209": "1", "r_210": "1", "r_211": [], "r_212": "1", "r_300_pekerjaan": "1"},
    ],
]


async def run_migrate(db) -> list[str]:
    """Buat semua indexes. Idempotent — aman dipanggil berkali-kali."""
    log = []
    try:
        await db["users"].create_index("email", unique=True)
        log.append("✓ Index unik email (users)")
    except Exception:
        log.append("⏭ Index email sudah ada")

    await db["users"].create_index("roles")
    await db["surveys"].create_index("created_at")

    # Questionnaires — field indexes
    for field in ["survey_id", "user_id", "r_102", "nama_petugas", "created_at",
                  "kode_provinsi", "kode_kabupaten", "kode_kecamatan", "kode_desa",
                  "nama_desa", "dusun"]:
        await db["questionnaires"].create_index(field)

    # Compound indexes untuk filter hierarki
    await db["questionnaires"].create_index([("kode_provinsi",  1), ("created_at", -1)])
    await db["questionnaires"].create_index([("kode_kabupaten", 1), ("created_at", -1)])
    await db["questionnaires"].create_index([("kode_kecamatan", 1), ("created_at", -1)])
    await db["questionnaires"].create_index([("kode_desa",      1), ("created_at", -1)])
    await db["questionnaires"].create_index([("survey_id",      1), ("kode_desa",   1)])
    log.append("✓ Indexes questionnaires selesai")

    # Wilayah collection
    try:
        await db["wilayah"].create_index("kode", unique=True)
        log.append("✓ Index unik kode (wilayah)")
    except Exception:
        log.append("⏭ Index kode wilayah sudah ada")

    await db["wilayah"].create_index("tipe")
    await db["wilayah"].create_index([("tipe", 1), ("parent_kode", 1)])
    await db["wilayah"].create_index([("tipe", 1), ("nama", 1)])
    log.append("✓ Indexes wilayah selesai")

    await db["token_blacklist"].create_index("expires_at", expireAfterSeconds=0)
    log.append("✓ TTL index token_blacklist")

    return log


async def run_reset(db) -> list[str]:
    """
    HAPUS SEMUA DATA. Gunakan hanya untuk setup ulang dari nol.
    Dipanggil via POST /setup/reset (bukan otomatis saat startup).
    """
    log = []
    for col in ["users", "surveys", "questionnaires", "wilayah", "permissions", "token_blacklist"]:
        result = await db[col].delete_many({})
        log.append(f"✓ Reset '{col}': {result.deleted_count} dokumen dihapus")
    return log


async def run_seed_users(db) -> list[str]:
    """Seed user default. Skip jika sudah ada."""
    log = []
    now = datetime.now(timezone.utc)
    for u in USERS:
        if await db["users"].find_one({"email": u["email"]}):
            log.append(f"⏭ Skip: {u['email']}")
            continue
        await db["users"].insert_one({
            "name": u["name"], "email": u["email"],
            "password": hash_password(u["password"]),
            "roles": u["roles"],
            "created_at": now, "updated_at": now,
        })
        log.append(f"✓ User: {u['email']} [{', '.join(u['roles'])}]")
    return log


async def run_seed_surveys(db) -> tuple[list[str], object]:
    """Seed survey default. Return (log, survey_id)."""
    log = []
    now = datetime.now(timezone.utc)
    survey_doc = await db["surveys"].find_one({"nama_survey": "Sensus Penduduk 2024"})
    if survey_doc:
        log.append("⏭ Survey sudah ada")
        return log, survey_doc["_id"]
    res = await db["surveys"].insert_one({"nama_survey": "Sensus Penduduk 2024", "created_at": now, "updated_at": now})
    await db["surveys"].insert_one({"nama_survey": "Pendataan Ekonomi 2024", "created_at": now, "updated_at": now})
    log.append("✓ Survey 'Sensus Penduduk 2024' dan 'Pendataan Ekonomi 2024' dibuat")
    return log, res.inserted_id


async def run_seed_sample_questionnaires(db, survey_id) -> list[str]:
    """
    Seed kuesioner contoh dari data wilayah yang sudah tersedia.
    Tidak akan jalan jika wilayah belum di-import.
    """
    log = []

    if await db["questionnaires"].count_documents({"survey_id": survey_id}) > 0:
        log.append(f"⏭ Kuesioner contoh sudah ada")
        return log

    wilayah_count = await db["wilayah"].count_documents({})
    if wilayah_count == 0:
        log.append("⚠️  Wilayah belum di-import → kuesioner contoh dilewati")
        log.append("   Kirim file wilayah ke POST /api/wilayah/import terlebih dahulu")
        return log

    # Ambil hingga 5 desa yang tersedia
    sample_desa = await db["wilayah"].find({"tipe": "desa"}).limit(5).to_list(length=5)
    if not sample_desa:
        log.append("⚠️  Tidak ada data desa di wilayah")
        return log

    # Helper: ambil hierarki dari kode kecamatan
    async def get_hierarchy(kode_kec: str) -> dict:
        kec  = await db["wilayah"].find_one({"kode": kode_kec,             "tipe": "kecamatan"}) or {}
        kab  = await db["wilayah"].find_one({"kode": kec.get("parent_kode"), "tipe": "kabupaten"}) or {}
        prov = await db["wilayah"].find_one({"kode": kab.get("parent_kode"), "tipe": "provinsi"})  or {}
        return {
            "kode_kecamatan": kec.get("kode"), "nama_kecamatan": kec.get("nama"),
            "kode_kabupaten": kab.get("kode"), "nama_kabupaten": kab.get("nama"),
            "kode_provinsi":  prov.get("kode"), "nama_provinsi":  prov.get("nama"),
        }

    petugas_list = await db["users"].find({"roles": "petugas"}).to_list(length=5)
    if not petugas_list:
        petugas_list = await db["users"].find().limit(1).to_list(length=1)

    now = datetime.now(timezone.utc)
    inserted = 0
    for i, desa in enumerate(sample_desa):
        hier = await get_hierarchy(desa.get("parent_kode", ""))
        petugas = petugas_list[i % len(petugas_list)]
        anggota = SAMPLE_ANGGOTA[i % len(SAMPLE_ANGGOTA)]
        t = now - timedelta(days=i)

        await db["questionnaires"].insert_one({
            "survey_id":      survey_id,
            "user_id":        petugas["_id"],
            "nama_petugas":   petugas["name"],
            **hier,
            "kode_desa":      desa["kode"],
            "nama_desa":      desa["nama"],
            "dusun":          f"Dusun {i + 1}" if i % 2 == 0 else None,
            "r_102":          f"337101010124{i + 1:04d}",
            "r_103":          "1",
            "r_104":          None,
            "kelompok_dasa_wisma": None,
            "lokasi_rumah":   None,
            "waktu_pendataan": t.strftime("%Y-%m-%d %H:%M"),
            "r_200":          anggota,
            "r_401":          None,
            "created_at":     t,
            "updated_at":     t,
        })
        inserted += 1

    log.append(f"✓ {inserted} kuesioner contoh dibuat")
    return log


async def auto_setup(db) -> None:
    """
    Dipanggil saat app startup. Selalu jalankan migrate (idempotent),
    lalu seed jika belum ada data.
    """
    print("🔧  Running auto-setup...")
    try:
        for line in await run_migrate(db):
            print(f"   {line}")
    except Exception as e:
        print(f"❌  Migrate error: {e}")
        return

    user_count = await db["users"].count_documents({})
    if user_count == 0:
        for line in await run_seed_users(db):
            print(f"   {line}")
    else:
        print(f"   ⏭ Users sudah ada ({user_count})")

    survey_log, survey_id = await run_seed_surveys(db)
    for line in survey_log:
        print(f"   {line}")

    for line in await run_seed_sample_questionnaires(db, survey_id):
        print(f"   {line}")

    wilayah_count = await db["wilayah"].count_documents({})
    print(f"\n✅  Auto-setup selesai!")
    print(f"   Users        : {await db['users'].count_documents({})}")
    print(f"   Surveys      : {await db['surveys'].count_documents({})}")
    print(f"   Questionnaires: {await db['questionnaires'].count_documents({})}")
    if wilayah_count > 0:
        print(f"   Wilayah      : {wilayah_count:,} record ✓")
    else:
        print(f"   Wilayah      : belum di-import ⚠️")
        print(f"   → POST /api/wilayah/import (kirim file CSV/JSON Kemendagri)")