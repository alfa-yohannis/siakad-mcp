"""Uji pembacaan jadwal mengajar."""

from __future__ import annotations

import pytest

from siakad_mcp.jadwal import JadwalMengajar, SlotJadwal
from conftest import JawabanTiruan, KlienTiruan


BARIS_JADWAL = {
    "DOSEN_ID": "0000000",
    "KD_MATA_KULIAH": "IF31613",
    "TAHUN_AJARAN": "2026",
    "TIPE_SEMESTER": "1",
    "HARI": "MONDAY",
    "JAM_MULAI": "08:25:00.0000000",
    "JAM_SELESAI": "11:05:00.0000000",
    "KD_RUANG": "BLB58 ",
    "KELOMPOK_KELAS": None,
    "nm_jurusan": "Informatika",
    "data_matkul": {"KD_MATA_KULIAH": "IF31613", "NM_MATA_KULIAH": "Arsitektur Perangkat Lunak", "SKS": 3},
    "data_ruang": {"KD_RUANG": "BLB58 ", "NM_RUANG": "A306"},
    "data_tahun_ajaran": {"NM_TAHUN_AJARAN": "2026 / 2027"},
    "data_tipe_semester": {"NM_TIPE_SEMESTER": "GANJIL"},
}


@pytest.fixture
def baris_jadwal() -> dict:
    return dict(BARIS_JADWAL)


def test_slot_dibaca_beserta_objek_bersarangnya(baris_jadwal):
    """Nama mata kuliah, ruang, dan periode datang sebagai objek terpisah."""
    slot = SlotJadwal.dari_baris(baris_jadwal)

    assert slot.nama_mk == "Arsitektur Perangkat Lunak"
    assert slot.ruang == "A306"
    assert slot.sks == "3"
    assert slot.nama_periode == "2026 / 2027 GANJIL"


def test_objek_bersarang_yang_hilang_tidak_menggagalkan(baris_jadwal):
    """Jadwal tanpa ruang tetap harus bisa ditampilkan."""
    slot = SlotJadwal.dari_baris({**baris_jadwal, "data_ruang": None, "data_matkul": None})

    assert slot.nama_mk == ""
    assert slot.ruang == "BLB58"
    assert slot.label.startswith("IF31613 - ")


def test_kelompok_kelas_kosong_tidak_muncul_di_label(baris_jadwal):
    slot = SlotJadwal.dari_baris(baris_jadwal)

    assert slot.label == "IF31613 - Arsitektur Perangkat Lunak"
    assert SlotJadwal.dari_baris({**baris_jadwal, "KELOMPOK_KELAS": "Kelas A"}).label.endswith("(Kelas A)")


def test_waktu_dibaca_manusia(baris_jadwal):
    assert SlotJadwal.dari_baris(baris_jadwal).waktu == "Senin 08:25-11:05"


def test_daftar_diurutkan_menurut_kalender_bukan_abjad(baris_jadwal, monkeypatch):
    """Senin harus lebih dulu dari Selasa, dan jam lebih awal lebih dulu."""
    baris = [
        {**baris_jadwal, "HARI": "TUESDAY", "JAM_MULAI": "09:20:00.0000000"},
        {**baris_jadwal, "HARI": "MONDAY", "JAM_MULAI": "13:00:00.0000000"},
        {**baris_jadwal, "HARI": "MONDAY", "JAM_MULAI": "08:25:00.0000000"},
    ]
    jadwal = JadwalMengajar(KlienTiruan())
    monkeypatch.setattr(
        jadwal, "kirim", lambda endpoint, muatan: JawabanTiruan({"rs_data": {"data": baris, "total": 3}})
    )

    hasil = jadwal.daftar("2026", "1")
    assert [satu.waktu for satu in hasil] == [
        "Senin 08:25-11:05", "Senin 13:00-11:05", "Selasa 09:20-11:05",
    ]


def test_parameter_pencarian_tanpa_sort_dan_order(baris_jadwal, monkeypatch):
    """`sort_search`/`order_search` kosong membuat SIAKAD membalas HTTP 500."""
    terkirim = {}

    def rekam(endpoint, muatan):
        terkirim.update(muatan)
        return JawabanTiruan({"rs_data": {"data": [baris_jadwal], "total": 1}})

    jadwal = JadwalMengajar(KlienTiruan())
    monkeypatch.setattr(jadwal, "kirim", rekam)
    jadwal.daftar("2026", "1", prodi="TI")

    assert "sort_search" not in terkirim and "order_search" not in terkirim
    assert terkirim["tahun_ajaran"] == "2026" and terkirim["prodi"] == "TI"


def test_pencarian_gagal_dilaporkan_jelas(monkeypatch):
    from siakad_mcp.siakad_client import SiakadError

    jadwal = JadwalMengajar(KlienTiruan())
    monkeypatch.setattr(jadwal, "kirim", lambda endpoint, muatan: JawabanTiruan(status_code=500))

    with pytest.raises(SiakadError, match="jadwal mengajar"):
        jadwal.daftar("2026", "1")
