# app/routers/wilayah.py
"""
Endpoint wilayah administratif Indonesia.

GET  /api/wilayah/provinsi
GET  /api/wilayah/kabupaten?kode_provinsi=XX
GET  /api/wilayah/kecamatan?kode_kabupaten=XXXX
GET  /api/wilayah/desa?kode_kecamatan=XXXXXXX
GET  /api/wilayah/search?q=...&tipe=desa
GET  /api/wilayah/stats

POST /api/wilayah/import-set   → upload 4 file sekaligus
POST /api/wilayah/import       → upload 1 file CSV/JSON generic
DELETE /api/wilayah/reset      → hapus semua data wilayah
"""
import csv
import json
import io
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne
from ..core.database import get_db
from ..core.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/wilayah", tags=["Wilayah"])


# ─── Cascading GET ────────────────────────────────────────────────────────────

@router.get("/provinsi")
async def list_provinsi(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await db["wilayah"].find(
        {"tipe": "provinsi"}, {"_id": 0}
    ).sort("nama", 1).to_list(length=100)


@router.get("/kabupaten")
async def list_kabupaten(
    kode_provinsi: str = Query(..., description="Kode provinsi (2 digit)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await db["wilayah"].find(
        {"tipe": "kabupaten", "parent_kode": kode_provinsi}, {"_id": 0}
    ).sort("nama", 1).to_list(length=600)


@router.get("/kecamatan")
async def list_kecamatan(
    kode_kabupaten: str = Query(..., description="Kode kabupaten/kota (4 digit)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await db["wilayah"].find(
        {"tipe": "kecamatan", "parent_kode": kode_kabupaten}, {"_id": 0}
    ).sort("nama", 1).to_list(length=1000)


@router.get("/desa")
async def list_desa(
    kode_kecamatan: str = Query(..., description="Kode kecamatan (7 digit)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await db["wilayah"].find(
        {"tipe": "desa", "parent_kode": kode_kecamatan}, {"_id": 0}
    ).sort("nama", 1).to_list(length=2000)


@router.get("/search")
async def search_wilayah(
    q: str = Query(..., min_length=2, description="Nama wilayah"),
    tipe: str = Query("desa", description="desa | kecamatan | kabupaten | provinsi"),
    limit: int = Query(20, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await db["wilayah"].find(
        {"tipe": tipe, "nama": {"$regex": q, "$options": "i"}}, {"_id": 0}
    ).limit(limit).to_list(length=limit)


@router.get("/stats")
async def wilayah_stats(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Jumlah record per tipe wilayah."""
    result = await db["wilayah"].aggregate([
        {"$group": {"_id": "$tipe", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=10)
    return {r["_id"]: r["count"] for r in result}


# ─── Import: 4 file sekaligus ─────────────────────────────────────────────────

@router.post("/import-set")
async def import_set(
    provinces: UploadFile = File(..., description="provinces.csv  — id;name  (delimiter ';')"),
    regencies: UploadFile = File(..., description="regencies.csv  — id,province_id,name  (delimiter ',')"),
    districts: UploadFile = File(..., description="districts.csv  — id;regency_id;name  (delimiter ';')"),
    villages:  UploadFile = File(..., description="villages.csv   — id,district_id,name  (delimiter ',')"),
    mode: str = Query("upsert", description="upsert | replace"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Import data wilayah dari 4 file sekaligus:
    provinces + regencies + districts + villages.

    **mode=upsert** (default): tambah/update, data lama yang tidak ada di file tetap ada.
    **mode=replace**: hapus SEMUA wilayah dulu, lalu import ulang.
    """
    prov_text = (await provinces.read()).decode("utf-8-sig")
    kab_text  = (await regencies.read()).decode("utf-8-sig")
    kec_text  = (await districts.read()).decode("utf-8-sig")
    desa_text = (await villages.read()).decode("utf-8-sig")

    prov_records = _parse_provinces(prov_text)
    kab_records  = _parse_regencies(kab_text)
    kec_records  = _parse_districts(kec_text)
    desa_records = _parse_villages(desa_text)

    all_records = prov_records + kab_records + kec_records + desa_records
    if not all_records:
        raise HTTPException(status_code=422, detail="Tidak ada data valid yang ditemukan")

    deleted = 0
    if mode == "replace":
        result = await db["wilayah"].delete_many({})
        deleted = result.deleted_count

    await _ensure_indexes(db)
    inserted, updated, errors = await _upsert_all(db, all_records)

    return {
        "status": "ok",
        "mode": mode,
        "deleted_before_import": deleted,
        "parsed": {
            "provinsi":  len(prov_records),
            "kabupaten": len(kab_records),
            "kecamatan": len(kec_records),
            "desa":      len(desa_records),
            "total":     len(all_records),
        },
        "inserted": inserted,
        "updated":  updated,
        "errors":   errors[:5],
        "breakdown": await _get_stats(db),
    }


# ─── Import: single file generic ─────────────────────────────────────────────

@router.post("/import")
async def import_single(
    file: UploadFile = File(..., description="File CSV atau JSON wilayah (format apapun)"),
    mode: str = Query("upsert", description="upsert | replace"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    Import wilayah dari satu file CSV/JSON generic.
    Berguna untuk update sebagian (misalnya hanya regencies.csv untuk update nama kabupaten).
    Tipe wilayah diinfer dari panjang kode jika tidak ada kolom tipe.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File diperlukan")

    content = await file.read()
    fn = (file.filename or "").lower()

    if fn.endswith(".csv"):
        records = _parse_generic_csv(content.decode("utf-8-sig"))
    elif fn.endswith(".json"):
        records = _parse_generic_json(content.decode("utf-8"))
    else:
        raise HTTPException(status_code=400, detail="Format harus .csv atau .json")

    if not records:
        raise HTTPException(status_code=422, detail="Tidak ada data valid yang ditemukan")

    deleted = 0
    if mode == "replace":
        result = await db["wilayah"].delete_many({})
        deleted = result.deleted_count

    await _ensure_indexes(db)
    inserted, updated, errors = await _upsert_all(db, records)

    return {
        "status": "ok",
        "file": file.filename,
        "mode": mode,
        "deleted_before_import": deleted,
        "total_parsed": len(records),
        "inserted": inserted,
        "updated":  updated,
        "errors":   errors[:5],
        "breakdown": await _get_stats(db),
    }


@router.delete("/reset")
async def reset_wilayah(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Hapus SEMUA data wilayah. Gunakan sebelum import ulang dari file baru."""
    result = await db["wilayah"].delete_many({})
    return {
        "status": "ok",
        "deleted": result.deleted_count,
        "message": "Semua data wilayah dihapus. Import ulang via POST /api/wilayah/import-set",
    }


# ─── Internal parsers (format spesifik) ──────────────────────────────────────

def _c(s: str) -> str:
    """Clean: strip whitespace dan quotes."""
    return s.strip().strip('"').strip("'").strip()

def _tc(s: str) -> str:
    """Title Case dengan pengecualian kata sambung."""
    exc = {"dan","di","ke","dari","yang","untuk","atau",
           "dengan","oleh","pada","dalam","atas","bawah"}
    words = s.lower().split()
    return " ".join(
        w if (i > 0 and w in exc) else w.capitalize()
        for i, w in enumerate(words)
    )

def _parse_provinces(text: str) -> list[dict]:
    """provinces.csv: delimiter ';', kolom id;name"""
    records = []
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        kode, nama = _c(row.get("id","")), _c(row.get("name",""))
        if kode and nama:
            records.append({"kode": kode, "nama": _tc(nama), "tipe": "provinsi"})
    return records

def _parse_regencies(text: str) -> list[dict]:
    """regencies.csv: delimiter ',', kolom id,province_id,name"""
    records = []
    for row in csv.DictReader(io.StringIO(text), delimiter=","):
        kode   = _c(row.get("id",""))
        nama   = _c(row.get("name",""))
        parent = _c(row.get("province_id","")) or (kode[:2] if len(kode) >= 2 else "")
        if kode and nama:
            records.append({"kode": kode, "nama": _tc(nama), "tipe": "kabupaten", "parent_kode": parent})
    return records

def _parse_districts(text: str) -> list[dict]:
    """districts.csv: delimiter ';', kolom id;regency_id;name"""
    records = []
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        kode   = _c(row.get("id",""))
        nama   = _c(row.get("name",""))
        parent = _c(row.get("regency_id","")) or (kode[:4] if len(kode) >= 4 else "")
        if kode and nama:
            records.append({"kode": kode, "nama": _tc(nama), "tipe": "kecamatan", "parent_kode": parent})
    return records

def _parse_villages(text: str) -> list[dict]:
    """villages.csv: delimiter ',', kolom id,district_id,name"""
    records = []
    for row in csv.DictReader(io.StringIO(text), delimiter=","):
        kode   = _c(row.get("id",""))
        nama   = _c(row.get("name",""))
        parent = _c(row.get("district_id","")) or (kode[:7] if len(kode) >= 7 else "")
        if kode and nama:
            records.append({"kode": kode, "nama": _tc(nama), "tipe": "desa", "parent_kode": parent})
    return records


# ─── Internal parsers (format generic) ───────────────────────────────────────

def _infer_tipe(kode: str) -> str:
    n = len(kode)
    if n == 2: return "provinsi"
    if n == 4: return "kabupaten"
    if n == 6: return "kecamatan"
    return "desa"

def _infer_parent(kode: str, tipe: str) -> str:
    cuts = {"kabupaten": 2, "kecamatan": 4, "desa": 6}
    c = cuts.get(tipe)
    return kode[:c] if (c and len(kode) > c) else ""

def _make_record(kode: str, nama: str, tipe: str, parent: str) -> dict | None:
    kode, nama = kode.strip(), nama.strip()
    tipe = tipe.strip().lower()
    if not kode or not nama: return None
    if not tipe: tipe = _infer_tipe(kode)
    if tipe == "kelurahan": tipe = "desa"
    if not parent and tipe != "provinsi": parent = _infer_parent(kode, tipe)
    rec: dict = {"kode": kode, "nama": _tc(nama), "tipe": tipe}
    if parent: rec["parent_kode"] = parent
    return rec

def _parse_generic_csv(text: str) -> list[dict]:
    sample = text[:1000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    records = []
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    hdrs = {h.strip().lower().replace(" ","_"): h for h in (reader.fieldnames or [])}

    def g(row, *keys):
        for k in keys:
            for hk, orig in hdrs.items():
                if k in hk:
                    v = row.get(orig,"").strip()
                    if v: return v
        return ""

    for row in reader:
        rec = _make_record(
            g(row,"kode","id"),
            g(row,"nama","name"),
            g(row,"tipe","level","type"),
            g(row,"parent_kode","parent_id","province_id","regency_id","district_id","kode_induk"),
        )
        if rec: records.append(rec)
    return records

def _parse_generic_json(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"JSON tidak valid: {e}")
    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="JSON harus berupa array")
    if data and isinstance(data[0], dict) and "children" in data[0]:
        return _flatten_nested(data)
    records = []
    for item in data:
        rec = _make_record(
            str(item.get("kode") or item.get("id") or ""),
            str(item.get("nama") or item.get("name") or ""),
            str(item.get("tipe") or item.get("type") or ""),
            str(item.get("parent_kode") or item.get("parent_id") or ""),
        )
        if rec: records.append(rec)
    return records

def _flatten_nested(data: list, parent_kode: str = "", level: int = 0) -> list[dict]:
    tipe_map = {0:"provinsi", 1:"kabupaten", 2:"kecamatan", 3:"desa"}
    records = []
    for item in data:
        kode = str(item.get("kode") or item.get("id") or "").strip()
        nama = str(item.get("nama") or item.get("name") or "").strip()
        if not kode or not nama: continue
        rec: dict = {"kode": kode, "nama": _tc(nama), "tipe": tipe_map.get(level,"desa")}
        if parent_kode: rec["parent_kode"] = parent_kode
        records.append(rec)
        children = (item.get("children") or item.get("kabupaten") or
                    item.get("kecamatan") or item.get("desa") or [])
        if children:
            records.extend(_flatten_nested(children, kode, level + 1))
    return records


# ─── Shared DB helpers ────────────────────────────────────────────────────────

async def _ensure_indexes(db):
    try:
        await db["wilayah"].create_index("kode", unique=True)
    except Exception:
        pass
    await db["wilayah"].create_index("tipe")
    await db["wilayah"].create_index([("tipe", 1), ("parent_kode", 1)])
    await db["wilayah"].create_index([("tipe", 1), ("nama", 1)])

async def _upsert_all(db, records: list[dict]) -> tuple[int, int, list[str]]:
    BATCH = 500
    ins = upd = 0
    errors: list[str] = []
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        ops = [UpdateOne({"kode": r["kode"]}, {"$set": r}, upsert=True) for r in batch]
        try:
            res = await db["wilayah"].bulk_write(ops, ordered=False)
            ins += res.upserted_count
            upd += res.modified_count
        except Exception as e:
            errors.append(str(e))
    return ins, upd, errors

async def _get_stats(db) -> dict:
    result = await db["wilayah"].aggregate([
        {"$group": {"_id": "$tipe", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(length=10)
    return {r["_id"]: r["count"] for r in result}