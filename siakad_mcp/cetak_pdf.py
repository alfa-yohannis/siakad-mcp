"""Ubah halaman cetak SIAKAD menjadi PDF.

Menu laporan SIAKAD tidak mengeluarkan PDF; yang dikirimnya halaman HTML siap
cetak, lalu pemakai menekan Ctrl+P di browser. Modul ini menggantikan langkah
itu dengan Chrome headless supaya hasilnya sama tanpa perlu dibuka manual.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from siakad_mcp.konfigurasi import baca_angka, baca_pengaturan


class CetakError(RuntimeError):
    """Pencetakan PDF gagal — Chrome tidak ada, atau hasilnya kosong.

    Sengaja bukan SystemExit: pustaka tidak boleh menghentikan program yang
    memakainya. Titik masuk CLI-lah yang menangkap ini dan keluar dengan rapi.
    """

# ukuran kertas mengikuti hasil cetak manual yang sudah dipakai selama ini
UKURAN_BAWAAN = "A4"
BATAS_WAKTU_BAWAAN_DETIK = 180
# waktu tunggu Chrome memuat CSS dan gambar sebelum halaman dicetak
JATAH_MUAT_BAWAAN_MS = 15000

KANDIDAT_CHROME = ["google-chrome", "chromium", "chromium-browser", "google-chrome-stable"]


def cari_chrome() -> str:
    """Chrome/Chromium yang dipakai mencetak.

    SIAKAD_CHROME dipakai kalau diisi — perlu di mesin yang binernya tidak ada
    di PATH atau memasang lebih dari satu peramban.
    """
    ditetapkan = baca_pengaturan("SIAKAD_CHROME")
    if ditetapkan:
        if not shutil.which(ditetapkan) and not Path(ditetapkan).is_file():
            raise CetakError(f"SIAKAD_CHROME menunjuk {ditetapkan}, tapi berkasnya tidak ada")
        return ditetapkan

    for nama in KANDIDAT_CHROME:
        lokasi = shutil.which(nama)
        if lokasi:
            return lokasi
    raise CetakError(
        "Chrome/Chromium tidak ditemukan. Pasang salah satunya, atau simpan "
        "halaman cetaknya lalu cetak manual dari browser."
    )


def sisipkan_ukuran_kertas(html: str, ukuran: str) -> str:
    """Tetapkan ukuran kertas pada halaman cetak.

    Halaman dari SIAKAD hanya mengatur margin, tanpa `size`, sehingga tabel lebar
    seperti daftar kehadiran akan terpotong kalau ukurannya tidak ditentukan.
    """
    aturan = f"<style>@page {{ size: {ukuran}; }}</style>"
    if "</head>" in html:
        return html.replace("</head>", f"{aturan}</head>", 1)
    return aturan + html


def cetak_html_ke_pdf(html: str, tujuan: Path, *, ukuran: str = UKURAN_BAWAAN) -> Path:
    """Cetak HTML jadi PDF di `tujuan`, kembalikan path berkasnya."""
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    chrome = cari_chrome()

    with tempfile.TemporaryDirectory() as ruang_kerja:
        ruang = Path(ruang_kerja)
        sumber = ruang / "cetak.html"
        sumber.write_text(sisipkan_ukuran_kertas(html, ukuran), encoding="utf-8")

        perintah = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={ruang / 'profil'}",
            # beri waktu CSS dan gambar dari server SIAKAD selesai dimuat
            f"--virtual-time-budget={baca_angka('SIAKAD_JATAH_MUAT_MS', JATAH_MUAT_BAWAAN_MS)}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={tujuan}",
            sumber.as_uri(),
        ]
        hasil = subprocess.run(perintah, capture_output=True, timeout=baca_angka("SIAKAD_BATAS_CETAK_DETIK", BATAS_WAKTU_BAWAAN_DETIK))

    if not tujuan.is_file() or tujuan.stat().st_size == 0:
        pesan = (hasil.stderr or b"").decode(errors="ignore")[-400:]
        raise CetakError(f"Gagal mencetak {tujuan.name}: {pesan}")
    return tujuan
