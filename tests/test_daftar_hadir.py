"""Uji pembacaan pertemuan dan daftar mahasiswa."""

from __future__ import annotations

import json

import pytest

from siakad_mcp.daftar_hadir import DaftarHadir, Mahasiswa, Pertemuan
from siakad_mcp.siakad_client import SiakadError
from conftest import JawabanTiruan, KlienTiruan


BARIS_PERTEMUAN = {
    "DOSEN_ID": "0000000",
    "KD_MATA_KULIAH": "IF30812",
    "NM_MATA_KULIAH": "Pemrograman Berorientasi Objek",
    "TAHUN_AJARAN": "2026",
    "TIPE_SEMESTER": "1",
    "HARI": "MONDAY",
    "JAM_MULAI": "08:25:00.0000000",
    "JAM_SELESAI_ABSENSI": "11:05:00.0000000",
    "TGL_ABSENSI": "2026-08-31",
    "SESI": "1",
    "NM_RUANG": "A306",
    "NM_JURUSAN": "Informatika",
    "KELOMPOK_KELAS": "Kelas B",
    "NAMA_DOSEN": "King Kong, S.T.,M.T.,Ph.D.",
    "JAM_ABSEN": None,
}

# rekam mahasiswa dari SIAKAD memuat jauh lebih banyak field daripada ini;
# yang dicontohkan hanya yang dipetakan, ditambah satu field pribadi untuk
# memastikan yang seperti itu tidak ikut terbawa
BARIS_MAHASISWA = {
    "NIM": "251110001",
    "STATUS": "A",
    "KD_SUB_KELAS": "1 ",
    "has_absensi": True,
    "data_mahasiswa": {
        "NIM": "251110001",
        "NAMA": "SPIDER MAN",
        "KELOMPOK_KELAS": "Kelas B",
        "KTP": "3210000000000000",
        "ALAMAT": "Jl. Karangan No. 1",
        "data_jurusan": {"NM_JURUSAN": "Informatika"},
    },
}


@pytest.fixture
def baris_pertemuan() -> dict:
    return dict(BARIS_PERTEMUAN)


@pytest.fixture
def hadir(monkeypatch, baris_pertemuan):
    """DaftarHadir dengan endpoint search dan detail yang dijawab tiruan."""
    menu = DaftarHadir(KlienTiruan())
    terkirim: dict[str, dict] = {}

    def kirim(endpoint, muatan):
        terkirim[endpoint] = muatan
        if endpoint == "search":
            return JawabanTiruan({"rs_data": {"data": [baris_pertemuan], "total": 1}})
        return JawabanTiruan({"list_mhs": [BARIS_MAHASISWA], "PERTEMUAN_CURR": 1})

    monkeypatch.setattr(menu, "kirim", kirim)
    menu.terkirim = terkirim
    return menu


def test_pertemuan_dibaca_dari_baris(baris_pertemuan):
    satu = Pertemuan.dari_baris(baris_pertemuan)

    assert satu.kode_mk == "IF30812"
    assert satu.tanggal == "2026-08-31"
    assert satu.ruang == "A306"
    assert satu.waktu == "Senin 08:25-11:05"
    assert satu.label.endswith("(Kelas B) — 2026-08-31")


def test_kelas_yang_belum_dibuka_ditandai(baris_pertemuan):
    """JAM_ABSEN hanya terisi setelah dosen membuka kelasnya."""
    assert Pertemuan.dari_baris(baris_pertemuan).sudah_dibuka is False
    assert Pertemuan.dari_baris({**baris_pertemuan, "JAM_ABSEN": "08:30"}).sudah_dibuka is True


def test_parameter_detail_lengkap(baris_pertemuan):
    parameter = Pertemuan.dari_baris(baris_pertemuan).sebagai_parameter()

    assert set(parameter) == {
        "DOSEN_ID", "KD_MATA_KULIAH", "TAHUN_AJARAN", "TIPE_SEMESTER",
        "HARI", "JAM_MULAI", "TGL_ABSENSI", "SESI",
    }


def test_tahun_akademik_dikirim_sebagai_json(hadir):
    """Dikosongkan, SIAKAD membalas HTTP 500 — jadi bentuknya harus tepat."""
    hadir.daftar_pertemuan("2026", "1")

    assert json.loads(hadir.terkirim["search"]["tahun_akademik"]) == {
        "tahun_ajaran": "2026", "tipe_semester": "1"
    }


def test_pertemuan_diurutkan_menurut_tanggal(hadir, baris_pertemuan, monkeypatch):
    baris = [
        {**baris_pertemuan, "TGL_ABSENSI": "2026-09-07"},
        {**baris_pertemuan, "TGL_ABSENSI": "2026-08-31"},
    ]
    monkeypatch.setattr(
        hadir, "kirim", lambda endpoint, muatan: JawabanTiruan({"rs_data": {"data": baris, "total": 2}})
    )

    assert [satu.tanggal for satu in hadir.daftar_pertemuan("2026", "1")] == [
        "2026-08-31", "2026-09-07",
    ]


def test_mahasiswa_hanya_membawa_field_perkuliahan():
    """Data pribadi yang ikut dikirim SIAKAD tidak boleh bocor lewat Mahasiswa."""
    satu = Mahasiswa.dari_baris(BARIS_MAHASISWA)

    assert (satu.nim, satu.nama, satu.kelompok_kelas) == ("251110001", "SPIDER MAN", "Kelas B")
    assert satu.prodi == "Informatika" and satu.hadir is True
    assert not any("KTP" in kunci or "ALAMAT" in kunci for kunci in satu.__dict__)


def test_email_diambil_dari_siakad_bukan_ditebak():
    """Alamat yang sudah ada di SIAKAD selalu menang atas pola setelan."""
    satu = Mahasiswa.dari_baris(
        {**BARIS_MAHASISWA,
         "data_mahasiswa": {**BARIS_MAHASISWA["data_mahasiswa"], "EMAIL": "spider.man@student.uji.ac.id"}}
    )

    assert satu.email == "spider.man@student.uji.ac.id"


def test_email_diturunkan_dari_pola_saat_siakad_kosong(monkeypatch):
    from siakad_mcp import atur_setelan
    from siakad_mcp.daftar_hadir import email_menurut_pola

    atur_setelan(email_mahasiswa="{nama_depan}.{nama_kedua}@student.uji.ac.id")
    monkeypatch.setattr(
        "siakad_mcp.daftar_hadir.baca_pemetaan",
        lambda kunci: {"26": "{nama_depan}.{nim}@student.uji.ac.id"},
    )
    try:
        assert email_menurut_pola("2610101030", "CHRISTIAN JUSTINO") == \
            "christian.2610101030@student.uji.ac.id"
        assert email_menurut_pola("2210101038", "HIGHAN AGOGOS FUTURO") == \
            "highan.agogos@student.uji.ac.id"
        # nama satu kata tidak boleh menghasilkan alamat setengah jadi
        assert email_menurut_pola("2210101039", "SUPARMAN") == "suparman.suparman@student.uji.ac.id"
    finally:
        atur_setelan()


def test_tanpa_setelan_pola_email_dibiarkan_kosong(monkeypatch):
    """Menebak alamat orang lebih buruk daripada mengosongkannya."""
    from siakad_mcp.daftar_hadir import email_menurut_pola

    monkeypatch.setattr("siakad_mcp.daftar_hadir.baca_pemetaan", lambda kunci: {})
    monkeypatch.setattr("siakad_mcp.daftar_hadir.baca_pengaturan", lambda kunci, bawaan="": "")

    assert email_menurut_pola("2610101030", "CHRISTIAN JUSTINO") == ""


def test_daftar_mahasiswa_diurutkan_menurut_nim(hadir, monkeypatch):
    kedua = {**BARIS_MAHASISWA, "NIM": "251110000",
             "data_mahasiswa": {**BARIS_MAHASISWA["data_mahasiswa"], "NIM": "251110000", "NAMA": "KING KONG"}}
    monkeypatch.setattr(
        hadir, "kirim",
        lambda endpoint, muatan: JawabanTiruan({"list_mhs": [BARIS_MAHASISWA, kedua]}),
    )

    hasil = hadir.daftar_mahasiswa(Pertemuan.dari_baris(BARIS_PERTEMUAN))
    assert [satu.nim for satu in hasil] == ["251110000", "251110001"]


def test_mahasiswa_kelas_memakai_pertemuan_pertama(hadir):
    pertemuan, mahasiswa = hadir.mahasiswa_kelas("2026", "1", "IF30812")

    assert pertemuan.tanggal == "2026-08-31"
    assert [satu.nama for satu in mahasiswa] == ["SPIDER MAN"]


def test_mata_kuliah_yang_tidak_ada_dilaporkan_jelas(hadir):
    with pytest.raises(SiakadError, match="IF99999"):
        hadir.mahasiswa_kelas("2026", "1", "IF99999")


def test_kelompok_kelas_menyaring_pertemuan(hadir):
    with pytest.raises(SiakadError, match="Kelas A"):
        hadir.mahasiswa_kelas("2026", "1", "IF30812", "Kelas A")


def test_kelas_yang_sudah_dibuka_tidak_dibuka_ulang(monkeypatch, baris_pertemuan):
    """Sekali dibuka tidak bisa ditutup; permintaan ulang ditahan di sini."""
    menu = DaftarHadir(KlienTiruan())
    monkeypatch.setattr(
        menu, "kirim", lambda endpoint, muatan: pytest.fail("tidak boleh dikirim ulang")
    )

    hasil = menu.buka_kelas(Pertemuan.dari_baris({**baris_pertemuan, "JAM_ABSEN": "08:30"}))
    assert hasil["ok"] is False and "08:30" in hasil["pesan"]


def test_buka_kelas_mengirim_delapan_kunci_pertemuan(monkeypatch, baris_pertemuan):
    terkirim = {}

    def rekam(endpoint, muatan):
        terkirim["endpoint"] = endpoint
        terkirim.update(muatan)
        return JawabanTiruan({"error": False, "Message": "Kelas dibuka"})

    menu = DaftarHadir(KlienTiruan())
    monkeypatch.setattr(menu, "kirim", rekam)
    hasil = menu.buka_kelas(Pertemuan.dari_baris(baris_pertemuan))

    assert terkirim["endpoint"] == "buka_kelas"
    assert set(terkirim) - {"endpoint"} == {
        "dosen_id", "kd_mata_kuliah", "tahun_ajaran", "tipe_semester",
        "hari", "jam_mulai", "tgl_absensi", "sesi",
    }
    assert hasil["ok"] is True


def test_uji_coba_tidak_mengirim_apa_pun(monkeypatch):
    """Satu-satunya operasi tulis paket ini harus bisa dijalankan kering dulu."""
    menu = DaftarHadir(KlienTiruan())
    monkeypatch.setattr(
        menu, "kirim",
        lambda endpoint, muatan: pytest.fail("uji coba tidak boleh menyentuh SIAKAD"),
    )

    hasil = menu.simpan_pembahasan(
        Pertemuan.dari_baris(BARIS_PERTEMUAN), "Session-01: Pengantar", "Membahas kontrak kuliah",
        uji_coba=True,
    )

    assert hasil["uji_coba"] is True
    assert hasil["muatan"]["topik_pembahasan"] == "Session-01: Pengantar"


def test_muatan_pembahasan_memakai_nama_field_huruf_kecil(monkeypatch):
    """Endpoint save_pembahasan memakai huruf kecil, berbeda dari endpoint detail."""
    terkirim = {}

    def rekam(endpoint, muatan):
        terkirim["endpoint"] = endpoint
        terkirim.update(muatan)
        return JawabanTiruan({"error": False, "Message": "Berhasil disimpan"})

    menu = DaftarHadir(KlienTiruan())
    monkeypatch.setattr(menu, "kirim", rekam)
    hasil = menu.simpan_pembahasan(Pertemuan.dari_baris(BARIS_PERTEMUAN), "Session-01", "Pengantar")

    assert terkirim["endpoint"] == "save_pembahasan"
    assert terkirim["kd_mata_kuliah"] == "IF30812" and terkirim["tgl_absensi"] == "2026-08-31"
    assert hasil["ok"] is True and hasil["pesan"] == "Berhasil disimpan"


def test_penolakan_siakad_dilaporkan_bukan_dianggap_berhasil(monkeypatch):
    menu = DaftarHadir(KlienTiruan())
    monkeypatch.setattr(
        menu, "kirim",
        lambda endpoint, muatan: JawabanTiruan({"error": True, "Message": "Kelas belum dibuka"}),
    )

    hasil = menu.simpan_pembahasan(Pertemuan.dari_baris(BARIS_PERTEMUAN), "Session-01")
    assert hasil["ok"] is False and "belum dibuka" in hasil["pesan"]
