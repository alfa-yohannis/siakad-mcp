"""Uji pembacaan kelas dan penamaan berkas bukti."""

from __future__ import annotations

import pytest

from siakad_mcp import berita_acara
from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah, Kelas
from conftest import JawabanTiruan, KlienTiruan, isi_folder_tanda_tangan


def test_kelas_dibaca_dari_baris_hasil_pencarian(baris_kelas):
    kelas = Kelas.dari_baris(baris_kelas)

    assert kelas.kode_mk == "IF30812"
    assert kelas.kelompok_kelas == "Kelas B"
    assert kelas.label == "IF30812 - Pemrograman Berorientasi Objek (Kelas B)"


def test_kelompok_kelas_strip_dianggap_tidak_ada(baris_kelas):
    """SIAKAD menulis '-' untuk kelas tunggal; itu bukan nama kelas."""
    kelas = Kelas.dari_baris({**baris_kelas, "KELOMPOK_KELAS": "-"})

    assert kelas.kelompok_kelas == ""
    assert kelas.label == "IF30812 - Pemrograman Berorientasi Objek"


def test_nama_berkas_mengikuti_pola_yang_sudah_dipakai(baris_kelas):
    kelas = Kelas.dari_baris(baris_kelas)

    assert kelas.nama_berkas("BAP") == "IF30812 - Pemrograman Berorientasi Objek - Kelas B - BAP.pdf"
    assert kelas.nama_berkas("Kehadiran").endswith(" - Kelas B - Kehadiran.pdf")


def test_nama_berkas_membuang_karakter_terlarang(baris_kelas):
    kelas = Kelas.dari_baris({**baris_kelas, "NM_MATA_KULIAH": "Basis Data / Lanjut", "KELOMPOK_KELAS": "-"})

    assert "/" not in kelas.nama_berkas("BAP")


def test_parameter_permintaan_lengkap(baris_kelas):
    parameter = Kelas.dari_baris(baris_kelas).sebagai_parameter()

    assert set(parameter) == {
        "DOSEN_ID", "KD_MATA_KULIAH", "TAHUN_AJARAN", "TIPE_SEMESTER", "JAM_MULAI", "HARI"
    }


def test_daftar_kelas_menelusuri_seluruh_halaman(baris_kelas, monkeypatch):
    """Hasil pencarian dipecah 15 baris per halaman; semuanya harus terambil."""
    halaman_satu = [dict(baris_kelas, KD_MATA_KULIAH=f"MK{nomor:02d}") for nomor in range(15)]
    halaman_dua = [dict(baris_kelas, KD_MATA_KULIAH="MK15")]
    urutan = [
        JawabanTiruan({"rs_data": {"data": halaman_satu, "total": 16}}),
        JawabanTiruan({"rs_data": {"data": halaman_dua, "total": 16}}),
    ]

    laporan = BeritaAcaraKuliah(KlienTiruan())
    monkeypatch.setattr(laporan, "kirim", lambda endpoint, muatan: urutan.pop(0))

    kelas = laporan.daftar_kelas("2025", "2")
    assert len(kelas) == 16
    assert kelas[-1].kode_mk == "MK15"


def test_jenis_bukti_hanya_bap_dan_kehadiran():
    assert set(JENIS_BUKTI) == {"bap", "kehadiran"}


def test_jenis_bukti_asing_ditolak(baris_kelas):
    from siakad_mcp.siakad_client import SiakadError

    laporan = BeritaAcaraKuliah(KlienTiruan())
    with pytest.raises(SiakadError, match="tidak dikenal"):
        laporan.halaman_cetak(Kelas.dari_baris(baris_kelas), "nilai")


@pytest.fixture
def bap_tercetak(monkeypatch, halaman_bap, tmp_path):
    """Cegat pencetakan PDF supaya HTML yang akan dicetak bisa diperiksa."""
    tercetak = {}

    def cetak_tiruan(html, tujuan, *, ukuran="A4"):
        tercetak["html"] = html
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_bytes(b"%PDF-uji")
        return tujuan

    monkeypatch.setattr(berita_acara, "cetak_html_ke_pdf", cetak_tiruan)
    monkeypatch.setattr(BeritaAcaraKuliah, "halaman_cetak", lambda self, kelas, jenis: halaman_bap)
    return tercetak


def test_folder_tanda_tangan_dari_pemanggil_dipakai_saat_unduh(bap_tercetak, baris_kelas, tmp_path):
    """Folder yang dikirim klien harus sampai ke pembubuhan tanda tangan."""
    ttd = isi_folder_tanda_tangan(tmp_path / "ttd-klien", "kong", "spider")

    laporan = BeritaAcaraKuliah(KlienTiruan())
    laporan.unduh_bukti(
        Kelas.dari_baris(baris_kelas), "bap", tmp_path / "keluaran", dir_tanda_tangan=ttd
    )

    assert "<img" in bap_tercetak["html"]


def test_folder_tanda_tangan_kosong_menghasilkan_bap_polos(bap_tercetak, baris_kelas, tmp_path):
    kosong = tmp_path / "ttd-kosong"
    kosong.mkdir()

    laporan = BeritaAcaraKuliah(KlienTiruan())
    laporan.unduh_bukti(
        Kelas.dari_baris(baris_kelas), "bap", tmp_path / "keluaran", dir_tanda_tangan=kosong
    )

    assert "<img" not in bap_tercetak["html"]
