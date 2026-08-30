"""MCP server SIAKAD Pradita.

Membuka kemampuan yang sama dengan api.py lewat protokol MCP, sehingga asisten AI
bisa mengambil sendiri bukti pengajaran (BAP dan daftar kehadiran) untuk BKD.

Kredensial boleh dikirim per pemanggilan, atau dibiarkan kosong supaya jatuh ke
SIAKAD_USERNAME / SIAKAD_PASSWORD di berkas .env.

Daftarkan ke Claude Code (perintah `siakad-mcp` ikut terpasang bersama paketnya):
    claude mcp add siakad-mcp -- siakad-mcp
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from siakad_mcp import __version__
from siakad_mcp.berita_acara import JENIS_BUKTI, BeritaAcaraKuliah
from siakad_mcp.cetak_pdf import CetakError
from siakad_mcp.daftar_hadir import DaftarHadir
from siakad_mcp.jadwal import JadwalMengajar
from siakad_mcp.konfigurasi import KonfigurasiError, akar_proyek, baca_pengaturan, dir_data
from siakad_mcp.siakad_client import SIAKAD_BASE_URL_BAWAAN, KlienSiakad, SiakadError

# instruksi menyebut instansi dan alamatnya supaya asisten tahu sistem mana yang
# sedang dipakai; keduanya ikut setelan, bukan ditanam di teks
NAMA_INSTANSI = baca_pengaturan("SIAKAD_NAMA_INSTANSI", "Pradita")
ALAMAT_INSTANSI = baca_pengaturan("SIAKAD_BASE_URL", SIAKAD_BASE_URL_BAWAAN)

server = MCPServer(
    name="siakad-mcp",
    version=__version__,
    instructions=(
        f"Mengambil data pengajaran dosen dari SIAKAD {NAMA_INSTANSI} "
        f"({ALAMAT_INSTANSI}), terutama untuk keperluan BKD. Urutan yang "
        "disarankan: daftar_kelas atau jadwal_mengajar untuk melihat kelas satu "
        "periode, lalu unduh_semua_bukti untuk menghasilkan PDF BAP dan daftar "
        "kehadiran. Untuk peserta kuliah pakai daftar_mahasiswa, dan untuk tatap "
        "muka per tanggal pakai daftar_pertemuan. Semua tool hanya membaca, "
        "kecuali buka_kelas (membuka pertemuan untuk absensi, tidak bisa "
        "dibatalkan) dan simpan_pembahasan (mengisi Topik/Deskripsi Pembahasan, "
        "menimpa isian lama) — jalankan keduanya dengan uji_coba=True lebih "
        "dulu dan minta persetujuan pemakai."
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
def jadwal_mengajar(
    tahun_ajaran: str, tipe_semester: str, prodi: str = "", username: str = "", password: str = ""
) -> list[dict]:
    """Jadwal mengajar satu periode: hari, jam, ruang, dan SKS tiap kelas.

    Berbeda dari daftar_kelas yang berangkat dari laporan Berita Acara, ini
    jadwal yang disusun bagian akademik — ruang dan jam selesai hanya ada di sini.
    """
    klien = KlienSiakad(username or None, password or None).login()
    return [
        satu.sebagai_dict()
        for satu in JadwalMengajar(klien).daftar(tahun_ajaran, tipe_semester, prodi)
    ]


@server.tool()
def daftar_pertemuan(
    tahun_ajaran: str,
    tipe_semester: str,
    tanggal: str = "",
    kode_mk: str = "",
    username: str = "",
    password: str = "",
) -> list[dict]:
    """Pertemuan (tatap muka) satu periode beserta keterangan sudah dibuka atau belum.

    `tanggal` kosong berarti seluruh periode; diisi YYYY-MM-DD berarti satu hari.
    """
    klien = KlienSiakad(username or None, password or None).login()
    pertemuan = DaftarHadir(klien).daftar_pertemuan(tahun_ajaran, tipe_semester, tanggal)
    if kode_mk:
        pertemuan = [satu for satu in pertemuan if satu.kode_mk == kode_mk]
    return [satu.sebagai_dict() for satu in pertemuan]


@server.tool()
def daftar_mahasiswa(
    tahun_ajaran: str,
    tipe_semester: str,
    kode_mk: str,
    kelompok_kelas: str = "",
    username: str = "",
    password: str = "",
) -> dict:
    """Mahasiswa yang terdaftar pada satu mata kuliah: NIM, nama, kelas, status.

    Diambil dari pertemuan pertama mata kuliah itu karena pesertanya sama di
    semua pertemuan. `kelompok_kelas` memisahkan Kelas A dari Kelas B. Rekam
    pribadi lain yang ikut dikirim SIAKAD (KTP, alamat, wali) tidak diteruskan.
    """
    klien = KlienSiakad(username or None, password or None).login()
    try:
        pertemuan, mahasiswa = DaftarHadir(klien).mahasiswa_kelas(
            tahun_ajaran, tipe_semester, kode_mk, kelompok_kelas
        )
    except SiakadError as galat:
        return {"ok": False, "pesan": str(galat)}
    return {
        "pertemuan": pertemuan.sebagai_dict(),
        "jumlah": len(mahasiswa),
        "mahasiswa": [satu.__dict__ for satu in mahasiswa],
    }


@server.tool()
def buka_kelas(
    tahun_ajaran: str,
    tipe_semester: str,
    kode_mk: str,
    tanggal: str,
    kelompok_kelas: str = "",
    uji_coba: bool = False,
    username: str = "",
    password: str = "",
) -> dict:
    """Buka satu pertemuan di SIAKAD supaya mahasiswa bisa mulai mengabsen.

    MENULIS ke SIAKAD, dan sekali dibuka tidak bisa ditutup lagi. SIAKAD hanya
    mengizinkannya pada hari pertemuan itu sendiri. Jalankan dengan
    `uji_coba=True` lebih dulu dan mintalah persetujuan pemakai.
    """
    klien = KlienSiakad(username or None, password or None).login()
    hadir = DaftarHadir(klien)
    pertemuan = [
        satu
        for satu in hadir.daftar_pertemuan(tahun_ajaran, tipe_semester, tanggal)
        if satu.kode_mk == kode_mk and (not kelompok_kelas or satu.kelompok_kelas == kelompok_kelas)
    ]
    if not pertemuan:
        return {"ok": False, "pesan": f"Tidak ada pertemuan {kode_mk} pada {tanggal}"}
    if len(pertemuan) > 1:
        return {
            "ok": False,
            "pesan": f"{len(pertemuan)} pertemuan cocok pada {tanggal}; sebutkan kelompok_kelas",
            "pilihan": [satu.kelompok_kelas for satu in pertemuan],
        }
    return hadir.buka_kelas(pertemuan[0], uji_coba=uji_coba)


@server.tool()
def simpan_pembahasan(
    tahun_ajaran: str,
    tipe_semester: str,
    kode_mk: str,
    tanggal: str,
    topik: str,
    deskripsi: str = "",
    kelompok_kelas: str = "",
    uji_coba: bool = False,
    username: str = "",
    password: str = "",
) -> dict:
    """Isi Topik dan Deskripsi Pembahasan (BAP) satu pertemuan di SIAKAD.

    SATU-SATUNYA tool di server ini yang MENULIS ke SIAKAD — selebihnya membaca.
    Isian lama pada pertemuan itu akan tertimpa dan SIAKAD tidak menyimpan
    riwayatnya, jadi pastikan tanggalnya benar. Jalankan dulu dengan
    `uji_coba=True` untuk melihat apa yang akan dikirim tanpa mengirimnya, dan
    mintalah persetujuan pemakai sebelum menulis banyak pertemuan sekaligus.

    `tanggal` wajib (YYYY-MM-DD) supaya tidak ada pertemuan yang terisi tanpa
    disengaja; `kelompok_kelas` dipakai kalau dua kelas bertemu pada tanggal sama.
    """
    klien = KlienSiakad(username or None, password or None).login()
    hadir = DaftarHadir(klien)
    pertemuan = [
        satu
        for satu in hadir.daftar_pertemuan(tahun_ajaran, tipe_semester, tanggal)
        if satu.kode_mk == kode_mk and (not kelompok_kelas or satu.kelompok_kelas == kelompok_kelas)
    ]
    if not pertemuan:
        return {"ok": False, "pesan": f"Tidak ada pertemuan {kode_mk} pada {tanggal}"}
    if len(pertemuan) > 1:
        return {
            "ok": False,
            "pesan": f"{len(pertemuan)} pertemuan cocok pada {tanggal}; sebutkan kelompok_kelas",
            "pilihan": [satu.kelompok_kelas for satu in pertemuan],
        }
    return hadir.simpan_pembahasan(pertemuan[0], topik, deskripsi, uji_coba=uji_coba)


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
