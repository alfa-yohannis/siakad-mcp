"""Sisipkan tanda tangan digital ke halaman cetak sebelum dijadikan PDF.

Berkas tanda tangan bernama `<nama>.png`, mis. `kong.png` dan `spider.png`.
Pemilihannya berdasarkan nama orang yang tertulis di halaman: berkas dipakai
kalau nama berkasnya muncul pada nama orang tersebut.

Letak foldernya ditentukan pemanggil — CLI lewat `--tanda-tangan`, REST API dan
MCP lewat parameter `tanda_tangan`. Kalau tidak diberikan, urutan pencariannya
ada di `cari_dir_tanda_tangan()`.

Yang disisipkan di halaman Berita Acara:
    kolom "Paraf"  -> tanda tangan dosen pengampu, satu per pertemuan
    blok kanan bawah -> tanda tangan pejabat (Kaprodi) di atas namanya
"""

from __future__ import annotations

import os
import re
from base64 import b64encode
from pathlib import Path

from bs4 import BeautifulSoup

from siakad_mcp.konfigurasi import akar_proyek, baca_angka, baca_pengaturan

NAMA_FOLDER_TANDA_TANGAN = "digital_signs"

# kota pada blok tanda tangan pejabat; dipakai untuk menemukan bloknya di halaman
# cetak, jadi harus sama dengan yang dicetak SIAKAD kampus bersangkutan
KOTA_BAWAAN = "Tangerang"

def kota_penanda_tangan() -> str:
    """Kota pada blok tanda tangan, dari SIAKAD_KOTA atau kota: di siakad.yaml."""
    return baca_pengaturan("SIAKAD_KOTA", KOTA_BAWAAN)


def tinggi_paraf() -> int:
    """Tinggi paraf dosen dalam piksel."""
    return baca_angka("SIAKAD_TINGGI_PARAF_PX", 58)


def tinggi_tanda_tangan() -> int:
    """Tinggi tanda tangan pejabat dalam piksel."""
    return baca_angka("SIAKAD_TINGGI_TTD_PX", 120)


def cari_dir_tanda_tangan(direktori: str | Path | None = None) -> Path:
    """Folder berisi berkas tanda tangan.

    Dicari berurutan: yang diberikan pemanggil, yang ditunjuk BKD_TANDA_TANGAN,
    milik repositori ini sendiri, lalu milik direktori kerja BKD. Dengan begitu
    aplikasi ini tetap bisa dipakai berdiri sendiri maupun sebagai bagian dari
    direktori kerja, dan pemanggil selalu bisa menimpanya.

    Path relatif dihitung dari akar proyek, sama seperti `--tujuan`.
    """
    diminta = direktori or os.environ.get("BKD_TANDA_TANGAN")
    if diminta:
        # permintaan eksplisit dipakai apa adanya — folder yang salah ketik lebih
        # baik terlihat sebagai tanda tangan yang hilang daripada diam-diam
        # diganti folder bawaan
        return tetapkan_dir(diminta)

    bawaan = [akar_proyek() / NAMA_FOLDER_TANDA_TANGAN]
    for satu in bawaan:
        if satu.is_dir():
            return satu
    return bawaan[-1]


def tetapkan_dir(diminta: str | Path) -> Path:
    """Path folder tanda tangan; yang relatif dihitung dari akar proyek."""
    lokasi = Path(diminta)
    return lokasi if lokasi.is_absolute() else akar_proyek() / lokasi


def daftar_tanda_tangan(direktori: str | Path | None = None) -> dict[str, Path]:
    """Berkas tanda tangan yang tersedia, berkunci nama berkasnya (huruf kecil)."""
    lokasi = cari_dir_tanda_tangan(direktori)
    if not lokasi.is_dir():
        return {}
    return {
        berkas.stem.lower(): berkas
        for berkas in sorted(lokasi.iterdir())
        if berkas.suffix.lower() in (".png", ".jpg", ".jpeg")
    }


def cari_tanda_tangan(nama_orang: str, direktori: str | Path | None = None) -> Path | None:
    """Tanda tangan milik seseorang, dicocokkan dari potongan namanya."""
    nama = re.sub(r"[^a-z ]", " ", nama_orang.lower())
    kata = set(nama.split())
    for kunci, berkas in daftar_tanda_tangan(direktori).items():
        if kunci in kata:
            return berkas
    return None


def ukuran_gambar(isi: bytes) -> tuple[int, int]:
    """Lebar dan tinggi gambar; (0, 0) kalau ukurannya tidak bisa dibaca."""
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(isi)) as gambar:
            return gambar.size
    except Exception:
        return (0, 0)


def pangkas_batas(berkas: Path) -> bytes:
    """Buang bidang kosong di sekeliling tanda tangan.

    Berkas pindaian biasanya menyisakan margin lebar; kalau tidak dipangkas,
    goresannya jadi kecil sekali saat tingginya dibatasi CSS.
    """
    try:
        from PIL import Image
    except ImportError:
        return berkas.read_bytes()

    with Image.open(berkas) as gambar:
        gambar = gambar.convert("RGBA")
        kotak = gambar.getbbox()
        if not kotak:
            return berkas.read_bytes()
        from io import BytesIO

        penampung = BytesIO()
        gambar.crop(kotak).save(penampung, format="PNG")
        return penampung.getvalue()


def sebagai_data_uri(isi: bytes) -> str:
    """Gambar ditanam langsung ke HTML supaya tetap tampil saat dicetak."""
    return f"data:image/png;base64,{b64encode(isi).decode()}"


def gambar_tanda_tangan(sup: BeautifulSoup, berkas: Path, tinggi_px: int):
    """Elemen <img> tanda tangan setinggi yang diminta, dengan lebar mengikuti aslinya.

    Hanya tingginya yang ditetapkan dan lebarnya dibiarkan `auto` — memberi batas
    lebar sekaligus akan memipihkan tanda tangannya.
    """
    isi = pangkas_batas(berkas)
    gambar = sup.new_tag("img", src=sebagai_data_uri(isi))
    gambar["style"] = f"height:{tinggi_px}px; width:auto;"
    return gambar


def lebar_pada_tinggi(berkas: Path, tinggi_px: int) -> int:
    """Lebar tampil sebuah tanda tangan pada tinggi tertentu, menurut rasio aslinya."""
    lebar, tinggi = ukuran_gambar(pangkas_batas(berkas))
    if not tinggi:
        return tinggi_px * 2
    return round(tinggi_px * lebar / tinggi)


def isi_kolom_paraf(sup: BeautifulSoup, berkas: Path) -> int:
    """Bubuhkan paraf dosen pada tiap baris pertemuan. Kembalikan jumlah barisnya."""
    sel_judul = sup.find(lambda tag: tag.name == "td" and tag.get_text(strip=True) == "Paraf")
    if not sel_judul:
        return 0

    baris_judul = sel_judul.find_parent("tr")
    kolom_paraf = baris_judul.find_all("td").index(sel_judul)

    # kolom Paraf aslinya sempit; dilebarkan supaya tanda tangan muat utuh
    lebar_kolom = lebar_pada_tinggi(berkas, tinggi_paraf()) + 16
    sel_judul["width"] = f"{lebar_kolom}px"
    sel_judul["style"] = (sel_judul.get("style", "") + f";min-width:{lebar_kolom}px;").lstrip(";")

    jumlah = 0
    for baris in baris_judul.find_next_siblings("tr"):
        sel = baris.find_all("td")
        if len(sel) <= kolom_paraf:
            continue
        target = sel[kolom_paraf]
        target.clear()
        target["style"] = (target.get("style", "") + ";text-align:center;").lstrip(";")
        target.append(gambar_tanda_tangan(sup, berkas, tinggi_paraf()))
        jumlah += 1
    return jumlah


def isi_blok_pejabat(sup: BeautifulSoup, tanggal: str, direktori: str | Path | None = None) -> str:
    """Bubuhkan tanda tangan pejabat penanda tangan di blok kanan bawah.

    Nama pejabatnya dibaca dari halaman itu sendiri, jadi kalau Kaprodi berganti
    tidak ada yang perlu diubah di sini.
    """
    kota = kota_penanda_tangan()
    sel_kota = sup.find(
        lambda tag: tag.name == "td" and tag.get_text(strip=True).startswith(f"{kota},")
    )
    if not sel_kota:
        return ""

    baris_nama = sel_kota.find_parent("tr").find_next_sibling("tr")
    if not baris_nama:
        return ""
    # tanggalnya diisi lebih dulu: berguna walau tanda tangan pejabatnya belum ada
    if tanggal and sel_kota.get_text(strip=True) == f"{kota},":
        sel_kota.string = f"{kota}, {tanggal}"

    sel_nama = baris_nama.find_all("td")[-1]
    nama_pejabat = sel_nama.get_text(" ", strip=True)
    berkas = cari_tanda_tangan(nama_pejabat, direktori)
    if not berkas:
        return ""

    sel_kota.append(sup.new_tag("br"))
    sel_kota.append(gambar_tanda_tangan(sup, berkas, tinggi_tanda_tangan()))
    return nama_pejabat


def sisipkan_tanda_tangan(
    html: str, nama_dosen: str, *, tanggal: str = "", direktori: str | Path | None = None
) -> str:
    """Kembalikan HTML yang sudah dibubuhi paraf dosen dan tanda tangan pejabat.

    `direktori` menimpa letak folder tanda tangan; kosong berarti ikut urutan
    pencarian bawaan.
    """
    sup = BeautifulSoup(html, "lxml")

    berkas_dosen = cari_tanda_tangan(nama_dosen, direktori)
    if berkas_dosen:
        isi_kolom_paraf(sup, berkas_dosen)
    isi_blok_pejabat(sup, tanggal, direktori)
    return str(sup)
