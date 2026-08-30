#!/usr/bin/env python3
"""Contoh memakai siakad-mcp sebagai pustaka dari program Python sendiri.

Pasang lalu jalankan:

    pip install siakad-mcp
    SIAKAD_USERNAME=... SIAKAD_PASSWORD=... python examples/pustaka.py

Kredensial boleh juga ditaruh di .env pada akar proyek, atau diberikan dari kode
lewat atur_setelan() seperti dicontohkan di bawah.
"""

from __future__ import annotations

import os
import sys

from siakad_mcp import (
    BeritaAcaraKuliah,
    CetakError,
    KlienSiakad,
    KonfigurasiError,
    SiakadError,
    atur_setelan,
)

TAHUN, SEMESTER = "2025", "2"


def main() -> int:
    # Setelan dari kode: berguna buat aplikasi yang menyimpan konfigurasinya
    # sendiri dan tidak mau bergantung pada berkas .env maupun siakad.yaml.
    # Kalau kampus Anda memakai instance lain, buka komentar baris ini:
    # atur_setelan(base_url="https://siakad.kampuslain.ac.id", kota="Bandung")

    username = os.environ.get("SIAKAD_USERNAME")
    password = os.environ.get("SIAKAD_PASSWORD")
    if username and password:
        atur_setelan(SIAKAD_USERNAME=username, SIAKAD_PASSWORD=password)

    try:
        # tanpa argumen, kredensial diambil dari setelan/.env di atas
        klien = KlienSiakad().login()
    except (SiakadError, KonfigurasiError) as galat:
        print(f"Login gagal: {galat}", file=sys.stderr)
        return 1

    laporan = BeritaAcaraKuliah(klien)

    print(f"Kelas yang diampu pada {TAHUN}/{SEMESTER}:")
    kelas_ditemukan = laporan.daftar_kelas(TAHUN, SEMESTER)
    for kelas in kelas_ditemukan:
        print(f"  {kelas.label}  [{kelas.hari} {kelas.jam_mulai[:5]}]")

    if not kelas_ditemukan:
        print("  (tidak ada)")
        return 0

    # Topik pertemuan dan rekap kehadiran kelas pertama, apa adanya dari SIAKAD
    detail = laporan.detail(kelas_ditemukan[0])
    topik = detail.get("rs_topik") or []
    print(f"\nTopik {kelas_ditemukan[0].label} ({len(topik)} pertemuan):")
    for satu in topik[:5]:
        print(f"  {satu.get('TGL_ABSENSI')} - {str(satu.get('TOPIK_PEMBAHASAN'))[:55]}")

    # Satu berkas bukti; folder tanda tangan boleh ditunjuk lewat dir_tanda_tangan
    print("\nMengunduh BAP kelas pertama...")
    try:
        berkas = laporan.unduh_bukti(kelas_ditemukan[0], "bap", "bukti/pengajaran")
    except (SiakadError, CetakError) as galat:
        print(f"  gagal: {galat}", file=sys.stderr)
        return 1
    print(f"  {berkas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
