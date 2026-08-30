# Referensi CLI SIAKAD

## Menjalankan

**1. Pasang.** Butuh Python 3.10+ dan Chrome/Chromium untuk mencetak PDF.

```bash
git clone https://github.com/alfa-yohannis/siakad-mcp.git
cd siakad-mcp
./siakad uji            # jalankan pertama menyiapkan .venv + dependensi
```

Terpasang lewat `pip install siakad-mcp`, perintahnya `siakad-bap` dengan
argumen yang sama persis — `./siakad bap` dan `siakad-bap` setara.

**2. Isi kredensial.**

```bash
cp .env.contoh .env     # SIAKAD_USERNAME, SIAKAD_PASSWORD
```

**3. Lihat dulu, baru unduh.**

```bash
./siakad bap --tahun 2025 --semester 2 --hanya-daftar
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran
```

## Semua sub-perintah

Dijalankan dari akar proyek, yaitu direktori berisi `siakad`.

```bash
./siakad bap ...        # unduh bukti BAP & kehadiran
./siakad jadwal ...     # jadwal mengajar: hari, jam, ruang, SKS
./siakad hadir ...      # pertemuan pada menu Daftar Hadir
./siakad mahasiswa ...  # peserta satu mata kuliah (bisa diekspor .xlsx)
./siakad pembahasan ... # ISI Topik & Deskripsi Pembahasan (satu-satunya yang menulis)
./siakad petakan <path> # petakan halaman saat menambah kemampuan
./siakad api            # REST API
./siakad mcp            # MCP server
./siakad uji            # unit test
```

Terpasang lewat pip, namanya `siakad-bap`, `siakad-jadwal`, `siakad-hadir`,
`siakad-mahasiswa`, `siakad-pembahasan`, `siakad-mcp`, dan `siakad-petakan`.

Semua perintah pembacaan menerima `--tahun`, `--semester`, dan `--json`.

## `./siakad bap`

Menghasilkan dua PDF per kelas pada satu periode:

```
<KODE> - <Nama Mata Kuliah>[ - Kelas X] - BAP.pdf
<KODE> - <Nama Mata Kuliah>[ - Kelas X] - Kehadiran.pdf
```

| Argumen          | Wajib | Keterangan                                                     |
|------------------|-------|-----------------------------------------------------------------|
| `--tahun`        | ya    | Tahun ajaran, `2025` berarti 2025/2026                          |
| `--semester`     | ya    | `1` ganjil, `2` genap, `3` semester pendek                      |
| `--tujuan`       |       | Direktori penyimpanan; bawaannya `data/bap`                     |
| `--prodi`        |       | Kode prodi, mis. `TI`. Kosong berarti semua prodi               |
| `--kode`         |       | Batasi ke satu kode mata kuliah, mis. `IF30812`                 |
| `--tanggal`      |       | Tanggal pada blok tanda tangan; bawaannya hari ini              |
| `--tanda-tangan` |       | Folder berkas tanda tangan; bawaannya `digital_signs`           |
| `--timpa`        |       | Tulis ulang berkas yang sudah ada                               |
| `--tanpa-ttd`    |       | Cetak polos, tanpa paraf dan tanda tangan                       |
| `--hanya-daftar` |       | Tampilkan kelasnya saja, tanpa mengunduh                        |

Contoh:

```bash
# lihat dulu kelas apa saja pada semester genap 2025/2026
./siakad bap --tahun 2025 --semester 2 --hanya-daftar

# unduh semuanya ke folder bukti BKD
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran

# ulangi satu mata kuliah saja setelah tanda tangannya diperbarui
./siakad bap --tahun 2025 --semester 2 --kode IF30812 --timpa
```

Berkas yang sudah ada dilewati, jadi perintahnya aman diulang. Path relatif pada
`--tujuan` dihitung dari akar proyek.

## `./siakad jadwal`

```bash
./siakad jadwal --tahun 2026 --semester 1
./siakad jadwal --tahun 2026 --semester 1 --json | jq '.[].waktu'
```

| Argumen     | Wajib | Keterangan                                  |
|-------------|-------|---------------------------------------------|
| `--tahun`   | ya    | Tahun ajaran, `2026` berarti 2026/2027      |
| `--semester`| ya    | `1` ganjil, `2` genap, `3` semester pendek  |
| `--prodi`   |       | Kode prodi; kosong berarti semua            |
| `--json`    |       | Cetak JSON, bukan tabel                     |

Keluarannya hari, jam, ruang, dan SKS tiap kelas — tiga hal terakhir tidak ada
pada `./siakad bap --hanya-daftar`, yang membaca menu Berita Acara.

## `./siakad hadir`

```bash
./siakad hadir --tahun 2026 --semester 1                      # seluruh periode
./siakad hadir --tahun 2026 --semester 1 --tanggal 2026-09-01 # satu hari
./siakad hadir --tahun 2026 --semester 1 --kode IF31613
```

Satu baris berarti satu tatap muka, ditutup keterangan `[belum dibuka]` atau
`[dibuka HH:MM]`.

## `./siakad mahasiswa`

```bash
./siakad mahasiswa --tahun 2026 --semester 1 --kode IF31613
./siakad mahasiswa --tahun 2026 --semester 1 --kode IF30212 --kelas "Kelas A" \
                   --excel "peserta/IF30212 - Kelas A.xlsx"
```

| Argumen   | Wajib | Keterangan                                                 |
|-----------|-------|-------------------------------------------------------------|
| `--kode`  | ya    | Kode mata kuliah                                            |
| `--kelas` |       | Kelompok kelas, mis. `"Kelas A"`                            |
| `--excel` |       | Simpan juga sebagai `.xlsx` (butuh extra `excel`)           |

Pesertanya diambil dari pertemuan pertama mata kuliah itu — daftarnya sama di
semua pertemuan. Yang dikeluarkan hanya NIM, nama, kelas, prodi, dan status;
rekam pribadi lain yang ikut dikirim SIAKAD tidak diteruskan.

## `./siakad pembahasan`

Satu-satunya perintah yang **menulis** ke SIAKAD. Isian lama tertimpa.

```bash
./siakad pembahasan --tahun 2026 --semester 1 --kode IF31613 --dari bap.json --uji-coba
./siakad pembahasan --tahun 2026 --semester 1 --kode IF31613 --dari bap.json
```

`--dari` menunjuk berkas JSON berisi daftar isian. Tiap isian menyebut
pertemuannya lewat `tanggal` (paling pasti) atau `pertemuan_ke` (urutan tanggal):

```json
[
  { "tanggal": "2026-08-31", "topik": "Session-01: Pengantar", "deskripsi": "Kontrak kuliah" },
  { "pertemuan_ke": 2, "topik": "Session-02: ...", "deskripsi": "..." }
]
```

| Argumen      | Wajib | Keterangan                                          |
|--------------|-------|------------------------------------------------------|
| `--kode`     | ya    | Kode mata kuliah                                     |
| `--dari`     | ya    | Berkas JSON berisi isiannya                          |
| `--kelas`    |       | Kelompok kelas, kalau mata kuliahnya berkelas ganda  |
| `--uji-coba` |       | Tampilkan yang akan dikirim, tanpa menulis apa pun   |

Jalankan `--uji-coba` dulu: isian yang salah tanggal tidak bisa dibatalkan,
SIAKAD tidak menyimpan riwayat isian sebelumnya.

## `./siakad petakan`

```bash
./siakad petakan /report/berita_acara_kuliah
./siakad petakan /dosen/kepanitiaan --semua-opsi
```

Mencetak dan menyimpan struktur halaman ke `siakad/data/form_<path>.json`: form,
seluruh field beserta pilihannya, jumlah tabel, dan daftar endpoint AJAX yang
dipanggil halaman itu. Hanya melakukan GET.

## Kredensial

Dibaca dari `.env` di akar proyek:

```
SIAKAD_WEBSITE=https://siakad.pradita.ac.id/login
SIAKAD_USERNAME=...
SIAKAD_PASSWORD=...
```

REST API dan MCP bisa menerima kredensial per permintaan sehingga `.env` tidak wajib.

## Syarat tambahan

Pembuatan PDF memakai Chrome/Chromium headless yang sudah terpasang di sistem
(`google-chrome`, `chromium`, atau `chromium-browser`). Kalau tidak ada, skrip
berhenti dengan pesan yang menjelaskan hal itu.
