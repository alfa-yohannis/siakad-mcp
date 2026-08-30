"""REST API SIAKAD Pradita.

Menyediakan data pengajaran yang dipakai sebagai bukti BKD: daftar kelas yang
diampu, detail berita acara (topik + kehadiran), jadwal mengajar, pertemuan
beserta mahasiswanya, serta berkas PDF BAP dan Kehadiran yang sudah dibubuhi
tanda tangan.

Jalankan:
    ./siakad api              # http://localhost:8000

Contoh:
    curl -X POST "localhost:8000/kelas" -H "Content-Type: application/json" \
         -d '{"username":"...","password":"...","tahun_ajaran":"2025","tipe_semester":"2"}'
"""

from __future__ import annotations

import time
from pathlib import Path


from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah, Kelas
from siakad_mcp.cetak_pdf import CetakError
from siakad_mcp.daftar_hadir import DaftarHadir, Pertemuan
from siakad_mcp.jadwal import JadwalMengajar
from siakad_mcp.konfigurasi import (
    KonfigurasiError,
    akar_proyek,
    baca_angka,
    baca_pengaturan,
    dir_data,
)
from siakad_mcp.siakad_client import KlienSiakad, SiakadError

# nama perguruan tinggi hanya untuk label; tidak memengaruhi perilaku apa pun
NAMA_INSTANSI = baca_pengaturan("SIAKAD_NAMA_INSTANSI", "Pradita")

# Rute dikumpulkan di router, bukan langsung di app, supaya proyek lain bisa
# menempelkannya ke aplikasi FastAPI miliknya sendiri:
#     from siakad_mcp.api import router
#     app_saya.include_router(router, prefix="/siakad")
router = APIRouter()


def buat_app() -> FastAPI:
    """Aplikasi FastAPI berdiri sendiri yang hanya berisi rute paket ini."""
    app = FastAPI(
        title=f"SIAKAD {NAMA_INSTANSI} API",
        version="1.0.0",
        description=(
            "Ambil data pengajaran dari SIAKAD: daftar kelas, berita acara, jadwal mengajar, "
            "pertemuan dan mahasiswanya, serta PDF BAP dan kehadiran."
        ),
    )
    app.include_router(router)
    return app

# satu sesi login dipakai ulang selama masih segar
UMUR_SESI_DETIK = baca_angka("SIAKAD_UMUR_SESI_DETIK", 900)
sesi_tersimpan: dict[str, tuple[float, KlienSiakad]] = {}


class Kredensial(BaseModel):
    username: str = Field(description="Email SIAKAD")
    password: str = Field(description="Password SIAKAD")


class PermintaanPeriode(Kredensial):
    tahun_ajaran: str = Field(description="Mis. 2025 untuk tahun ajaran 2025/2026")
    tipe_semester: str = Field(description="1 ganjil, 2 genap, 3 semester pendek")
    prodi: str = Field(default="", description="Kode prodi, mis. TI. Kosong berarti semua")
    kode_mk: str = Field(default="", description="Batasi ke satu kode mata kuliah")


class PermintaanPertemuan(PermintaanPeriode):
    tanggal: str = Field(default="", description="YYYY-MM-DD; kosong berarti seluruh periode")


class PermintaanMahasiswa(PermintaanPeriode):
    kelompok_kelas: str = Field(default="", description="Mis. 'Kelas A'; kosong berarti kelas pertama")


class PermintaanBukaKelas(PermintaanPeriode):
    tanggal: str = Field(description="Tanggal pertemuan yang dibuka, YYYY-MM-DD")
    kelompok_kelas: str = Field(default="", description="Mis. 'Kelas A', kalau tanggalnya bentrok")
    uji_coba: bool = Field(default=False, description="true: tampilkan muatannya, jangan kirim")


class PermintaanPembahasan(PermintaanPeriode):
    tanggal: str = Field(description="Tanggal pertemuan yang diisi, YYYY-MM-DD")
    topik: str = Field(description="Topik Pembahasan")
    deskripsi: str = Field(default="", description="Deskripsi Pembahasan")
    kelompok_kelas: str = Field(default="", description="Mis. 'Kelas A', kalau tanggalnya bentrok")
    uji_coba: bool = Field(default=False, description="true: tampilkan muatannya, jangan kirim")


class PermintaanBukti(PermintaanPeriode):
    jenis: str = Field(default="bap", description="bap atau kehadiran")
    tujuan: str = Field(default="", description="Direktori penyimpanan; kosong = data/bap")
    tanggal: str = Field(default="", description="Tanggal pada blok tanda tangan")
    tanda_tangan: str = Field(
        default="", description="Folder berkas tanda tangan; kosong = digital_signs di akar proyek"
    )
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


@router.post("/sesi", summary="Cek kredensial SIAKAD")
def cek_sesi(kredensial: Kredensial):
    laporan = ambil_laporan(kredensial)
    return {"ok": True, "beranda": laporan.klien.url_beranda}


@router.post("/kelas", summary="Kelas yang diampu pada satu periode")
def daftar_kelas(permintaan: PermintaanPeriode):
    return {"data": [satu.__dict__ | {"label": satu.label} for satu in cari_kelas(permintaan)]}


@router.post("/berita-acara", summary="Topik pembahasan dan rekap kehadiran satu kelas")
def berita_acara(permintaan: PermintaanPeriode):
    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")
    laporan = ambil_laporan(permintaan)
    return {"kelas": kelas[0].label, "detail": laporan.detail(kelas[0])}


@router.post("/bukti/halaman", summary="Halaman cetak BAP/kehadiran (HTML)", response_class=HTMLResponse)
def halaman_bukti(permintaan: PermintaanBukti):
    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")
    laporan = ambil_laporan(permintaan)
    return HTMLResponse(laporan.halaman_cetak(kelas[0], permintaan.jenis))


@router.post("/bukti/pdf", summary="Unduh satu bukti sebagai PDF")
def pdf_bukti(permintaan: PermintaanBukti):
    if permintaan.jenis not in JENIS_BUKTI:
        raise HTTPException(status_code=422, detail=f"Jenis harus salah satu dari {list(JENIS_BUKTI)}")

    kelas = cari_kelas(permintaan)
    if not kelas:
        raise HTTPException(status_code=404, detail="Tidak ada kelas yang cocok")

    tujuan = Path(permintaan.tujuan) if permintaan.tujuan else dir_data() / "bap"
    if not tujuan.is_absolute():
        tujuan = akar_proyek() / tujuan
    laporan = ambil_laporan(permintaan)
    berkas = laporan.unduh_bukti(
        kelas[0], permintaan.jenis, tujuan,
        timpa=permintaan.timpa,
        bertanda_tangan=permintaan.bertanda_tangan,
        tanggal_tanda_tangan=permintaan.tanggal,
        dir_tanda_tangan=permintaan.tanda_tangan or None,
    )
    return FileResponse(berkas, media_type="application/pdf", filename=berkas.name)


@router.post("/jadwal", summary="Jadwal mengajar satu periode")
def jadwal_mengajar(permintaan: PermintaanPeriode):
    """Hari, jam, ruang, dan SKS tiap kelas — dari menu Jadwal Mengajar."""
    jadwal = JadwalMengajar(ambil_laporan(permintaan).klien).daftar(
        permintaan.tahun_ajaran, permintaan.tipe_semester, permintaan.prodi
    )
    if permintaan.kode_mk:
        jadwal = [satu for satu in jadwal if satu.kode_mk == permintaan.kode_mk]
    return {"data": [satu.sebagai_dict() for satu in jadwal]}


@router.post("/pertemuan", summary="Pertemuan pada menu Daftar Hadir")
def daftar_pertemuan(permintaan: PermintaanPertemuan):
    """Satu baris berarti satu tatap muka. `tanggal` kosong = seluruh periode."""
    pertemuan = DaftarHadir(ambil_laporan(permintaan).klien).daftar_pertemuan(
        permintaan.tahun_ajaran, permintaan.tipe_semester, permintaan.tanggal
    )
    if permintaan.kode_mk:
        pertemuan = [satu for satu in pertemuan if satu.kode_mk == permintaan.kode_mk]
    return {"data": [satu.sebagai_dict() for satu in pertemuan]}


@router.post("/mahasiswa", summary="Mahasiswa yang terdaftar pada satu mata kuliah")
def daftar_mahasiswa(permintaan: PermintaanMahasiswa):
    """Diambil dari pertemuan pertama mata kuliah itu; pesertanya sama di semua pertemuan.

    Hanya NIM, nama, kelas, dan status yang dikembalikan. Rekam pribadi lain yang
    ikut dikirim SIAKAD (KTP, alamat, wali) sengaja tidak diteruskan.
    """
    if not permintaan.kode_mk:
        raise HTTPException(status_code=422, detail="kode_mk wajib diisi")
    try:
        pertemuan, mahasiswa = DaftarHadir(ambil_laporan(permintaan).klien).mahasiswa_kelas(
            permintaan.tahun_ajaran, permintaan.tipe_semester,
            permintaan.kode_mk, permintaan.kelompok_kelas,
        )
    except SiakadError as galat:
        raise HTTPException(status_code=404, detail=str(galat))
    return {
        "pertemuan": pertemuan.sebagai_dict(),
        "jumlah": len(mahasiswa),
        "data": [satu.__dict__ for satu in mahasiswa],
    }


def satu_pertemuan(hadir: DaftarHadir, permintaan) -> "Pertemuan":
    """Pertemuan tunggal yang ditunjuk permintaan; menolak kalau ambigu.

    Dipakai endpoint yang menulis: lebih baik menolak daripada mengubah
    pertemuan yang tidak dimaksud.
    """
    cocok = [
        satu
        for satu in hadir.daftar_pertemuan(permintaan.tahun_ajaran, permintaan.tipe_semester, permintaan.tanggal)
        if satu.kode_mk == permintaan.kode_mk
        and (not permintaan.kelompok_kelas or satu.kelompok_kelas == permintaan.kelompok_kelas)
    ]
    if not cocok:
        raise HTTPException(status_code=404, detail="Tidak ada pertemuan yang cocok")
    if len(cocok) > 1:
        raise HTTPException(
            status_code=409,
            detail=f"{len(cocok)} pertemuan cocok; sebutkan tanggal (dan kelompok_kelas) yang tepat",
        )
    return cocok[0]


@router.post("/buka-kelas", summary="Buka satu pertemuan supaya mahasiswa bisa mengabsen")
def buka_kelas(permintaan: PermintaanBukaKelas):
    """**Menulis** ke SIAKAD, dan kelas yang sudah dibuka tidak bisa ditutup lagi."""
    hadir = DaftarHadir(ambil_laporan(permintaan).klien)
    return hadir.buka_kelas(satu_pertemuan(hadir, permintaan), uji_coba=permintaan.uji_coba)


@router.post("/pembahasan", summary="Isi Topik dan Deskripsi Pembahasan satu pertemuan")
def simpan_pembahasan(permintaan: PermintaanPembahasan):
    """Satu-satunya endpoint yang **menulis** ke SIAKAD; isian lama akan tertimpa.

    `uji_coba` bernilai true mengembalikan muatan yang akan dikirim tanpa
    mengirimnya, supaya isian bisa diperiksa dulu.
    """
    hadir = DaftarHadir(ambil_laporan(permintaan).klien)
    return hadir.simpan_pembahasan(
        satu_pertemuan(hadir, permintaan), permintaan.topik, permintaan.deskripsi,
        uji_coba=permintaan.uji_coba,
    )


@router.post("/bukti/semua", summary="Unduh BAP dan kehadiran seluruh kelas satu periode")
def semua_bukti(permintaan: PermintaanBukti):
    """Berkas yang sudah ada dilewati, kecuali `timpa` bernilai true."""
    kelas = cari_kelas(permintaan)
    tujuan = Path(permintaan.tujuan) if permintaan.tujuan else dir_data() / "bap"
    if not tujuan.is_absolute():
        tujuan = akar_proyek() / tujuan

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
                    dir_tanda_tangan=permintaan.tanda_tangan or None,
                )
                dihasilkan.append(berkas.name)
            except (SiakadError, CetakError, KonfigurasiError) as galat:
                gagal.append({"kelas": satu.label, "jenis": jenis, "pesan": str(galat)})
    return {"tujuan": str(tujuan), "berkas": dihasilkan, "gagal": gagal}


app = buat_app()
