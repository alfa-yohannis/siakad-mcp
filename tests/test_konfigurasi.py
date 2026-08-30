"""Uji akar proyek (berdiri sendiri vs dipakai proyek lain) dan urutan setelan."""

from __future__ import annotations

import pytest

from siakad_mcp import konfigurasi


@pytest.fixture(autouse=True)
def lingkungan_bersih(monkeypatch):
    """Setelan mesin pengembang tidak boleh ikut menentukan hasil uji."""
    for kunci in ("SIAKAD_AKAR_PROYEK", "BKD_AKAR_PROYEK", "SIAKAD_KOTA", "SIAKAD_BASE_URL"):
        monkeypatch.delenv(kunci, raising=False)
    konfigurasi.atur_akar_proyek(None)
    konfigurasi.atur_setelan()
    konfigurasi.lupakan_konfigurasi()
    yield
    konfigurasi.atur_akar_proyek(None)
    konfigurasi.atur_setelan()
    konfigurasi.lupakan_konfigurasi()


@pytest.fixture
def akar_tiruan(tmp_path):
    """Akar proyek tiruan, dipasang lewat API yang dipakai proyek pemanggil."""
    konfigurasi.atur_akar_proyek(tmp_path)
    return tmp_path


# --- akar proyek -----------------------------------------------------------


def test_berdiri_sendiri_berakar_di_repositori_ini():
    """Mode pertama: repositori di-clone lalu dijalankan apa adanya."""
    akar = konfigurasi.akar_bawaan()

    assert (akar / "pyproject.toml").is_file()
    assert konfigurasi.akar_proyek() == akar


def test_env_proyek_induk_tidak_ikut_terpungut(tmp_path, monkeypatch):
    """Direktori di atas akar tidak pernah ditelusuri.

    Penelusuran ke atas membuat kredensial yang terpakai bergantung pada letak
    folder — dan bisa jadi milik proyek lain.
    """
    induk = tmp_path / "induk"
    aplikasi = induk / "app"
    aplikasi.mkdir(parents=True)
    (induk / ".env").write_text("SIAKAD_USERNAME=induk\nSIAKAD_PASSWORD=induk\n")
    konfigurasi.atur_akar_proyek(aplikasi)

    assert konfigurasi.akar_proyek() == aplikasi
    assert konfigurasi.berkas_env() == aplikasi / ".env"
    with pytest.raises(konfigurasi.KonfigurasiError):
        konfigurasi.baca_kredensial("SIAKAD_USERNAME", "SIAKAD_PASSWORD")


def test_proyek_pemanggil_menentukan_akarnya_sendiri(akar_tiruan):
    """Mode kedua: proyek lain memasang paket ini dan menunjuk akarnya."""
    assert konfigurasi.akar_proyek() == akar_tiruan
    assert konfigurasi.dir_data() == akar_tiruan / "data"


def test_akar_lewat_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SIAKAD_AKAR_PROYEK", str(tmp_path))

    assert konfigurasi.akar_proyek() == tmp_path


def test_nama_lama_bkd_akar_proyek_masih_diterima(tmp_path, monkeypatch):
    monkeypatch.setenv("BKD_AKAR_PROYEK", str(tmp_path))

    assert konfigurasi.akar_proyek() == tmp_path


# --- urutan setelan --------------------------------------------------------


def test_setelan_yaml_dibaca(akar_tiruan):
    (akar_tiruan / "siakad.yaml").write_text("kota: Jakarta\ntinggi_paraf_px: 72\n")

    assert konfigurasi.baca_pengaturan("SIAKAD_KOTA", "Tangerang") == "Jakarta"
    assert konfigurasi.baca_angka("SIAKAD_TINGGI_PARAF_PX", 58) == 72


def test_environment_menang_atas_yaml(akar_tiruan, monkeypatch):
    (akar_tiruan / "siakad.yaml").write_text("kota: Jakarta\n")
    monkeypatch.setenv("SIAKAD_KOTA", "Surabaya")

    assert konfigurasi.baca_pengaturan("SIAKAD_KOTA", "Tangerang") == "Surabaya"


def test_setelan_dari_kode_menang_atas_environment(akar_tiruan, monkeypatch):
    """Proyek yang menyetel dari kode tidak boleh berubah karena environment mesin."""
    (akar_tiruan / "siakad.yaml").write_text("kota: Jakarta\n")
    monkeypatch.setenv("SIAKAD_KOTA", "Surabaya")
    konfigurasi.atur_setelan(kota="Medan")

    assert konfigurasi.baca_pengaturan("SIAKAD_KOTA", "Tangerang") == "Medan"


def test_setelan_dari_kode_menerima_kedua_gaya_nama(akar_tiruan):
    konfigurasi.atur_setelan(SIAKAD_BASE_URL="https://a.ac.id")
    assert konfigurasi.baca_pengaturan("SIAKAD_BASE_URL") == "https://a.ac.id"

    konfigurasi.atur_setelan(base_url="https://b.ac.id")
    assert konfigurasi.baca_pengaturan("SIAKAD_BASE_URL") == "https://b.ac.id"


def test_kredensial_boleh_datang_dari_kode_tanpa_berkas_env(akar_tiruan):
    """Proyek pemakai tidak wajib menyediakan .env sama sekali."""
    konfigurasi.atur_setelan(SIAKAD_USERNAME="a@b.ac.id", SIAKAD_PASSWORD="rahasia")

    assert konfigurasi.baca_kredensial("SIAKAD_USERNAME", "SIAKAD_PASSWORD") == {
        "SIAKAD_USERNAME": "a@b.ac.id",
        "SIAKAD_PASSWORD": "rahasia",
    }


def test_setelan_tanpa_yaml_memakai_nilai_bawaan(akar_tiruan):
    assert konfigurasi.berkas_konfigurasi() is None
    assert konfigurasi.baca_pengaturan("SIAKAD_KOTA", "Tangerang") == "Tangerang"


def test_angka_tidak_masuk_akal_ditolak_jelas(akar_tiruan, monkeypatch):
    monkeypatch.setenv("SIAKAD_TINGGI_PARAF_PX", "setinggi mungkin")

    with pytest.raises(konfigurasi.KonfigurasiError, match="harus berupa angka"):
        konfigurasi.baca_angka("SIAKAD_TINGGI_PARAF_PX", 58)


def test_kesalahan_setelan_bukan_systemexit(akar_tiruan, monkeypatch):
    """Pustaka tidak boleh menghentikan program yang memakainya."""
    monkeypatch.setenv("SIAKAD_TINGGI_PARAF_PX", "bukan angka")

    with pytest.raises(Exception) as galat:
        konfigurasi.baca_angka("SIAKAD_TINGGI_PARAF_PX", 58)
    assert not isinstance(galat.value, SystemExit)
