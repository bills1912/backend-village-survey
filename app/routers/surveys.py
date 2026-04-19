# app/routers/surveys.py
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from ..core.database import get_db
from ..core.deps import get_current_user, require_admin
from ..core.utils import serialize_doc, serialize_list
from ..schemas import SurveyCreate, SurveyUpdate

router = APIRouter(prefix="/api/surveys", tags=["Surveys"])


@router.get("")
async def list_surveys(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    pipeline = [
        {
            "$lookup": {
                "from": "questionnaires",
                "localField": "_id",
                "foreignField": "survey_id",
                "as": "questionnaires",
            }
        },
        {
            "$addFields": {
                "questionnaires_count": {"$size": "$questionnaires"}
            }
        },
        {"$project": {"questionnaires": 0}},
        {"$sort": {"created_at": -1}},
    ]
    docs = await db["surveys"].aggregate(pipeline).to_list(length=100)
    return serialize_list(docs)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_survey(
    body: SurveyCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    doc = {
        "nama_survey": body.nama_survey,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    res = await db["surveys"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_doc(doc)


@router.get("/{survey_id}")
async def get_survey(
    survey_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(survey_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")
    doc = await db["surveys"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Survei tidak ditemukan")
    return serialize_doc(doc)


@router.put("/{survey_id}")
async def update_survey(
    survey_id: str,
    body: SurveyUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(survey_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")

    update = body.model_dump(exclude_none=True)
    update["updated_at"] = datetime.now(timezone.utc)
    await db["surveys"].update_one({"_id": oid}, {"$set": update})
    doc = await db["surveys"].find_one({"_id": oid})
    return serialize_doc(doc)


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(require_admin),
):
    try:
        oid = ObjectId(survey_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID tidak valid")
    await db["surveys"].delete_one({"_id": oid})
    await db["questionnaires"].delete_many({"survey_id": oid})
