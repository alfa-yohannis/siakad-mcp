"""Konfigurasi bersama satu aplikasi: kredensial, sesi HTTP, dan penyimpanan hasil.

Letak berkasnya:
    <akar proyek>/.env          kredensial semua aplikasi, dipakai bersama
    <akar aplikasi>/data/       hasil tarikan aplikasi ini saja
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import dotenv_values

AKAR_APLIKASI = Path(__file__).resolve().parent.parent
DIR_DATA = AKAR_APLIKASI / "data"

PENYAMARAN_BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def kandidat_akar_proyek() -> list[Path]:
    """Direktori yang mungkin memuat .env, dari yang paling dekat.

    Aplikasi ini bisa dipakai dari dua arah: langsung di direktorinya sendiri,
    atau lewat symlink dari direktori kerja BKD. Karena itu path "apa adanya"
    (symlink belum diikuti) ikut ditelusuri, selain path sebenarnya.
    """
    # .env milik repositori ini sendiri selalu menang: kalau aplikasi dipakai
    # berdiri sendiri, kredensialnya jelas berasal dari sini
    kandidat: list[Path] = [AKAR_APLIKASI]

    ditetapkan = os.environ.get("BKD_AKAR_PROYEK")
    if ditetapkan:
        kandidat.append(Path(ditetapkan))

    for awal in (Path(__file__).absolute().parent.parent, AKAR_APLIKASI):
        kandidat += [awal, *awal.parents]
    return kandidat


def cari_akar_proyek() -> Path:
    """Direktori berisi .env — kredensial semua aplikasi dikumpulkan di sana."""
    for direktori in kandidat_akar_proyek():
        if (direktori / ".env").is_file():
            return direktori
    return AKAR_APLIKASI


AKAR_PROYEK = cari_akar_proyek()
BERKAS_ENV = AKAR_PROYEK / ".env"


def baca_kredensial(*kunci_wajib: str) -> dict[str, str]:
    """Ambil variabel yang diminta dari .env. Error kalau ada yang belum diisi."""
    semua_nilai = dotenv_values(BERKAS_ENV)
    belum_ada = [kunci for kunci in kunci_wajib if not semua_nilai.get(kunci)]
    if belum_ada:
        raise SystemExit(f"Variabel belum ada di {BERKAS_ENV}: {', '.join(belum_ada)}")
    return {kunci: semua_nilai[kunci] for kunci in kunci_wajib}


def buat_sesi_http() -> requests.Session:
    """Sesi yang menyimpan cookie antar-permintaan dan menyamar sebagai browser."""
    sesi = requests.Session()
    sesi.headers.update({"User-Agent": PENYAMARAN_BROWSER})
    return sesi


def simpan_ke_data(nama_berkas: str, isi, *, teks_mentah: bool = False) -> Path:
    """Simpan hasil tarikan ke data/. JSON secara bawaan, teks mentah kalau diminta."""
    DIR_DATA.mkdir(exist_ok=True)
    tujuan = DIR_DATA / nama_berkas
    if teks_mentah:
        tujuan.write_text(isi, encoding="utf-8")
    else:
        tujuan.write_text(json.dumps(isi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  tersimpan: {tujuan.relative_to(AKAR_PROYEK)}")
    return tujuan
