# Referensi CLI SIAKAD

Dijalankan dari akar proyek, yaitu direktori berisi `siakad`. Virtualenv dan
dependensinya disiapkan sendiri pada jalankan pertama.

```bash
./siakad bap ...        # unduh bukti BAP & kehadiran
./siakad petakan <path> # petakan halaman saat menambah kemampuan
./siakad api            # REST API
./siakad mcp            # MCP server
./siakad uji            # unit test
```

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
