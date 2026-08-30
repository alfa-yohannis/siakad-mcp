"""Konfigurasi: kredensial, setelan, sesi HTTP, dan penyimpanan hasil.

Paket ini dipakai dari dua arah, dan keduanya harus benar tanpa disetel apa pun:

    berdiri sendiri   repositori ini di-clone lalu dijalankan lewat ./siakad.
                      Akar proyek = direktori repositori itu sendiri.

    sebagai pustaka   proyek lain memasangnya (`pip install siakad-mcp`) dan
                      mengimpor `siakad_mcp`. Akar proyek = direktori kerja
                      proyek itu, bukan site-packages tempat paket ini terpasang.

Akar proyek menentukan letak berkas-berkas ini:

    <akar>/.env            kredensial (SIAKAD_USERNAME, SIAKAD_PASSWORD)
    <akar>/siakad.yaml     setelan non-rahasia (alamat instance, kota, cetak)
    <akar>/digital_signs   berkas tanda tangan
    <akar>/data/           hasil tarikan

Direktori di atasnya tidak pernah ikut ditelusuri, supaya hasilnya tidak berubah
hanya karena paket ini dipindah. Proyek yang memakainya sebagai pustaka bisa
menentukan sendiri lewat `atur_akar_proyek()` atau `atur_setelan()`, atau lewat
SIAKAD_AKAR_PROYEK.

Rahasia dipisah dari setelan dengan sengaja: `.env` memuat username/password dan
tidak pernah ikut ter-commit, sedangkan `siakad.yaml` aman dibagikan ke sesama
pemakai satu perguruan tinggi.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import dotenv_values

PENYAMARAN_BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class KonfigurasiError(RuntimeError):
    """Setelan atau kredensial yang tidak bisa dipakai.

    Sengaja bukan SystemExit: pustaka tidak boleh menghentikan program yang
    memakainya. Titik masuk CLI-lah yang menangkap ini dan keluar dengan rapi.
    """


# Ditetapkan dari kode lewat atur_akar_proyek()/atur_setelan(); dipakai proyek
# lain yang tidak mau bergantung pada berkas atau environment sama sekali.
_akar_ditetapkan: Path | None = None
_setelan_ditetapkan: dict[str, str] = {}
_konfigurasi_tersimpan: dict | None = None


def akar_bawaan() -> Path:
    """Akar proyek kalau tidak ada yang menentukan.

    Kalau paket ini berada di dalam checkout repositorinya sendiri, direktori
    repositori itulah akarnya — inilah mode "berdiri sendiri". Kalau sudah
    terpasang sebagai pustaka, site-packages jelas bukan tempat menaruh .env
    milik pemakai, jadi yang dipakai direktori kerja proyek pemanggil.
    """
    akar_repo = Path(__file__).resolve().parent.parent
    if (akar_repo / "pyproject.toml").is_file():
        return akar_repo
    return Path.cwd()


def akar_proyek() -> Path:
    """Direktori tempat .env, siakad.yaml, digital_signs/, dan data/ dicari."""
    if _akar_ditetapkan is not None:
        return _akar_ditetapkan
    ditetapkan = os.environ.get("SIAKAD_AKAR_PROYEK") or os.environ.get("BKD_AKAR_PROYEK")
    if ditetapkan:
        return Path(ditetapkan).expanduser()
    return akar_bawaan()


def atur_akar_proyek(path: str | Path | None) -> None:
    """Tetapkan akar proyek dari kode. `None` mengembalikan ke perilaku bawaan."""
    global _akar_ditetapkan
    _akar_ditetapkan = Path(path).expanduser().resolve() if path is not None else None
    lupakan_konfigurasi()


def atur_setelan(**nilai: object) -> None:
    """Setelan dari kode, mis. `atur_setelan(base_url="https://siakad.lain.ac.id")`.

    Kuncinya boleh gaya YAML (`base_url`) atau gaya environment
    (`SIAKAD_BASE_URL`). Ini kepastian tertinggi: proyek yang menyetel sesuatu
    secara eksplisit tidak boleh berubah diam-diam karena environment mesin.
    Panggil tanpa argumen untuk mengosongkannya kembali.
    """
    if not nilai:
        _setelan_ditetapkan.clear()
        return
    for kunci, isi in nilai.items():
        _setelan_ditetapkan[nama_di_yaml(kunci)] = str(isi)


def lupakan_konfigurasi() -> None:
    """Buang isi siakad.yaml yang diingat, supaya dibaca ulang berikutnya."""
    global _konfigurasi_tersimpan
    _konfigurasi_tersimpan = None


def berkas_env() -> Path:
    """Letak .env yang dipakai."""
    return akar_proyek() / ".env"


def dir_data() -> Path:
    """Direktori hasil tarikan."""
    return akar_proyek() / "data"


def berkas_konfigurasi() -> Path | None:
    """Berkas siakad.yaml (atau .yml) yang dipakai, kalau memang ada."""
    akar = akar_proyek()
    for nama in ("siakad.yaml", "siakad.yml"):
        if (akar / nama).is_file():
            return akar / nama
    return None


def muat_konfigurasi() -> dict:
    """Isi siakad.yaml sebagai dict datar. Dibaca sekali lalu diingat.

    PyYAML sengaja diimpor di sini, bukan di kepala modul: pemakai yang cukup
    dengan setelan bawaan tidak perlu punya berkas konfigurasi sama sekali.
    """
    global _konfigurasi_tersimpan
    if _konfigurasi_tersimpan is not None:
        return _konfigurasi_tersimpan

    berkas = berkas_konfigurasi()
    if berkas is None:
        _konfigurasi_tersimpan = {}
        return _konfigurasi_tersimpan

    try:
        import yaml
    except ImportError as galat:
        raise KonfigurasiError(
            f"{berkas} ada tapi PyYAML belum terpasang. Pasang dulu: pip install pyyaml"
        ) from galat

    isi = yaml.safe_load(berkas.read_text(encoding="utf-8")) or {}
    if not isinstance(isi, dict):
        raise KonfigurasiError(
            f"{berkas} harus berupa pemetaan kunci: nilai, bukan {type(isi).__name__}"
        )
    _konfigurasi_tersimpan = isi
    return _konfigurasi_tersimpan


def nama_di_yaml(kunci: str) -> str:
    """SIAKAD_BASE_URL -> base_url; kunci tanpa awalan dipakai apa adanya."""
    return kunci[len("SIAKAD_"):].lower() if kunci.startswith("SIAKAD_") else kunci.lower()


def baca_pengaturan(kunci: str, bawaan: str = "") -> str:
    """Setelan opsional, dari yang paling khusus ke yang paling umum:

        atur_setelan()  ->  environment  ->  .env  ->  siakad.yaml  ->  bawaan

    Kuncinya ditulis gaya environment (SIAKAD_BASE_URL); di siakad.yaml nama yang
    sama dipakai tanpa awalan SIAKAD_ dan huruf kecil (base_url).

    Berbeda dengan baca_kredensial() yang mewajibkan, ini dipakai untuk nilai
    yang boleh kosong — mis. alamat instance atau kota penanda tangan, yang
    berbeda tiap perguruan tinggi dan karena itu tidak boleh ditanam di kode.
    """
    dari_kode = _setelan_ditetapkan.get(nama_di_yaml(kunci))
    if dari_kode:
        return dari_kode

    dari_lingkungan = os.environ.get(kunci) or dotenv_values(berkas_env()).get(kunci)
    if dari_lingkungan:
        return dari_lingkungan

    dari_berkas = muat_konfigurasi().get(nama_di_yaml(kunci))
    return str(dari_berkas) if dari_berkas not in (None, "") else bawaan


def baca_angka(kunci: str, bawaan: int) -> int:
    """Setelan berupa bilangan bulat; isian yang tidak masuk akal ditolak jelas."""
    nilai = baca_pengaturan(kunci, str(bawaan))
    try:
        return int(nilai)
    except ValueError as galat:
        raise KonfigurasiError(f"Setelan {kunci} harus berupa angka, bukan {nilai!r}") from galat


def baca_pemetaan(kunci: str) -> dict[str, str]:
    """Setelan berupa pemetaan, mis. daftar singkatan. Hanya dari berkas YAML."""
    nilai = muat_konfigurasi().get(nama_di_yaml(kunci)) or {}
    if not isinstance(nilai, dict):
        raise KonfigurasiError(f"Setelan {nama_di_yaml(kunci)} harus berupa pemetaan kunci: nilai")
    return {str(k): str(v) for k, v in nilai.items()}


def baca_kredensial(*kunci_wajib: str) -> dict[str, str]:
    """Ambil kredensial yang diminta. Error kalau ada yang belum diisi.

    Sumbernya sama dengan setelan lain, jadi proyek yang memakai pustaka ini
    boleh memberikannya lewat atur_setelan() atau environment tanpa perlu
    menyediakan berkas .env sama sekali.
    """
    hasil = {kunci: baca_pengaturan(kunci) for kunci in kunci_wajib}
    belum_ada = [kunci for kunci, nilai in hasil.items() if not nilai]
    if belum_ada:
        raise KonfigurasiError(
            f"Kredensial belum ada: {', '.join(belum_ada)}. "
            f"Isi di {berkas_env()}, lewat environment, atau atur_setelan()."
        )
    return hasil


def buat_sesi_http() -> requests.Session:
    """Sesi yang menyimpan cookie antar-permintaan dan menyamar sebagai browser."""
    sesi = requests.Session()
    sesi.headers.update({"User-Agent": baca_pengaturan("SIAKAD_USER_AGENT", PENYAMARAN_BROWSER)})
    return sesi


def simpan_ke_data(nama_berkas: str, isi, *, teks_mentah: bool = False) -> Path:
    """Simpan hasil tarikan ke data/. JSON secara bawaan, teks mentah kalau diminta."""
    tujuan_dir = dir_data()
    tujuan_dir.mkdir(parents=True, exist_ok=True)
    tujuan = tujuan_dir / nama_berkas
    if teks_mentah:
        tujuan.write_text(isi, encoding="utf-8")
    else:
        tujuan.write_text(json.dumps(isi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  tersimpan: {tujuan}")
    return tujuan
