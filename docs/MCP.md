# Referensi MCP SIAKAD

Server MCP membuka kemampuan yang sama dengan REST API, sehingga asisten AI bisa
mengambil sendiri bukti pengajaran dari SIAKAD.

## Pemasangan

Pakai path absolut ke launcher `siakad` di hasil klona:

```bash
claude mcp add bkd-siakad -- /path/ke/siakad-mcp/siakad mcp
```

Untuk klien MCP lain:

```json
{
  "mcpServers": {
    "bkd-siakad": { "command": "/path/ke/siakad-mcp/siakad", "args": ["mcp"] }
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
| `berita_acara`       | `tahun_ajaran`, `tipe_semester`, `kode_mk`, `username?`, `password?`                             | topik pertemuan + rekap kehadiran |
| `unduh_semua_bukti`  | `tahun_ajaran`, `tipe_semester`, `tujuan?`, `prodi?`, `kode_mk?`, `tanggal?`, `timpa?`, `bertanda_tangan?` | PDF BAP + Kehadiran |

`tahun_ajaran` `"2025"` berarti 2025/2026. `tipe_semester`: `1` ganjil, `2` genap,
`3` semester pendek.

### `unduh_semua_bukti`

Menghasilkan dua PDF per kelas di `tujuan` (path relatif dihitung dari akar
proyek; bawaannya `data/bap`):

```
IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf
IF30812 - Pemrograman Berorientasi Objek - Kelas B - Kehadiran.pdf
```

Halaman BAP dibubuhi paraf dosen pada tiap pertemuan dan tanda tangan pejabat,
diambil dari folder `digital_signs/`. Berkas yang sudah ada dilewati kecuali
`timpa=True`, jadi pemanggilan ulang aman.

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

## Catatan untuk agen

- Aplikasi ini **hanya membaca** SIAKAD; tidak ada tool yang menulis data ke sana.
- Pembuatan PDF memerlukan Chrome/Chromium di mesin yang menjalankan server MCP.
- Satu periode berisi 8 kelas memakan waktu sekitar satu menit karena tiap
  berkas dicetak terpisah — sampaikan itu ke pemakai sebelum memulai.
- Prodi yang belum punya berkas tanda tangan di `digital_signs/` tetap dicetak,
  hanya blok tanda tangan pejabatnya kosong.
- Untuk mendaftarkan berkas ini sebagai bukti BKD di SISTER, pakai server MCP
  [bkd-sister](https://github.com/alfa-yohannis/sister-mcp) — SISTER hanya
  menyimpan tautannya, jadi berkasnya perlu diunggah dulu ke penyimpanan yang
  bisa dibuka asesor.
