# app/routers/permissions.py
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from ..core.database import get_db
from ..core.deps import get_current_user, require_admin
from ..core.utils import serialize_doc

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])

# Default permissions per role — dipakai sebagai fallback
DEFAULT_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": [
        "dashboard", "questionnaire_view", "questionnaire_create",
        "questionnaire_edit", "questionnaire_delete", "reports",
        "reports_export", "user_view", "user_create", "user_edit",
        "feature_management", "sync_manage", "offline_mode", "gps_location",
    ],
    "admin": [
        "dashboard", "questionnaire_view", "questionnaire_create",
        "questionnaire_edit", "reports", "reports_export",
        "user_view", "user_create", "user_edit",
        "sync_manage", "offline_mode", "gps_location",
    ],
    "petugas": [
        "dashboard", "questionnaire_view", "questionnaire_create",
        "questionnaire_edit", "reports", "offline_mode", "gps_location",
    ],
}


@router.get("/my")
async def get_my_permissions(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Endpoint yang dipanggil mobile saat login.
    Urutan lookup:
      1. user-level override (collection permissions, type=user)
      2. role-level override (collection permissions, type=role)
      3. DEFAULT_PERMISSIONS hardcoded
    """
    user_id = str(current_user["_id"])
    roles = current_user.get("roles", [])

    # 1. Cek user-level override
    user_perm = await db["permissions"].find_one({
        "type": "user",
        "target_id": user_id,
    })
    if user_perm:
        return {"user_id": user_id, "permissions": user_perm["features"], "source": "user"}

    # 2. Ambil role utama (prioritas: super_admin > admin > petugas)
    primary_role = (
        "super_admin" if "super_admin" in roles
        else "admin" if "admin" in roles
        else "petugas"
    )

    role_perm = await db["permissions"].find_one({
        "type": "role",
        "target_id": primary_role,
    })
    if role_perm:
        return {"user_id": user_id, "permissions": role_perm["features"], "source": "role"}

    # 3. Fallback ke default
    return {
        "user_id": user_id,
        "permissions": DEFAULT_PERMISSIONS.get(primary_role, DEFAULT_PERMISSIONS["petugas"]),
        "source": "default",
    }


@router.get("/roles")
async def get_role_permissions(
    _: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Ambil semua role-level permissions (untuk ditampilkan di web admin)."""
    docs = await db["permissions"].find({"type": "role"}).to_list(length=10)
    result = {d["target_id"]: d["features"] for d in docs}

    # Isi default untuk role yang belum ada di DB
    for role, features in DEFAULT_PERMISSIONS.items():
        if role not in result:
            result[role] = features

    return result


@router.put("/roles/{role}")
async def set_role_permissions(
    role: str,
    body: dict,
    _: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Simpan/update permissions untuk sebuah role."""
    valid_roles = {"super_admin", "admin", "petugas"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Role tidak valid")

    features = body.get("features", [])
    if not isinstance(features, list):
        raise HTTPException(status_code=400, detail="'features' harus berupa list")

    await db["permissions"].update_one(
        {"type": "role", "target_id": role},
        {"$set": {
            "type": "role",
            "target_id": role,
            "features": features,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return {"role": role, "features": features}


@router.get("/users/{user_id}")
async def get_user_permissions(
    user_id: str,
    _: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Ambil user-level permission override (jika ada)."""
    doc = await db["permissions"].find_one({"type": "user", "target_id": user_id})
    if not doc:
        return {"user_id": user_id, "features": None, "customized": False}
    return {"user_id": user_id, "features": doc["features"], "customized": True}


@router.put("/users/{user_id}")
async def set_user_permissions(
    user_id: str,
    body: dict,
    _: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Simpan user-level permission override."""
    features = body.get("features", [])
    if not isinstance(features, list):
        raise HTTPException(status_code=400, detail="'features' harus berupa list")

    await db["permissions"].update_one(
        {"type": "user", "target_id": user_id},
        {"$set": {
            "type": "user",
            "target_id": user_id,
            "features": features,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return {"user_id": user_id, "features": features}


@router.delete("/users/{user_id}")
async def delete_user_permissions(
    user_id: str,
    _: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Hapus user-level override → kembali ke default role."""
    await db["permissions"].delete_one({"type": "user", "target_id": user_id})
    return {"user_id": user_id, "message": "Override dihapus, kembali ke role default"}