"""REST API SIAKAD Pradita.

Menyediakan data pengajaran yang dipakai sebagai bukti BKD: daftar kelas yang
diampu, detail berita acara (topik + kehadiran), serta berkas PDF BAP dan
Kehadiran yang sudah dibubuhi tanda tangan.

Jalankan:
    ./siakad api              # http://localhost:8000

Contoh:
    curl -X POST "localhost:8000/kelas" -H "Content-Type: application/json" \
         -d '{"username":"...","password":"...","tahun_ajaran":"2025","tipe_semester":"2"}'
"""

from __future__ import annotations

import time
from pathlib import Path

from dependensi import pastikan_dependensi

# harus dipanggil sebelum impor paket pihak ketiga di bawahnya
pastikan_dependensi("api")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from berita_acara import JENIS_BUKTI, BeritaAcaraKuliah, Kelas
from konfigurasi import AKAR_PROYEK, DIR_DATA
from siakad_client import KlienSiakad, SiakadError

app = FastAPI(
    title="SIAKAD Pradita API",
    version="1.0.0",
    description="Ambil bukti pengajaran dari SIAKAD: daftar kelas, berita acara, BAP, kehadiran.",
)

# satu sesi login dipakai ulang selama masih segar
UMUR_SESI_DETIK = 900
sesi_tersimpan: dict[str, tuple[float, KlienSiakad]] = {}


class Kredensial(BaseModel):
    username: str = Field(description="Email SIAKAD")
    password: str = Field(description="Password SIAKAD")


class PermintaanPeriode(Kredensial):
    tahun_ajaran: str = Field(description="Mis. 2025 untuk tahun ajaran 2025/2026")
    tipe_semester: str = Field(description="1 ganjil, 2 genap, 3 semester pendek")
    prodi: str = Field(default="", description="Kode prodi, mis. TI. Kosong berarti semua")
    kode_mk: str = Field(default="", description="Batasi ke satu kode mata kuliah")


class PermintaanBukti(PermintaanPeriode):
    jenis: str = Field(default="bap", description="bap atau kehadiran")
    tujuan: str = Field(default="", description="Direktori penyimpanan; kosong = data/bap")
    tanggal: str = Field(default="", description="Tanggal pada blok tanda tangan")
    timpa: bool = False
    bertanda_tangan: bool = True


def ambil_laporan(kredensial: Kredensial) -> BeritaAcaraKuliah:
    """Login sekali, lalu pakai ulang sesinya untuk permintaan berikutnya."""
    kunci = f"{kredensial.username}:{hash(kredensial.password)}"
    tersimpan = sesi_tersimpan.get(kunci)
    if tersimpan and time.monotonic() - tersimpan[0] < UMUR_SESI_DETIK:
        return BeritaAcaraKuliah(tersimpan[1])

    try:
        klien = KlienSiakad(kredensial.username, kredensial.password).login()
    except SiakadError as galat:
        raise HTTPException(status_code=401, detail=str(galat))
    sesi_tersimpan[kunci] = (time.monotonic(), klien)
    return BeritaAcaraKuliah(klien)


def cari_kelas(permintaan: PermintaanPeriode) -> list[Kelas]:
    """Kelas pada periode yang diminta, sudah disaring kode mata kuliahnya."""
    laporan = ambil_laporan(permintaan)
    try:
        kelas = laporan.daftar_kelas(permintaan.tahun_ajaran, permintaan.tipe_semester, permintaan.prodi)
    except SiakadError as galat:
        raise HTTPException(status_code=502, detail=str(galat))
    if permintaan.kode_mk:
        kelas = [satu for satu in kelas if satu.kode_mk == permintaan.kode_mk]
    return kelas


@app.post("/sesi", summary="Cek kredensial SIAKAD")
def cek_sesi(kredensial: Kredensial):
    laporan = ambil_laporan(kredensial)
    return {"ok": True, "beranda": laporan.klien.url_beranda}


@app.post("/kelas", summary="Kelas yang diampu pada satu periode")
def daftar_kelas(permintaan: PermintaanPeriode):
    return {"data": [satu.__dict__ | {"label": satu.label} for satu in cari_kelas(permintaan)]}


@app.post("/berita-acara", summary="Topik pembahasan dan rekap kehadiran satu kelas")
def berita_acara(permintaan: PermintaanPeriode):
    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")
    laporan = ambil_laporan(permintaan)
    return {"kelas": kelas[0].label, "detail": laporan.detail(kelas[0])}


@app.post("/bukti/halaman", summary="Halaman cetak BAP/kehadiran (HTML)", response_class=HTMLResponse)
def halaman_bukti(permintaan: PermintaanBukti):
    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")
    laporan = ambil_laporan(permintaan)
    return HTMLResponse(laporan.halaman_cetak(kelas[0], permintaan.jenis))


@app.post("/bukti/pdf", summary="Unduh satu bukti sebagai PDF")
def pdf_bukti(permintaan: PermintaanBukti):
    if permintaan.jenis not in JENIS_BUKTI:
        raise HTTPException(status_code=422, detail=f"Jenis harus salah satu dari {list(JENIS_BUKTI)}")

    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")

    tujuan = Path(permintaan.tujuan) if permintaan.tujuan else DIR_DATA / "bap"
    if not tujuan.is_absolute():
        tujuan = AKAR_PROYEK / tujuan
    laporan = ambil_laporan(permintaan)
    berkas = laporan.unduh_bukti(
        kelas[0], permintaan.jenis, tujuan,
        timpa=permintaan.timpa,
        bertanda_tangan=permintaan.bertanda_tangan,
        tanggal_tanda_tangan=permintaan.tanggal,
    )
    return FileResponse(berkas, media_type="application/pdf", filename=berkas.name)


@app.post("/bukti/semua", summary="Unduh BAP dan kehadiran seluruh kelas satu periode")
def semua_bukti(permintaan: PermintaanBukti):
    """Berkas yang sudah ada dilewati, kecuali `timpa` bernilai true."""
    kelas = cari_kelas(permintaan)
    tujuan = Path(permintaan.tujuan) if permintaan.tujuan else DIR_DATA / "bap"
    if not tujuan.is_absolute():
        tujuan = AKAR_PROYEK / tujuan

    laporan = ambil_laporan(permintaan)
    dihasilkan, gagal = [], []
    for satu in kelas:
        for jenis in JENIS_BUKTI:
            try:
                berkas = laporan.unduh_bukti(
                    satu, jenis, tujuan,
                    timpa=permintaan.timpa,
                    bertanda_tangan=permintaan.bertanda_tangan,
                    tanggal_tanda_tangan=permintaan.tanggal,
                )
                dihasilkan.append(berkas.name)
            except (SiakadError, SystemExit) as galat:
                gagal.append({"kelas": satu.label, "jenis": jenis, "pesan": str(galat)})
    return {"tujuan": str(tujuan), "berkas": dihasilkan, "gagal": gagal}
