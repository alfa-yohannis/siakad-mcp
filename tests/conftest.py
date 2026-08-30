"""Perkakas bersama untuk unit test SIAKAD.

Seluruh test berjalan tanpa jaringan: SIAKAD digantikan objek tiruan, sehingga
bisa dijalankan kapan saja tanpa kredensial.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

# Data contoh; nama tokoh dan nomor induk di seluruh berkas uji sengaja dikarang.
BARIS_KELAS = {
    "DOSEN_ID": "0000000",
    "KD_MATA_KULIAH": "IF30812",
    "NM_MATA_KULIAH": "Pemrograman Berorientasi Objek",
    "TAHUN_AJARAN": "2025",
    "TIPE_SEMESTER": "2",
    "JAM_MULAI": "09:20:00.0000000",
    "JAM_SELESAI": "11:05:00.0000000",
    "NAMA_DOSEN": "King Kong, S.T.,M.T.,Ph.D.",
    "HARI": "THURSDAY",
    "NM_JURUSAN": "Informatika",
    "KELOMPOK_KELAS": "Kelas B",
}

HALAMAN_BAP = """
<html><head><style>@page { margin-top: 120px; }</style></head><body>
<table class="content">
  <tr><td>Tanggal</td><td>Topik pembahasan</td><td>Deskripsi</td><td width="8%">Paraf</td></tr>
  <tr><td>05/02/2026</td><td>Session-01</td><td>Pengantar</td><td></td></tr>
  <tr><td>12/02/2026</td><td>Session-02</td><td>Kelas &amp; objek</td><td></td></tr>
</table>
<table>
  <tr><td style="width:70%"></td><td style="height:125px">Tangerang, </td></tr>
  <tr><td></td><td>Spider Man, S.Kom., M.Kom</td></tr>
  <tr><td></td><td>Kaprodi Informatika</td></tr>
</table>
</body></html>
"""


# PNG 1x1 piksel; cukup untuk menguji penyisipan tanpa bergantung berkas asli
PNG_SEPIKSEL = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def isi_folder_tanda_tangan(direktori: Path, *nama: str) -> Path:
    """Buat folder tanda tangan tiruan berisi berkas PNG bernama `nama`."""
    from base64 import b64decode

    direktori.mkdir(parents=True, exist_ok=True)
    for satu in nama:
        (direktori / f"{satu}.png").write_bytes(b64decode(PNG_SEPIKSEL))
    return direktori


class JawabanTiruan:
    """Pengganti requests.Response seperlunya saja."""

    def __init__(self, isi_json=None, teks="", status_code=200):
        self._json = isi_json
        self.text = teks
        self.status_code = status_code

    def json(self):
        if self._json is None:
            raise ValueError("bukan JSON")
        return self._json


class KlienTiruan:
    """Pengganti KlienSiakad yang tidak menyentuh jaringan sama sekali."""

    def __init__(self, halaman_hasil: list | None = None):
        self.url_beranda = "https://siakad.pradita.ac.id/dashboard"
        self.halaman_hasil = halaman_hasil or []
        self.permintaan: list[tuple[str, dict]] = []

    def baca_token_csrf(self, sup) -> str:
        return "token-uji"

    def ambil_halaman(self, path):
        return JawabanTiruan(teks="<html><meta name='csrf-token' content='token-uji'></html>")


@pytest.fixture
def baris_kelas() -> dict:
    return dict(BARIS_KELAS)


@pytest.fixture
def halaman_bap() -> str:
    return HALAMAN_BAP
