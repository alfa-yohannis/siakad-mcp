"""Klien SIAKAD Pradita: login, baca halaman, dan kirim form.

SIAKAD adalah aplikasi Laravel biasa — jauh lebih sederhana dari SISTER yang
memakai SSO OAuth2. Loginnya satu langkah:

    GET  /login          -> ambil _token (CSRF) dari formnya
    POST /login_process  -> _token + email + password
    -> sesi tersimpan di cookie siakad_session

Semua modul lain (CLI, REST API, MCP) memakai kelas di sini, jadi logika
login/kirim form hanya ditulis sekali.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from konfigurasi import baca_kredensial, buat_sesi_http

SIAKAD_BASE_URL = "https://siakad.pradita.ac.id"
PATH_PROSES_LOGIN = "/login_process"


class SiakadError(RuntimeError):
    """Kegagalan yang berasal dari SIAKAD (login ditolak, halaman berubah, dsb.)."""


@dataclass
class Formulir:
    """Satu <form> SIAKAD beserta konteks yang diperlukan untuk mengisinya."""

    url: str
    action: str
    method: str
    enctype: str
    csrf_token: str
    pilihan: dict[str, list[dict]] = field(default_factory=dict)
    isian_teks: dict[str, str] = field(default_factory=dict)

    def nilai_pilihan(self, nama_field: str, label_atau_nilai: str) -> str:
        """Ubah label yang manusiawi jadi value yang dimengerti SIAKAD.

        Dicocokkan bertahap dari yang paling pasti ke yang paling longgar:
        value asli -> label persis -> label yang memuat teks itu.
        """
        dicari = str(label_atau_nilai).strip()
        opsi = self.pilihan.get(nama_field, [])
        for satu in opsi:
            if satu["value"] == dicari:
                return dicari
        for satu in opsi:
            if satu["label"].strip().lower() == dicari.lower():
                return satu["value"]
        for satu in opsi:
            if dicari.lower() in satu["label"].strip().lower():
                return satu["value"]
        if not opsi:
            # select yang diisi lewat AJAX kosong saat halaman dimuat
            return dicari
        raise SiakadError(
            f"Pilihan '{label_atau_nilai}' tidak ada pada field {nama_field}. "
            f"Contoh yang tersedia: {[o['label'] for o in opsi[:5]]}"
        )

    def daftar_pilihan(self, nama_field: str) -> list[dict]:
        """Seluruh pilihan sah sebuah field — dipakai API/MCP untuk menampilkan referensi."""
        return self.pilihan.get(nama_field, [])


class KlienSiakad:
    """Sesi SIAKAD milik satu pengguna. Cukup beri email dan password."""

    def __init__(self, email: str | None = None, password: str | None = None):
        # kalau tidak diberikan, jatuh ke .env supaya pemakaian CLI tetap ringkas
        if not email or not password:
            kredensial = baca_kredensial("SIAKAD_USERNAME", "SIAKAD_PASSWORD")
            email = email or kredensial["SIAKAD_USERNAME"]
            password = password or kredensial["SIAKAD_PASSWORD"]
        self.email = email
        self.password = password
        self.sesi_http = buat_sesi_http()
        self.url_beranda = ""

    def login(self) -> "KlienSiakad":
        """Login satu langkah ke SIAKAD; error kalau kredensialnya ditolak."""
        halaman_login = self.sesi_http.get(f"{SIAKAD_BASE_URL}/login", timeout=60)
        halaman_login.raise_for_status()
        sup = BeautifulSoup(halaman_login.text, "lxml")

        isian = {
            masukan["name"]: masukan.get("value", "")
            for masukan in sup.find_all("input")
            if masukan.get("name")
        }
        isian["email"] = self.email
        isian["password"] = self.password

        jawaban = self.sesi_http.post(
            f"{SIAKAD_BASE_URL}{PATH_PROSES_LOGIN}",
            data=isian,
            timeout=60,
            allow_redirects=True,
            headers={"Referer": halaman_login.url},
        )
        jawaban.raise_for_status()

        # gagal login dikembalikan ke /login, biasanya dengan pesan di halamannya
        if "/login" in jawaban.url:
            raise SiakadError(f"Login ditolak — periksa SIAKAD_USERNAME/SIAKAD_PASSWORD ({jawaban.url})")

        self.url_beranda = jawaban.url
        return self

    def ambil_halaman(self, path_atau_url: str):
        """GET halaman SIAKAD. Terima path relatif maupun URL penuh."""
        url = path_atau_url if path_atau_url.startswith("http") else urljoin(SIAKAD_BASE_URL, path_atau_url)
        jawaban = self.sesi_http.get(url, timeout=120)
        jawaban.raise_for_status()
        return jawaban

    def buka_formulir(self, path_atau_url: str) -> Formulir:
        """Ambil form isian utama sebuah halaman beserta seluruh pilihan yang sah.

        Satu halaman memuat beberapa form (pencarian, ganti kata sandi, logout);
        yang paling banyak field-nya selalu form isian yang dicari.
        """
        jawaban = self.ambil_halaman(path_atau_url)
        sup = BeautifulSoup(jawaban.text, "lxml")
        semua_form = sup.find_all("form")
        if not semua_form:
            raise SiakadError(f"Tidak ada form di {jawaban.url}")
        form_html = max(semua_form, key=lambda f: len(f.find_all(["input", "select", "textarea"])))

        formulir = Formulir(
            url=jawaban.url,
            action=urljoin(jawaban.url, form_html.get("action") or jawaban.url),
            method=(form_html.get("method") or "POST").upper(),
            enctype=form_html.get("enctype", "application/x-www-form-urlencoded"),
            csrf_token=self.baca_token_csrf(sup),
        )
        for pilihan in form_html.find_all("select"):
            if pilihan.get("name"):
                formulir.pilihan[pilihan["name"]] = [
                    {"value": opsi.get("value", ""), "label": opsi.get_text(strip=True)}
                    for opsi in pilihan.find_all("option")
                ]
        for masukan in form_html.find_all(["input", "textarea"]):
            nama = masukan.get("name")
            if nama and nama not in formulir.isian_teks:
                formulir.isian_teks[nama] = masukan.get("value", "")
        return formulir

    def baca_token_csrf(self, sup) -> str:
        """Token CSRF halaman: dari <meta csrf-token>, atau input _token pada formnya."""
        meta = sup.find("meta", {"name": "csrf-token"})
        if meta and meta.get("content"):
            return meta["content"]
        masukan = sup.find("input", {"name": "_token"})
        if masukan and masukan.get("value"):
            return masukan["value"]
        raise SiakadError("CSRF token tidak ditemukan di halaman")

    def kirim_formulir(self, formulir: Formulir, isian: list[tuple[str, str]], berkas: list | None = None) -> dict:
        """Kirim form. Balikan: {'ok': bool, 'status': int, 'url': str, 'kesalahan': {...}}.

        `isian` berupa list pasangan, bukan dict, karena field Laravel yang berulang
        (mis. `nilai[]`) mengandalkan urutan untuk memasangkan antar-kolom.
        """
        muatan = [("_token", formulir.csrf_token), *isian]
        jawaban = self.sesi_http.post(
            formulir.action,
            data=muatan,
            files=berkas or None,
            timeout=300,
            headers={"Referer": formulir.url, "X-Requested-With": "XMLHttpRequest"},
        )
        return self.baca_hasil_kirim(jawaban)

    def baca_hasil_kirim(self, jawaban) -> dict:
        """Terjemahkan balasan SIAKAD — bisa JSON, bisa halaman HTML berisi pesan galat."""
        hasil = {"status": jawaban.status_code, "url": jawaban.url, "ok": False, "kesalahan": {}}
        try:
            badan = jawaban.json()
        except ValueError:
            badan = None

        if isinstance(badan, dict):
            hasil["mentah"] = badan
            kesalahan = badan.get("errors") or {}
            if kesalahan:
                hasil["kesalahan"] = kesalahan
                return hasil
            hasil["ok"] = badan.get("success", True) is not False
            return hasil

        pesan = baca_pesan_kesalahan(jawaban.text or "")
        if pesan:
            hasil["kesalahan"] = pesan
            return hasil

        hasil["ok"] = jawaban.status_code in (200, 302)
        if not hasil["ok"]:
            hasil["kesalahan"] = {"http": f"status {jawaban.status_code}"}
        return hasil

    def baca_tabel(self, path_atau_url: str) -> list[list[dict]]:
        """Seluruh tabel di sebuah halaman, tiap baris jadi dict berkunci nama kolom."""
        sup = BeautifulSoup(self.ambil_halaman(path_atau_url).text, "lxml")
        semua_tabel = []
        for tabel in sup.find_all("table"):
            kolom = [th.get_text(" ", strip=True) for th in tabel.find_all("th")]
            baris = []
            for tr in tabel.find_all("tr"):
                sel = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if sel and len(sel) == len(kolom):
                    baris.append(dict(zip(kolom, sel)))
                elif sel:
                    baris.append({str(nomor): isi for nomor, isi in enumerate(sel)})
            if baris:
                semua_tabel.append(baris)
        return semua_tabel

    def daftar_navigasi(self) -> list[dict]:
        """Menu yang tersedia setelah login — pijakan untuk menambah kemampuan baru."""
        sup = BeautifulSoup(self.ambil_halaman(self.url_beranda or "/").text, "lxml")
        menu = {}
        for tautan in sup.find_all("a", href=True):
            teks = tautan.get_text(" ", strip=True)
            alamat = urljoin(SIAKAD_BASE_URL, tautan["href"])
            if teks and alamat.startswith(SIAKAD_BASE_URL) and "logout" not in alamat.lower():
                menu.setdefault(alamat, teks[:60])
        return [{"nama": nama, "url": alamat} for alamat, nama in sorted(menu.items(), key=lambda x: x[1])]


def baca_pesan_kesalahan(html: str) -> dict[str, str]:
    """Ambil pesan galat Laravel yang dirender di halaman (blok .invalid-feedback / .alert)."""
    sup = BeautifulSoup(html, "lxml")
    pesan = {}
    for nomor, blok in enumerate(sup.select(".invalid-feedback, .alert-danger, .text-danger")):
        teks = blok.get_text(" ", strip=True)
        if teks:
            pesan[f"pesan_{nomor}"] = teks[:200]
    return pesan


def lampirkan_berkas(nama_field: str, path_berkas: str | Path) -> tuple:
    """Siapkan satu berkas dari disk untuk dikirim sebagai bagian multipart."""
    path = Path(path_berkas)
    if not path.is_file():
        raise SiakadError(f"Berkas tidak ditemukan: {path}")
    tipe = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return (nama_field, (path.name, path.read_bytes(), tipe))
