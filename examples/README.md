# Contoh SIAKAD

| Berkas             | Isi                                                        |
|--------------------|-------------------------------------------------------------|
| `prompt_mcp.md`    | contoh prompt untuk asisten AI lewat MCP                    |
| `klien_api.sh`     | memakai REST API dari `curl`                                |

## Lewat CLI

```bash
./siakad bap --tahun 2025 --semester 2 --hanya-daftar
./siakad bap --tahun 2025 --semester 2 --tujuan bukti/pengajaran
```

## Lewat REST API

```bash
./siakad api                                    # terminal pertama
export SIAKAD_USERNAME=... SIAKAD_PASSWORD=...      # terminal kedua
examples/klien_api.sh
```

## Lewat MCP

> Ambilkan bukti pengajaran semester genap 2025/2026 dari SIAKAD — BAP dan
> daftar kehadiran untuk semua kelas — simpan ke folder `bukti/pengajaran`.

Prompt lain ada di [prompt_mcp.md](prompt_mcp.md).
