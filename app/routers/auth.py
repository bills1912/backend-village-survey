# app/routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..core.database import get_db
from ..core.security import verify_password, create_access_token
from ..core.deps import get_current_user
from ..core.utils import serialize_doc
from ..schemas import LoginRequest

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/login")
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db["users"].find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
        )

    token = create_access_token({"sub": str(user["_id"])})

    user_out = serialize_doc(user)
    user_out.pop("password", None)

    # Format roles agar sesuai dengan Flutter model yang ekspek list of {name: ...}
    raw_roles = user_out.get("roles", [])
    user_out["roles"] = [{"name": r} for r in raw_roles]

    return {"token": token, "user": user_out}


@router.post("/logout")
async def logout(_: dict = Depends(get_current_user)):
    # JWT stateless – client cukup hapus token lokal
    return {"message": "Logout berhasil"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user_out = serialize_doc(current_user)
    user_out.pop("password", None)
    user_out["roles"] = [{"name": r} for r in user_out.get("roles", [])]
    return user_out
