#!/usr/bin/env bash
# Contoh memakai REST API SIAKAD dari baris perintah.
# Jalankan API-nya lebih dulu: ./siakad api
#
#   SIAKAD_USERNAME=... SIAKAD_PASSWORD=... siakad-mcp/examples/klien_api.sh

set -euo pipefail

API="${SIAKAD_API:-http://localhost:8000}"
PERIODE="\"tahun_ajaran\":\"2025\",\"tipe_semester\":\"2\""
AKUN="\"username\":\"$SIAKAD_USERNAME\",\"password\":\"$SIAKAD_PASSWORD\""

echo "== cek kredensial"
curl -s -X POST "$API/sesi" -H 'Content-Type: application/json' -d "{$AKUN}"

echo -e "\n\n== kelas yang diampu semester genap 2025/2026"
curl -s -X POST "$API/kelas" -H 'Content-Type: application/json' -d "{$AKUN,$PERIODE}" |
	python3 -c 'import json,sys; [print("  ", k["label"]) for k in json.load(sys.stdin)["data"]]'

echo -e "\n== topik pertemuan satu mata kuliah"
curl -s -X POST "$API/berita-acara" -H 'Content-Type: application/json' \
	-d "{$AKUN,$PERIODE,\"kode_mk\":\"IF30812\"}" |
	python3 -c '
import json, sys
hasil = json.load(sys.stdin)
print("  ", hasil["kelas"])
for topik in hasil["detail"]["rs_topik"][:5]:
    print("   ", topik["TGL_ABSENSI"], "-", topik["TOPIK_PEMBAHASAN"][:55])
'

echo -e "\n== unduh seluruh bukti ke folder BKD"
curl -s -X POST "$API/bukti/semua" -H 'Content-Type: application/json' \
	-d "{$AKUN,$PERIODE,\"tujuan\":\"bukti/pengajaran\"}" |
	python3 -c 'import json,sys; h=json.load(sys.stdin); print("  tujuan:", h["tujuan"]); [print("   ", b) for b in h["berkas"]]'
