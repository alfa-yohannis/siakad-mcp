# Setelan

Aplikasi ini berdiri sendiri: semua berkasnya ada di direktorinya sendiri, dan
direktori di atasnya tidak pernah ikut ditelusuri.

```
.env            kredensial — SIAKAD_USERNAME, SIAKAD_PASSWORD (tidak ikut ter-commit)
siakad.yaml     setelan non-rahasia — alamat instance, kota, ukuran kertas, dsb.
digital_signs/  berkas tanda tangan (tidak ikut ter-commit)
data/           hasil tarikan
```

Salin contohnya lalu ubah yang perlu:

```bash
cp .env.contoh .env                 # isi username dan password
cp siakad.yaml.contoh siakad.yaml   # semua baris boleh tetap dikomentari
```

`siakad.yaml` tidak wajib. Tanpa berkas itu, seluruh nilai bawaan di bawah
dipakai apa adanya.

## Urutan yang menang

```
environment  ->  .env  ->  siakad.yaml  ->  nilai bawaan
```

Nama kuncinya sama, hanya bentuknya berbeda: di environment dan `.env` berawalan
`SIAKAD_` dan huruf besar (`SIAKAD_BASE_URL`); di `siakad.yaml` tanpa awalan dan
huruf kecil (`base_url`).

Rahasia dan setelan sengaja dipisah: `.env` memuat username/password dan tidak
pernah ikut ter-commit, sedangkan `siakad.yaml` tidak memuat rahasia apa pun
sehingga aman dibagikan ke sesama pemakai satu perguruan tinggi.

## Daftar setelan

### Instance SIAKAD

| `siakad.yaml`   | Bawaan                          | Keterangan                                  |
|-----------------|---------------------------------|---------------------------------------------|
| `base_url`      | `https://siakad.pradita.ac.id`  | alamat instance SIAKAD                      |
| `nama_instansi` | `Pradita`                       | label pada judul REST API dan instruksi MCP |
| `path_login`    | `/login_process`                | endpoint POST login                         |
| `path_laporan`  | `/report/berita_acara_kuliah`   | menu Berita Acara Perkuliahan               |

### Blok tanda tangan

| `siakad.yaml`     | Bawaan      | Keterangan                                     |
|-------------------|-------------|------------------------------------------------|
| `kota`            | `Tangerang` | kota pada blok tanda tangan pejabat             |
| `tinggi_paraf_px` | `58`        | tinggi paraf dosen; lebar mengikuti rasio asli  |
| `tinggi_ttd_px`   | `120`       | tinggi tanda tangan pejabat                     |

`kota` dipakai untuk **menemukan** blok tanda tangan di halaman cetak, jadi
harus sama persis dengan yang dicetak SIAKAD Anda. Kalau tidak cocok, tanda
tangan pejabat tidak terpasang dan halaman lainnya tetap tercetak normal.

Letak folder tanda tangan bukan setelan berkas, melainkan diberikan pemanggil —
lihat [Tanda tangan di README](../README.md#tanda-tangan).

### Ukuran kertas

| `siakad.yaml`      | Bawaan | Keterangan                            |
|--------------------|--------|---------------------------------------|
| `ukuran_bap`       | `A3`   | BAP lebar karena tabelnya banyak kolom |
| `ukuran_kehadiran` | `A4`   | daftar kehadiran                       |

Halaman dari SIAKAD tidak menentukan ukuran kertas sendiri, jadi nilainya
disisipkan sebelum dicetak.

### Pencetakan

| `siakad.yaml`        | Bawaan          | Keterangan                                     |
|----------------------|-----------------|------------------------------------------------|
| `chrome`             | dicari di PATH  | biner Chrome/Chromium                          |
| `batas_cetak_detik`  | `180`           | batas waktu satu proses Chrome                 |
| `jatah_muat_ms`      | `15000`         | tunggu CSS dan gambar selesai sebelum dicetak  |

Isi `chrome` kalau binernya tidak ada di PATH atau ada lebih dari satu peramban
terpasang. Path yang salah ditolak dengan pesan jelas, bukan didiamkan.

### Batas waktu jaringan

| `siakad.yaml`          | Bawaan | Keterangan                          |
|------------------------|--------|-------------------------------------|
| `batas_login_detik`    | `60`   | GET dan POST login                  |
| `batas_halaman_detik`  | `120`  | GET halaman biasa                   |
| `batas_kirim_detik`    | `300`  | POST form, termasuk unggah berkas   |
| `batas_laporan_detik`  | `300`  | endpoint laporan; ekspor bisa lama  |

Naikkan kalau jaringan ke SIAKAD lambat.

### Lain-lain

| `siakad.yaml`       | Bawaan            | Keterangan                                  |
|---------------------|-------------------|---------------------------------------------|
| `baris_per_halaman` | `15`              | ukuran halaman hasil pencarian, ikut server |
| `umur_sesi_detik`   | `900`             | lama sesi login disimpan REST API           |
| `user_agent`        | Chrome 126 di X11 | User-Agent permintaan HTTP                  |

## Memakai ruang kerja yang lebih besar

Kalau `.env` dan `digital_signs/` memang mau diambil dari direktori kerja lain,
tunjuk sendiri:

```bash
SIAKAD_AKAR_PROYEK=/path/ke/ruang-kerja ./siakad bap --tahun 2025 --semester 2
```

Tanpa variabel itu, aplikasi hanya melihat direktorinya sendiri — hasilnya tidak
berubah hanya karena aplikasi dipindah ke folder lain. `BKD_AKAR_PROYEK` masih
diterima sebagai nama lama.
