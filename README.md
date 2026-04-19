# 🏘️ Backend API – Pendataan Desa Suka Makmur

Backend REST API untuk Aplikasi Android Pendataan Desa Suka Makmur.
Dibangun dengan **FastAPI** + **MongoDB (Motor async)**.

---

## ⚡ Quickstart

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Konfigurasi `.env`
File `.env` sudah ada dengan koneksi MongoDB Atlas. Edit jika perlu:
```env
MONGODB_URL=mongodb+srv://...
DB_NAME=village_survey_db
SECRET_KEY=ganti-dengan-string-panjang-random
ACCESS_TOKEN_EXPIRE_HOURS=24
```

### 3. Jalankan migrasi (buat indexes)
```bash
python migrate.py
```

### 4. Jalankan seeder (buat data awal: users, surveys, contoh kuesioner)
```bash
python seed.py

# Ingin reset + seed ulang dari awal:
python seed.py --reset
```

### 5. Jalankan server
```bash
python run.py --reload        # development (auto-reload)
python run.py                 # production
```

Server berjalan di: **http://localhost:8000**
Swagger UI: **http://localhost:8000/docs**

---

## 🔑 Akun Default (setelah seed)

| Email | Password | Role |
|---|---|---|
| `superadmin@desasukamakmur.id` | `admin123` | super_admin |
| `admin@desasukamakmur.id` | `admin123` | admin |
| `budi@desasukamakmur.id` | `petugas123` | petugas |
| `siti@desasukamakmur.id` | `petugas123` | petugas |
| `ahmad@desasukamakmur.id` | `petugas123` | petugas |

> ⚠️ Ganti password semua akun setelah deploy ke production!

---

## 📡 Endpoint API

### Auth
| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/api/login` | Login, mengembalikan Bearer token |
| POST | `/api/logout` | Logout (client hapus token) |
| GET | `/api/me` | Info user yang sedang login |

### Surveys
| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/surveys` | Daftar semua survei + jumlah kuesioner |
| POST | `/api/surveys` | Buat survei baru (admin) |
| GET | `/api/surveys/{id}` | Detail survei |
| PUT | `/api/surveys/{id}` | Update survei (admin) |
| DELETE | `/api/surveys/{id}` | Hapus survei + kuesionernya (admin) |

### Questionnaires
| Method | Endpoint | Query Params | Keterangan |
|---|---|---|---|
| GET | `/api/questionnaires` | `dusun`, `survey_id`, `page`, `limit` | Daftar kuesioner |
| POST | `/api/questionnaires` | | Buat kuesioner baru |
| GET | `/api/questionnaires/{id}` | | Detail kuesioner |
| PUT | `/api/questionnaires/{id}` | | Update kuesioner |
| DELETE | `/api/questionnaires/{id}` | | Hapus kuesioner |

### Statistics
| Method | Endpoint | Query Params | Keterangan |
|---|---|---|---|
| GET | `/api/statistics` | `dusun`, `survey_id` | Statistik lengkap desa |

### Users (admin only)
| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/users` | Daftar semua user |
| POST | `/api/users` | Tambah user baru |
| GET | `/api/users/{id}` | Detail user |
| PUT | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Hapus user |

---

## 📦 Response Format

### Login Response
```json
{
  "token": "eyJhbGci...",
  "user": {
    "id": "abc123",
    "name": "Budi Santoso",
    "email": "budi@desasukamakmur.id",
    "roles": [{"name": "petugas"}]
  }
}
```

### Questionnaire Response
```json
{
  "id": "665abc123def",
  "survey_id": "665abc000000",
  "nama_petugas": "Budi Santoso",
  "dusun": "1",
  "r_102": "3371010101240001",
  "r_103": "1",
  "r_200": [
    {
      "r_201": "Hendra Gunawan",
      "r_202": "1271010101800001",
      "r_203": "1",
      "r_205": "1",
      "r_207_usia": 44,
      "r_212": "4",
      "r_300_pekerjaan": "2"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Statistics Response
```json
{
  "total_kk": 150,
  "total_jiwa": 520,
  "total_laki_laki": 260,
  "total_perempuan": 260,
  "per_dusun": {"Dusun I-A": 30, "Dusun I-B": 25, ...},
  "per_petugas": {"Budi Santoso": 45, ...},
  "per_pendidikan": {"SMA/Sederajat": 180, ...},
  "kelompok_usia": {"0-4": 40, "5-14": 85, ...},
  ...
}
```

---

## 🔐 Roles & Hak Akses

| Aksi | super_admin | admin | petugas |
|---|:---:|:---:|:---:|
| Login / Logout | ✅ | ✅ | ✅ |
| Lihat semua kuesioner | ✅ | ✅ | ❌ |
| Lihat kuesioner sendiri | ✅ | ✅ | ✅ |
| Buat kuesioner | ✅ | ✅ | ✅ |
| Edit kuesioner sendiri | ✅ | ✅ | ✅ |
| Edit kuesioner orang lain | ✅ | ✅ | ❌ |
| Lihat statistik | ✅ | ✅ | ✅ |
| Manajemen user | ✅ | ✅ | ❌ |
| Buat/edit/hapus survei | ✅ | ✅ | ❌ |

---

## 🗂️ Struktur Proyek

```
backend/
├── .env                    # Konfigurasi environment
├── requirements.txt
├── migrate.py              # Buat indexes MongoDB
├── seed.py                 # Seed data awal
├── run.py                  # Jalankan server
├── Procfile                # Untuk Railway/Heroku
├── railway.toml            # Konfigurasi Railway deploy
└── app/
    ├── main.py             # FastAPI app + CORS + lifespan
    ├── core/
    │   ├── config.py       # Settings dari .env
    │   ├── database.py     # Koneksi MongoDB (Motor)
    │   ├── security.py     # JWT + bcrypt
    │   ├── deps.py         # FastAPI dependencies (auth)
    │   └── utils.py        # serialize_doc (ObjectId → str)
    ├── schemas/
    │   └── __init__.py     # Pydantic request/response schemas
    └── routers/
        ├── auth.py         # POST /api/login, logout, me
        ├── surveys.py      # CRUD /api/surveys
        ├── questionnaires.py # CRUD /api/questionnaires
        ├── statistics.py   # GET /api/statistics
        └── users.py        # CRUD /api/users
```

---

## 🚀 Deploy ke Railway

1. Push ke GitHub
2. Buat project baru di [Railway](https://railway.app)
3. Connect repo
4. Tambah environment variables dari `.env` ke Railway Variables
5. Railway otomatis detect `Procfile` dan deploy

Setelah deploy, update `apiBaseUrl` di Flutter:
```dart
// lib/utils/app_theme.dart
static const String apiBaseUrl = 'https://your-app.up.railway.app/api';
```

---

## 🔧 Konfigurasi Flutter

Di file `lib/utils/app_theme.dart` aplikasi Android, pastikan URL backend sudah benar:

```dart
// Lokal (emulator Android)
static const String apiBaseUrl = 'http://10.0.2.2:8000/api';

// Lokal (device fisik, ganti dengan IP LAN)
static const String apiBaseUrl = 'http://192.168.1.x:8000/api';

// Production (Railway/VPS)
static const String apiBaseUrl = 'https://your-app.up.railway.app/api';
```
