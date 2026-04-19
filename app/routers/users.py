# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from ..core.database import get_db
from ..core.security import hash_password
from ..core.deps import get_current_user, require_admin
from ..core.utils import serialize_doc, serialize_list
from ..schemas import UserCreate, UserUpdate

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("")
async def list_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    docs = await db["users"].find().sort("name", 1).to_list(length=200)
    result = serialize_list(docs)
    for u in result:
        u.pop("password", None)
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if await db["users"].find_one({"email": body.email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    # Validasi roles
    valid_roles = {"super_admin", "admin", "petugas"}
    for r in body.roles:
        if r not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Role '{r}' tidak valid")

    doc = {
        "name": body.name,
        "email": body.email,
        "password": hash_password(body.password),
        "roles": body.roles,
    }
    from datetime import datetime, timezone
    doc["created_at"] = datetime.now(timezone.utc)

    res = await db["users"].insert_one(doc)
    doc["_id"] = res.inserted_id
    out = serialize_doc(doc)
    out.pop("password", None)
    return out


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")
    if not doc:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    out = serialize_doc(doc)
    out.pop("password", None)
    return out


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")

    update = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "password" in update:
        update["password"] = hash_password(update["password"])

    if not update:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk diperbarui")

    await db["users"].update_one({"_id": oid}, {"$set": update})
    doc = await db["users"].find_one({"_id": oid})
    out = serialize_doc(doc)
    out.pop("password", None)
    return out


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")
    await db["users"].delete_one({"_id": oid})
