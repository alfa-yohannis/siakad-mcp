"""Uji pembubuhan tanda tangan pada halaman cetak BAP."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from siakad_mcp import konfigurasi, tanda_tangan
from siakad_mcp.cetak_pdf import sisipkan_ukuran_kertas
from conftest import isi_folder_tanda_tangan


@pytest.fixture(autouse=True)
def tanpa_env_tanda_tangan(monkeypatch):
    """Lingkungan pengembang tidak boleh ikut menentukan hasil uji."""
    monkeypatch.delenv("BKD_TANDA_TANGAN", raising=False)


@pytest.fixture
def dir_tanda_tangan(tmp_path) -> Path:
    """Folder tanda tangan tiruan, diberikan ke fungsi sebagai parameter."""
    return isi_folder_tanda_tangan(tmp_path / "ttd", "kong", "spider")


def test_tanda_tangan_dicocokkan_dari_potongan_nama(dir_tanda_tangan):
    berkas = tanda_tangan.cari_tanda_tangan("King Kong, S.T.,M.T.,Ph.D.", dir_tanda_tangan)

    assert berkas is not None
    assert berkas.name == "kong.png"


def test_nama_tanpa_berkas_tanda_tangan_menghasilkan_none(dir_tanda_tangan):
    assert tanda_tangan.cari_tanda_tangan("Dr.Eng. Iron Man, S.Si., M.Eng.", dir_tanda_tangan) is None


def test_paraf_dibubuhkan_pada_setiap_pertemuan(dir_tanda_tangan, halaman_bap):
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong", direktori=dir_tanda_tangan)
    sup = BeautifulSoup(hasil, "lxml")

    baris_paraf = [
        baris for baris in sup.find_all("tr") if baris.find_all("td") and baris.find("img")
    ]
    assert len(baris_paraf) == 3  # dua pertemuan + blok tanda tangan pejabat


def test_tanda_tangan_tidak_diberi_batas_lebar(dir_tanda_tangan, halaman_bap):
    """Membatasi lebar sekaligus tinggi akan memipihkan tanda tangannya."""
    hasil = tanda_tangan.sisipkan_tanda_tangan(halaman_bap, "King Kong", direktori=dir_tanda_tangan)

    for gambar in BeautifulSoup(hasil, "lxml").find_all("img"):
        assert "width:auto" in gambar["style"]
        assert "max-width" not in gambar["style"]


def test_pejabat_ditandatangani_dan_tanggalnya_terisi(dir_tanda_tangan, halaman_bap):
    hasil = tanda_tangan.sisipkan_tanda_tangan(
        halaman_bap, "King Kong", tanggal="19 Agustus 2026", direktori=dir_tanda_tangan
    )

    assert "Tangerang, 19 Agustus 2026" in hasil


def test_tanggal_tetap_terisi_walau_tanda_tangan_pejabat_tidak_ada(tmp_path, halaman_bap):
    kosong = tmp_path / "kosong"
    kosong.mkdir()
    hasil = tanda_tangan.sisipkan_tanda_tangan(
        halaman_bap, "King Kong", tanggal="19 Agustus 2026", direktori=kosong
    )

    assert "Tangerang, 19 Agustus 2026" in hasil
    assert "<img" not in hasil


def test_folder_dari_pemanggil_dipakai_apa_adanya(tmp_path):
    """Folder yang diberikan pemanggil dipakai, bukan bawaan aplikasi."""
    milik_pemanggil = isi_folder_tanda_tangan(tmp_path / "punya-klien", "kong")

    assert tanda_tangan.cari_dir_tanda_tangan(milik_pemanggil) == milik_pemanggil
    assert tanda_tangan.cari_tanda_tangan("King Kong", milik_pemanggil) is not None


def test_folder_dari_pemanggil_menang_atas_env(tmp_path, monkeypatch):
    """Parameter pemanggil lebih tinggi daripada BKD_TANDA_TANGAN."""
    lewat_env = isi_folder_tanda_tangan(tmp_path / "env", "spider")
    milik_pemanggil = isi_folder_tanda_tangan(tmp_path / "klien", "kong")
    monkeypatch.setenv("BKD_TANDA_TANGAN", str(lewat_env))

    assert tanda_tangan.cari_dir_tanda_tangan(milik_pemanggil) == milik_pemanggil
    # 'spider' hanya ada di folder env, jadi tidak boleh ikut terbaca
    assert tanda_tangan.cari_tanda_tangan("Spider Man", milik_pemanggil) is None


def test_folder_pemanggil_yang_tidak_ada_tidak_jatuh_ke_bawaan(tmp_path):
    """Salah ketik folder harus terlihat sebagai tanda tangan yang hilang.

    Kalau permintaan eksplisit diam-diam diganti folder bawaan, BAP bisa terbit
    dengan tanda tangan dari folder yang tidak diminta siapa pun.
    """
    tidak_ada = tmp_path / "salah-ketik"

    assert tanda_tangan.cari_dir_tanda_tangan(tidak_ada) == tidak_ada
    assert tanda_tangan.daftar_tanda_tangan(tidak_ada) == {}


def test_env_dipakai_kalau_pemanggil_tidak_menentukan(tmp_path, monkeypatch):
    lewat_env = isi_folder_tanda_tangan(tmp_path / "env", "spider")
    monkeypatch.setenv("BKD_TANDA_TANGAN", str(lewat_env))

    assert tanda_tangan.cari_dir_tanda_tangan() == lewat_env


def test_folder_relatif_dihitung_dari_akar_proyek():
    """Sama seperti --tujuan, path relatif bukan dihitung dari direktori kerja."""
    hasil = tanda_tangan.cari_dir_tanda_tangan("bukti/ttd")

    assert hasil.is_absolute()
    assert hasil == konfigurasi.akar_proyek() / "bukti/ttd"


def test_ukuran_kertas_disisipkan_ke_halaman_cetak(halaman_bap):
    hasil = sisipkan_ukuran_kertas(halaman_bap, "A3")

    assert "@page { size: A3; }" in hasil
    assert hasil.count("</head>") == 1
