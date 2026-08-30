"""MCP server SIAKAD Pradita.

Membuka kemampuan yang sama dengan api.py lewat protokol MCP, sehingga asisten AI
bisa mengambil sendiri bukti pengajaran (BAP dan daftar kehadiran) untuk BKD.

Kredensial boleh dikirim per pemanggilan, atau dibiarkan kosong supaya jatuh ke
SIAKAD_USERNAME / SIAKAD_PASSWORD di berkas .env.

Daftarkan ke Claude Code (perintah `siakad-mcp` ikut terpasang bersama paketnya):
    claude mcp add bkd-siakad -- siakad-mcp
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from siakad_mcp import __version__
from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah
from siakad_mcp.cetak_pdf import CetakError
from siakad_mcp.konfigurasi import KonfigurasiError, akar_proyek, baca_pengaturan, dir_data
from siakad_mcp.siakad_client import SIAKAD_BASE_URL_BAWAAN, KlienSiakad, SiakadError

# instruksi menyebut instansi dan alamatnya supaya asisten tahu sistem mana yang
# sedang dipakai; keduanya ikut setelan, bukan ditanam di teks
NAMA_INSTANSI = baca_pengaturan("SIAKAD_NAMA_INSTANSI", "Pradita")
ALAMAT_INSTANSI = baca_pengaturan("SIAKAD_BASE_URL", SIAKAD_BASE_URL_BAWAAN)

server = MCPServer(
    name="bkd-siakad",
    version=__version__,
    instructions=(
        f"Mengambil bukti pengajaran dosen dari SIAKAD {NAMA_INSTANSI} "
        f"({ALAMAT_INSTANSI}) untuk keperluan BKD. Urutan yang disarankan: "
        "daftar_kelas untuk melihat kelas satu periode, lalu unduh_bukti atau "
        "unduh_semua_bukti untuk menghasilkan PDF BAP dan daftar kehadiran."
    ),
)


def buka_laporan(username: str = "", password: str = "") -> BeritaAcaraKuliah:
    """Login SIAKAD lalu siapkan akses menu Berita Acara Perkuliahan."""
    return BeritaAcaraKuliah(KlienSiakad(username or None, password or None).login())


def tentukan_tujuan(tujuan: str):
    """Direktori penyimpanan PDF; path relatif dihitung dari akar proyek."""
    lokasi = Path(tujuan) if tujuan else dir_data() / "bap"
    return lokasi if lokasi.is_absolute() else akar_proyek() / lokasi


@server.tool()
def cek_login(username: str = "", password: str = "") -> dict:
    """Cek apakah email dan password SIAKAD bisa dipakai."""
    try:
        klien = KlienSiakad(username or None, password or None).login()
    except SiakadError as galat:
        return {"ok": False, "pesan": str(galat)}
    return {"ok": True, "beranda": klien.url_beranda}


@server.tool()
def daftar_menu(username: str = "", password: str = "") -> list[dict]:
    """Menu SIAKAD yang tersedia bagi akun ini."""
    return KlienSiakad(username or None, password or None).login().daftar_navigasi()


@server.tool()
def daftar_kelas(
    tahun_ajaran: str, tipe_semester: str, prodi: str = "", username: str = "", password: str = ""
) -> list[dict]:
    """Kelas yang diampu pada satu periode.

    tahun_ajaran '2025' berarti 2025/2026; tipe_semester 1 ganjil, 2 genap, 3 pendek.
    """
    laporan = buka_laporan(username, password)
    return [
        satu.__dict__ | {"label": satu.label}
        for satu in laporan.daftar_kelas(tahun_ajaran, tipe_semester, prodi)
    ]


@server.tool()
def berita_acara(
    tahun_ajaran: str, tipe_semester: str, kode_mk: str, username: str = "", password: str = ""
) -> dict:
    """Topik pembahasan tiap pertemuan dan rekap kehadiran mahasiswa satu kelas."""
    laporan = buka_laporan(username, password)
    kelas = [
        satu
        for satu in laporan.daftar_kelas(tahun_ajaran, tipe_semester)
        if satu.kode_mk == kode_mk
    ]
    if not kelas:
        return {"ok": False, "pesan": f"Mata kuliah {kode_mk} tidak ada pada periode itu"}
    return {"kelas": kelas[0].label, "detail": laporan.detail(kelas[0])}


@server.tool()
def unduh_semua_bukti(
    tahun_ajaran: str,
    tipe_semester: str,
    tujuan: str = "",
    prodi: str = "",
    kode_mk: str = "",
    tanggal: str = "",
    tanda_tangan: str = "",
    timpa: bool = False,
    bertanda_tangan: bool = True,
    username: str = "",
    password: str = "",
) -> dict:
    """Hasilkan PDF BAP dan Kehadiran untuk seluruh kelas pada satu periode.

    Berkas yang sudah ada dilewati kecuali `timpa` bernilai True. Halaman BAP
    dibubuhi paraf dosen dan tanda tangan pejabat dari folder `tanda_tangan`;
    kalau dikosongkan, dipakai folder digital_signs di akar proyek.
    """
    laporan = buka_laporan(username, password)
    lokasi = tentukan_tujuan(tujuan)
    kelas = laporan.daftar_kelas(tahun_ajaran, tipe_semester, prodi)
    if kode_mk:
        kelas = [satu for satu in kelas if satu.kode_mk == kode_mk]

    dihasilkan, gagal = [], []
    for satu in kelas:
        for jenis in JENIS_BUKTI:
            try:
                berkas = laporan.unduh_bukti(
                    satu, jenis, lokasi,
                    timpa=timpa, bertanda_tangan=bertanda_tangan, tanggal_tanda_tangan=tanggal,
                    dir_tanda_tangan=tanda_tangan or None,
                )
                dihasilkan.append(str(berkas))
            except (SiakadError, CetakError, KonfigurasiError) as galat:
                gagal.append({"kelas": satu.label, "jenis": jenis, "pesan": str(galat)})
    return {"tujuan": str(lokasi), "berkas": dihasilkan, "gagal": gagal}


def jalankan() -> None:
    """Titik masuk perintah `siakad-mcp` (stdio)."""
    server.run()


if __name__ == "__main__":
    jalankan()
