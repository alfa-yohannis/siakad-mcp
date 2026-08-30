# SIAKAD MCP

Aplikasi untuk menarik bukti pengajaran dari SIAKAD Pradita
(<https://siakad.pradita.ac.id>): daftar kelas yang diampu, berita acara
perkuliahan, dan daftar kehadiran mahasiswa — lengkap dengan tanda tangan,
siap dilampirkan sebagai bukti BKD.

Pasangannya adalah [sister-mcp](https://github.com/alfa-yohannis/sister-mcp)
yang mengisi data ke SISTER. Keduanya berdiri sendiri: kode, dokumentasi,
contoh, dan pengujiannya terpisah.

Tersedia dalam tiga bentuk, semuanya dari paket yang sama:

| Mode         | Untuk siapa                             | Referensi                          |
|--------------|-----------------------------------------|------------------------------------|
| **MCP**      | asisten AI (Claude Code, dsb.)          | [docs/MCP.md](docs/MCP.md)         |
| **REST API** | aplikasi apa pun lewat HTTP             | [docs/API.md](docs/API.md)         |
| **Pustaka**  | program Python Anda sendiri             | [docs/PUSTAKA.md](docs/PUSTAKA.md) |

Ada juga CLI (`siakad-bap`) untuk pemakaian langsung dari terminal —
lihat [docs/CLI.md](docs/CLI.md).

## Prasyarat

- Python 3.10 atau lebih baru
- Chrome/Chromium terpasang di sistem — dipakai mencetak PDF
  (`google-chrome`, `chromium`, atau `chromium-browser`)
- Akun SIAKAD yang aktif

## Pasang

Ada dua cara, pilih salah satu.

**A. Berdiri sendiri** — klona lalu jalankan; cocok kalau Anda hanya mau
memakai aplikasinya:

```bash
git clone https://github.com/alfa-yohannis/siakad-mcp.git
cd siakad-mcp
./siakad uji          # jalankan pertama menyiapkan .venv + dependensi sendiri
```

**B. Sebagai paket** — kalau aplikasi Anda sendiri yang akan memakainya:

```bash
pip install "siakad-mcp[api,mcp]"   # extras: pasang hanya yang dipakai
pip install siakad-mcp              # pustaka saja, tanpa FastAPI dan mcp
```

## Kredensial

Salin contohnya lalu isi:

```bash
cp .env.contoh .env       # SIAKAD_USERNAME, SIAKAD_PASSWORD
```

`.env` tidak ikut ter-commit. REST API dan MCP juga menerima kredensial per
permintaan, dan program Python bisa memberikannya lewat `atur_setelan()` —
jadi `.env` tidak wajib.

Perguruan tinggi selain Pradita menyalin `siakad.yaml.contoh` menjadi
`siakad.yaml` lalu mengubah alamat instance, kota penanda tangan, dan ukuran
kertasnya — tanpa menyentuh kode. Daftarnya di [docs/SETELAN.md](docs/SETELAN.md).

## Menjalankan

### 1. MCP

```bash
claude mcp add bkd-siakad -- siakad-mcp        # setelah `pip install`
claude mcp add bkd-siakad -- /path/ke/siakad-mcp/siakad mcp   # dari klona
```

Untuk klien MCP lain, isi `mcpServers` dengan `"command": "siakad-mcp"`.
Cek servernya hidup tanpa mendaftarkannya dulu:

```bash
./siakad mcp        # bicara JSON-RPC lewat stdio; Ctrl-C untuk berhenti
```

Lalu minta asisten Anda, misalnya: *"Kelas apa saja yang saya ampu pada semester
genap 2025/2026 menurut SIAKAD?"* Lima tool tersedia — daftar lengkapnya dan
contoh prompt lain di [docs/MCP.md](docs/MCP.md).

### 2. REST API

```bash
./siakad api                  # http://localhost:8000
PORT=9001 ./siakad api        # ganti port
```

Terpasang sebagai paket, jalankan lewat uvicorn:

```bash
uvicorn siakad_mcp.api:app --port 8000
```

Dokumentasi interaktif ada di `/docs`, skema mesin di `/openapi.json`. Coba:

```bash
curl -X POST localhost:8000/kelas -H 'Content-Type: application/json' \
  -d '{"username":"...","password":"...","tahun_ajaran":"2025","tipe_semester":"2"}'
```

Untuk menempelkannya ke aplikasi FastAPI Anda sendiri:

```python
from siakad_mcp.api import router
app.include_router(router, prefix="/siakad")
```

Endpoint selengkapnya di [docs/API.md](docs/API.md).

### 3. Pustaka

```python
from siakad_mcp import KlienSiakad, BeritaAcaraKuliah

klien = KlienSiakad("dosen@kampus.ac.id", "sandi").login()
laporan = BeritaAcaraKuliah(klien)

for kelas in laporan.daftar_kelas("2025", "2"):
    print(kelas.label)
    laporan.unduh_bukti(kelas, "bap", "bukti/pengajaran")
```

Setelan boleh diberikan dari kode, tanpa berkas apa pun:

```python
from siakad_mcp import atur_setelan
atur_setelan(base_url="https://siakad.kampuslain.ac.id", kota="Bandung")
```

Selengkapnya di [docs/PUSTAKA.md](docs/PUSTAKA.md).

### CLI

```bash
./siakad bap --tahun 2025 --semester 2 --hanya-daftar         # lihat kelasnya dulu
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran
```

Terpasang sebagai paket, perintahnya `siakad-bap` dengan argumen yang sama.
Hasilnya dua PDF per kelas:

```
IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf
IF30812 - Pemrograman Berorientasi Objek - Kelas B - Kehadiran.pdf
```

Berkas yang sudah ada dilewati, jadi perintahnya aman diulang. Argumen
selengkapnya di [docs/CLI.md](docs/CLI.md).

## Akar proyek

Menentukan letak `.env`, `siakad.yaml`, `digital_signs/`, dan `data/`, serta titik
hitung path relatif:

- dijalankan dari klona repositori ini → direktori repositori itu sendiri
- dipasang sebagai paket → direktori kerja proyek pemakai

Direktori di atasnya tidak pernah ikut ditelusuri, jadi hasilnya tidak berubah
hanya karena aplikasi dipindah. Untuk menentukan sendiri, setel
`SIAKAD_AKAR_PROYEK` atau panggil `atur_akar_proyek()`.

## Tanda tangan

Berkas tanda tangan bernama `<nama>.png`, mis. `kong.png` dan `spider.png`.
Foldernya ditentukan pemanggil:

| Mode     | Cara                                        |
|----------|---------------------------------------------|
| MCP      | parameter `tanda_tangan`                    |
| REST API | field `tanda_tangan`                        |
| Pustaka  | `sisipkan_tanda_tangan(..., direktori=...)` |
| CLI      | `--tanda-tangan <dir>`                      |

Kalau tidak diberikan: `BKD_TANDA_TANGAN`, lalu `digital_signs/` di akar proyek.
Path relatif dihitung dari akar proyek, sama seperti `--tujuan`. Folder
`digital_signs/` masuk `.gitignore` karena isinya data pribadi.

Pada halaman BAP:

- **kolom Paraf** diisi tanda tangan dosen pengampu untuk setiap pertemuan
- **blok kanan bawah** diisi tanda tangan pejabat penanda tangan, di atas namanya

Pemilihannya otomatis: nama pejabat dibaca dari halaman itu sendiri, lalu dicari
berkas yang nama filenya muncul pada nama tersebut. Jadi kalau Kaprodi berganti,
cukup tambahkan berkas PNG baru — tidak ada kode yang perlu diubah. Prodi yang
belum punya berkas tanda tangan tetap dicetak, hanya blok tanda tangannya kosong.

Gambar dipangkas otomatis dari bidang kosong di sekelilingnya, dan hanya
tingginya yang diatur agar rasio aslinya terjaga.

## Rancangan

```
pyproject.toml              metadata paket, dependensi, dan perintah terpasang
siakad                      launcher untuk pemakaian berdiri sendiri
siakad_mcp/__init__.py      API publik paket ini
siakad_mcp/siakad_client.py KlienSiakad: login, ambil halaman, baca/kirim form
siakad_mcp/berita_acara.py  BeritaAcaraKuliah + Kelas: daftar kelas, detail, unduh bukti
siakad_mcp/tanda_tangan.py  pembubuhan paraf & tanda tangan ke halaman cetak
siakad_mcp/cetak_pdf.py     halaman cetak -> PDF lewat Chrome headless
siakad_mcp/konfigurasi.py   akar proyek, setelan, kredensial
siakad_mcp/cli.py           CLI (perintah siakad-bap)
siakad_mcp/api.py           REST API: router yang bisa ditempel + app siap pakai
siakad_mcp/mcp_server.py    MCP server (perintah siakad-mcp)
siakad_mcp/petakan_form.py  alat bantu memetakan halaman saat menambah kemampuan
```

## Catatan perilaku SIAKAD

- **Login satu langkah.** `GET /login` untuk mengambil `_token`, lalu
  `POST /login_process`. Jauh lebih sederhana dari SSO SISTER.
- **Isi tabel datang lewat AJAX.** Halaman laporan dikirim kosong; datanya dari
  `POST /report/berita_acara_kuliah/search`.
- **`sort_search` dan `order_search` harus tidak dikirim.** Kalau ikut terkirim
  dalam keadaan kosong, server membalas HTTP 500 tanpa penjelasan. Di browser
  keduanya bernilai `undefined` sehingga jQuery memang tidak mengirimkannya.
- **Ekspor PDF sebenarnya HTML.** `export_pdf_topik_pembahasan` dan
  `export_pdf_absensi_mahasiswa` mengembalikan halaman siap cetak, bukan PDF —
  di browser pemakai menekan Ctrl+P. Chrome headless yang menggantikan langkah itu.
- **Ukuran kertas tidak ditentukan halamannya.** Hanya margin yang diatur, jadi
  ukurannya disisipkan sendiri: A3 untuk BAP, A4 untuk daftar kehadiran.
- **Penanda tangan berbeda per prodi.** Informatika ditandatangani Kaprodi
  Informatika, Teknologi Informasi oleh Kaprodi TI — halaman cetaknya sendiri
  yang menentukan.

## Menambah kemampuan baru

```bash
./siakad petakan /dosen/kepanitiaan --semua-opsi
```

Perintah itu mencetak seluruh form, field, dan endpoint AJAX sebuah halaman ke
`data/form_<path>.json` — pijakan sebelum menulis modul baru.

## Pengujian

```bash
./siakad uji
```

35 unit test, semuanya berjalan tanpa jaringan dan tanpa kredensial. Nama tokoh
dan nomor induk pada berkas uji dan dokumentasi seluruhnya dikarang.
