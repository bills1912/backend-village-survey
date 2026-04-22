# app/routers/statistics.py
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from ..core.database import get_db
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/statistics", tags=["Statistics"])

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
    # ── Filter hierarki wilayah (semua opsional, tapi biasanya diisi bertingkat) ──
    kode_provinsi:  str | None = Query(None, description="Filter by kode provinsi"),
    kode_kabupaten: str | None = Query(None, description="Filter by kode kabupaten/kota"),
    kode_kecamatan: str | None = Query(None, description="Filter by kode kecamatan"),
    kode_desa:      str | None = Query(None, description="Filter by kode desa (paling spesifik)"),
    # ── Sub-filter dusun (teks, opsional) ──────────────────────────────────────
    dusun:          str | None = Query(None, description="Filter by nama dusun (partial match)"),
    # ── Filter survey ──────────────────────────────────────────────────────────
    survey_id:      str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Statistik kuesioner dengan filter hierarki wilayah bertingkat.

    Urutan filter yang direkomendasikan (dari luar ke dalam):
      kode_provinsi → kode_kabupaten → kode_kecamatan → kode_desa

    Filter lebih spesifik (dalam) otomatis mengabaikan filter lebih luar.
    Contoh: jika kode_desa diisi, kode_provinsi/kab/kec diabaikan oleh MongoDB
    karena index kode_desa sudah cukup.
    """
    filt: dict = {}

    # Gunakan filter paling spesifik yang tersedia
    if kode_desa:
        filt["kode_desa"] = kode_desa
    elif kode_kecamatan:
        filt["kode_kecamatan"] = kode_kecamatan
    elif kode_kabupaten:
        filt["kode_kabupaten"] = kode_kabupaten
    elif kode_provinsi:
        filt["kode_provinsi"] = kode_provinsi

    if dusun:
        filt["dusun"] = {"$regex": dusun, "$options": "i"}

    if survey_id:
        try:
            filt["survey_id"] = ObjectId(survey_id)
        except Exception:
            pass

    docs = await db["questionnaires"].find(filt).to_list(length=100_000)

    # ── Aggregasi ──────────────────────────────────────────────────────────────
    total_kk = len(docs)
    total_jiwa = 0
    total_laki = 0
    total_perempuan = 0

    # Distribusi wilayah
    per_provinsi:  dict[str, int] = {}
    per_kabupaten: dict[str, int] = {}
    per_kecamatan: dict[str, int] = {}
    per_desa:      dict[str, int] = {}
    per_dusun:     dict[str, int] = {}

    per_petugas:          dict[str, int] = {}
    per_status_kk:        dict[str, int] = {}
    per_pendidikan:       dict[str, int] = {}
    per_pekerjaan:        dict[str, int] = {}
    per_status_kawin:     dict[str, int] = {}
    per_kewarganegaraan:  dict[str, int] = {}
    per_keberadaan:       dict[str, int] = {}
    per_disabilitas:      dict[str, int] = {}
    kelompok_usia:        dict[str, int] = {}

    for q in docs:
        # Wilayah
        def _inc(d: dict, key: str | None):
            if key:
                d[key] = d.get(key, 0) + 1

        _inc(per_provinsi,  q.get("nama_provinsi"))
        _inc(per_kabupaten, q.get("nama_kabupaten"))
        _inc(per_kecamatan, q.get("nama_kecamatan"))
        _inc(per_desa,      q.get("nama_desa"))
        _inc(per_dusun,     q.get("dusun"))

        # Petugas & status KK
        _inc(per_petugas,   q.get("nama_petugas"))
        _inc(per_status_kk, q.get("r_103"))

        for a in q.get("r_200", []):
            total_jiwa += 1
            jk = a.get("r_205")
            if jk == "1": total_laki += 1
            elif jk == "2": total_perempuan += 1

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
                    else "Sudah Bekerja"  if pkj == "2"
                    else "Tidak Bekerja"
                )
                per_pekerjaan[pkj_label] = per_pekerjaan.get(pkj_label, 0) + 1

            # Status kawin
            kawin_map = {"1": "Kawin", "2": "Belum Kawin", "3": "Cerai Hidup", "4": "Cerai Mati"}
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
            kb_map = {"1": "Berdomisili", "2": "Sudah Pindah", "3": "KK Baru", "4": "Meninggal"}
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
                dl = disab_map.get(code, code)
                per_disabilitas[dl] = per_disabilitas.get(dl, 0) + 1

            # Kelompok usia
            usia = a.get("r_207_usia")
            if usia is not None:
                try:
                    u = int(usia)
                    bucket = (
                        "0-4"   if u <  5 else
                        "5-14"  if u < 15 else
                        "15-24" if u < 25 else
                        "25-39" if u < 40 else
                        "40-59" if u < 60 else
                        "60+"
                    )
                    kelompok_usia[bucket] = kelompok_usia.get(bucket, 0) + 1
                except (ValueError, TypeError):
                    pass

    return {
        # Ringkasan
        "total_kk":        total_kk,
        "total_jiwa":      total_jiwa,
        "total_laki_laki": total_laki,
        "total_perempuan": total_perempuan,

        # Distribusi wilayah bertingkat
        "per_provinsi":    per_provinsi,
        "per_kabupaten":   per_kabupaten,
        "per_kecamatan":   per_kecamatan,
        "per_desa":        per_desa,
        "per_dusun":       per_dusun,

        # Lainnya
        "per_petugas":         per_petugas,
        "per_status_kk":       per_status_kk,
        "per_pendidikan":      per_pendidikan,
        "per_pekerjaan":       per_pekerjaan,
        "per_status_kawin":    per_status_kawin,
        "per_kewarganegaraan": per_kewarganegaraan,
        "per_keberadaan":      per_keberadaan,
        "per_disabilitas":     per_disabilitas,
        "kelompok_usia":       kelompok_usia,
    }