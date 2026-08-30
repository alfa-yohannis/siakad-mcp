# Contoh prompt untuk MCP SIAKAD

Permintaan siap salin untuk asisten AI setelah server `siakad-mcp` didaftarkan
(lihat [../docs/MCP.md](../docs/MCP.md)). Kredensial diambil sendiri dari `.env`.

## Melihat isi SIAKAD

```
Cek apakah login SIAKAD saya masih jalan.
```

```
Kelas apa saja yang saya ampu pada semester genap 2025/2026 menurut SIAKAD?
```

```
Tampilkan topik pertemuan mata kuliah IF30812 semester genap 2025/2026,
sekalian sebutkan berapa mahasiswa yang hadir di tiap pertemuan.
```

## Mengambil bukti untuk BKD

```
Ambilkan bukti pengajaran semester genap 2025/2026 dari SIAKAD — BAP dan daftar
kehadiran untuk semua kelas — simpan ke folder bukti/pengajaran.
```

```
Ambilkan bukti pengajaran untuk mata kuliah IF30812 saja, tanpa tanda tangan.
```

```
Tanda tangan Kaprodi baru sudah saya taruh di digital_signs. Cetak ulang semua
BAP semester genap 2025/2026 supaya memakai tanda tangan itu.
```

```
Isi folder bukti/pengajaran sudah ada. Periksa apakah semua kelas yang saya
ampu semester genap 2025/2026 sudah punya berkas BAP dan Kehadiran; lengkapi
yang belum ada saja.
```

## Jadwal, pertemuan, dan peserta

```
Jadwal mengajar saya semester ganjil 2026/2027 — hari, jam, ruang, dan SKS-nya.
```

```
Siapa saja peserta IF31613 semester ganjil 2026/2027? Sebutkan jumlahnya.
```

```
Pertemuan apa saja yang ada minggu ini, dan mana yang kelasnya belum dibuka?
```

## Mengisi BAP dan membuka kelas (menulis ke SIAKAD)

```
Isi Topik Pembahasan pertemuan 31 Agustus 2026 mata kuliah IF31613 dengan
"Session-01: Peran & konsep arsitektur perangkat lunak". Tampilkan dulu apa yang
akan dikirim sebelum benar-benar menyimpannya.
```

```
Buka kelas IF30212 Kelas B untuk pertemuan hari ini.
```

Keduanya menulis ke SIAKAD: kelas yang sudah dibuka tidak bisa ditutup lagi, dan
isian pembahasan lama tertimpa tanpa riwayat. Asisten diminta menjalankan
`uji_coba` lebih dulu dan meminta persetujuan.

## Menyambung ke SISTER

```
Ambil bukti pengajaran semester genap 2025/2026 dari SIAKAD, lalu daftarkan
tautan folder Google Drive berikut sebagai bukti penugasan tiap mata kuliah di
rekap BKD SISTER: <tautan folder>
```

## Menambah kemampuan baru

```
Petakan halaman /dosen/kepanitiaan di SIAKAD — form, field, dan endpoint AJAX-nya —
supaya kita bisa menarik datanya juga.
```

## Yang perlu diketahui

- Dari sepuluh tool, hanya `buka_kelas` dan `simpan_pembahasan` yang menulis ke
  SIAKAD; delapan sisanya membaca.
- Menghasilkan PDF butuh Chrome/Chromium; satu periode berisi 8 kelas memakan
  waktu sekitar satu menit.
- SISTER menyimpan bukti sebagai **tautan**, bukan berkas. Jadi PDF hasil unduhan
  perlu diunggah dulu ke penyimpanan yang bisa dibuka asesor sebelum tautannya
  didaftarkan.
