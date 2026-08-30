# Memakai dari proyek sendiri

Paket ini bisa dipakai dua arah, dan keduanya benar tanpa disetel apa pun:

- **berdiri sendiri** — repositori ini di-clone lalu dijalankan lewat `./siakad`
- **sebagai paket** — proyek Anda memasangnya lalu mengimpor `siakad_mcp`

## Menjalankan

**1. Pasang.** Butuh Python 3.10+ dan Chrome/Chromium untuk mencetak PDF.

```bash
pip install siakad-mcp                # pustaka saja
pip install "siakad-mcp[api]"         # + REST API (FastAPI)
pip install "siakad-mcp[mcp]"         # + MCP server
pip install "siakad-mcp[api,mcp]"     # keduanya
```

Extras sengaja dipisah: proyek yang cuma butuh `KlienSiakad` tidak ikut memasang
FastAPI maupun paket `mcp`. `import siakad_mcp` tetap jalan tanpa keduanya.

**2. Pastikan terpasang.**

```bash
python -c "import siakad_mcp; print(siakad_mcp.__version__)"
```

**3. Program pertama.**

```python
from siakad_mcp import KlienSiakad, BeritaAcaraKuliah

klien = KlienSiakad("dosen@kampus.ac.id", "sandi").login()
laporan = BeritaAcaraKuliah(klien)

for kelas in laporan.daftar_kelas("2025", "2"):
    print(kelas.label)
    laporan.unduh_bukti(kelas, "bap", "keluaran/", dir_tanda_tangan="ttd/")
```

Kredensial boleh dikosongkan kalau sudah ada di `.env` atau diberikan lewat
`atur_setelan()` — lihat bagian berikutnya.

Contoh utuh yang bisa dijalankan: [../examples/pustaka.py](../examples/pustaka.py).

Yang diekspor: `KlienSiakad`, `MenuSiakad`, `BeritaAcaraKuliah`, `Kelas`,
`JadwalMengajar`, `SlotJadwal`, `DaftarHadir`, `Pertemuan`, `Mahasiswa`,
`JENIS_BUKTI`, `sisipkan_tanda_tangan`, `cari_tanda_tangan`, `cetak_html_ke_pdf`,
fungsi setelan, dan kelas kesalahan `SiakadError`, `KonfigurasiError`, `CetakError`.

### Tiga menu SIAKAD

Semuanya berangkat dari satu `KlienSiakad` dan berbagi dasar `MenuSiakad`
(token CSRF, pengiriman, penelusuran halaman hasil):

```python
from siakad_mcp import KlienSiakad, JadwalMengajar, DaftarHadir

klien = KlienSiakad().login()

for slot in JadwalMengajar(klien).daftar("2026", "1"):
    print(slot.waktu, slot.ruang, slot.label, slot.sks)

hadir = DaftarHadir(klien)
pertemuan, mahasiswa = hadir.mahasiswa_kelas("2026", "1", "IF31613")
print(pertemuan.label, len(mahasiswa), "mahasiswa")
```

`DaftarHadir.detail(pertemuan)` mengembalikan balasan SIAKAD apa adanya kalau
yang dibutuhkan lebih dari `nim`/`nama`/`kelas`/`status` yang dipetakan
`Mahasiswa` — data pribadi tidak ikut mengalir kecuali memang diambil sendiri.

### Menulis: `simpan_pembahasan`

Satu-satunya operasi tulis di paket ini. `uji_coba=True` mengembalikan muatannya
tanpa mengirim, dan isian lama tertimpa tanpa riwayat:

```python
hasil = hadir.simpan_pembahasan(
    pertemuan, "Session-01: Pengantar", "Membahas kontrak kuliah", uji_coba=True
)
print(hasil["muatan"])
```

### Ekspor .xlsx

```python
from siakad_mcp.ekspor import tulis_xlsx     # butuh: pip install "siakad-mcp[excel]"

tulis_xlsx(["NIM", "Nama"], [[m.nim, m.nama] for m in mahasiswa], "peserta.xlsx")
```

### Kesalahan

Pustaka tidak pernah memanggil `sys.exit`. Semua kegagalan berupa exception biasa
sehingga aplikasi Anda yang memutuskan apa yang terjadi berikutnya:

```python
from siakad_mcp import SiakadError, KonfigurasiError, CetakError

try:
    laporan.unduh_bukti(kelas, "bap", "keluaran/")
except CetakError as galat:          # Chrome tidak ada, hasil cetak kosong
    ...
except (SiakadError, KonfigurasiError) as galat:
    ...
```

## Setelan tanpa berkas

Proyek yang menyimpan konfigurasinya sendiri tidak perlu menyediakan `.env`
maupun `siakad.yaml`:

```python
from siakad_mcp import atur_setelan

atur_setelan(
    base_url="https://siakad.kampuslain.ac.id",
    kota="Bandung",
    SIAKAD_USERNAME="dosen@kampuslain.ac.id",   # kedua gaya nama diterima
    SIAKAD_PASSWORD="sandi",
)
```

`atur_setelan()` adalah kepastian tertinggi — mengalahkan environment, `.env`,
dan `siakad.yaml` — supaya nilai yang Anda tetapkan dari kode tidak berubah
diam-diam karena setelan mesin. Daftar kuncinya di [SETELAN.md](SETELAN.md).

### Akar proyek

Akar proyek menentukan letak `.env`, `siakad.yaml`, `digital_signs/`, dan
`data/`. Kalau tidak ditentukan:

- dijalankan dari checkout repositori ini → direktori repositori itu
- terpasang sebagai paket → direktori kerja proyek Anda

Direktori di atasnya tidak pernah ikut ditelusuri, dan site-packages tidak pernah
dipakai sebagai akar. Untuk menentukan sendiri:

```python
from siakad_mcp import atur_akar_proyek
atur_akar_proyek("/path/ke/data-kampus")
```

## REST API

Rute dikumpulkan di `router`, jadi bisa ditempel ke aplikasi FastAPI Anda:

```python
from fastapi import FastAPI
from siakad_mcp.api import router

app = FastAPI(title="Aplikasi Saya")
app.include_router(router, prefix="/siakad")
```

Hasilnya `/siakad/kelas`, `/siakad/berita-acara`, `/siakad/bukti/pdf`, dan
seterusnya, berdampingan dengan rute Anda sendiri. Kalau yang dibutuhkan aplikasi
yang berdiri sendiri, pakai `siakad_mcp.api:app` atau `buat_app()`.

Daftar endpoint dan badan permintaannya di [API.md](API.md).

## MCP

```bash
claude mcp add siakad-mcp -- siakad-mcp
```

Perintah `siakad-mcp` terpasang bersama paketnya, jadi tidak perlu menunjuk path
ke berkas mana pun. Untuk menjalankannya dari kode Anda sendiri:

```python
from siakad_mcp.mcp_server import server
server.run()
```

Daftar tool-nya di [MCP.md](MCP.md).

## Perintah baris perintah

Ikut terpasang bersama paketnya:

| Perintah            | Sama dengan           |
|---------------------|-----------------------|
| `siakad-bap`        | `./siakad bap`        |
| `siakad-jadwal`     | `./siakad jadwal`     |
| `siakad-hadir`      | `./siakad hadir`      |
| `siakad-mahasiswa`  | `./siakad mahasiswa`  |
| `siakad-pembahasan` | `./siakad pembahasan` |
| `siakad-mcp`        | `./siakad mcp`        |
| `siakad-petakan`    | `./siakad petakan`    |
