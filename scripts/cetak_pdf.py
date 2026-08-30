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

# ukuran kertas mengikuti hasil cetak manual yang sudah dipakai selama ini
UKURAN_BAWAAN = "A4"
BATAS_WAKTU_DETIK = 180

KANDIDAT_CHROME = ["google-chrome", "chromium", "chromium-browser", "google-chrome-stable"]


def cari_chrome() -> str:
    """Cari Chrome/Chromium yang terpasang; kesalahan dijelaskan kalau tidak ada."""
    for nama in KANDIDAT_CHROME:
        lokasi = shutil.which(nama)
        if lokasi:
            return lokasi
    raise SystemExit(
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
            "--virtual-time-budget=15000",
            "--no-pdf-header-footer",
            f"--print-to-pdf={tujuan}",
            sumber.as_uri(),
        ]
        hasil = subprocess.run(perintah, capture_output=True, timeout=BATAS_WAKTU_DETIK)

    if not tujuan.is_file() or tujuan.stat().st_size == 0:
        pesan = (hasil.stderr or b"").decode(errors="ignore")[-400:]
        raise SystemExit(f"Gagal mencetak {tujuan.name}: {pesan}")
    return tujuan
