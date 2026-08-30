# Referensi MCP SIAKAD

Server MCP membuka kemampuan yang sama dengan REST API, sehingga asisten AI bisa
mengambil sendiri bukti pengajaran dari SIAKAD.

## Menjalankan

**1. Pasang.** Butuh Python 3.10+ dan Chrome/Chromium untuk mencetak PDF.

```bash
pip install "siakad-mcp[mcp]"
```

Atau dari klona repositori: `git clone …` lalu `./siakad uji` sekali untuk
menyiapkan `.venv`.

**2. Isi kredensial** di `.env` pada akar proyek — salin dari `.env.contoh`:

```
SIAKAD_USERNAME=nama.anda@pradita.ac.id
SIAKAD_PASSWORD=...
```

Boleh dilewati kalau kredensial dikirim per pemanggilan tool.

**3. Cek servernya hidup** sebelum didaftarkan:

```bash
siakad-mcp        # atau ./siakad mcp dari klona
```

Server bicara JSON-RPC lewat stdio, jadi terminal akan tampak diam menunggu
masukan — itu memang benar. Ctrl-C untuk berhenti.

**4. Daftarkan.**

```bash
claude mcp add siakad-mcp -- siakad-mcp
```

Dari klona, tunjuk launcher-nya dengan path absolut:

```bash
claude mcp add siakad-mcp -- /path/ke/siakad-mcp/siakad mcp
```

**5. Coba.** Minta asisten Anda:

```
Kelas apa saja yang saya ampu pada semester genap 2025/2026 menurut SIAKAD?
```

Contoh prompt lain di [../examples/prompt_mcp.md](../examples/prompt_mcp.md).

Untuk klien MCP lain:

```json
{
  "mcpServers": {
    "siakad-mcp": { "command": "siakad-mcp", "args": [] }
  }
}
```

Kredensial diambil dari `SIAKAD_USERNAME` / `SIAKAD_PASSWORD` di `.env` kalau
parameternya dikosongkan, sehingga asisten tidak perlu memegang kredensial.

## Tool

| Tool                 | Parameter                                                                                      | Hasil |
|----------------------|-------------------------------------------------------------------------------------------------|-------|
| `cek_login`          | `username?`, `password?`                                                                         | `{ok, beranda}` |
| `daftar_menu`        | `username?`, `password?`                                                                         | menu SIAKAD yang tersedia |
| `daftar_kelas`       | `tahun_ajaran`, `tipe_semester`, `prodi?`, `username?`, `password?`                              | kelas satu periode |
| `jadwal_mengajar`    | `tahun_ajaran`, `tipe_semester`, `prodi?`, `username?`, `password?`                              | jadwal: hari, jam, ruang, SKS |
| `berita_acara`       | `tahun_ajaran`, `tipe_semester`, `kode_mk`, `username?`, `password?`                             | topik pertemuan + rekap kehadiran |
| `daftar_pertemuan`   | `tahun_ajaran`, `tipe_semester`, `tanggal?`, `kode_mk?`, `username?`, `password?`                 | tatap muka per tanggal |
| `daftar_mahasiswa`   | `tahun_ajaran`, `tipe_semester`, `kode_mk`, `kelompok_kelas?`, `username?`, `password?`           | peserta satu mata kuliah |
| `buka_kelas`         | `tahun_ajaran`, `tipe_semester`, `kode_mk`, `tanggal`, `kelompok_kelas?`, `uji_coba?`            | **menulis** — buka pertemuan untuk absensi |
| `simpan_pembahasan`  | `tahun_ajaran`, `tipe_semester`, `kode_mk`, `tanggal`, `topik`, `deskripsi?`, `kelompok_kelas?`, `uji_coba?` | **menulis** Topik & Deskripsi Pembahasan |
| `unduh_semua_bukti`  | `tahun_ajaran`, `tipe_semester`, `tujuan?`, `prodi?`, `kode_mk?`, `tanggal?`, `tanda_tangan?`, `timpa?`, `bertanda_tangan?` | PDF BAP + Kehadiran |

`tahun_ajaran` `"2025"` berarti 2025/2026. `tipe_semester`: `1` ganjil, `2` genap,
`3` semester pendek.

### `daftar_kelas` vs `jadwal_mengajar`

Keduanya menyebut kelas satu periode, tapi sumbernya berbeda menu.
`daftar_kelas` berangkat dari laporan Berita Acara — itu yang dipakai
`unduh_semua_bukti`. `jadwal_mengajar` berangkat dari jadwal yang disusun bagian
akademik, sehingga **ruang, jam selesai, dan SKS** hanya ada di sini.

### `daftar_pertemuan` dan `daftar_mahasiswa`

Menu Daftar Hadir berangkat dari **pertemuan**: satu baris berarti satu tatap
muka pada tanggal tertentu, lengkap dengan keterangan kelasnya sudah dibuka atau
belum. `tanggal` kosong berarti seluruh periode.

`daftar_mahasiswa` mengambil peserta dari pertemuan pertama mata kuliah itu —
pesertanya sama di semua pertemuan, jadi satu permintaan sudah cukup. Yang
dikembalikan hanya `nim`, `nama`, `kelompok_kelas`, `prodi`, `status`, dan
`hadir`. SIAKAD sebenarnya mengirim rekam mahasiswa selengkapnya pada endpoint
itu — nomor KTP, alamat, nama orang tua, nomor telepon — dan semuanya sengaja
tidak diteruskan supaya data pribadi tidak ikut mengalir ke asisten AI.

### `unduh_semua_bukti`

Menghasilkan dua PDF per kelas di `tujuan` (path relatif dihitung dari akar
proyek; bawaannya `data/bap`):

```
IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf
IF30812 - Pemrograman Berorientasi Objek - Kelas B - Kehadiran.pdf
```

Halaman BAP dibubuhi paraf dosen pada tiap pertemuan dan tanda tangan pejabat,
diambil dari folder yang ditunjuk `tanda_tangan` (path relatif dihitung dari akar
proyek). Kalau dikosongkan, dipakai `digital_signs/` di akar proyek. Berkas yang
sudah ada dilewati kecuali `timpa=True`, jadi pemanggilan ulang aman.

Balasannya:

```json
{ "tujuan": "/path/ke/siakad-mcp/bukti/pengajaran", "berkas": ["..."], "gagal": [] }
```

## Contoh prompt

```
Ambilkan bukti pengajaran semester genap 2025/2026 dari SIAKAD, simpan ke
folder bukti/pengajaran.
```

```
Kelas apa saja yang saya ampu pada semester ganjil 2026/2027 menurut SIAKAD?
```

```
Tampilkan topik pertemuan dan rekap kehadiran mata kuliah IF30812 semester
genap 2025/2026. Sebutkan pertemuan yang kehadirannya paling rendah.
```

```
Berkas BAP untuk IF30812 perlu dicetak ulang karena tanda tangannya diperbarui —
timpa berkas lamanya.
```

Contoh lain ada di [../examples/prompt_mcp.md](../examples/prompt_mcp.md).

### `buka_kelas` dan `simpan_pembahasan`

Dua tool yang **menulis** ke SIAKAD; delapan sisanya hanya membaca.

`buka_kelas` membuka satu pertemuan supaya mahasiswa bisa mengabsen. SIAKAD
hanya mengizinkannya pada hari pertemuan itu, dan **kelas yang sudah dibuka
tidak bisa ditutup lagi**.

`simpan_pembahasan` mengisi Topik dan Deskripsi Pembahasan. Isian lama pada
pertemuan itu tertimpa dan SIAKAD tidak menyimpan riwayatnya. Untuk keduanya:

- `tanggal` wajib diisi (YYYY-MM-DD) supaya tidak ada pertemuan yang terisi
  tanpa disengaja; `kelompok_kelas` dipakai kalau dua kelas bertemu pada tanggal
  yang sama;
- jalankan dulu dengan `uji_coba=true` — muatannya dikembalikan tanpa dikirim;
- mintalah persetujuan pemakai sebelum mengisi banyak pertemuan sekaligus.

```json
{ "ok": true, "pertemuan": "IF31613 - Arsitektur Perangkat Lunak — 2026-08-31",
  "pesan": "Sukses update topik pembahasan" }
```

## Catatan untuk agen

- Selain `buka_kelas` dan `simpan_pembahasan`, seluruh tool **hanya membaca** SIAKAD.
- Pembuatan PDF memerlukan Chrome/Chromium di mesin yang menjalankan server MCP.
- Satu periode berisi 8 kelas memakan waktu sekitar satu menit karena tiap
  berkas dicetak terpisah — sampaikan itu ke pemakai sebelum memulai.
- Prodi yang belum punya berkas tanda tangan di `digital_signs/` tetap dicetak,
  hanya blok tanda tangan pejabatnya kosong.
- Untuk mendaftarkan berkas ini sebagai bukti BKD di SISTER, pakai server MCP
  [bkd-sister](https://github.com/alfa-yohannis/sister-mcp) — SISTER hanya
  menyimpan tautannya, jadi berkasnya perlu diunggah dulu ke penyimpanan yang
  bisa dibuka asesor.
