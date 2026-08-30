"""Petakan halaman SIAKAD: form, field, tautan aksi, dan endpoint AJAX-nya.

Dipakai saat menyiapkan kemampuan baru. Banyak halaman SIAKAD memuat tabelnya
lewat AJAX, jadi endpoint yang dipanggil JS ikut didaftar di sini. Skrip ini
hanya melakukan GET, tidak pernah mengirim data.

Pakai:
    python scripts/petakan_form.py /report/berita_acara_kuliah
    python scripts/petakan_form.py /dosen/kepanitiaan --semua-opsi
"""

from __future__ import annotations

import json
import re
import sys

from dependensi import pastikan_dependensi

# harus dipanggil sebelum impor paket pihak ketiga di bawahnya
pastikan_dependensi()

from bs4 import BeautifulSoup

from konfigurasi import simpan_ke_data
from siakad_client import KlienSiakad

MAKS_OPSI_TAMPIL = 12
POLA_AJAX = re.compile(r"""url\s*:\s*[`'"]([^`'"]+)[`'"]""")


def ringkas_field(field, *, semua_opsi: bool) -> dict:
    """Ringkas satu <input>/<select>/<textarea> jadi dict yang enak dibaca."""
    ringkasan = {
        "tag": field.name,
        "name": field.get("name"),
        "id": field.get("id"),
        "type": field.get("type", "select" if field.name == "select" else field.name),
        "value": field.get("value", ""),
    }
    if field.name == "select":
        opsi = [
            {"value": pilihan.get("value", ""), "label": pilihan.get_text(strip=True)}
            for pilihan in field.find_all("option")
        ]
        ringkasan["jumlah_opsi"] = len(opsi)
        ringkasan["opsi"] = opsi if semua_opsi else opsi[:MAKS_OPSI_TAMPIL]
    return ringkasan


def ringkas_form(form, *, semua_opsi: bool) -> dict:
    """Ringkas satu <form> beserta seluruh field-nya."""
    field = form.find_all(["input", "select", "textarea"])
    return {
        "id": form.get("id"),
        "action": form.get("action", ""),
        "method": (form.get("method") or "get").upper(),
        "jumlah_field": len(field),
        "field": [ringkas_field(satu, semua_opsi=semua_opsi) for satu in field if satu.get("name")],
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    path = sys.argv[1]
    semua_opsi = "--semua-opsi" in sys.argv

    klien = KlienSiakad().login()
    jawaban = klien.ambil_halaman(path)
    sup = BeautifulSoup(jawaban.text, "lxml")

    laporan = {
        "url": jawaban.url,
        "status": jawaban.status_code,
        "judul": sup.title.get_text(strip=True) if sup.title else "",
        "form": [ringkas_form(form, semua_opsi=semua_opsi) for form in sup.find_all("form")],
        # tabel yang kosong biasanya berarti isinya datang dari endpoint di bawah ini
        "endpoint_ajax": sorted(set(POLA_AJAX.findall(jawaban.text))),
        "jumlah_tabel": len(klien.baca_tabel(path)),
    }

    print(json.dumps(laporan, ensure_ascii=False, indent=2)[:6000])
    nama_aman = path.strip("/").replace("/", "_") or "beranda"
    simpan_ke_data(f"form_{nama_aman}.json", laporan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
