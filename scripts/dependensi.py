"""Pemeriksa dependensi: pasang paket yang belum ada saat pertama kali dijalankan.

Dipanggil di awal setiap titik masuk (CLI, REST API, MCP) supaya pemakai baru
tidak perlu tahu daftar paketnya. Pemasangan hanya dilakukan ke dalam virtualenv;
kalau skrip dijalankan dengan Python sistem, hanya diberi peringatan agar tidak
mengotori lingkungan global.

Matikan perilaku ini dengan menyetel BKD_TANPA_PASANG=1.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

# nama modul saat diimpor -> nama paket saat dipasang
PAKET_WAJIB = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "lxml": "lxml",
    "dotenv": "python-dotenv",
    "pydantic": "pydantic",
    "PIL": "pillow",
}

PAKET_TAMBAHAN = {
    "api": {"fastapi": "fastapi", "uvicorn": "uvicorn[standard]", "multipart": "python-multipart"},
    "mcp": {"mcp": "mcp"},
    "uji": {"pytest": "pytest"},
}


def sedang_di_virtualenv() -> bool:
    """True kalau Python yang berjalan berasal dari virtualenv, bukan Python sistem."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def paket_hilang(kebutuhan: dict[str, str]) -> dict[str, str]:
    """Saring kebutuhan, sisakan yang modulnya memang belum bisa diimpor."""
    return {
        modul: paket
        for modul, paket in kebutuhan.items()
        if importlib.util.find_spec(modul) is None
    }


def pasang(paket: list[str]) -> None:
    """Pasang paket ke interpreter yang sedang berjalan."""
    print(f"Memasang dependensi: {', '.join(paket)}", file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *paket])


def pastikan_dependensi(*tambahan: str) -> None:
    """Pastikan paket inti (dan kelompok tambahan yang diminta) tersedia.

    Contoh: pastikan_dependensi("api") untuk titik masuk REST API.
    """
    kebutuhan = dict(PAKET_WAJIB)
    for nama_kelompok in tambahan:
        kebutuhan.update(PAKET_TAMBAHAN.get(nama_kelompok, {}))

    hilang = paket_hilang(kebutuhan)
    if not hilang:
        return

    if os.environ.get("BKD_TANPA_PASANG"):
        raise SystemExit(f"Dependensi belum lengkap: {', '.join(sorted(hilang.values()))}")

    if not sedang_di_virtualenv():
        raise SystemExit(
            "Dependensi belum lengkap dan Python yang dipakai bukan virtualenv.\n"
            "Buat dulu: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
            f"Yang kurang: {', '.join(sorted(hilang.values()))}"
        )

    pasang(sorted(set(hilang.values())))
