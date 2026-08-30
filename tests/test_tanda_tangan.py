"""Uji pembubuhan tanda tangan pada halaman cetak BAP."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import tanda_tangan
from cetak_pdf import sisipkan_ukuran_kertas


@pytest.fixture
def dir_tanda_tangan(tmp_path, monkeypatch) -> Path:
    """Folder tanda tangan tiruan berisi satu berkas PNG kecil."""
    from base64 import b64decode

    # PNG 1x1 piksel; cukup untuk menguji penyisipan tanpa bergantung berkas asli
    png = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    (tmp_path / "kong.png").write_bytes(png)
    (tmp_path / "spider.png").write_bytes(png)
    monkeypatch.setattr(tanda_tangan, "DIR_TANDA_TANGAN", tmp_path)
    return tmp_path


def test_tanda_tangan_dicocokkan_dari_potongan_nama(dir_tanda_tangan):
    berkas = tanda_tangan.cari_tanda_tangan("King Kong, S.T.,M.T.,Ph.D.")

    assert berkas is not None
    assert berkas.name == "kong.png"


def test_nama_tanpa_berkas_tanda_tangan_menghasilkan_none(dir_tanda_tangan):
    assert tanda_tangan.cari_tanda_tangan("Dr.Eng. Iron Man, S.Si., M.Eng.") is None


def test_paraf_dibubuhkan_pada_setiap_pertemuan(dir_tanda_tangan, halaman_bap):
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong")
    sup = BeautifulSoup(hasil, "lxml")

    baris_paraf = [
        baris for baris in sup.find_all("tr") if baris.find_all("td") and baris.find("img")
    ]
    assert len(baris_paraf) == 3  # dua pertemuan + blok tanda tangan pejabat


def test_tanda_tangan_tidak_diberi_batas_lebar(dir_tanda_tangan, halaman_bap):
    """Membatasi lebar sekaligus tinggi akan memipihkan tanda tangannya."""
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong")

    for gambar in BeautifulSoup(hasil, "lxml").find_all("img"):
        assert "width:auto" in gambar["style"]
        assert "max-width" not in gambar["style"]


def test_pejabat_ditandatangani_dan_tanggalnya_terisi(dir_tanda_tangan, halaman_bap):
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong", tanggal="19 Agustus 2026")

    assert "Tangerang, 19 Agustus 2026" in hasil


def test_tanggal_tetap_terisi_walau_tanda_tangan_pejabat_tidak_ada(tmp_path, monkeypatch, halaman_bap):
    monkeypatch.setattr(tanda_tangan, "DIR_TANDA_TANGAN", tmp_path)
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong", tanggal="19 Agustus 2026")

    assert "Tangerang, 19 Agustus 2026" in hasil
    assert "<img" not in hasil


def test_ukuran_kertas_disisipkan_ke_halaman_cetak(halaman_bap):
    hasil = sisipkan_ukuran_kertas(halaman_bap, "A3")

    assert "@page { size: A3; }" in hasil
    assert hasil.count("</head>") == 1
