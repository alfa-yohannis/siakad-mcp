"""Berita Acara Perkuliahan (/report/berita_acara_kuliah).

Menyediakan tiga hal yang dibutuhkan untuk bukti BKD pengajaran:

    daftar_kelas()  -> kelas yang diampu pada satu periode
    detail()        -> topik pembahasan + rekap kehadiran mahasiswa (JSON)
    unduh_bukti()   -> berkas PDF "BAP" dan "Kehadiran" per kelas

Catatan penting soal endpoint pencariannya: SIAKAD membalas HTTP 500 kalau
`sort_search`/`order_search` ikut dikirim dalam keadaan kosong, jadi keduanya
sengaja tidak pernah disertakan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from siakad_mcp.cetak_pdf import cetak_html_ke_pdf
from siakad_mcp.konfigurasi import baca_pengaturan
from siakad_mcp.menu import MenuSiakad
from siakad_mcp.siakad_client import SiakadError
from siakad_mcp.tanda_tangan import sisipkan_tanda_tangan

PATH_LAPORAN_BAWAAN = "/report/berita_acara_kuliah"

# jenis bukti -> (endpoint ekspor, akhiran nama berkas, kunci setelan ukuran kertas)
JENIS_BUKTI = {
    "bap": ("export_pdf_topik_pembahasan", "BAP", "SIAKAD_UKURAN_BAP", "A3"),
    "kehadiran": ("export_pdf_absensi_mahasiswa", "Kehadiran", "SIAKAD_UKURAN_KEHADIRAN", "A4"),
}


@dataclass
class Kelas:
    """Satu kelas yang diampu pada satu periode — kunci untuk semua permintaan lain."""

    dosen_id: str
    kode_mk: str
    nama_mk: str
    tahun_ajaran: str
    tipe_semester: str
    jam_mulai: str
    hari: str
    kelompok_kelas: str = ""
    nama_dosen: str = ""
    jurusan: str = ""

    @classmethod
    def dari_baris(cls, baris: dict) -> "Kelas":
        """Bangun dari satu baris hasil pencarian SIAKAD."""
        kelompok = (baris.get("KELOMPOK_KELAS") or "").strip()
        return cls(
            dosen_id=baris["DOSEN_ID"],
            kode_mk=baris["KD_MATA_KULIAH"],
            nama_mk=baris["NM_MATA_KULIAH"],
            tahun_ajaran=str(baris["TAHUN_AJARAN"]),
            tipe_semester=str(baris["TIPE_SEMESTER"]),
            jam_mulai=baris["JAM_MULAI"],
            hari=baris["HARI"],
            kelompok_kelas="" if kelompok in ("", "-") else kelompok,
            nama_dosen=baris.get("NAMA_DOSEN", ""),
            jurusan=baris.get("NM_JURUSAN", ""),
        )

    @property
    def label(self) -> str:
        """Nama yang enak dibaca, mis. 'IF30812 - Pemrograman Berorientasi Objek (Kelas B)'."""
        kelas = f" ({self.kelompok_kelas})" if self.kelompok_kelas else ""
        return f"{self.kode_mk} - {self.nama_mk}{kelas}"

    def nama_berkas(self, akhiran: str) -> str:
        """Nama berkas bukti, mengikuti pola berkas yang sudah dipakai selama ini."""
        kelas = f" - {self.kelompok_kelas}" if self.kelompok_kelas else ""
        aman = "".join(huruf for huruf in self.nama_mk if huruf not in '/\\:*?"<>|').strip()
        return f"{self.kode_mk} - {aman}{kelas} - {akhiran}.pdf"

    def sebagai_parameter(self) -> dict[str, str]:
        """Parameter yang diminta endpoint detail dan ekspor."""
        return {
            "DOSEN_ID": self.dosen_id,
            "KD_MATA_KULIAH": self.kode_mk,
            "TAHUN_AJARAN": self.tahun_ajaran,
            "TIPE_SEMESTER": self.tipe_semester,
            "JAM_MULAI": self.jam_mulai,
            "HARI": self.hari,
        }


class BeritaAcaraKuliah(MenuSiakad):
    """Akses menu Berita Acara Perkuliahan untuk satu sesi SIAKAD."""

    path_bawaan = PATH_LAPORAN_BAWAAN
    kunci_path = "SIAKAD_PATH_LAPORAN"

    def daftar_kelas(
        self, tahun_ajaran: str, tipe_semester: str, prodi: str = "", pencarian: str = ""
    ) -> list[Kelas]:
        """Kelas pada satu periode. Semua halaman hasil ditelusuri sampai habis."""
        baris = self.cari_semua(
            "search",
            {
                "text_search": pencarian,
                "tipe_semester": tipe_semester,
                "tahun_ajaran": tahun_ajaran,
                "prodi_search": prodi,
            },
            keterangan="kelas",
        )
        return [Kelas.dari_baris(satu) for satu in baris]

    def detail(self, kelas: Kelas) -> dict:
        """Topik pembahasan dan rekap kehadiran satu kelas, apa adanya dari SIAKAD."""
        jawaban = self.kirim("detail", kelas.sebagai_parameter())
        if jawaban.status_code != 200:
            raise SiakadError(f"Detail {kelas.label} gagal (HTTP {jawaban.status_code})")
        return jawaban.json()

    def halaman_cetak(self, kelas: Kelas, jenis: str) -> str:
        """Halaman siap cetak dari SIAKAD — inilah yang biasanya di-Ctrl+P manual."""
        if jenis not in JENIS_BUKTI:
            raise SiakadError(f"Jenis bukti '{jenis}' tidak dikenal: {', '.join(JENIS_BUKTI)}")

        endpoint, _, _, _ = JENIS_BUKTI[jenis]
        # endpoint ekspor memakai nama field huruf kecil, berbeda dari endpoint detail
        jawaban = self.kirim(
            endpoint,
            {
                "kd_mata_kuliah": kelas.kode_mk,
                "nm_mata_kuliah": kelas.nama_mk,
                "dosen_id": kelas.dosen_id,
                "tahun_ajaran": kelas.tahun_ajaran,
                "tipe_semester": kelas.tipe_semester,
                "jam_mulai": kelas.jam_mulai,
                "hari": kelas.hari,
            },
        )
        if jawaban.status_code != 200:
            raise SiakadError(f"Halaman cetak {jenis} gagal (HTTP {jawaban.status_code})")
        return jawaban.text

    def unduh_bukti(
        self,
        kelas: Kelas,
        jenis: str,
        dir_tujuan: Path,
        *,
        timpa: bool = False,
        bertanda_tangan: bool = True,
        tanggal_tanda_tangan: str = "",
        dir_tanda_tangan: str | Path | None = None,
    ) -> Path:
        """Simpan satu bukti (bap/kehadiran) sebagai PDF di direktori tujuan.

        `dir_tanda_tangan` menimpa letak folder tanda tangan; kosong berarti
        ikut urutan pencarian bawaan.
        """
        _, akhiran, kunci_ukuran, ukuran_bawaan = JENIS_BUKTI[jenis]
        ukuran = baca_pengaturan(kunci_ukuran, ukuran_bawaan)
        tujuan = Path(dir_tujuan) / kelas.nama_berkas(akhiran)
        if tujuan.is_file() and not timpa:
            return tujuan

        html = self.halaman_cetak(kelas, jenis)
        # hanya halaman BAP yang punya kolom paraf dan blok tanda tangan pejabat
        if bertanda_tangan and jenis == "bap":
            html = sisipkan_tanda_tangan(
                html, kelas.nama_dosen, tanggal=tanggal_tanda_tangan, direktori=dir_tanda_tangan
            )
        return cetak_html_ke_pdf(html, tujuan, ukuran=ukuran)
