"""Daftar Hadir (/dosen/daftar_hadir).

Menu ini berangkat dari **pertemuan**, bukan dari kelas: satu baris berarti satu
tatap muka pada tanggal tertentu, dan daftar mahasiswanya menempel di situ.

    daftar_pertemuan()   -> seluruh pertemuan satu periode (boleh disaring tanggal)
    daftar_mahasiswa()   -> mahasiswa satu pertemuan, beserta status kehadirannya
    mahasiswa_kelas()    -> jalan pintas: mahasiswa satu mata kuliah
    detail()             -> balasan SIAKAD apa adanya, untuk keperluan lain
    buka_kelas()         -> buka pertemuan supaya mahasiswa bisa mengabsen
    simpan_pembahasan()  -> tulis Topik & Deskripsi Pembahasan satu pertemuan

Dua yang terakhir satu-satunya yang menulis ke SIAKAD di seluruh paket ini.
Keduanya menyediakan `uji_coba` supaya bisa dijalankan kering dulu — penting
karena kelas yang sudah dibuka tidak bisa ditutup lagi, dan isian pembahasan
lama tertimpa tanpa riwayat.

Catatan privasi: SIAKAD mengirim rekam mahasiswa selengkapnya pada endpoint
detail — nomor KTP, alamat, nama orang tua, nomor telepon. Yang dipetakan ke
`Mahasiswa` hanya yang diperlukan untuk urusan perkuliahan (NIM, nama, email
kampus, kelas, status). Pemanggil yang memang membutuhkan sisanya bisa memakai
`detail()` dan mengambilnya sendiri, jadi data pribadi tidak ikut mengalir tanpa
diminta.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from siakad_mcp.konfigurasi import baca_pemetaan, baca_pengaturan
from siakad_mcp.menu import MenuSiakad, jam_ringkas, nama_hari
from siakad_mcp.siakad_client import SiakadError

PATH_DAFTAR_HADIR_BAWAAN = "/dosen/daftar_hadir"

# parameter yang menentukan satu pertemuan pada endpoint detail
KUNCI_PERTEMUAN = (
    "DOSEN_ID", "KD_MATA_KULIAH", "TAHUN_AJARAN", "TIPE_SEMESTER",
    "HARI", "JAM_MULAI", "TGL_ABSENSI", "SESI",
)


@dataclass
class Pertemuan:
    """Satu tatap muka: mata kuliah, tanggal, jam, ruang, dan kelasnya."""

    dosen_id: str
    kode_mk: str
    nama_mk: str
    tahun_ajaran: str
    tipe_semester: str
    hari: str
    jam_mulai: str
    tanggal: str
    sesi: str
    jam_selesai: str = ""
    ruang: str = ""
    kelompok_kelas: str = ""
    prodi: str = ""
    nama_dosen: str = ""
    jam_dibuka: str = ""

    @classmethod
    def dari_baris(cls, baris: dict) -> "Pertemuan":
        """Bangun dari satu baris hasil pencarian daftar hadir."""
        kelompok = (baris.get("KELOMPOK_KELAS") or "").strip()
        return cls(
            dosen_id=baris.get("DOSEN_ID", ""),
            kode_mk=(baris.get("KD_MATA_KULIAH") or "").strip(),
            nama_mk=(baris.get("NM_MATA_KULIAH") or "").strip(),
            tahun_ajaran=str(baris.get("TAHUN_AJARAN", "")),
            tipe_semester=str(baris.get("TIPE_SEMESTER", "")),
            hari=baris.get("HARI", ""),
            jam_mulai=baris.get("JAM_MULAI", ""),
            tanggal=baris.get("TGL_ABSENSI", ""),
            sesi=str(baris.get("SESI", "")),
            jam_selesai=baris.get("JAM_SELESAI_ABSENSI") or baris.get("JAM_SELESAI") or "",
            ruang=(baris.get("NM_RUANG") or baris.get("KD_RUANG") or "").strip(),
            kelompok_kelas="" if kelompok in ("", "-") else kelompok,
            prodi=baris.get("NM_JURUSAN", ""),
            nama_dosen=baris.get("NAMA_DOSEN", ""),
            # JAM_ABSEN hanya terisi kalau kelasnya sudah pernah dibuka
            jam_dibuka=baris.get("JAM_ABSEN") or "",
        )

    @property
    def label(self) -> str:
        """Mis. 'IF31613 - Arsitektur Perangkat Lunak (Kelas A) — 2026-08-31'."""
        kelas = f" ({self.kelompok_kelas})" if self.kelompok_kelas else ""
        return f"{self.kode_mk} - {self.nama_mk}{kelas} — {self.tanggal}"

    @property
    def waktu(self) -> str:
        """Mis. 'Senin 08:25-11:05'."""
        return f"{nama_hari(self.hari)} {jam_ringkas(self.jam_mulai)}-{jam_ringkas(self.jam_selesai)}"

    @property
    def sudah_dibuka(self) -> bool:
        """Kelas yang belum dibuka belum punya rekaman kehadiran sama sekali."""
        return bool(self.jam_dibuka)

    def sebagai_parameter(self) -> dict[str, str]:
        """Parameter yang diminta endpoint detail."""
        return {
            "DOSEN_ID": self.dosen_id,
            "KD_MATA_KULIAH": self.kode_mk,
            "TAHUN_AJARAN": self.tahun_ajaran,
            "TIPE_SEMESTER": self.tipe_semester,
            "HARI": self.hari,
            "JAM_MULAI": self.jam_mulai,
            "TGL_ABSENSI": self.tanggal,
            "SESI": self.sesi,
        }

    def sebagai_dict(self) -> dict:
        """Bentuk datar siap dikirim REST API/MCP."""
        return self.__dict__ | {
            "label": self.label,
            "waktu": self.waktu,
            "sudah_dibuka": self.sudah_dibuka,
        }


def email_menurut_pola(nim: str, nama: str) -> str:
    """Email kampus menurut pola setelan — cadangan kalau SIAKAD mengosongkannya.

    Polanya berbeda tiap perguruan tinggi, dan bisa berbeda pula antar-angkatan,
    jadi keduanya disetel di `siakad.yaml` alih-alih ditanam di kode:

        email_mahasiswa: "{nama_depan}.{nama_kedua}@student.kampus.ac.id"
        email_mahasiswa_angkatan:
          "26": "{nama_depan}.{nim}@student.kampus.ac.id"

    Kunci `email_mahasiswa_angkatan` dicocokkan dengan awalan NIM. Tanpa setelan
    apa pun, hasilnya kosong — menebak alamat orang lebih buruk daripada diam.
    """
    bagian = [satu for satu in nama.lower().split() if satu]
    pola = baca_pemetaan("SIAKAD_EMAIL_MAHASISWA_ANGKATAN").get(nim[:2]) or baca_pengaturan(
        "SIAKAD_EMAIL_MAHASISWA"
    )
    if not pola or not bagian:
        return ""
    try:
        return pola.format(
            nim=nim,
            nama_depan=bagian[0],
            nama_kedua=bagian[1] if len(bagian) > 1 else bagian[0],
        )
    except (KeyError, IndexError):
        return ""


@dataclass
class Mahasiswa:
    """Satu mahasiswa pada satu pertemuan — seperlunya untuk urusan kuliah."""

    nim: str
    nama: str
    email: str = ""
    kelompok_kelas: str = ""
    prodi: str = ""
    status: str = ""
    hadir: bool = False

    @classmethod
    def dari_baris(cls, baris: dict) -> "Mahasiswa":
        """Ambil yang perlu saja dari rekam mahasiswa; sisanya sengaja dilewat."""
        diri = baris.get("data_mahasiswa") or {}
        jurusan = diri.get("data_jurusan") or {}
        kelompok = (diri.get("KELOMPOK_KELAS") or baris.get("KD_SUB_KELAS") or "").strip()
        nim = str(baris.get("NIM") or diri.get("NIM") or "").strip()
        nama = (diri.get("NAMA") or "").strip()
        return cls(
            nim=nim,
            nama=nama,
            # email kampus datang dari SIAKAD; pola setelan hanya cadangan
            email=(diri.get("EMAIL") or "").strip() or email_menurut_pola(nim, nama),
            kelompok_kelas="" if kelompok in ("", "-") else kelompok,
            prodi=(jurusan.get("NM_JURUSAN") or "").strip() if isinstance(jurusan, dict) else "",
            # STATUS 'A' = aktif mengambil mata kuliah ini
            status=(baris.get("STATUS") or "").strip(),
            hadir=bool(baris.get("has_absensi")),
        )


class DaftarHadir(MenuSiakad):
    """Akses menu Daftar Hadir untuk satu sesi SIAKAD."""

    path_bawaan = PATH_DAFTAR_HADIR_BAWAAN
    kunci_path = "SIAKAD_PATH_DAFTAR_HADIR"

    def daftar_pertemuan(
        self, tahun_ajaran: str, tipe_semester: str, tanggal: str = "", pencarian: str = ""
    ) -> list[Pertemuan]:
        """Pertemuan satu periode, urut tanggal lalu jam.

        `tanggal` kosong berarti seluruh periode; diisi (YYYY-MM-DD) berarti satu
        hari saja. Menu ini memakai dua parameter periode yang berbeda bentuk:
        `tahun_ajaran`/`tipe_semester` untuk penyaringan, dan `tahun_akademik`
        berupa JSON yang wajib ada — dikosongkan, SIAKAD membalas HTTP 500.
        """
        akademik = json.dumps(
            {"tahun_ajaran": str(tahun_ajaran), "tipe_semester": str(tipe_semester)},
            separators=(",", ":"),
        )
        baris = self.cari_semua(
            "search",
            {
                "text_search": pencarian,
                "tanggal": tanggal,
                # dua field ini menyaring lagi di dalam periode; dikosongkan
                # supaya seluruh pertemuan periode itu terbawa
                "tipe_semester": "",
                "tahun_ajaran": "",
                "tahun_akademik": akademik,
            },
            keterangan="daftar hadir",
        )
        return sorted(
            (Pertemuan.dari_baris(satu) for satu in baris),
            key=lambda satu: (satu.tanggal, satu.jam_mulai),
        )

    def detail(self, pertemuan: Pertemuan) -> dict:
        """Balasan detail satu pertemuan apa adanya dari SIAKAD.

        Di dalamnya ada `list_mhs` (mahasiswa), `list_dosen`, topik pembahasan,
        dan nomor pertemuan. Dipakai langsung kalau yang dibutuhkan lebih dari
        yang dipetakan `Mahasiswa`.
        """
        jawaban = self.kirim("detail", pertemuan.sebagai_parameter())
        if jawaban.status_code != 200:
            raise SiakadError(f"Detail pertemuan {pertemuan.label} gagal (HTTP {jawaban.status_code})")
        return jawaban.json()

    def daftar_mahasiswa(self, pertemuan: Pertemuan) -> list[Mahasiswa]:
        """Mahasiswa yang terdaftar pada satu pertemuan, urut NIM."""
        isi = self.detail(pertemuan)
        return sorted(
            (Mahasiswa.dari_baris(satu) for satu in (isi.get("list_mhs") or [])),
            key=lambda satu: satu.nim,
        )

    def buka_kelas(self, pertemuan: Pertemuan, *, uji_coba: bool = False) -> dict:
        """Buka kelas satu pertemuan supaya mahasiswa bisa mulai mengabsen.

        Di SIAKAD ini tombol "Buka" yang hanya aktif pada hari pertemuannya, dan
        sekali dibuka tidak bisa ditutup lagi — karena itu `uji_coba` disediakan,
        dan pertemuan yang `sudah_dibuka` ditolak di sini alih-alih dikirim ulang.
        """
        if pertemuan.sudah_dibuka:
            return {
                "ok": False,
                "pertemuan": pertemuan.label,
                "pesan": f"Kelas sudah dibuka pada {pertemuan.jam_dibuka}",
            }

        muatan = {
            "dosen_id": pertemuan.dosen_id,
            "kd_mata_kuliah": pertemuan.kode_mk,
            "tahun_ajaran": pertemuan.tahun_ajaran,
            "tipe_semester": pertemuan.tipe_semester,
            "hari": pertemuan.hari,
            "jam_mulai": pertemuan.jam_mulai,
            "tgl_absensi": pertemuan.tanggal,
            "sesi": pertemuan.sesi,
        }
        if uji_coba:
            return {"ok": True, "uji_coba": True, "pertemuan": pertemuan.label, "muatan": muatan}

        jawaban = self.kirim("buka_kelas", muatan)
        if jawaban.status_code != 200:
            raise SiakadError(f"Membuka kelas {pertemuan.label} gagal (HTTP {jawaban.status_code})")
        try:
            isi = jawaban.json()
        except ValueError:
            raise SiakadError(f"Balasan SIAKAD untuk {pertemuan.label} bukan JSON")
        return {"ok": not isi.get("error"), "pertemuan": pertemuan.label, "pesan": isi.get("Message", "")}

    def simpan_pembahasan(
        self,
        pertemuan: Pertemuan,
        topik: str,
        deskripsi: str = "",
        *,
        kolom_pijar: str = "",
        berita_acara_ujian: str = "",
        uji_coba: bool = False,
    ) -> dict:
        """Tulis Topik dan Deskripsi Pembahasan satu pertemuan ke SIAKAD.

        Ini satu-satunya operasi paket ini yang **menulis** ke SIAKAD; selebihnya
        hanya membaca. Karena itu `uji_coba` disediakan: bernilai True, muatannya
        dikembalikan apa adanya tanpa dikirim, sehingga isian bisa diperiksa dulu
        sebelum benar-benar masuk.

        Isian lama akan tertimpa — SIAKAD tidak menyimpan riwayatnya.

        Nama field di sini huruf kecil, berbeda dari endpoint detail yang memakai
        huruf besar; itu memang perbedaan di sisi SIAKAD, bukan salah ketik.
        """
        muatan = {
            "dosen_id": pertemuan.dosen_id,
            "tahun_ajaran": pertemuan.tahun_ajaran,
            "tipe_semester": pertemuan.tipe_semester,
            "kd_mata_kuliah": pertemuan.kode_mk,
            "hari": pertemuan.hari,
            "jam_mulai": pertemuan.jam_mulai,
            "tgl_absensi": pertemuan.tanggal,
            "sesi": pertemuan.sesi,
            "topik_pembahasan": topik,
            "deskripsi_pembahasan": deskripsi,
            "kolom_pijar": kolom_pijar,
            "berita_acara_ujian": berita_acara_ujian,
        }
        if uji_coba:
            return {"ok": True, "uji_coba": True, "pertemuan": pertemuan.label, "muatan": muatan}

        jawaban = self.kirim("save_pembahasan", muatan)
        if jawaban.status_code != 200:
            raise SiakadError(
                f"Menyimpan pembahasan {pertemuan.label} gagal (HTTP {jawaban.status_code})"
            )
        try:
            isi = jawaban.json()
        except ValueError:
            raise SiakadError(f"Balasan SIAKAD untuk {pertemuan.label} bukan JSON")
        return {
            "ok": not isi.get("error"),
            "pertemuan": pertemuan.label,
            "pesan": isi.get("Message", ""),
        }

    def mahasiswa_kelas(
        self, tahun_ajaran: str, tipe_semester: str, kode_mk: str, kelompok_kelas: str = ""
    ) -> tuple[Pertemuan, list[Mahasiswa]]:
        """Mahasiswa satu mata kuliah, diambil dari pertemuan pertamanya.

        Daftar peserta sama untuk semua pertemuan kelas yang sama, jadi satu
        pertemuan saja sudah cukup — dan itu menghemat satu permintaan per
        pertemuan. `kelompok_kelas` memisahkan Kelas A dari Kelas B.
        """
        pertemuan = [
            satu
            for satu in self.daftar_pertemuan(tahun_ajaran, tipe_semester)
            if satu.kode_mk == kode_mk
            and (not kelompok_kelas or satu.kelompok_kelas == kelompok_kelas)
        ]
        if not pertemuan:
            kelas = f" {kelompok_kelas}" if kelompok_kelas else ""
            raise SiakadError(
                f"Tidak ada pertemuan {kode_mk}{kelas} pada periode {tahun_ajaran}/{tipe_semester}"
            )
        return pertemuan[0], self.daftar_mahasiswa(pertemuan[0])
