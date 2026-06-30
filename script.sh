#!/usr/bin/env bash
# ============================================================
# script.sh — Execução do Simulador TR1
# ============================================================
# Uso:
#   bash script.sh servidor   → inicia o receptor
#   bash script.sh cliente    → inicia o transmissor
#   bash script.sh ambos      → inicia servidor em background e depois o cliente
# ============================================================

set -e

echo ""
echo "Iniciando modo: ${1:-ambos}"
echo ""

case "${1:-ambos}" in
    servidor)
        python main_servidor.py
        ;;
    cliente)
        python main_cliente.py
        ;;
    ambos)
        python main_servidor.py &
        SERVIDOR_PID=$!
        sleep 1
        python main_cliente.py
        kill "$SERVIDOR_PID" 2>/dev/null || true
        ;;
    *)
        echo "Uso: bash script.sh [servidor|cliente|ambos]"
        exit 1
        ;;
esac