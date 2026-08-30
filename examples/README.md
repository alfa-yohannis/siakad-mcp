# Contoh SIAKAD

Contoh siap jalan untuk ketiga mode. Semuanya butuh Python 3.10+ dan
Chrome/Chromium (untuk mencetak PDF).

| Berkas             | Mode     | Isi                                              |
|--------------------|----------|--------------------------------------------------|
| `prompt_mcp.md`    | MCP      | prompt siap salin untuk asisten AI               |
| `mcp_klien.json`   | MCP      | konfigurasi server untuk klien MCP selain Claude |
| `klien_api.sh`     | REST API | memakai REST API dari `curl`                     |
| `api_sendiri.py`   | REST API | menempel router ke aplikasi FastAPI sendiri      |
| `pustaka.py`       | Pustaka  | memakai `siakad_mcp` dari program Python sendiri |

## 1. MCP

```bash
pip install "siakad-mcp[mcp]"
claude mcp add siakad-mcp -- siakad-mcp
```

Lalu minta asisten Anda:

> Ambilkan bukti pengajaran semester genap 2025/2026 dari SIAKAD — BAP dan
> daftar kehadiran untuk semua kelas — simpan ke folder `bukti/pengajaran`.

Prompt lain di [prompt_mcp.md](prompt_mcp.md). Untuk klien MCP selain Claude
Code, pakai [mcp_klien.json](mcp_klien.json).

## 2. REST API

```bash
pip install "siakad-mcp[api]"
uvicorn siakad_mcp.api:app --port 8000              # terminal pertama

export SIAKAD_USERNAME=... SIAKAD_PASSWORD=...      # terminal kedua
examples/klien_api.sh
```

Dari klona repositori, servernya dihidupkan dengan `./siakad api`.

Untuk menempelkan rutenya ke aplikasi FastAPI Anda sendiri:

```bash
uvicorn examples.api_sendiri:app --port 8000
```

Buka <http://localhost:8000/docs> — rute `/siakad/...` muncul berdampingan
dengan rute milik aplikasi contoh itu sendiri.

## 3. Pustaka

```bash
pip install siakad-mcp
SIAKAD_USERNAME=... SIAKAD_PASSWORD=... python examples/pustaka.py
```

Mencetak daftar kelas yang diampu, topik pertemuan kelas pertama, lalu mengunduh
satu berkas BAP.

## Lewat CLI

```bash
./siakad bap --tahun 2025 --semester 2 --hanya-daftar
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran
```

Terpasang lewat pip, perintahnya `siakad-bap` dengan argumen yang sama.
