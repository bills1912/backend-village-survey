# app/schemas/__init__.py
# ─── Auth Schemas ─────────────────────────────────────────────────────────────
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: dict


# ─── User Schemas ─────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    roles: List[str] = ["petugas"]


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    roles: Optional[List[str]] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    roles: List[str]
    created_at: Optional[datetime] = None


# ─── Survey Schemas ───────────────────────────────────────────────────────────
class SurveyCreate(BaseModel):
    nama_survey: str = Field(..., min_length=3)


class SurveyUpdate(BaseModel):
    nama_survey: Optional[str] = None


# ─── Questionnaire Schemas ────────────────────────────────────────────────────
class AnggotaKeluargaSchema(BaseModel):
    r_201: Optional[str] = None   # Nama
    r_202: Optional[str] = None   # NIK
    r_203: Optional[str] = None   # Status Keluarga
    r_204: Optional[str] = None   # Status Perkawinan
    r_205: Optional[str] = None   # Jenis Kelamin (1=L, 2=P)
    r_206: Optional[str] = None   # Tempat Lahir
    r_207: Optional[str] = None   # Tanggal Lahir
    r_207_usia: Optional[int] = None
    r_208: Optional[str] = None   # Suku
    r_209: Optional[str] = None   # Kewarganegaraan
    r_210: Optional[str] = None   # Keberadaan
    r_211: Optional[List[str]] = None   # Disabilitas
    r_212: Optional[str] = None   # Pendidikan Terakhir
    r_300_pekerjaan: Optional[str] = None

    model_config = {"extra": "allow"}


class QuestionnaireCreate(BaseModel):
    survey_id: Optional[Any] = None
    nama_petugas: str
    kelompok_dasa_wisma: Optional[str] = None
    lokasi_rumah: Optional[dict] = None
    waktu_pendataan: Optional[str] = None
    dusun: str
    r_102: str                              # No. KK
    r_103: Optional[str] = None            # Status KK
    r_104: Optional[str] = None
    r_200: List[AnggotaKeluargaSchema] = []
    r_401: Optional[str] = None

    model_config = {"extra": "allow"}


class QuestionnaireUpdate(QuestionnaireCreate):
    pass
