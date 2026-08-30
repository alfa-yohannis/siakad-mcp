#!/usr/bin/env python3
"""Contoh menempelkan REST API SIAKAD ke aplikasi FastAPI milik sendiri.

Rute paket ini dikumpulkan di `router`, jadi tidak harus dijalankan sebagai
server terpisah — bisa hidup berdampingan dengan rute Anda sendiri.

    pip install "siakad-mcp[api]"
    uvicorn examples.api_sendiri:app --port 8000

Lalu buka http://localhost:8000/docs — rute /siakad/... muncul bersama /versi.
"""

from __future__ import annotations

from fastapi import FastAPI

from siakad_mcp import __version__, atur_setelan
from siakad_mcp.api import router

# Kalau kampus Anda memakai instance lain, tetapkan sekali di sini alih-alih
# menyediakan siakad.yaml. Setelan dari kode mengalahkan environment dan berkas.
# atur_setelan(base_url="https://siakad.kampuslain.ac.id", kota="Bandung")

app = FastAPI(title="Aplikasi Saya", version="0.1.0")

# Prefix bebas; endpoint jadi /siakad/kelas, /siakad/berita-acara, dan seterusnya
app.include_router(router, prefix="/siakad", tags=["siakad"])


@app.get("/versi", summary="Rute milik aplikasi ini sendiri")
def versi() -> dict:
    return {"aplikasi": "0.1.0", "siakad_mcp": __version__}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
