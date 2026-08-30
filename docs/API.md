# Referensi REST API SIAKAD

## Menjalankan

**1. Pasang.** Butuh Python 3.10+ dan Chrome/Chromium untuk mencetak PDF.

```bash
pip install "siakad-mcp[api]"
```

**2. Hidupkan servernya.**

```bash
uvicorn siakad_mcp.api:app --port 8000     # setelah pip install
./siakad api                               # dari klona; PORT=9001 untuk ganti port
```

**3. Pastikan hidup.**

```bash
curl -s localhost:8000/openapi.json | head -c 80
```

Dokumentasi interaktif di <http://localhost:8000/docs>, skema mesin di
`/openapi.json`.

**4. Permintaan pertama.**

```bash
curl -X POST localhost:8000/kelas -H 'Content-Type: application/json' \
  -d '{"username":"...","password":"...","tahun_ajaran":"2025","tipe_semester":"2"}'
```

Contoh lengkap yang bisa dijalankan: [../examples/klien_api.sh](../examples/klien_api.sh).

### Menempel ke aplikasi FastAPI sendiri

Rute dikumpulkan di `router`, jadi tidak harus dijalankan sebagai server
terpisah:

```python
from fastapi import FastAPI
from siakad_mcp.api import router

app = FastAPI()
app.include_router(router, prefix="/siakad")
```

Contoh utuh: [../examples/api_sendiri.py](../examples/api_sendiri.py).

## Kredensial

Setiap permintaan membawa `username` dan `password` SIAKAD. Sesi login disimpan
di memori server selama 15 menit lalu dipakai ulang.

## Alur yang disarankan

1. `POST /kelas` atau `POST /jadwal` — lihat kelas yang diampu pada satu periode
2. `POST /berita-acara` — periksa isi topik dan rekap kehadirannya
3. `POST /bukti/semua` — hasilkan seluruh PDF sekaligus

Untuk keperluan lain: `POST /pertemuan` (tatap muka per tanggal),
`POST /mahasiswa` (peserta kuliah), dan `POST /pembahasan` (mengisi BAP).

## Endpoint

### `POST /sesi`

```json
{ "username": "...", "password": "..." }
```

```json
{ "ok": true, "beranda": "https://siakad.pradita.ac.id/dashboard" }
```

Balas `401` kalau kredensialnya ditolak.

### `POST /kelas`

```json
{
  "username": "...", "password": "...",
  "tahun_ajaran": "2025", "tipe_semester": "2",
  "prodi": "", "kode_mk": ""
}
```

```json
{
  "data": [
    {
      "dosen_id": "0000000",
      "kode_mk": "IF30812",
      "nama_mk": "Pemrograman Berorientasi Objek",
      "tahun_ajaran": "2025", "tipe_semester": "2",
      "jam_mulai": "09:20:00.0000000", "hari": "THURSDAY",
      "kelompok_kelas": "Kelas B",
      "label": "IF30812 - Pemrograman Berorientasi Objek (Kelas B)"
    }
  ]
}
```

`tahun_ajaran` `"2025"` berarti tahun ajaran 2025/2026. `tipe_semester`: `1`
ganjil, `2` genap, `3` semester pendek. `prodi` kosong berarti semua prodi.

### `POST /berita-acara`

Badan sama seperti `/kelas`; yang dikembalikan detail kelas pertama yang cocok —
gunakan `kode_mk` untuk memastikan kelas yang dimaksud.

```json
{
  "kelas": "IF30812 - Pemrograman Berorientasi Objek (Kelas B)",
  "detail": {
    "rs_info": { "NM_MATA_KULIAH": "...", "list_dosen": [] },
    "rs_topik": [{ "TGL_ABSENSI": "2026-02-05", "TOPIK_PEMBAHASAN": "Session-01: ...", "DESKRIPSI_PEMBAHASAN": "..." }],
    "rs_absensi_mhs": [{ "nim": "0000000000", "nama": "...", "fg_approve": ["1", "1"] }]
  }
}
```

### `POST /jadwal`

Badan sama seperti `/kelas`. Yang dikembalikan jadwal dari menu Jadwal Mengajar,
lengkap dengan ruang, jam selesai, dan SKS:

```json
{
  "data": [
    {
      "kode_mk": "IF31613", "nama_mk": "Arsitektur Perangkat Lunak",
      "hari": "MONDAY", "jam_mulai": "08:25:00.0000000", "jam_selesai": "11:05:00.0000000",
      "ruang": "A306", "sks": "3", "nama_periode": "2026 / 2027 GANJIL",
      "label": "IF31613 - Arsitektur Perangkat Lunak", "waktu": "Senin 08:25-11:05"
    }
  ]
}
```

### `POST /pertemuan`

Badan `/kelas` ditambah `tanggal` (`YYYY-MM-DD`; kosong berarti seluruh periode).
Satu baris berarti satu tatap muka:

```json
{
  "data": [
    {
      "kode_mk": "IF31613", "tanggal": "2026-08-31", "sesi": "1",
      "ruang": "A306", "kelompok_kelas": "Kelas A, Kelas B",
      "waktu": "Senin 08:25-11:05", "sudah_dibuka": false
    }
  ]
}
```

### `POST /mahasiswa`

Badan `/kelas` (dengan `kode_mk` wajib) ditambah `kelompok_kelas`.

```json
{
  "pertemuan": { "kode_mk": "IF31613", "tanggal": "2026-08-31", "...": "..." },
  "jumlah": 51,
  "data": [
    { "nim": "2510101001", "nama": "...", "kelompok_kelas": "", "prodi": "Informatika",
      "status": "A", "hadir": false }
  ]
}
```

Pesertanya diambil dari pertemuan pertama mata kuliah itu. Hanya field di atas
yang dikembalikan; rekam pribadi lain yang ikut dikirim SIAKAD (KTP, alamat,
wali, telepon) sengaja tidak diteruskan.

### `POST /pembahasan`

Satu-satunya endpoint yang **menulis** ke SIAKAD.

```json
{
  "username": "...", "password": "...",
  "tahun_ajaran": "2026", "tipe_semester": "1", "kode_mk": "IF31613",
  "tanggal": "2026-08-31",
  "topik": "Session-01: Peran & konsep arsitektur perangkat lunak",
  "deskripsi": "Mengidentifikasi peran arsitektur PL",
  "kelompok_kelas": "", "uji_coba": true
}
```

```json
{ "ok": true, "pertemuan": "IF31613 - ... — 2026-08-31", "pesan": "Sukses update topik pembahasan" }
```

`uji_coba: true` mengembalikan muatan yang akan dikirim tanpa mengirimnya. Isian
lama tertimpa dan SIAKAD tidak menyimpan riwayatnya, jadi `tanggal` wajib. Balas
`409` kalau lebih dari satu pertemuan cocok — sebutkan `kelompok_kelas`.

### `POST /bukti/pdf`

Badan `/kelas` ditambah:

| Field             | Bawaan  | Keterangan                                      |
|-------------------|---------|--------------------------------------------------|
| `jenis`           | `bap`   | `bap` atau `kehadiran`                            |
| `tujuan`          | `data/bap` | direktori penyimpanan; path relatif dari akar proyek |
| `tanggal`         | kosong  | tanggal pada blok tanda tangan                    |
| `tanda_tangan`    | kosong  | folder berkas tanda tangan; path relatif dari akar proyek |
| `timpa`           | `false` | tulis ulang berkas yang sudah ada                 |
| `bertanda_tangan` | `true`  | bubuhkan paraf dan tanda tangan pejabat           |

Balasannya berkas PDF (`application/pdf`).

### `POST /bukti/halaman`

Sama seperti `/bukti/pdf`, tapi mengembalikan halaman cetak apa adanya (HTML)
tanpa dijadikan PDF. Berguna untuk memeriksa isi sebelum dicetak.

### `POST /bukti/semua`

Menghasilkan BAP dan kehadiran untuk seluruh kelas pada periode itu.

```json
{
  "tujuan": "/path/ke/siakad-mcp/bukti/pengajaran",
  "berkas": ["IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf"],
  "gagal": []
}
```

Berkas yang sudah ada dilewati kecuali `timpa` bernilai `true`, jadi permintaan
ini aman diulang.

## Batas yang sudah diketahui

- Pembuatan PDF memerlukan Chrome/Chromium di mesin yang menjalankan API.
- Satu kelas menghasilkan PDF 250–550 KB; satu periode berisi 8 kelas memakan
  waktu sekitar satu menit karena tiap berkas dicetak terpisah.
- Selain `POST /buka-kelas` dan `POST /pembahasan`, seluruh endpoint hanya
  membaca SIAKAD.
- Ekspor `.xlsx` (dipakai perintah `siakad-mahasiswa --excel`) butuh extra
  `excel`: `pip install "siakad-mcp[excel]"`.
