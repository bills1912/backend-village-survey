# app/routers/statistics.py
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from ..core.database import get_db
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/statistics", tags=["Statistics"])

DUSUN_LABELS = {
    "1": "Dusun I-A",
    "2": "Dusun I-B",
    "3": "Dusun II Timur",
    "4": "Dusun II Barat",
    "5": "Dusun III",
    "6": "Dusun IV",
}

PDK_LABELS = {
    "1": "Tidak Sekolah/Belum Tamat SD",
    "2": "SD/Sederajat",
    "3": "SMP/Sederajat",
    "4": "SMA/Sederajat",
    "5": "D1/D2/D3",
    "6": "S1/S2/S3",
}


@router.get("")
async def get_statistics(
    dusun: str | None = Query(None),
    survey_id: str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    filt: dict = {}
    if dusun:
        filt["dusun"] = dusun
    if survey_id:
        try:
            filt["survey_id"] = ObjectId(survey_id)
        except Exception:
            pass

    # Ambil semua kuesioner yang sesuai filter
    docs = await db["questionnaires"].find(filt).to_list(length=10000)

    # ── Hitung semua metrik ──────────────────────────────────────────────────
    total_kk = len(docs)
    total_jiwa = 0
    total_laki = 0
    total_perempuan = 0

    per_dusun: dict[str, int] = {}
    per_petugas: dict[str, int] = {}
    per_status_kk: dict[str, int] = {}
    per_pendidikan: dict[str, int] = {}
    per_pekerjaan: dict[str, int] = {}
    per_status_kawin: dict[str, int] = {}
    per_kewarganegaraan: dict[str, int] = {}
    per_keberadaan: dict[str, int] = {}
    per_disabilitas: dict[str, int] = {}
    kelompok_usia: dict[str, int] = {}

    for q in docs:
        # Dusun
        dl = DUSUN_LABELS.get(q.get("dusun", ""), f"Dusun {q.get('dusun', '?')}")
        per_dusun[dl] = per_dusun.get(dl, 0) + 1

        # Petugas
        petugas = q.get("nama_petugas", "Tidak Diketahui")
        per_petugas[petugas] = per_petugas.get(petugas, 0) + 1

        # Status KK
        sk = q.get("r_103")
        if sk:
            per_status_kk[sk] = per_status_kk.get(sk, 0) + 1

        # Anggota keluarga
        for a in q.get("r_200", []):
            total_jiwa += 1
            jk = a.get("r_205")
            if jk == "1":
                total_laki += 1
            elif jk == "2":
                total_perempuan += 1

            # Pendidikan
            pdk = a.get("r_212")
            if pdk:
                label = PDK_LABELS.get(pdk, pdk)
                per_pendidikan[label] = per_pendidikan.get(label, 0) + 1

            # Pekerjaan
            pkj = a.get("r_300_pekerjaan")
            if pkj:
                pkj_label = (
                    "Masih Bersekolah" if pkj == "1"
                    else "Sudah Bekerja" if pkj == "2"
                    else "Tidak Bekerja"
                )
                per_pekerjaan[pkj_label] = per_pekerjaan.get(pkj_label, 0) + 1

            # Status kawin
            kawin_map = {"1": "Kawin", "2": "Belum Kawin",
                         "3": "Cerai Hidup", "4": "Cerai Mati"}
            kw = a.get("r_204")
            if kw:
                kl = kawin_map.get(kw, kw)
                per_status_kawin[kl] = per_status_kawin.get(kl, 0) + 1

            # Kewarganegaraan
            wn = a.get("r_209")
            if wn:
                wl = "WNI" if wn == "1" else "WNA"
                per_kewarganegaraan[wl] = per_kewarganegaraan.get(wl, 0) + 1

            # Keberadaan
            kb_map = {"1": "Berdomisili", "2": "Sudah Pindah",
                      "3": "KK Baru", "4": "Meninggal"}
            kb = a.get("r_210")
            if kb:
                kbl = kb_map.get(kb, kb)
                per_keberadaan[kbl] = per_keberadaan.get(kbl, 0) + 1

            # Disabilitas
            disab_map = {
                "1": "Penglihatan", "2": "Pendengaran",
                "3": "Berjalan/Naik Tangga", "4": "Tangan/Jari",
                "5": "Mengingat/Konsentrasi", "6": "Merawat Diri",
                "7": "Komunikasi", "8": "Perilaku/Emosi",
            }
            for code in (a.get("r_211") or []):
                dl2 = disab_map.get(code, code)
                per_disabilitas[dl2] = per_disabilitas.get(dl2, 0) + 1

            # Kelompok usia
            usia = a.get("r_207_usia")
            if usia is not None:
                try:
                    u = int(usia)
                    if u < 5:        bucket = "0-4"
                    elif u < 15:     bucket = "5-14"
                    elif u < 25:     bucket = "15-24"
                    elif u < 40:     bucket = "25-39"
                    elif u < 60:     bucket = "40-59"
                    else:            bucket = "60+"
                    kelompok_usia[bucket] = kelompok_usia.get(bucket, 0) + 1
                except (ValueError, TypeError):
                    pass

    return {
        "total_kk": total_kk,
        "total_jiwa": total_jiwa,
        "total_laki_laki": total_laki,
        "total_perempuan": total_perempuan,
        "per_dusun": per_dusun,
        "per_petugas": per_petugas,
        "per_status_kk": per_status_kk,
        "per_pendidikan": per_pendidikan,
        "per_pekerjaan": per_pekerjaan,
        "per_status_kawin": per_status_kawin,
        "per_kewarganegaraan": per_kewarganegaraan,
        "per_keberadaan": per_keberadaan,
        "per_disabilitas": per_disabilitas,
        "kelompok_usia": kelompok_usia,
    }
