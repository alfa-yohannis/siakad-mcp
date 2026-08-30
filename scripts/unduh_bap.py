"""Unduh bukti Berita Acara Perkuliahan (BAP) dan Kehadiran dari SIAKAD.

Untuk tiap kelas yang diampu pada satu periode, dua berkas PDF dihasilkan:

    <KODE> - <Nama Mata Kuliah>[ - Kelas X] - BAP.pdf
    <KODE> - <Nama Mata Kuliah>[ - Kelas X] - Kehadiran.pdf

Halaman BAP dibubuhi paraf dosen pada tiap pertemuan dan tanda tangan pejabat
penanda tangan, diambil dari <akar proyek>/digital_signs/.

Pakai:
    python scripts/unduh_bap.py --tahun 2025 --semester 2 --tujuan ../2026-08/pengajaran
    python scripts/unduh_bap.py --tahun 2025 --semester 2 --kode IF30812 --timpa
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from dependensi import pastikan_dependensi

# harus dipanggil sebelum impor paket pihak ketiga di bawahnya
pastikan_dependensi()

from berita_acara import JENIS_BUKTI, BeritaAcaraKuliah
from konfigurasi import AKAR_PROYEK, DIR_DATA
from siakad_client import KlienSiakad, SiakadError


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
    pengurai = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    pengurai.add_argument("--tahun", required=True, help="Tahun ajaran, mis. 2025 untuk 2025/2026")
    pengurai.add_argument("--semester", required=True, choices=["1", "2", "3"],
                          help="1 ganjil, 2 genap, 3 semester pendek")
    pengurai.add_argument("--prodi", default="", help="Kode prodi, mis. TI. Kosong berarti semua")
    pengurai.add_argument("--kode", default="", help="Batasi ke satu kode mata kuliah")
    pengurai.add_argument("--tujuan", default=str(DIR_DATA / "bap"), help="Direktori penyimpanan PDF")
    pengurai.add_argument("--tanggal", default=tanggal_hari_ini(),
                          help="Tanggal pada blok tanda tangan (bawaan: hari ini)")
    pengurai.add_argument("--timpa", action="store_true", help="Tulis ulang berkas yang sudah ada")
    pengurai.add_argument("--tanpa-ttd", action="store_true", help="Cetak tanpa membubuhkan tanda tangan")
    pengurai.add_argument("--hanya-daftar", action="store_true", help="Tampilkan kelasnya saja, tanpa mengunduh")
    return pengurai.parse_args()


def main() -> int:
    argumen = baca_argumen()
    tujuan = Path(argumen.tujuan)
    if not tujuan.is_absolute():
        tujuan = (AKAR_PROYEK / tujuan).resolve()

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
                )
            except (SiakadError, SystemExit) as galat:
                print(f"  GAGAL {satu.label} [{jenis}]: {galat}")
                gagal += 1
                continue
            ukuran_kb = berkas.stat().st_size // 1024
            print(f"  {berkas.name}  ({ukuran_kb} KB)")

    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
