# app/routers/questionnaires.py
from fastapi import APIRouter, HTTPException, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from ..core.database import get_db
from ..core.deps import get_current_user
from ..core.utils import serialize_doc, serialize_list
from ..schemas import QuestionnaireCreate, QuestionnaireUpdate

router = APIRouter(prefix="/api/questionnaires", tags=["Questionnaires"])


def _safe_oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")


def _prep_body(body: QuestionnaireCreate | QuestionnaireUpdate, user: dict) -> dict:
    """Konversi schema ke dokumen MongoDB."""
    doc = body.model_dump()

    # Resolve survey_id ke ObjectId
    sid = doc.get("survey_id")
    if sid:
        try:
            doc["survey_id"] = ObjectId(str(sid))
        except Exception:
            doc["survey_id"] = None

    # Tambah metadata
    doc["nama_petugas"] = doc.get("nama_petugas") or user.get("name", "")
    doc["user_id"] = user["_id"]
    return doc


@router.get("")
async def list_questionnaires(
    dusun: str | None = Query(None),
    survey_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    filt: dict = {}

    # Petugas non-admin hanya bisa lihat data mereka sendiri
    roles = current_user.get("roles", [])
    if "super_admin" not in roles and "admin" not in roles:
        filt["user_id"] = current_user["_id"]

    if dusun:
        filt["dusun"] = dusun
    if survey_id:
        try:
            filt["survey_id"] = ObjectId(survey_id)
        except Exception:
            pass

    skip = (page - 1) * limit
    total = await db["questionnaires"].count_documents(filt)
    docs = (
        await db["questionnaires"]
        .find(filt)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )

    return {
        "data": serialize_list(docs),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_questionnaire(
    body: QuestionnaireCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = _prep_body(body, current_user)
    now = datetime.now(timezone.utc)
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await db["questionnaires"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_doc(doc)


@router.get("/{q_id}")
async def get_questionnaire(
    q_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    oid = _safe_oid(q_id)
    doc = await db["questionnaires"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Kuesioner tidak ditemukan")

    # Cek akses
    roles = current_user.get("roles", [])
    if "super_admin" not in roles and "admin" not in roles:
        if str(doc.get("user_id")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Akses ditolak")

    return serialize_doc(doc)


@router.put("/{q_id}")
async def update_questionnaire(
    q_id: str,
    body: QuestionnaireUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    oid = _safe_oid(q_id)
    existing = await db["questionnaires"].find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Kuesioner tidak ditemukan")

    roles = current_user.get("roles", [])
    if "super_admin" not in roles and "admin" not in roles:
        if str(existing.get("user_id")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Akses ditolak")

    doc = _prep_body(body, current_user)
    doc["updated_at"] = datetime.now(timezone.utc)
    doc.pop("created_at", None)

    await db["questionnaires"].update_one({"_id": oid}, {"$set": doc})
    updated = await db["questionnaires"].find_one({"_id": oid})
    return serialize_doc(updated)


@router.delete("/{q_id}", status_code=status.HTTP_200_OK)
async def delete_questionnaire(
    q_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    oid = _safe_oid(q_id)
    existing = await db["questionnaires"].find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Kuesioner tidak ditemukan")

    roles = current_user.get("roles", [])
    if "super_admin" not in roles and "admin" not in roles:
        if str(existing.get("user_id")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Akses ditolak")

    await db["questionnaires"].delete_one({"_id": oid})
    return {"message": "Kuesioner berhasil dihapus"}
