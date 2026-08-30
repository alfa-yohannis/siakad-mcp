"""Dasar bersama untuk menu SIAKAD yang isinya datang lewat AJAX.

Tiga menu yang dipakai paket ini berperilaku persis sama:

    /report/berita_acara_kuliah   topik pertemuan dan rekap kehadiran
    /dosen/jadwal_mengajar        jadwal mengajar satu periode
    /dosen/daftar_hadir           pertemuan dan daftar mahasiswanya

Halamannya dikirim kosong; tabelnya menyusul dari POST ke `<path menu>/search`
memakai token CSRF halaman itu, dan hasilnya dipecah beberapa halaman. Yang
berbeda hanya path menu dan nama parameter pencariannya, jadi bagian yang sama
ditulis sekali di sini dan tiap menu tinggal mewarisinya.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from siakad_mcp.konfigurasi import baca_angka, baca_pengaturan
from siakad_mcp.siakad_client import KlienSiakad, SiakadError

BARIS_PER_HALAMAN_BAWAAN = 15
BATAS_LAPORAN_BAWAAN_DETIK = 300

# SIAKAD memakai nama hari bahasa Inggris; yang dibaca manusia bahasa Indonesia
HARI_INDONESIA = {
    "MONDAY": "Senin",
    "TUESDAY": "Selasa",
    "WEDNESDAY": "Rabu",
    "THURSDAY": "Kamis",
    "FRIDAY": "Jumat",
    "SATURDAY": "Sabtu",
    "SUNDAY": "Minggu",
}


def baris_per_halaman() -> int:
    """Jumlah baris per halaman hasil pencarian, mengikuti setelan server."""
    return baca_angka("SIAKAD_BARIS_PER_HALAMAN", BARIS_PER_HALAMAN_BAWAAN)


def nama_hari(hari: str) -> str:
    """'MONDAY' -> 'Senin'. Nilai yang tidak dikenal dibiarkan apa adanya."""
    return HARI_INDONESIA.get((hari or "").strip().upper(), hari or "")


def jam_ringkas(jam: str) -> str:
    """'08:25:00.0000000' -> '08:25'. SIAKAD selalu mengirim jam selengkap itu."""
    return (jam or "")[:5]


class MenuSiakad:
    """Satu menu SIAKAD beserta endpoint AJAX-nya, untuk satu sesi login.

    Turunannya cukup menetapkan `path_bawaan` (dan `kunci_path` kalau path itu
    boleh dipindah lewat setelan), lalu memakai `kirim()` untuk endpoint tunggal
    atau `cari_semua()` untuk tabel yang berhalaman.
    """

    path_bawaan: str = ""
    kunci_path: str = ""

    def __init__(self, klien: KlienSiakad):
        self.klien = klien
        self._token = ""

    def path(self) -> str:
        """Path menu ini; instance lain bisa menaruhnya di alamat berbeda."""
        if self.kunci_path:
            return baca_pengaturan(self.kunci_path, self.path_bawaan)
        return self.path_bawaan

    def token(self) -> str:
        """Token CSRF halaman menu, diambil sekali lalu dipakai ulang."""
        if not self._token:
            sup = BeautifulSoup(self.klien.ambil_halaman(self.path()).text, "lxml")
            self._token = self.klien.baca_token_csrf(sup)
        return self._token

    def kirim(self, endpoint: str, muatan: dict):
        """POST ke salah satu endpoint menu ini dengan token CSRF yang benar."""
        return self.klien.sesi_http.post(
            f"{self.klien.base_url}{self.path()}/{endpoint}",
            headers={"X-CSRF-TOKEN": self.token(), "X-Requested-With": "XMLHttpRequest"},
            data={"_token": self.token(), **muatan},
            timeout=baca_angka("SIAKAD_BATAS_LAPORAN_DETIK", BATAS_LAPORAN_BAWAAN_DETIK),
        )

    def cari_semua(self, endpoint: str, muatan: dict, *, keterangan: str = "") -> list[dict]:
        """Seluruh baris sebuah tabel, halaman demi halaman sampai habis.

        `muatan` berisi parameter pencarian tanpa `page` — nomor halamannya
        ditambahkan di sini. `sort_search` dan `order_search` sengaja tidak
        pernah ikut: SIAKAD membalas HTTP 500 kalau keduanya terkirim kosong.
        """
        semua: list[dict] = []
        halaman = 1
        while True:
            jawaban = self.kirim(endpoint, {"page": halaman, **muatan})
            if jawaban.status_code != 200:
                nama = keterangan or f"{self.path()}/{endpoint}"
                raise SiakadError(f"Pencarian {nama} gagal (HTTP {jawaban.status_code})")

            isi = jawaban.json().get("rs_data", {})
            baris = isi.get("data") or []
            semua.extend(baris)
            if len(baris) < baris_per_halaman() or len(semua) >= int(isi.get("total") or 0):
                return semua
            halaman += 1
