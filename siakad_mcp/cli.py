"""Perintah baris perintah SIAKAD.

    siakad-bap        unduh bukti BAP & Kehadiran satu periode sebagai PDF
    siakad-jadwal     jadwal mengajar: hari, jam, ruang, SKS
    siakad-hadir      pertemuan pada menu Daftar Hadir
    siakad-mahasiswa  mahasiswa yang terdaftar pada satu mata kuliah

Dari klona repositori, keempatnya dipanggil lewat peluncur: `./siakad bap`,
`./siakad jadwal`, `./siakad hadir`, `./siakad mahasiswa`.

`siakad-bap` menghasilkan dua berkas per kelas:

    <KODE> - <Nama Mata Kuliah>[ - Kelas X] - BAP.pdf
    <KODE> - <Nama Mata Kuliah>[ - Kelas X] - Kehadiran.pdf

Halaman BAP dibubuhi paraf dosen pada tiap pertemuan dan tanda tangan pejabat
penanda tangan, diambil dari <akar proyek>/digital_signs/.

Pakai:
    siakad-bap --tahun 2026 --semester 1 --tujuan bukti/pengajaran
    siakad-jadwal --tahun 2026 --semester 1
    siakad-mahasiswa --tahun 2026 --semester 1 --kode IF31613 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path


from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah
from siakad_mcp.cetak_pdf import CetakError
from siakad_mcp.daftar_hadir import DaftarHadir
from siakad_mcp.ekspor import tulis_xlsx
from siakad_mcp.jadwal import JadwalMengajar
from siakad_mcp.konfigurasi import KonfigurasiError, akar_proyek, dir_data
from siakad_mcp.menu import jam_ringkas, nama_hari
from siakad_mcp.siakad_client import KlienSiakad, SiakadError


BULAN_INDONESIA = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def tanggal_hari_ini() -> str:
    """Tanggal hari ini dalam ejaan Indonesia, mis. '19 Agustus 2026'."""
    hari_ini = date.today()
    return f"{hari_ini.day} {BULAN_INDONESIA[hari_ini.month - 1]} {hari_ini.year}"


def baca_argumen() -> argparse.Namespace:
    """Argumen baris perintah beserta nilai bawaannya."""
    pengurai = argparse.ArgumentParser(
        description="Unduh bukti BAP dan Kehadiran satu periode sebagai PDF, lengkap dengan tanda tangan.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pengurai.add_argument("--tahun", required=True, help="Tahun ajaran, mis. 2025 untuk 2025/2026")
    pengurai.add_argument("--semester", required=True, choices=["1", "2", "3"],
                          help="1 ganjil, 2 genap, 3 semester pendek")
    pengurai.add_argument("--prodi", default="", help="Kode prodi, mis. TI. Kosong berarti semua")
    pengurai.add_argument("--kode", default="", help="Batasi ke satu kode mata kuliah")
    pengurai.add_argument("--tujuan", default=str(dir_data() / "bap"), help="Direktori penyimpanan PDF")
    pengurai.add_argument("--tanggal", default=tanggal_hari_ini(),
                          help="Tanggal pada blok tanda tangan (bawaan: hari ini)")
    pengurai.add_argument("--tanda-tangan", default="", metavar="DIR",
                          help="Folder berkas tanda tangan (bawaan: digital_signs/ di akar proyek)")
    pengurai.add_argument("--timpa", action="store_true", help="Tulis ulang berkas yang sudah ada")
    pengurai.add_argument("--tanpa-ttd", action="store_true", help="Cetak tanpa membubuhkan tanda tangan")
    pengurai.add_argument("--hanya-daftar", action="store_true", help="Tampilkan kelasnya saja, tanpa mengunduh")
    return pengurai.parse_args()


def main() -> int:
    argumen = baca_argumen()
    tujuan = Path(argumen.tujuan)
    if not tujuan.is_absolute():
        tujuan = (akar_proyek() / tujuan).resolve()

    laporan = BeritaAcaraKuliah(KlienSiakad().login())
    print(f"Login SIAKAD OK — periode {argumen.tahun}/{argumen.semester}\n")

    kelas_ditemukan = laporan.daftar_kelas(argumen.tahun, argumen.semester, argumen.prodi)
    if argumen.kode:
        kelas_ditemukan = [satu for satu in kelas_ditemukan if satu.kode_mk == argumen.kode]
    if not kelas_ditemukan:
        print("Tidak ada kelas yang cocok.")
        return 1

    print(f"{len(kelas_ditemukan)} kelas ditemukan:")
    for satu in kelas_ditemukan:
        print(f"  - {satu.label}  [{satu.hari} {satu.jam_mulai[:5]}]")
    if argumen.hanya_daftar:
        return 0

    print(f"\nMenyimpan ke {tujuan}")
    gagal = 0
    for satu in kelas_ditemukan:
        for jenis in JENIS_BUKTI:
            try:
                berkas = laporan.unduh_bukti(
                    satu, jenis, tujuan,
                    timpa=argumen.timpa,
                    bertanda_tangan=not argumen.tanpa_ttd,
                    tanggal_tanda_tangan=argumen.tanggal,
                    dir_tanda_tangan=argumen.tanda_tangan or None,
                )
            except (SiakadError, CetakError, KonfigurasiError) as galat:
                print(f"  GAGAL {satu.label} [{jenis}]: {galat}")
                gagal += 1
                continue
            ukuran_kb = berkas.stat().st_size // 1024
            print(f"  {berkas.name}  ({ukuran_kb} KB)")

    return 1 if gagal else 0


def jalankan_aman(perintah) -> int:
    """Jalankan satu perintah CLI dengan penanganan kesalahan yang seragam.

    Kesalahan pustaka sengaja tidak dibiarkan menjadi traceback: pemakai CLI
    butuh satu baris pesan yang bisa ditindaklanjuti, bukan jejak tumpukan.
    """
    try:
        return perintah()
    except (SiakadError, CetakError, KonfigurasiError) as galat:
        print(f"Gagal: {galat}", file=sys.stderr)
        return 1


def jalankan() -> int:
    """Titik masuk perintah `siakad-bap`."""
    return jalankan_aman(main)


def pengurai_periode(deskripsi: str) -> argparse.ArgumentParser:
    """Argumen yang sama untuk semua perintah pembacaan: periode dan bentuk keluaran."""
    pengurai = argparse.ArgumentParser(description=deskripsi)
    pengurai.add_argument("--tahun", required=True, help="Tahun ajaran, mis. 2026 untuk 2026/2027")
    pengurai.add_argument("--semester", required=True, choices=["1", "2", "3"],
                          help="1 ganjil, 2 genap, 3 semester pendek")
    pengurai.add_argument("--json", action="store_true", help="Cetak JSON, bukan tabel")
    return pengurai


def cetak_json(data) -> int:
    """Keluaran untuk dipipa ke perkakas lain."""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def main_jadwal() -> int:
    pengurai = pengurai_periode("Jadwal mengajar satu periode: hari, jam, ruang, dan SKS.")
    pengurai.add_argument("--prodi", default="", help="Kode prodi; kosong berarti semua")
    argumen = pengurai.parse_args()

    jadwal = JadwalMengajar(KlienSiakad().login()).daftar(argumen.tahun, argumen.semester, argumen.prodi)
    if argumen.json:
        return cetak_json([satu.sebagai_dict() for satu in jadwal])
    if not jadwal:
        print("Tidak ada jadwal pada periode itu.")
        return 1

    print(f"Jadwal mengajar {argumen.tahun}/{argumen.semester} — {len(jadwal)} kelas\n")
    for satu in jadwal:
        sks = f"{satu.sks} SKS" if satu.sks else ""
        print(f"  {nama_hari(satu.hari):<7} {jam_ringkas(satu.jam_mulai)}-{jam_ringkas(satu.jam_selesai)}"
              f"  {satu.ruang:<12} {satu.label}  {sks}")
    return 0


def main_hadir() -> int:
    pengurai = pengurai_periode("Pertemuan pada menu Daftar Hadir SIAKAD.")
    pengurai.add_argument("--tanggal", default="", help="YYYY-MM-DD; kosong berarti seluruh periode")
    pengurai.add_argument("--kode", default="", help="Batasi ke satu kode mata kuliah")
    argumen = pengurai.parse_args()

    pertemuan = DaftarHadir(KlienSiakad().login()).daftar_pertemuan(
        argumen.tahun, argumen.semester, argumen.tanggal
    )
    if argumen.kode:
        pertemuan = [satu for satu in pertemuan if satu.kode_mk == argumen.kode]
    if argumen.json:
        return cetak_json([satu.sebagai_dict() for satu in pertemuan])
    if not pertemuan:
        print("Tidak ada pertemuan yang cocok.")
        return 1

    print(f"{len(pertemuan)} pertemuan pada periode {argumen.tahun}/{argumen.semester}\n")
    for satu in pertemuan:
        keadaan = f"dibuka {jam_ringkas(satu.jam_dibuka)}" if satu.sudah_dibuka else "belum dibuka"
        print(f"  {satu.tanggal}  {nama_hari(satu.hari):<7} {jam_ringkas(satu.jam_mulai)}-"
              f"{jam_ringkas(satu.jam_selesai)}  {satu.ruang:<12} {satu.kode_mk} - {satu.nama_mk}"
              f"{f' ({satu.kelompok_kelas})' if satu.kelompok_kelas else ''}  [{keadaan}]")
    return 0


def main_mahasiswa() -> int:
    pengurai = pengurai_periode("Mahasiswa yang terdaftar pada satu mata kuliah.")
    pengurai.add_argument("--kode", required=True, help="Kode mata kuliah, mis. IF31613")
    pengurai.add_argument("--kelas", default="", help="Kelompok kelas, mis. 'Kelas A'")
    pengurai.add_argument("--excel", default="", metavar="BERKAS",
                          help="Simpan juga sebagai .xlsx; path relatif dari akar proyek")
    argumen = pengurai.parse_args()

    pertemuan, mahasiswa = DaftarHadir(KlienSiakad().login()).mahasiswa_kelas(
        argumen.tahun, argumen.semester, argumen.kode, argumen.kelas
    )
    if argumen.excel:
        tujuan = Path(argumen.excel)
        berkas = tulis_xlsx(
            ["No", "NIM", "Nama", "Email", "Kelas", "Program Studi", "Status"],
            [[nomor, satu.nim, satu.nama, satu.email, satu.kelompok_kelas, satu.prodi, satu.status]
             for nomor, satu in enumerate(mahasiswa, start=1)],
            tujuan if tujuan.is_absolute() else akar_proyek() / tujuan,
            nama_lembar=pertemuan.kode_mk,
        )
        print(f"tersimpan: {berkas}")

    if argumen.json:
        return cetak_json({"pertemuan": pertemuan.sebagai_dict(),
                           "mahasiswa": [satu.__dict__ for satu in mahasiswa]})

    print(f"{pertemuan.kode_mk} - {pertemuan.nama_mk}"
          f"{f' ({pertemuan.kelompok_kelas})' if pertemuan.kelompok_kelas else ''}"
          f" — {len(mahasiswa)} mahasiswa")
    print(f"diambil dari pertemuan {pertemuan.tanggal} {pertemuan.waktu}\n")
    for nomor, satu in enumerate(mahasiswa, start=1):
        print(f"  {nomor:>3}. {satu.nim:<12} {satu.nama}")
    return 0


def main_buka_kelas() -> int:
    pengurai = pengurai_periode("Buka pertemuan hari ini supaya mahasiswa bisa mengabsen.")
    pengurai.add_argument("--tanggal", default="", help="YYYY-MM-DD; bawaannya hari ini")
    pengurai.add_argument("--kode", default="", help="Batasi ke satu kode mata kuliah")
    pengurai.add_argument("--menit", type=int, default=0, metavar="N",
                          help="Hanya yang mulai dalam N menit ke depan; 0 berarti semua hari itu")
    pengurai.add_argument("--uji-coba", action="store_true",
                          help="Tampilkan yang akan dibuka, tanpa membuka apa pun")
    argumen = pengurai.parse_args()

    tanggal = argumen.tanggal or date.today().isoformat()
    hadir = DaftarHadir(KlienSiakad().login())
    pertemuan = hadir.daftar_pertemuan(argumen.tahun, argumen.semester, tanggal)
    if argumen.kode:
        pertemuan = [satu for satu in pertemuan if satu.kode_mk == argumen.kode]
    if argumen.menit:
        pertemuan = [satu for satu in pertemuan if segera_mulai(satu, argumen.menit)]

    if not pertemuan:
        print(f"Tidak ada pertemuan yang perlu dibuka pada {tanggal}.")
        return 0

    hasil_semua = []
    for satu in pertemuan:
        hasil = hadir.buka_kelas(satu, uji_coba=argumen.uji_coba)
        hasil_semua.append(hasil)
        tanda = "OK   " if hasil["ok"] else "LEWAT"
        print(f"  {tanda} {satu.tanggal} {jam_ringkas(satu.jam_mulai)}  {satu.kode_mk} - {satu.nama_mk}"
              f"{f' ({satu.kelompok_kelas})' if satu.kelompok_kelas else ''}"
              f"  {hasil.get('pesan', '')}")

    if argumen.json:
        return cetak_json(hasil_semua)
    if argumen.uji_coba:
        print("\nTidak ada yang dibuka. Hilangkan --uji-coba untuk benar-benar membuka.")
    return 0


def segera_mulai(pertemuan, menit: int) -> bool:
    """Pertemuan yang jam mulainya jatuh dalam `menit` ke depan (atau baru lewat).

    Batas bawahnya sengaja diberi kelonggaran satu jam ke belakang: cron yang
    telat jalan tetap membuka kelas yang sudah dimulai, bukan melewatinya.
    """
    sekarang = datetime.now()
    jam, _, sisa = pertemuan.jam_mulai.partition(":")
    try:
        mulai = sekarang.replace(hour=int(jam), minute=int(sisa[:2]), second=0, microsecond=0)
    except ValueError:
        return False
    selisih = (mulai - sekarang).total_seconds() / 60
    return -60 <= selisih <= menit


def main_pembahasan() -> int:
    pengurai = pengurai_periode("Isi Topik dan Deskripsi Pembahasan (BAP) dari sebuah berkas JSON.")
    pengurai.add_argument("--kode", required=True, help="Kode mata kuliah, mis. IF31613")
    pengurai.add_argument("--kelas", default="", help="Kelompok kelas, mis. 'Kelas A'")
    pengurai.add_argument("--dari", required=True, metavar="BERKAS",
                          help="JSON berisi daftar {tanggal|pertemuan_ke, topik, deskripsi}")
    pengurai.add_argument("--uji-coba", action="store_true",
                          help="Tampilkan yang akan dikirim, tanpa menulis apa pun ke SIAKAD")
    argumen = pengurai.parse_args()

    isian = json.loads(Path(argumen.dari).read_text(encoding="utf-8"))
    hadir = DaftarHadir(KlienSiakad().login())
    pertemuan = [
        satu
        for satu in hadir.daftar_pertemuan(argumen.tahun, argumen.semester)
        if satu.kode_mk == argumen.kode and (not argumen.kelas or satu.kelompok_kelas == argumen.kelas)
    ]
    if not pertemuan:
        print(f"Tidak ada pertemuan {argumen.kode} pada periode itu.")
        return 1

    menurut_tanggal = {satu.tanggal: satu for satu in pertemuan}
    awalan = "[uji coba] " if argumen.uji_coba else ""
    print(f"{awalan}{argumen.kode}: {len(isian)} isian untuk {len(pertemuan)} pertemuan\n")

    gagal = 0
    for satu_isian in isian:
        nomor = satu_isian.get("pertemuan_ke")
        tujuan = menurut_tanggal.get(satu_isian.get("tanggal", "")) or (
            pertemuan[nomor - 1] if nomor and 0 < nomor <= len(pertemuan) else None
        )
        if tujuan is None:
            print(f"  LEWAT  {satu_isian.get('tanggal') or satu_isian.get('pertemuan_ke')}: pertemuannya tidak ada")
            gagal += 1
            continue

        hasil = hadir.simpan_pembahasan(
            tujuan, satu_isian.get("topik", ""), satu_isian.get("deskripsi", ""),
            uji_coba=argumen.uji_coba,
        )
        tanda = "OK   " if hasil["ok"] else "GAGAL"
        gagal += 0 if hasil["ok"] else 1
        print(f"  {tanda}  {tujuan.tanggal}  {satu_isian.get('topik', '')[:70]}")
        if not hasil["ok"]:
            print(f"         {hasil.get('pesan', '')}")

    if argumen.uji_coba:
        print("\nTidak ada yang dikirim ke SIAKAD. Hilangkan --uji-coba untuk benar-benar menulis.")
    return 1 if gagal else 0


def jalankan_jadwal() -> int:
    """Titik masuk perintah `siakad-jadwal`."""
    return jalankan_aman(main_jadwal)


def jalankan_hadir() -> int:
    """Titik masuk perintah `siakad-hadir`."""
    return jalankan_aman(main_hadir)


def jalankan_mahasiswa() -> int:
    """Titik masuk perintah `siakad-mahasiswa`."""
    return jalankan_aman(main_mahasiswa)


def jalankan_pembahasan() -> int:
    """Titik masuk perintah `siakad-pembahasan`."""
    return jalankan_aman(main_pembahasan)


def jalankan_buka_kelas() -> int:
    """Titik masuk perintah `siakad-buka-kelas`."""
    return jalankan_aman(main_buka_kelas)


if __name__ == "__main__":
    sys.exit(jalankan())
