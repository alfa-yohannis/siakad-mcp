"""SIAKAD MCP — ambil bukti pengajaran dari SIAKAD sebagai pustaka, REST API, atau MCP.

Tiga cara memakainya, semuanya dari paket yang sama:

    pustaka   from siakad_mcp import KlienSiakad, BeritaAcaraKuliah
              klien = KlienSiakad("nama@kampus.ac.id", "sandi").login()
              for kelas in BeritaAcaraKuliah(klien).daftar_kelas("2025", "2"):
                  print(kelas.label)

Tiga menu SIAKAD tersedia, semuanya berangkat dari satu `KlienSiakad`:

    BeritaAcaraKuliah   topik pertemuan, rekap kehadiran, PDF BAP & Kehadiran
    JadwalMengajar      jadwal satu periode: hari, jam, ruang, SKS
    DaftarHadir         pertemuan per tanggal dan daftar mahasiswanya

    REST API  from siakad_mcp.api import router
              app_saya.include_router(router, prefix="/siakad")

    MCP       from siakad_mcp.mcp_server import server
              server.run()                       # atau lewat perintah `siakad-mcp`

Setelan bisa diberikan tanpa berkas apa pun, berguna buat proyek yang menyimpan
konfigurasinya sendiri:

    from siakad_mcp import atur_setelan
    atur_setelan(base_url="https://siakad.kampuslain.ac.id", kota="Jakarta")

Impor di sini sengaja hanya menyentuh modul inti. `siakad_mcp.api` butuh FastAPI
dan `siakad_mcp.mcp_server` butuh paket mcp, jadi keduanya diimpor sendiri oleh
yang memerlukan — pemakai pustaka tidak dipaksa memasang keduanya.
"""

from __future__ import annotations

from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah, Kelas
from siakad_mcp.cetak_pdf import CetakError, cetak_html_ke_pdf
from siakad_mcp.daftar_hadir import DaftarHadir, Mahasiswa, Pertemuan
from siakad_mcp.jadwal import JadwalMengajar, SlotJadwal
from siakad_mcp.konfigurasi import (
    KonfigurasiError,
    akar_proyek,
    atur_akar_proyek,
    atur_setelan,
    baca_pengaturan,
)
from siakad_mcp.menu import MenuSiakad
from siakad_mcp.siakad_client import KlienSiakad, SiakadError
from siakad_mcp.tanda_tangan import cari_tanda_tangan, sisipkan_tanda_tangan

__version__ = "1.1.0"

__all__ = [
    # sesi dan data
    "KlienSiakad",
    "MenuSiakad",
    "BeritaAcaraKuliah",
    "Kelas",
    "JENIS_BUKTI",
    "JadwalMengajar",
    "SlotJadwal",
    "DaftarHadir",
    "Pertemuan",
    "Mahasiswa",
    # tanda tangan dan cetak
    "sisipkan_tanda_tangan",
    "cari_tanda_tangan",
    "cetak_html_ke_pdf",
    # setelan
    "atur_setelan",
    "atur_akar_proyek",
    "baca_pengaturan",
    "akar_proyek",
    # kesalahan
    "SiakadError",
    "KonfigurasiError",
    "CetakError",
    "__version__",
]
