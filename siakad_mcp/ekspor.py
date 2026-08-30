"""Ekspor tabel sederhana ke .xlsx.

Dipakai perintah dan endpoint yang menghasilkan daftar — mis. peserta kuliah —
supaya hasilnya langsung bisa dibuka di Excel/LibreOffice tanpa disalin ulang.

openpyxl sengaja diimpor di dalam fungsi, bukan di kepala modul: ia ada di extra
`excel`, dan pemakai yang cukup dengan JSON tidak perlu memasangnya sama sekali.
"""

from __future__ import annotations

from pathlib import Path


def tulis_xlsx(judul_kolom: list[str], baris: list[list], tujuan: str | Path, *, nama_lembar: str = "Data") -> Path:
    """Tulis satu tabel ke berkas .xlsx, kembalikan path-nya.

    Lebar kolom disetel mengikuti isi terpanjangnya supaya berkasnya bisa dibaca
    tanpa perlu diatur lagi setelah dibuka.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as galat:
        raise RuntimeError(
            "Ekspor .xlsx butuh openpyxl. Pasang dulu: pip install \"siakad-mcp[excel]\""
        ) from galat

    buku = Workbook()
    lembar = buku.active
    # Excel menolak nama lembar lebih dari 31 karakter
    lembar.title = nama_lembar[:31]

    lembar.append(judul_kolom)
    for satu in baris:
        lembar.append(list(satu))
    for sel in lembar[1]:
        sel.font = Font(bold=True)

    for nomor, judul in enumerate(judul_kolom, start=1):
        terpanjang = max(
            [len(str(judul))] + [len(str(satu[nomor - 1])) for satu in baris if len(satu) >= nomor]
        )
        lembar.column_dimensions[lembar.cell(row=1, column=nomor).column_letter].width = min(terpanjang + 2, 60)

    tujuan = Path(tujuan)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    buku.save(tujuan)
    return tujuan
