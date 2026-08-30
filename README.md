# SIAKAD MCP

Aplikasi untuk menarik bukti pengajaran dari SIAKAD Pradita
(<https://siakad.pradita.ac.id>): daftar kelas yang diampu, berita acara
perkuliahan, dan daftar kehadiran mahasiswa — lengkap dengan tanda tangan,
siap dilampirkan sebagai bukti BKD.

Pasangannya adalah [sister-mcp](https://github.com/alfa-yohannis/sister-mcp)
yang mengisi data ke SISTER. Keduanya berdiri sendiri: kode, dokumentasi,
contoh, dan pengujiannya terpisah.

| Bentuk    | Perintah          | Referensi                    |
|-----------|-------------------|------------------------------|
| CLI       | `./siakad bap`    | [docs/CLI.md](docs/CLI.md)   |
| REST API  | `./siakad api`    | [docs/API.md](docs/API.md)   |
| MCP       | `./siakad mcp`    | [docs/MCP.md](docs/MCP.md)   |

## Mulai cepat

```bash
git clone https://github.com/alfa-yohannis/siakad-mcp.git
cd siakad-mcp
cp .env.contoh .env                                     # lalu isi kredensialnya

./siakad bap --tahun 2025 --semester 2 --hanya-daftar    # lihat kelasnya dulu
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran
```

`./siakad` membuat virtualenv di `.venv/` dan memasang `requirements.txt` sendiri
pada jalankan pertama; tidak ada langkah pemasangan terpisah. Pembuatan PDF
memerlukan Chrome/Chromium yang sudah terpasang di sistem.

Hasilnya dua PDF per kelas:

```
IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf
IF30812 - Pemrograman Berorientasi Objek - Kelas B - Kehadiran.pdf
```

Kredensial dibaca dari `.env` di akar proyek (`SIAKAD_USERNAME`, `SIAKAD_PASSWORD`).
REST API dan MCP juga bisa menerima kredensial per permintaan, sehingga `.env`
tidak wajib.

Aplikasi ini bisa dipakai berdiri sendiri seperti di atas, atau dari ruang kerja
yang lebih besar. Kalau `BKD_AKAR_PROYEK` disetel, direktori itulah yang dipakai
sebagai akar proyek — tempat `.env`, `digital_signs/`, dan titik hitung path
relatif — menggantikan direktori aplikasi ini.

## Tanda tangan

Berkas tanda tangan diletakkan di `digital_signs/<nama>.png`, mis. `kong.png` dan
`spider.png`. Folder itu masuk `.gitignore` karena isinya data pribadi. Pada
halaman BAP:

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
siakad                     launcher: virtualenv, dependensi, dan sub-perintah
scripts/siakad_client.py   KlienSiakad: login, ambil halaman, baca/kirim form
scripts/berita_acara.py    BeritaAcaraKuliah + Kelas: daftar kelas, detail, unduh bukti
scripts/tanda_tangan.py    pembubuhan paraf & tanda tangan ke halaman cetak
scripts/cetak_pdf.py       halaman cetak -> PDF lewat Chrome headless
scripts/unduh_bap.py       CLI
scripts/api.py             REST API (FastAPI)
scripts/mcp_server.py      MCP server
scripts/petakan_form.py    alat bantu memetakan halaman saat menambah kemampuan
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

15 unit test, semuanya berjalan tanpa jaringan dan tanpa kredensial. Nama tokoh
dan nomor induk pada berkas uji dan dokumentasi seluruhnya dikarang.
