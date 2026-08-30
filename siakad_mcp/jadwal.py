"""Jadwal Mengajar (/dosen/jadwal_mengajar).

Menjawab satu pertanyaan: pada satu periode, kelas apa saja yang diampu, hari
dan jam berapa, di ruang mana.

    daftar()  -> seluruh slot jadwal satu periode

Berbeda dari Berita Acara yang berangkat dari laporan pengajaran, menu ini
adalah jadwal yang disusun bagian akademik, sehingga ruang, jam selesai, dan SKS
ikut terbawa — tiga hal yang tidak ada pada daftar kelas Berita Acara.
"""

from __future__ import annotations

from dataclasses import dataclass

from siakad_mcp.menu import HARI_INDONESIA, MenuSiakad, jam_ringkas, nama_hari

PATH_JADWAL_BAWAAN = "/dosen/jadwal_mengajar"


@dataclass
class SlotJadwal:
    """Satu kelas pada jadwal mengajar: mata kuliah, waktu, dan ruangnya."""

    kode_mk: str
    nama_mk: str
    hari: str
    jam_mulai: str
    jam_selesai: str
    ruang: str = ""
    kelompok_kelas: str = ""
    prodi: str = ""
    sks: str = ""
    tahun_ajaran: str = ""
    tipe_semester: str = ""
    dosen_id: str = ""
    nama_periode: str = ""

    @classmethod
    def dari_baris(cls, baris: dict) -> "SlotJadwal":
        """Bangun dari satu baris hasil pencarian jadwal.

        Nama mata kuliah, ruang, dan nama periode datang sebagai objek bersarang;
        yang tidak terisi dibiarkan kosong supaya jadwal tetap bisa ditampilkan.
        """
        def bersarang(nama_objek: str, nama_field: str) -> str:
            isi = baris.get(nama_objek)
            return str(isi.get(nama_field) or "").strip() if isinstance(isi, dict) else ""

        kelompok = (baris.get("KELOMPOK_KELAS") or "").strip()
        nama_ta = bersarang("data_tahun_ajaran", "NM_TAHUN_AJARAN")
        nama_semester = bersarang("data_tipe_semester", "NM_TIPE_SEMESTER")
        return cls(
            kode_mk=(baris.get("KD_MATA_KULIAH") or "").strip(),
            nama_mk=bersarang("data_matkul", "NM_MATA_KULIAH"),
            hari=baris.get("HARI", ""),
            jam_mulai=baris.get("JAM_MULAI", ""),
            jam_selesai=baris.get("JAM_SELESAI", ""),
            ruang=bersarang("data_ruang", "NM_RUANG") or (baris.get("KD_RUANG") or "").strip(),
            kelompok_kelas="" if kelompok in ("", "-") else kelompok,
            prodi=baris.get("nm_jurusan") or baris.get("NM_JURUSAN") or "",
            sks=str(bersarang("data_matkul", "SKS")),
            tahun_ajaran=str(baris.get("TAHUN_AJARAN", "")),
            tipe_semester=str(baris.get("TIPE_SEMESTER", "")),
            dosen_id=baris.get("DOSEN_ID", ""),
            nama_periode=" ".join(bagian for bagian in (nama_ta, nama_semester) if bagian),
        )

    @property
    def label(self) -> str:
        """Mis. 'IF31613 - Arsitektur Perangkat Lunak (Kelas A)'."""
        kelas = f" ({self.kelompok_kelas})" if self.kelompok_kelas else ""
        return f"{self.kode_mk} - {self.nama_mk}{kelas}"

    @property
    def waktu(self) -> str:
        """Mis. 'Senin 08:25-11:05'."""
        return f"{nama_hari(self.hari)} {jam_ringkas(self.jam_mulai)}-{jam_ringkas(self.jam_selesai)}"

    def sebagai_dict(self) -> dict:
        """Bentuk datar siap dikirim REST API/MCP, lengkap dengan turunannya."""
        return self.__dict__ | {"label": self.label, "waktu": self.waktu, "hari_id": nama_hari(self.hari)}


class JadwalMengajar(MenuSiakad):
    """Akses menu Jadwal Mengajar untuk satu sesi SIAKAD."""

    path_bawaan = PATH_JADWAL_BAWAAN
    kunci_path = "SIAKAD_PATH_JADWAL"

    def daftar(
        self, tahun_ajaran: str, tipe_semester: str, prodi: str = "", pencarian: str = ""
    ) -> list[SlotJadwal]:
        """Jadwal satu periode, urut hari lalu jam.

        `tahun_ajaran` '2026' berarti 2026/2027; `tipe_semester` 1 ganjil,
        2 genap, 3 pendek — sama seperti menu lain.
        """
        baris = self.cari_semua(
            "search",
            {
                "text_search": pencarian,
                "tipe_semester": tipe_semester,
                "tahun_ajaran": tahun_ajaran,
                "prodi": prodi,
            },
            keterangan="jadwal mengajar",
        )
        # urutan hari mengikuti kalender, bukan abjad — Senin dulu, bukan Jumat
        urutan_hari = list(HARI_INDONESIA)
        return sorted(
            (SlotJadwal.dari_baris(satu) for satu in baris),
            key=lambda slot: (
                urutan_hari.index(slot.hari.upper()) if slot.hari.upper() in urutan_hari else len(urutan_hari),
                slot.jam_mulai,
            ),
        )
