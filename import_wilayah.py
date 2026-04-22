#!/usr/bin/env python3
"""
import_wilayah.py — Import 4 file CSV wilayah Indonesia ke MongoDB.

File yang diperlukan:
  provinces.csv   → delimiter ';'  | kolom: id;name
  regencies.csv   → delimiter ','  | kolom: id,province_id,name
  districts.csv   → delimiter ';'  | kolom: id;regency_id;name
  villages.csv    → delimiter ','  | kolom: id,district_id,name

Penggunaan:
    python import_wilayah.py                      # upsert semua 4 file
    python import_wilayah.py --mode replace       # hapus wilayah lama dulu
    python import_wilayah.py --dry-run            # preview tanpa tulis ke DB

    # Path kustom:
    python import_wilayah.py \\
      --provinces /path/provinces.csv \\
      --regencies /path/regencies.csv \\
      --districts /path/districts.csv \\
      --villages  /path/villages.csv
"""

import asyncio, csv, os, sys, argparse
from pathlib import Path

# ── Baca .env jika ada ───────────────────────────────────────────────────────
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

MONGODB_URL = os.environ.get("MONGODB_URL", "YOUR-MONGO-DB-URL")
DB_NAME     = os.environ.get("DB_NAME",     "YOUR-DB-NAME")

DEFAULT_PROVINCES = "provinces.csv"
DEFAULT_REGENCIES = "regencies.csv"
DEFAULT_DISTRICTS = "districts.csv"
DEFAULT_VILLAGES  = "villages.csv"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean(s: str) -> str:
    return s.strip().strip('"').strip("'").strip()

def title_case(s: str) -> str:
    exc = {"dan","di","ke","dari","yang","untuk","atau",
           "dengan","oleh","pada","dalam","atas","bawah"}
    words = s.lower().split()
    return " ".join(
        w if (i > 0 and w in exc) else w.capitalize()
        for i, w in enumerate(words)
    )


# ─── Parsers ──────────────────────────────────────────────────────────────────

def parse_provinces(fp: str) -> list[dict]:
    """provinces.csv: delimiter ';', kolom id;name"""
    records = []
    with open(fp, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            kode = clean(row.get("id", ""))
            nama = clean(row.get("name", ""))
            if kode and nama:
                records.append({"kode": kode, "nama": title_case(nama), "tipe": "provinsi"})
    return records

def parse_regencies(fp: str) -> list[dict]:
    """regencies.csv: delimiter ',', kolom id,province_id,name"""
    records = []
    with open(fp, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=","):
            kode   = clean(row.get("id", ""))
            nama   = clean(row.get("name", ""))
            parent = clean(row.get("province_id", "")) or (kode[:2] if len(kode) >= 2 else "")
            if kode and nama:
                records.append({
                    "kode": kode,
                    "nama": title_case(nama),
                    "tipe": "kabupaten",
                    "parent_kode": parent,
                })
    return records

def parse_districts(fp: str) -> list[dict]:
    """districts.csv: delimiter ';', kolom id;regency_id;name"""
    records = []
    with open(fp, encoding="latin1") as f:
        for row in csv.DictReader(f, delimiter=";"):
            kode   = clean(row.get("id", ""))
            nama   = clean(row.get("name", ""))
            parent = clean(row.get("regency_id", "")) or (kode[:4] if len(kode) >= 4 else "")
            if kode and nama:
                records.append({
                    "kode": kode,
                    "nama": title_case(nama),
                    "tipe": "kecamatan",
                    "parent_kode": parent,
                })
    return records

def parse_villages(fp: str) -> list[dict]:
    """villages.csv: delimiter ',', kolom id,district_id,name"""
    records = []
    with open(fp, encoding="latin1") as f:
        for row in csv.DictReader(f, delimiter=";"):
            kode   = clean(row.get("id", ""))
            nama   = clean(row.get("name", ""))
            parent = clean(row.get("district_id", "")) or (kode[:7] if len(kode) >= 7 else "")
            if kode and nama:
                records.append({
                    "kode": kode,
                    "nama": title_case(nama),
                    "tipe": "desa",
                    "parent_kode": parent,
                })
    return records


# ─── Validation ───────────────────────────────────────────────────────────────

def validate(prov, kab, kec, desa) -> list[str]:
    prov_k = {r["kode"] for r in prov}
    kab_k  = {r["kode"] for r in kab}
    kec_k  = {r["kode"] for r in kec}
    warns = []
    orphan_kab = sum(1 for r in kab  if r["parent_kode"] not in prov_k)
    orphan_kec = sum(1 for r in kec  if r["parent_kode"] not in kab_k)
    orphan_des = sum(1 for r in desa if r["parent_kode"] not in kec_k)
    if orphan_kab: warns.append(f"⚠️  {orphan_kab} kabupaten tanpa provinsi valid")
    if orphan_kec: warns.append(f"⚠️  {orphan_kec} kecamatan tanpa kabupaten valid")
    if orphan_des: warns.append(f"⚠️  {orphan_des} desa tanpa kecamatan valid")
    return warns


# ─── MongoDB upsert ───────────────────────────────────────────────────────────

async def upsert_batch(db, records: list[dict], label: str) -> tuple[int, int]:
    from pymongo import UpdateOne
    if not records: return 0, 0
    BATCH = 500
    total_ins = total_upd = 0
    nb = (len(records) + BATCH - 1) // BATCH
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        ops = [UpdateOne({"kode": r["kode"]}, {"$set": r}, upsert=True) for r in batch]
        res = await db["wilayah"].bulk_write(ops, ordered=False)
        total_ins += res.upserted_count
        total_upd += res.modified_count
        print(f"   [{label:<10}] Batch {i//BATCH+1:>3}/{nb} "
              f"→ +{res.upserted_count} baru, {res.modified_count} diperbarui")
    return total_ins, total_upd


# ─── Main ─────────────────────────────────────────────────────────────────────

async def run(provinces_file, regencies_file, districts_file, villages_file, mode, dry_run):
    print("=" * 60)
    print("  Import Wilayah Indonesia → MongoDB")
    print("=" * 60)

    for f in [provinces_file, regencies_file, districts_file, villages_file]:
        if not Path(f).exists():
            print(f"❌  File tidak ditemukan: {f}")
            sys.exit(1)

    print("\n📂  Membaca file CSV...")
    prov = parse_provinces(provinces_file)
    kab  = parse_regencies(regencies_file)
    kec  = parse_districts(districts_file)
    desa = parse_villages(villages_file)

    total = len(prov) + len(kab) + len(kec) + len(desa)
    print(f"\n{'Tipe':<12} {'Jumlah':>8}  {'File'}")
    print("-" * 45)
    print(f"{'Provinsi':<12} {len(prov):>8,}  {provinces_file}")
    print(f"{'Kabupaten':<12} {len(kab):>8,}  {regencies_file}")
    print(f"{'Kecamatan':<12} {len(kec):>8,}  {districts_file}")
    print(f"{'Desa':<12} {len(desa):>8,}  {villages_file}")
    print("-" * 45)
    print(f"{'TOTAL':<12} {total:>8,}")

    print("\n🔍  Validasi konsistensi parent-child...")
    warns = validate(prov, kab, kec, desa)
    if warns:
        for w in warns: print(f"   {w}")
    else:
        print("   ✅  Semua valid — 0 orphan")

    print("\n📋  Sampel data:")
    print(f"   Prov : {prov[0]}")
    print(f"   Kab  : {kab[0]}")
    print(f"   Kec  : {kec[0]}")
    print(f"   Desa : {desa[0]}")

    if dry_run:
        print("\n⚠️   DRY RUN — tidak ada yang ditulis ke database.")
        return

    print(f"\n🔌  Menghubungkan ke MongoDB ({DB_NAME})...")
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=15_000)
    db = client[DB_NAME]
    try:
        await client.admin.command("ping")
        print("   ✅  Terhubung!")
    except Exception as e:
        print(f"❌  Gagal terhubung: {e}")
        sys.exit(1)

    if mode == "replace":
        before = await db["wilayah"].count_documents({})
        await db["wilayah"].delete_many({})
        print(f"\n🗑️   Mode replace: {before:,} record lama dihapus")

    print("\n🔧  Memastikan indexes...")
    try:
        await db["wilayah"].create_index("kode", unique=True)
    except Exception:
        pass
    await db["wilayah"].create_index("tipe")
    await db["wilayah"].create_index([("tipe", 1), ("parent_kode", 1)])
    await db["wilayah"].create_index([("tipe", 1), ("nama", 1)])
    print("   ✅  OK")

    print("\n⬆️   Mengimport data ke MongoDB...")
    all_ins = all_upd = 0
    for records, label in [
        (prov, "Provinsi"),
        (kab,  "Kabupaten"),
        (kec,  "Kecamatan"),
        (desa, "Desa"),
    ]:
        ins, upd = await upsert_batch(db, records, label)
        all_ins += ins
        all_upd += upd

    print(f"\n{'=' * 60}")
    print(f"✅  Import selesai!")
    print(f"   Baru di-insert : {all_ins:,}")
    print(f"   Diperbarui     : {all_upd:,}")

    pipeline = [
        {"$group": {"_id": "$tipe", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    result = await db["wilayah"].aggregate(pipeline).to_list(length=10)
    db_total = sum(r["count"] for r in result)
    print(f"\n📊  Data wilayah di MongoDB ({DB_NAME}):")
    for r in result:
        print(f"   {r['_id']:<12}: {r['count']:>8,}")
    print(f"   {'TOTAL':<12}: {db_total:>8,}")

    client.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Import data wilayah Indonesia ke MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--provinces", default=DEFAULT_PROVINCES)
    p.add_argument("--regencies", default=DEFAULT_REGENCIES)
    p.add_argument("--districts", default=DEFAULT_DISTRICTS)
    p.add_argument("--villages",  default=DEFAULT_VILLAGES)
    p.add_argument("--mode", choices=["upsert", "replace"], default="upsert",
                   help="upsert: tambah/update (default) | replace: hapus semua dulu")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview hasil parse tanpa menulis ke database")
    args = p.parse_args()

    asyncio.run(run(
        args.provinces, args.regencies,
        args.districts, args.villages,
        args.mode, args.dry_run,
    ))